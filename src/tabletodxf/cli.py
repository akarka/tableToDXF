"""Argüman ayrıştırma, config birleştirme, çıkış kodu.

Öncelik: CLI bayrağı > config dosyası > yerleşik varsayılan (F-001).
Çıkış kodları: `0` başarılı (uyarılar olabilir), `1` doğrulama/veri hatası,
`2` kullanım hatası.
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

from . import dxf_writer, geometry, ods_reader
from .errors import CONFIG_INVALID, FONT_NOT_FOUND, TableToDxfError, UsageError
from .metrics import FontMetrics
from .report import Report

DEFAULT_CONFIG_NAME = "tabletodxf.toml"

OVERFLOW_MODES = ("mtext", "marker", "full")

DEFAULTS = {
    "scale": 10.0,
    "overflow": "mtext",
    "text_style": "ONCU_TBL_TEXT",
    "font": "NotoSans-Regular.ttf",
    "layer_prefix": "ONCU_TBL",
    "dxf_version": "R2013",
}

EXIT_OK = 0
EXIT_DATA_ERROR = 1
EXIT_USAGE_ERROR = 2


@dataclass
class Settings:
    source: Path
    sheet: str
    range_text: str
    out: Path
    block: str
    scale: float
    overflow: str
    text_style: str
    font: str
    layer_prefix: str
    dxf_version: str
    report_path: Path
    verbose: bool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tabletodxf",
        description=(
            "LibreOffice Calc'ta biçimlendirilmiş bir .ods aralığını, kendi kendine "
            "yeten bir AutoCAD blok tanımına çevirir."
        ),
    )
    parser.add_argument("source", help="kaynak .ods dosyası")
    parser.add_argument("--sheet", required=True, help="sayfa adı")
    parser.add_argument("--range", dest="range_text", required=True, help="B3:C500 biçiminde")
    parser.add_argument("--out", required=True, help="çıktı DXF yolu")
    parser.add_argument("--block", required=True, help="blok adı (önek dahil)")

    # Varsayılanlar bilinçli olarak None: bayrağın açıkça verilip verilmediğini
    # ayırt edemezsek config dosyası yerleşik varsayılanı hiçbir zaman ezemez.
    parser.add_argument("--config", default=None, help=f"config yolu (varsayılan ./{DEFAULT_CONFIG_NAME})")
    parser.add_argument("--scale", type=float, default=None, help="1 cm kaç çizim birimi")
    parser.add_argument(
        "--overflow",
        choices=OVERFLOW_MODES,
        default=None,
        help="taşan hücre: mtext (düzenlenebilir kutu) | marker (###) | full (taşmasına izin ver)",
    )
    parser.add_argument("--text-style", dest="text_style", default=None)
    parser.add_argument("--font", default=None, help="ölçüm ve stil için TTF")
    parser.add_argument("--layer-prefix", dest="layer_prefix", default=None)
    parser.add_argument("--dxf-version", dest="dxf_version", default=None)
    parser.add_argument("--report", default=None, help="rapor dosyası yolu")
    parser.add_argument("--verbose", action="store_true", help="[TBL DEBUG] satırlarını da bas")
    return parser


def load_config(explicit: str | None, cwd: Path) -> dict:
    path = Path(explicit) if explicit else cwd / DEFAULT_CONFIG_NAME
    if not path.is_file():
        if explicit:
            raise UsageError(
                CONFIG_INVALID, op="load_config", reason="config file not found", config=str(path)
            )
        return {}
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise UsageError(
            CONFIG_INVALID,
            op="load_config",
            reason="config file is not valid TOML",
            config=str(path),
            detail=str(exc).split("\n")[0],
        ) from exc


def merge(args: argparse.Namespace, config: dict) -> Settings:
    text_section = config.get("text", {})
    layers_section = config.get("layers", {})

    def pick(flag_value, config_value, default_key: str):  # noqa: ANN001, ANN202
        if flag_value is not None:
            return flag_value
        if config_value is not None:
            return config_value
        return DEFAULTS[default_key]

    overflow = pick(args.overflow, config.get("overflow"), "overflow")
    if overflow not in OVERFLOW_MODES:
        raise UsageError(
            CONFIG_INVALID,
            op="load_config",
            reason=f"overflow must be one of {', '.join(OVERFLOW_MODES)}",
            overflow=overflow,
        )

    dxf_version = validate_dxf_version(
        str(pick(args.dxf_version, config.get("dxf_version"), "dxf_version"))
    )

    out = Path(args.out)
    report_path = Path(args.report) if args.report else out.with_suffix(".report.txt")

    return Settings(
        source=Path(args.source),
        sheet=args.sheet,
        range_text=args.range_text,
        out=out,
        block=args.block,
        scale=float(pick(args.scale, config.get("scale_cm_to_units"), "scale")),
        overflow=overflow,
        text_style=pick(args.text_style, text_section.get("style_name"), "text_style"),
        font=pick(args.font, text_section.get("font_file"), "font"),
        layer_prefix=pick(args.layer_prefix, layers_section.get("prefix"), "layer_prefix"),
        dxf_version=dxf_version,
        report_path=report_path,
        verbose=bool(args.verbose),
    )


def validate_dxf_version(name: str) -> str:
    """R2013 altını reddeder.

    AC-9 Kiril/CJK'yı şart koşuyor; bu da TTF tabanlı metin stili ve Unicode
    metin demek. Eski sürümler bunu taşımaz — R12 çıktısı sessizce bozuk glif
    üretirdi. Sürüm bir görünüm ayarı değil, doğruluk koşulu.
    """
    from ezdxf.lldxf import const

    requested = name.strip().upper()
    code = const.acad_release_to_dxf_version.get(requested, requested)
    if code not in const.versions_supported_by_new:
        raise UsageError(
            CONFIG_INVALID,
            op="load_config",
            reason="unknown DXF version",
            dxf_version=name,
            supported="R2013, R2018",
        )
    if code < const.acad_release_to_dxf_version["R2013"]:
        raise UsageError(
            CONFIG_INVALID,
            op="load_config",
            reason="DXF version must be R2013 or newer — older versions cannot carry TTF text styles",
            dxf_version=name,
        )
    return requested


def resolve_font(font: str) -> Path:
    """Verilen yol → paketle gelen `fonts/` → sistem font klasörleri.

    Kullanıcı çıplak bir dosya adı verebiliyor (`--font NotoSans-Regular.ttf`);
    ölçüm yapılamadan çıktı üretmek anlamsız olduğu için bulunamama ERROR'dur.
    """
    candidate = Path(font)
    if candidate.is_file():
        return candidate

    searched = [str(candidate)]
    for directory in _font_search_dirs():
        probe = directory / candidate.name
        searched.append(str(probe))
        if probe.is_file():
            return probe

    raise TableToDxfError(
        FONT_NOT_FOUND,
        op="load_font",
        reason="font file not found — pass --font with a full path to a .ttf",
        font=font,
        searched=len(searched),
    )


def _font_search_dirs() -> list[Path]:
    dirs = [Path(__file__).resolve().parent / "fonts", Path.cwd() / "fonts"]
    windir = Path(sys.prefix).anchor
    dirs.append(Path(windir) / "Windows" / "Fonts")
    dirs.append(Path.home() / "AppData" / "Local" / "Microsoft" / "Windows" / "Fonts")
    dirs.append(Path("/usr/share/fonts"))
    dirs.append(Path("/Library/Fonts"))
    return [d for d in dirs if d.is_dir()]


def run(settings: Settings, report: Report) -> None:
    """Üretim hattı. Hata durumunda hiçbir dosya yazılmadan istisna atar."""
    font_path = resolve_font(settings.font)
    metrics = FontMetrics.from_file(font_path)
    report.debug("load_font", "font loaded", font=font_path.name, upem=metrics.units_per_em)

    model = ods_reader.read(settings.source, settings.sheet, settings.range_text, report)
    report.info(
        "read_selection",
        "selection read",
        cell=model.source_ref,
        rows=model.n_rows,
        cols=model.n_cols,
    )

    drawing = geometry.build(
        model,
        metrics,
        report,
        scale_cm_to_units=settings.scale,
        overflow=settings.overflow,  # type: ignore[arg-type]
    )

    dxf_writer.write(
        drawing,
        settings.out,
        report,
        block_name=settings.block,
        layer_prefix=settings.layer_prefix,
        text_style=settings.text_style,
        font_file=font_path.name,
        dxf_version=settings.dxf_version,
    )
    report.write(settings.report_path)


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
        config = load_config(args.config, Path.cwd())
        settings = merge(args, config)
        run(settings, report)
    except UsageError as error:
        _print_error(error)
        return EXIT_USAGE_ERROR
    except TableToDxfError as error:
        _print_error(error)
        return EXIT_DATA_ERROR

    if report.warn_count:
        print(
            f"[TBL INFO]   op=finish reason=\"completed with warnings\" warnings={report.warn_count}"
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
