"""Tipli ayar katmanı (F-002, ADR-003).

Bu modül **saf veridir**: `odfpy`, `ezdxf` ve `tkinter` görmez, I/O yapmaz,
log basmaz. Tek istisnası TOML okuma/yazma yardımcıları — onlar da dosya
yolunu dışarıdan alır.

`Config` kalıcı ayarları taşır (UI'ın düzenlediği, TOML'a yazılan).
Çalıştırmaya özgü girdiler `Job` içinde durur; ikisinin ömrü farklı.

**Her alanın varsayılanı bugünkü davranıştır** — `Config()` mevcut çıktıyı
birebir üretir (F-002 AC-1). Bu bir golden testle sabitlenmiştir.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import asdict, dataclass, field, fields, replace
from pathlib import Path
from typing import Any, Literal, get_args, get_origin, get_type_hints

from .errors import CONFIG_INVALID, UsageError

# Tipler `model`'den geliyor — ikisi de saf veri, tek tanım tek yerde kalsın.
from .model import BLACK, HAlign, Rgb, VAlign

OverflowMode = Literal["condense", "mtext", "marker", "full"]

# `ezdxf.new()`'in kabul ettiği R2013 ve üstü sürümlerin tamamı. Sürüm bir
# görünüm ayarı değil doğruluk koşulu: AC-9 Kiril/CJK istiyor, bu da TTF tabanlı
# metin stili demek ve R2013 altı bunu taşımaz.
#
# `Literal` olması kontrolü tip katmanına taşıyor. Daha önce bu denetim yalnızca
# `cli.py`'de duruyordu; UI ve kütüphane `convert()`'i doğrudan çağırdığı için
# onlarda hiç çalışmıyordu ve Çıktı sekmesine `R12` yazmak sessizce AC1009 bir
# dosya ürettiriyordu. Şimdi config dosyası, `--set`, adanmış bayrak ve UI formu
# aynı kapıdan geçiyor; hiçbiri atlanamıyor.
DxfVersion = Literal["R2013", "R2018"]

WHITE: Rgb = (255, 255, 255)

DEFAULT_CONFIG_NAME = "tabletodxf.toml"

# Profiller burada saklanır — proje klasöründen bağımsız, kullanıcı başına.
# `LOCALAPPDATA` (roaming değil) seçildi: profiller makineye özgüdür, ağ
# profili senkronizasyonuyla taşınması istenmez. "OncuCAD" klasörü bilinçli:
# araç ileride bir suite'e taşınacak (ADR-003); o suite'in diğer araçları da
# aynı kök altında kendi alt klasörlerini açabilir.
_APP_VENDOR = "OncuCAD"
_APP_NAME = "TableToDXF"
DEFAULT_PROFILE_NAME = "Varsayılan"
_PROFILE_FORBIDDEN_CHARS = frozenset('\\/:*?"<>|')


# ── Bölümler ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SourceConfig:
    """`.ods`'in söylemediği şeyler için varsayılanlar.

    Sayfa bir değeri veriyorsa **her zaman sayfa kazanır** (ADR-002); buradaki
    değerler yalnızca bilgi yokken devreye girer.
    """

    default_col_width_mm: float = 22.58
    default_row_height_mm: float = 4.52
    default_padding_mm: float = 0.97
    default_font_size_pt: float = 10.0
    default_text_color: Rgb = BLACK
    default_border_color: Rgb = BLACK
    # `"solid #000000"` gibi kalınlık taşımayan kenarlık. `0` = çizilmez.
    borderless_width_pt: float = 0.5
    default_v_align: VAlign = "bottom"
    # Açık hizalaması olmayan hücrede değer tipine göre karar (Calc davranışı).
    align_numeric: HAlign = "right"
    align_boolean: HAlign = "center"
    align_text: HAlign = "left"
    # `SRC_STALE` için yanında aranan kardeş dosyalar. Boş = kontrol kapalı.
    stale_check_suffixes: tuple[str, ...] = (".xlsx", ".xls", ".xlsm")

    def validate(self) -> None:
        _positive("source.default_col_width_mm", self.default_col_width_mm)
        _positive("source.default_row_height_mm", self.default_row_height_mm)
        _non_negative("source.default_padding_mm", self.default_padding_mm)
        _positive("source.default_font_size_pt", self.default_font_size_pt)
        _non_negative("source.borderless_width_pt", self.borderless_width_pt)


@dataclass(frozen=True)
class LayoutConfig:
    scale_cm_to_units: float = 10.0
    frame_mm: float = 0.35
    # Çok satırlı hücrede satır adımının em çarpanı.
    line_spacing: float = 1.0

    def validate(self) -> None:
        _positive("layout.scale_cm_to_units", self.scale_cm_to_units)
        _non_negative(
            "layout.frame_mm", self.frame_mm, hint="0 kullanarak çerçeveyi kapatın"
        )
        _positive("layout.line_spacing", self.line_spacing)


@dataclass(frozen=True)
class TextConfig:
    style_name: str = "ONCU_TBL_TEXT"
    font_file: str = "NotoSans-Regular.ttf"
    # Fontta `OS/2.sCapHeight` yoksa büyük harf yüksekliği oranı.
    fallback_cap_ratio: float = 0.70

    def validate(self) -> None:
        _non_empty("text.style_name", self.style_name)
        _non_empty("text.font_file", self.font_file)
        _in_range("text.fallback_cap_ratio", self.fallback_cap_ratio, 0.1, 1.0)


@dataclass(frozen=True)
class OverflowConfig:
    mode: OverflowMode = "condense"
    marker_char: str = "#"
    # `condense` modunda okunabilirlik tabanı.
    min_width_factor: float = 0.25

    def validate(self) -> None:
        if len(self.marker_char) != 1:
            raise _invalid(
                "overflow.marker_char",
                self.marker_char,
                "tek bir karakter olmalı",
            )
        _in_range("overflow.min_width_factor", self.min_width_factor, 0.01, 1.0)


@dataclass(frozen=True)
class BackgroundConfig:
    enabled: bool = True
    color: Rgb = WHITE


@dataclass(frozen=True)
class LayerConfig:
    prefix: str = "ONCU_TBL"
    grid_suffix: str = "_GRID"
    text_suffix: str = "_TEXT"
    fill_suffix: str = "_FILL"
    overflow_suffix: str = "_OVERFLOW"
    grid_color: int = 7
    text_color: int = 7
    fill_color: int = 7
    # Kırmızı: `###` içerik değil, teşhis çıktısıdır.
    overflow_color: int = 1

    def names(self) -> dict[str, str]:
        return {
            "grid": f"{self.prefix}{self.grid_suffix}",
            "text": f"{self.prefix}{self.text_suffix}",
            "fill": f"{self.prefix}{self.fill_suffix}",
            "overflow": f"{self.prefix}{self.overflow_suffix}",
        }

    def colors(self) -> dict[str, int]:
        return {
            "grid": self.grid_color,
            "text": self.text_color,
            "fill": self.fill_color,
            "overflow": self.overflow_color,
        }

    def validate(self) -> None:
        for name, value in (
            ("grid_color", self.grid_color),
            ("text_color", self.text_color),
            ("fill_color", self.fill_color),
            ("overflow_color", self.overflow_color),
        ):
            _in_range(f"layers.{name}", value, 1, 255)

        produced = self.names()
        if len(set(produced.values())) != len(produced):
            raise _invalid(
                "layers",
                ", ".join(sorted(produced.values())),
                "katman adları birbirinden farklı olmalı — aynı ada düşen iki katman "
                "birbirinin içeriğini gizler",
            )


@dataclass(frozen=True)
class OutputConfig:
    dxf_version: DxfVersion = "R2013"
    # Blok tanımının yanına model uzayına bir INSERT konsun mu. Kapatılırsa
    # dosya doğrudan açıldığında boş görünür (tanım durur).
    insert_block_reference: bool = True
    block_base_point: tuple[float, float] = (0.0, 0.0)
    write_report: bool = True
    # ADR-002'ye bilinçli bir istisna (kullanıcı kararı, 2026-08-14): kenarlık
    # ve metin rengi normalde varlık üzerinde (true_color) taşınır, çünkü
    # hücre başına değişir. Ama en sık görülen durum — sıradan siyah kenarlık,
    # otomatik/varsayılan siyah metin — hiçbir bilgi taşımaz; ofisin CTB/kalem
    # tablosu ise ACI/BYLAYER'a göre çalışır ve true-color varlıkları çoğu
    # zaman görmezden gelir. Açıkken, rengi **tam siyah (0,0,0)** olan
    # varlıklar true_color almaz, katmanın kendi rengine (BYLAYER) düşer.
    # Gerçek bir vurgu rengi (kırmızı kenarlık, renkli başlık metni) olan
    # hiçbir şeye dokunulmaz. Kalınlık bu kararın dışında — polyline global
    # width'i zaten gerçek geometri, katman `lineweight`'i burada anlamsız.
    bylayer_defaults: bool = False


@dataclass(frozen=True)
class Config:
    source: SourceConfig = field(default_factory=SourceConfig)
    layout: LayoutConfig = field(default_factory=LayoutConfig)
    text: TextConfig = field(default_factory=TextConfig)
    overflow: OverflowConfig = field(default_factory=OverflowConfig)
    background: BackgroundConfig = field(default_factory=BackgroundConfig)
    layers: LayerConfig = field(default_factory=LayerConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    def validate(self) -> None:
        """Tüm bölümleri doğrular. Hata → hiçbir dosya yazılmadan durulur."""
        for section in fields(self):
            value = getattr(self, section.name)
            validator = getattr(value, "validate", None)
            if validator is not None:
                validator()


# ── Doğrulama yardımcıları ──────────────────────────────────────────────────


def _invalid(key: str, value: object, reason: str) -> UsageError:
    return UsageError(
        CONFIG_INVALID, op="load_config", reason=reason, setting=key, value=value
    )


def _positive(key: str, value: float) -> None:
    if value <= 0:
        raise _invalid(key, value, "sıfırdan büyük olmalı")


def _non_negative(key: str, value: float, *, hint: str = "") -> None:
    if value < 0:
        reason = "negatif olamaz" + (f" — {hint}" if hint else "")
        raise _invalid(key, value, reason)


def _non_empty(key: str, value: str) -> None:
    if not value.strip():
        raise _invalid(key, value, "boş olamaz")


def _in_range(key: str, value: float, low: float, high: float) -> None:
    if not (low <= value <= high):
        raise _invalid(key, value, f"{low} ile {high} arasında olmalı")


# ── Sözlük → Config (TOML yükleme) ──────────────────────────────────────────


def _parse_color(value: object, key: str) -> Rgb:
    """`"#rrggbb"` ya da `[r, g, b]`."""
    if isinstance(value, str):
        text = value.strip().lstrip("#")
        if len(text) == 6:
            try:
                return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
            except ValueError:
                pass
        raise _invalid(key, value, "renk '#rrggbb' biçiminde olmalı")
    if isinstance(value, (list, tuple)) and len(value) == 3:
        channels = []
        for channel in value:
            if not isinstance(channel, int) or isinstance(channel, bool):
                raise _invalid(key, value, "renk kanalları tam sayı olmalı")
            if not 0 <= channel <= 255:
                raise _invalid(key, value, "renk kanalları 0–255 arasında olmalı")
            channels.append(channel)
        return (channels[0], channels[1], channels[2])
    raise _invalid(key, value, "renk '#rrggbb' ya da [r, g, b] olmalı")


def _coerce(value: object, hint: Any, key: str) -> Any:  # noqa: ANN401
    """TOML'dan gelen ham değeri alan tipine çevirir.

    Tip uymuyorsa **hata** atar; sessiz dönüşüm yok. `frame_mm = "kalın"`
    çalışma anında değil, burada yakalanır (AC-4).
    """
    origin = get_origin(hint)

    if origin is Literal:
        allowed = get_args(hint)
        if value not in allowed:
            raise _invalid(key, value, f"şunlardan biri olmalı: {', '.join(map(str, allowed))}")
        return value

    if hint is bool:
        if not isinstance(value, bool):
            raise _invalid(key, value, "true ya da false olmalı")
        return value

    if hint is int:
        # `bool` Python'da `int` alt tipi; ayarda 1/0 yerine true/false yazılmasını
        # sessizce kabul etmek istemiyoruz.
        if isinstance(value, bool) or not isinstance(value, int):
            raise _invalid(key, value, "tam sayı olmalı")
        return value

    if hint is float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise _invalid(key, value, "sayı olmalı")
        return float(value)

    if hint is str:
        if not isinstance(value, str):
            raise _invalid(key, value, "metin olmalı")
        return value

    if hint == Rgb:  # tuple[int, int, int]
        return _parse_color(value, key)

    if hint == tuple[float, float]:
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise _invalid(key, value, "iki sayıdan oluşan bir liste olmalı")
        return (float(value[0]), float(value[1]))

    if hint == tuple[str, ...]:
        if not isinstance(value, (list, tuple)):
            raise _invalid(key, value, "metin listesi olmalı")
        for item in value:
            if not isinstance(item, str):
                raise _invalid(key, value, "metin listesi olmalı")
        return tuple(value)

    raise _invalid(key, value, f"desteklenmeyen ayar tipi: {hint!r}")


def _section_from_dict(section_type: type, data: dict, prefix: str):  # noqa: ANN202
    if not isinstance(data, dict):
        raise _invalid(prefix, data, "bir bölüm (tablo) olmalı")

    hints = get_type_hints(section_type)
    known = {f.name for f in fields(section_type)}

    unknown = set(data) - known
    if unknown:
        raise _invalid(
            f"{prefix}.{sorted(unknown)[0]}",
            "",
            f"tanınmayan ayar; geçerli anahtarlar: {', '.join(sorted(known))}",
        )

    values = {
        name: _coerce(raw, hints[name], f"{prefix}.{name}")
        for name, raw in data.items()
    }
    return section_type(**values)


def config_from_dict(data: dict) -> Config:
    """Sözlükten `Config`. Tanınmayan bölüm/anahtar **hata**dır (AC-3).

    Sessizce yok saymak, kullanıcının ayarının neden uygulanmadığını fark
    etmemesine yol açar — bir yazım hatası saatlerce yanlış çıktı üretebilir.
    """
    if not isinstance(data, dict):
        raise _invalid("config", data, "config bir tablo olmalı")

    section_types = {f.name: f.type for f in fields(Config)}
    resolved = get_type_hints(Config)

    unknown = set(data) - set(section_types)
    if unknown:
        raise _invalid(
            sorted(unknown)[0],
            "",
            f"tanınmayan bölüm; geçerli bölümler: {', '.join(sorted(section_types))}",
        )

    sections = {
        name: _section_from_dict(resolved[name], raw, name)
        for name, raw in data.items()
    }
    config = Config(**sections)
    config.validate()
    return config


# ── Config → sözlük (kaydetme) ──────────────────────────────────────────────


def _to_toml_value(value: object) -> object:
    if isinstance(value, tuple) and len(value) == 3 and all(
        isinstance(channel, int) for channel in value
    ):
        return "#{:02x}{:02x}{:02x}".format(*value)
    if isinstance(value, tuple):
        return list(value)
    return value


def config_to_dict(config: Config) -> dict:
    """`Config` → TOML'a yazılabilir sözlük. Round-trip kayıpsızdır (AC-10)."""
    raw = asdict(config)
    return {
        section: {key: _to_toml_value(value) for key, value in values.items()}
        for section, values in raw.items()
    }


