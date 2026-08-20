"""CLI — `api.convert()` üzerine ince bir sarmalayıcı (ADR-003).

Bu modül argüman ayrıştırır, `Job` ve `Config` üretir, `convert()` çağırır ve
çıkış kodunu döndürür. İş mantığı burada değildir.

Öncelik: `--set` > adanmış bayrak > config dosyası > yerleşik varsayılan (F-002).
Çıkış kodları: `0` başarılı (uyarılar olabilir), `1` doğrulama/veri hatası,
`2` kullanım hatası.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import get_args

from .api import Job, convert, resolve_font  # noqa: F401 — resolve_font geriye dönük dışa açık
from .config import (
    DEFAULT_CONFIG_NAME,
    DEFAULT_PROFILE_NAME,
    Config,
    DxfVersion,
    apply_overrides,
    find_config_file,
    load_config,
    load_profile,
)
from .errors import TableToDxfError, UsageError
from .report import Report

OVERFLOW_MODES = ("condense", "mtext", "marker", "full")
DXF_VERSIONS = get_args(DxfVersion)

EXIT_OK = 0
EXIT_DATA_ERROR = 1
EXIT_USAGE_ERROR = 2

# Adanmış bayrak → `bölüm.anahtar`. `--set` ile aynı yola indiği için ikisi
# arasında davranış farkı doğamaz (F-002 AC-6/AC-7).
FLAG_TO_SETTING: dict[str, str] = {
    "scale": "layout.scale_cm_to_units",
    "frame": "layout.frame_mm",
    "overflow": "overflow.mode",
    "text_style": "text.style_name",
    "font": "text.font_file",
    "layer_prefix": "layers.prefix",
    "dxf_version": "output.dxf_version",
    "bylayer_defaults": "output.bylayer_defaults",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tabletodxf",
        description=(
            "LibreOffice Calc'ta biçimlendirilmiş bir .ods aralığını, kendi kendine "
            "yeten bir AutoCAD blok tanımına çevirir."
        ),
        epilog=(
            "Kataloğdaki her ayara --set ile erişilebilir, ör. "
            "--set layers.prefix=PROJE --set background.enabled=false. "
            "Tam liste: DOCS/Features/F-002.md"
        ),
    )
    parser.add_argument("source", help="kaynak .ods dosyası")
    parser.add_argument("--sheet", required=True, help="sayfa adı")
    parser.add_argument("--range", dest="range_text", required=True, help="B3:C500 biçiminde")
    parser.add_argument("--out", required=True, help="çıktı DXF yolu")
    parser.add_argument("--block", required=True, help="blok adı (önek dahil)")

    # Varsayılanlar bilinçli olarak None: bayrağın açıkça verilip verilmediğini
    # ayırt edemezsek config dosyası yerleşik varsayılanı hiçbir zaman ezemez.
    config_source = parser.add_mutually_exclusive_group()
    config_source.add_argument(
        "--config", default=None, help=f"config yolu (varsayılan ./{DEFAULT_CONFIG_NAME})"
    )
    config_source.add_argument(
        "--profile",
        default=None,
        help=(
            "kayıtlı profil adı (UI'ın kaydettiği ayar seti); "
            f"'{DEFAULT_PROFILE_NAME}' varsayılan profildir. --config ile birlikte kullanılamaz"
        ),
    )
    parser.add_argument("--scale", type=float, default=None, help="1 cm kaç çizim birimi")
    parser.add_argument(
        "--frame",
        type=float,
        default=None,
        help="tablonun dış sınırındaki çerçeve kalınlığı, mm (0 = çerçeve yok)",
    )
    parser.add_argument(
        "--overflow",
        choices=OVERFLOW_MODES,
        default=None,
        help=(
            "taşan hücre: condense (hücreye sığacak şekilde yatay sıkıştır, varsayılan) "
            "| mtext (düzenlenebilir kutu) | marker (###) | full (taşmasına izin ver)"
        ),
    )
    parser.add_argument("--text-style", dest="text_style", default=None)
    parser.add_argument("--font", default=None, help="ölçüm ve stil için TTF")
    parser.add_argument("--layer-prefix", dest="layer_prefix", default=None)
    parser.add_argument(
        "--dxf-version",
        dest="dxf_version",
        choices=DXF_VERSIONS,
        default=None,
        help="R2013 veya R2018 — eskisi TTF metin stili taşımaz",
    )
    parser.add_argument(
        "--bylayer-defaults",
        dest="bylayer_defaults",
        action="store_true",
        default=None,
        help=(
            "tam siyah (0,0,0) kenarlık/metni katman rengine (BYLAYER) bırak — "
            "CTB/kalem tablosu uyumu için. Renkli hiçbir şeye dokunmaz. "
            "Kapatmak için --set output.bylayer_defaults=false"
        ),
    )
    parser.add_argument("--report", default=None, help="rapor dosyası yolu")
    parser.add_argument(
        "--set",
        dest="overrides",
        action="append",
        default=[],
        metavar="BÖLÜM.ANAHTAR=DEĞER",
        help="herhangi bir ayarı doğrudan ez; tekrarlanabilir",
    )
    parser.add_argument("--verbose", action="store_true", help="[TBL DEBUG] satırlarını da bas")
    return parser


def build_config(args: argparse.Namespace, cwd: Path | None = None) -> Config:
    """Config dosyası + adanmış bayraklar + `--set` → tek bir `Config`.

    Bayraklar `--set` ile aynı mekanizmadan geçirilir; böylece iki yol arasında
    dönüşüm ya da doğrulama farkı oluşamaz.
    """
    cwd = cwd or Path.cwd()
    if args.profile:
        config = load_profile(args.profile)
    elif args.config:
        config = load_config(args.config, required=True)
    else:
        config = load_config(find_config_file(cwd), required=False)

    flag_overrides: list[str] = []
    for attribute, setting in FLAG_TO_SETTING.items():
        value = getattr(args, attribute, None)
        if value is not None:
            flag_overrides.append(f"{setting}={_as_toml(value)}")

    # `--set` en sonda: en açık niyet o (F-002 AC-7).
    return apply_overrides(config, flag_overrides + list(args.overrides))


def _as_toml(value: object) -> str:
    r"""Bayrak değerini `--set`'in beklediği TOML skalerine çevirir.

    Metin, TOML **literal** dizesi (tek tırnak) olarak verilir: literal dizede
    kaçış dizisi yoktur, bu yüzden Windows yolları olduğu gibi geçer. Daha önce
    çift tırnaklı temel dize kullanılıyordu ve ters bölü kaçış sayıldığı için
    `--font C:\fonts\noto.ttf` sessizce `C:\x0conts…` oluyordu (`\f` geçerli bir
    TOML kaçışı); `\U` gibi geçersiz bir kaçış varsa da ayrıştırma düşüyor ve
    değer **tırnaklarıyla birlikte** metne kalıyordu.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        if "'" not in value and "\n" not in value:
            return f"'{value}'"
        # Kesme işareti ya da satır sonu taşıyan değer literal dizede
        # taşınamaz; temel dizeye düşülür ve kaçışlar elle uygulanır.
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'
    return str(value)


def build_job(args: argparse.Namespace) -> Job:
    return Job(
        source=Path(args.source),
        sheet=args.sheet,
        range_text=args.range_text,
        out=Path(args.out),
        block=args.block,
        report_path=Path(args.report) if args.report else None,
        verbose=bool(args.verbose),
    )


def _harden_console() -> None:
    """Konsol kodlaması Türkçe/Kiril karakteri basamıyorsa çalıştırma çökmesin.

    Rapor **dosyası** her zaman UTF-8; bozulabilecek tek yer konsoldur ve orada
    bir karakterin yerine `?` konması, üretimin `UnicodeEncodeError` ile
    yarıda kalmasından iyidir. Kodlama zorlanmaz — cp1254 gibi konsollar Türkçe
    karakterleri zaten doğru basar.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _harden_console()
    report = Report(verbose=args.verbose)

    try:
        config = build_config(args)
        convert(build_job(args), config, report)
    except UsageError as error:
        _print_error(error)
        return EXIT_USAGE_ERROR
    except TableToDxfError as error:
        _print_error(error)
        return EXIT_DATA_ERROR

    if report.warn_count:
        print(
            f'[TBL INFO]   op=finish reason="completed with warnings" '
            f"warnings={report.warn_count}"
        )
    return EXIT_OK


def _print_error(error: TableToDxfError) -> None:
    """Hata satırı stderr'e gider; rapor dosyası **yazılmaz** (AC-10).

    Kısmi çıktı üretilmediği gibi, kısmi rapor da bırakılmaz — yarım bir
    `.report.txt` bir sonraki çalıştırmada başarılı sanılabilir.
    """
    from .report import format_line

    line = format_line(
        "ERROR", error.op, error.reason, error.cell, code=error.code, **error.fields
    )
    print(line, file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