# ── Dosya yardımcıları ──────────────────────────────────────────────────────


def load_config(path: str | Path | None, *, required: bool = True) -> Config:
    """TOML dosyasından `Config`. Yol `None` ise yerleşik varsayılanlar.

    `required=False` ile dosya yoksa sessizce varsayılanlar döner — `--config`
    verilmediğinde `./tabletodxf.toml` araması bu şekilde yapılır.
    """
    if path is None:
        return Config()

    config_path = Path(path)
    if not config_path.is_file():
        if required:
            raise _invalid(str(config_path), "", "config dosyası bulunamadı")
        return Config()

    try:
        with config_path.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise UsageError(
            CONFIG_INVALID,
            op="load_config",
            reason="config dosyası geçerli TOML değil",
            config=str(config_path),
            detail=str(exc).split("\n")[0],
        ) from exc

    return config_from_dict(data)


def save_config(config: Config, path: str | Path) -> Path:
    """`Config`'i TOML olarak yazar. UI'ın kaydetme biçimi budur."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_render_toml(config_to_dict(config)), encoding="utf-8")
    return target


def _render_toml(data: dict) -> str:
    """Küçük bir TOML yazıcı.

    `tomllib` yalnızca okur; yazmak için `tomli-w` gerekirdi. Şema bize ait ve
    dar (yalnızca str/int/float/bool/liste), bu yüzden yeni bir bağımlılık
    eklemek yerine burada üretiliyor — ADR-004'teki paket boyutu kaygısıyla da
    tutarlı.
    """
    lines: list[str] = []
    for section, values in data.items():
        lines.append(f"[{section}]")
        for key, value in values.items():
            lines.append(f"{key} = {_render_toml_value(value)}")
        lines.append("")
    return "\n".join(lines)


def _render_toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, list):
        return "[" + ", ".join(_render_toml_value(item) for item in value) + "]"
    return repr(value)


# ── CLI / UI üzerine yazma ──────────────────────────────────────────────────


def apply_overrides(config: Config, overrides: list[str]) -> Config:
    """`["layers.prefix=PROJE", …]` biçimindeki üzerine yazmaları uygular (AC-5).

    Değerler TOML değeri olarak ayrıştırılır; böylece `--set` ile dosyadaki
    yazım birebir aynı olur (`true`, `0.4`, `"#f5f5f5"` hepsi çalışır).
    """
    if not overrides:
        return config

    merged: dict[str, dict] = {}
    for override in overrides:
        key, separator, raw = override.partition("=")
        if not separator:
            raise _invalid(override, "", "biçim: bölüm.anahtar=değer")
        section, dot, name = key.strip().partition(".")
        if not dot:
            raise _invalid(key, "", "biçim: bölüm.anahtar=değer")
        merged.setdefault(section.strip(), {})[name.strip()] = _parse_scalar(raw.strip(), key)

    updated = config
    section_types = get_type_hints(Config)
    known_sections = {f.name for f in fields(Config)}

    for section, values in merged.items():
        if section not in known_sections:
            raise _invalid(
                section,
                "",
                f"tanınmayan bölüm; geçerli bölümler: {', '.join(sorted(known_sections))}",
            )
        current = getattr(updated, section)
        hints = get_type_hints(section_types[section])
        known = {f.name for f in fields(section_types[section])}
        changes = {}
        for name, raw in values.items():
            if name not in known:
                raise _invalid(
                    f"{section}.{name}",
                    "",
                    f"tanınmayan ayar; geçerli anahtarlar: {', '.join(sorted(known))}",
                )
            changes[name] = _coerce(raw, hints[name], f"{section}.{name}")
        updated = replace(updated, **{section: replace(current, **changes)})

    updated.validate()
    return updated


def _parse_scalar(text: str, key: str) -> object:
    """`--set` değerini TOML skaleri olarak okur; olmazsa düz metin sayar.

    `#f5f5f5` gibi tırnaksız değerler TOML'da yorum başlatır, bu yüzden
    ayrıştırma başarısız olduğunda metne düşülür — kullanıcı `--set
    background.color=#f5f5f5` yazabilsin diye.
    """
    try:
        return tomllib.loads(f"value = {text}")["value"]
    except (tomllib.TOMLDecodeError, KeyError):
        return text


def find_config_file(cwd: Path) -> Path | None:
    """Çalışma dizinindeki varsayılan config dosyası, varsa."""
    candidate = cwd / DEFAULT_CONFIG_NAME
    return candidate if candidate.is_file() else None


# ── Profil yönetimi ──────────────────────────────────────────────────────────
#
# Ofiste birden çok tablo tipi (mahal listesi, çizim listesi, metraj) farklı
# ayar ister. Her profil, `profiles_dir()` altında kendi adıyla bir `.toml`
# dosyasıdır — `Config`'in kendisiyle aynı serileştirme, tek fark konumu.
# UI'ın "profil seç / kaydet / farklı kaydet / sil" akışı doğrudan bunlara
# bağlanır; CLI'da `--profile <ad>`, `--config <yol>`'un bir kısayolu gibi
# çalışır (F-002 Open Questions → Ayar profilleri, 2026-08-13).


def app_data_dir() -> Path:
    """Kullanıcı başına, makineye özgü veri kökü.

    Windows'ta `%LOCALAPPDATA%\\OncuCAD\\TableToDXF`. `LOCALAPPDATA`
    tanımsızsa (Windows dışı geliştirme/test ortamı) taşınabilir bir yedeğe
    düşülür; üretim hedefi yalnızca Windows'tur (F-001).
    """
    base = os.environ.get("LOCALAPPDATA")
    root = Path(base) if base else Path.home() / ".local" / "share"
    return root / _APP_VENDOR / _APP_NAME


def profiles_dir() -> Path:
    return app_data_dir() / "profiles"


def _sanitize_profile_name(name: str) -> str:
    """Profil adını doğrular; dosya adı olarak da kullanılır.

    Görünen ad ile dosya adı **kasıtlı olarak aynı** — ayrı bir eşleme
    tablosu, ismi değiştirilmiş ama dosyası yeniden adlandırılmamış bir
    profille sonuçlanabilirdi. Türkçe karakter ve boşluk NTFS'te sorunsuz;
    yasaklanan yalnızca Windows'un dosya adında izin vermediği karakterler.
    """
    trimmed = name.strip()
    if not trimmed:
        raise _invalid("profile", name, "profil adı boş olamaz")
    bad = _PROFILE_FORBIDDEN_CHARS & set(trimmed)
    if bad:
        raise _invalid(
            "profile",
            name,
            'profil adı şu karakterleri içeremez: \\ / : * ? " < > |',
        )
    return trimmed


def _profile_path(name: str) -> Path:
    return profiles_dir() / f"{_sanitize_profile_name(name)}.toml"


def list_profiles() -> list[str]:
    """Var olan profil adları, alfabetik. Klasör yoksa boş liste."""
    directory = profiles_dir()
    if not directory.is_dir():
        return []
    return sorted(path.stem for path in directory.glob("*.toml"))


def load_profile(name: str) -> Config:
    path = _profile_path(name)
    if not path.is_file():
        raise _invalid(name, "", "profil bulunamadı")
    return load_config(path)


def save_profile(name: str, config: Config) -> Path:
    """Profili kaydeder; aynı adlı profil sessizce üzerine yazılır."""
    return save_config(config, _profile_path(name))


def delete_profile(name: str) -> None:
    """Profili siler. Yoksa sessizce geçer — silme işleminin sonucu aynı."""
    path = _profile_path(name)
    if path.is_file():
        path.unlink()


def rename_profile(old_name: str, new_name: str) -> Path:
    old_path = _profile_path(old_name)
    new_path = _profile_path(new_name)
    if not old_path.is_file():
        raise _invalid(old_name, "", "profil bulunamadı")
    if new_path.exists():
        raise _invalid(new_name, "", "bu adda bir profil zaten var")
    old_path.rename(new_path)
    return new_path


def ensure_default_profile() -> Path:
    """İlk çalıştırmada `Varsayılan` profilini yerleşik değerlerle oluşturur.

    Zaten varsa dokunmaz — kullanıcının `Varsayılan`ı düzenlemiş olma ihtimali
    her zaman var; UI açılışta bunu çağırıp listenin hiçbir zaman boş
    olmayacağından emin olur.
    """
    path = _profile_path(DEFAULT_PROFILE_NAME)
    if not path.is_file():
        save_config(Config(), path)
    return path
