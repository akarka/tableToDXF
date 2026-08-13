"""Ayar katmanı — yükleme, doğrulama, üzerine yazma, round-trip (F-002)."""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import tomllib
from dataclasses import fields
from pathlib import Path

import pytest

from tabletodxf.config import (
    Config,
    LayerConfig,
    apply_overrides,
    config_from_dict,
    config_to_dict,
    find_config_file,
    load_config,
    save_config,
)
from tabletodxf.errors import CONFIG_INVALID, UsageError


# ── Varsayılanlar bugünkü davranış (AC-1) ───────────────────────────────────


def test_defaults_match_todays_behaviour() -> None:
    """Bu değerler F-001'in ürettiği çıktıyı tanımlıyor; değişirse çıktı kayar."""
    config = Config()

    assert config.layout.scale_cm_to_units == 10.0
    assert config.layout.frame_mm == 0.35
    assert config.layout.line_spacing == 1.0

    assert config.overflow.mode == "condense"
    assert config.overflow.marker_char == "#"
    assert config.overflow.min_width_factor == 0.25

    assert config.background.enabled is True
    assert config.background.color == (255, 255, 255)

    assert config.source.default_col_width_mm == 22.58
    assert config.source.default_row_height_mm == 4.52
    assert config.source.default_padding_mm == 0.97
    assert config.source.default_font_size_pt == 10.0
    assert config.source.default_v_align == "bottom"
    assert config.source.align_numeric == "right"

    assert config.text.style_name == "ONCU_TBL_TEXT"
    assert config.text.font_file == "NotoSans-Regular.ttf"
    assert config.text.fallback_cap_ratio == 0.70

    assert config.layers.prefix == "ONCU_TBL"
    assert config.layers.overflow_color == 1

    assert config.output.dxf_version == "R2013"
    assert config.output.insert_block_reference is True
    assert config.output.write_report is True


def test_default_config_validates() -> None:
    Config().validate()


def test_example_toml_documents_the_real_defaults() -> None:
    """`tabletodxf.example.toml` her ayarı varsayılan değeriyle listeliyor.

    Örnek dosya "bunu olduğu gibi kullanmak hiçbir şeyi değiştirmez" diyor;
    bu test o sözü tutuyor. Bir varsayılan değişip örnek güncellenmezse
    kullanıcı dosyayı kopyaladığı anda davranış sessizce sapardı.
    """
    example = Path(__file__).resolve().parents[2] / "tabletodxf.example.toml"
    assert load_config(example) == Config()

    documented = tomllib.loads(example.read_text(encoding="utf-8"))
    for section in fields(Config):
        assert section.name in documented, f"örnekte eksik bölüm: {section.name}"
        keys = {f.name for f in fields(getattr(Config(), section.name))}
        missing = keys - set(documented[section.name])
        assert not missing, f"örnekte eksik ayar: {section.name}.{sorted(missing)}"


def test_layer_names_compose_from_prefix_and_suffixes() -> None:
    assert LayerConfig().names() == {
        "grid": "ONCU_TBL_GRID",
        "text": "ONCU_TBL_TEXT",
        "fill": "ONCU_TBL_FILL",
        "overflow": "ONCU_TBL_OVERFLOW",
    }
    assert LayerConfig(prefix="X").names()["grid"] == "X_GRID"


# ── Katman yalıtımı (AC-9) ──────────────────────────────────────────────────


def test_config_module_declares_no_heavy_dependencies() -> None:
    """`config.py` kendi başına `odfpy`/`ezdxf`/`tkinter`'a bağlı olmamalı (AC-9).

    Statik kontrol, çünkü çalışma zamanı ölçümü yanıltıcı: `tabletodxf.config`
    içe aktarmak önce paketin `__init__`'ini çalıştırır, o da hattın tamamını
    (ve dolayısıyla `ezdxf`'i) çeker. Buradaki iddia paketin değil, **dosyanın**
    bağımsızlığı — suite'e kopyalandığında tek başına çalışabilmesi.
    """
    source = (
        Path(__file__).resolve().parents[2] / "src" / "tabletodxf" / "config.py"
    ).read_text(encoding="utf-8")

    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])

    assert not imported & {"odf", "odfpy", "ezdxf", "tkinter", "numpy", "fontTools"}


def test_importing_config_does_not_pull_the_ui_or_cli() -> None:
    """Ayrı süreçte: ayar katmanı arayüz ya da CLI'ı zorunlu kılmıyor."""
    probe = (
        "import sys, tabletodxf.config;"
        "print(int('tkinter' in sys.modules), int('tabletodxf.cli' in sys.modules))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)},
        check=True,
    )
    assert completed.stdout.split() == ["0", "0"]


# ── TOML yükleme ────────────────────────────────────────────────────────────


def test_sections_load_from_toml(tmp_path: Path) -> None:
    path = tmp_path / "c.toml"
    path.write_text(
        """
[layout]
scale_cm_to_units = 25.0
frame_mm = 0.0

[background]
enabled = false
color = "#102030"

[source]
stale_check_suffixes = [".xlsx"]
align_numeric = "center"
""",
        encoding="utf-8",
    )
    config = load_config(path)

    assert config.layout.scale_cm_to_units == 25.0
    assert config.layout.frame_mm == 0.0
    assert config.background.enabled is False
    assert config.background.color == (16, 32, 48)
    assert config.source.stale_check_suffixes == (".xlsx",)
    assert config.source.align_numeric == "center"
    # Verilmeyen bölümler varsayılanda kalır.
    assert config.text == Config().text


def test_missing_path_returns_defaults() -> None:
    assert load_config(None) == Config()


def test_missing_file_is_an_error_when_required(tmp_path: Path) -> None:
    with pytest.raises(UsageError):
        load_config(tmp_path / "yok.toml", required=True)


def test_missing_file_is_tolerated_when_optional(tmp_path: Path) -> None:
    assert load_config(tmp_path / "yok.toml", required=False) == Config()


def test_find_config_file(tmp_path: Path) -> None:
    assert find_config_file(tmp_path) is None
    (tmp_path / "tabletodxf.toml").write_text("", encoding="utf-8")
    assert find_config_file(tmp_path) is not None


# ── Tanınmayan anahtarlar (AC-3) ────────────────────────────────────────────


def test_unknown_section_is_rejected() -> None:
    """Sessizce yok saymak, ayarın uygulanmadığını fark ettirmez."""
    with pytest.raises(UsageError) as excinfo:
        config_from_dict({"olmayan": {"x": 1}})
    assert excinfo.value.code == CONFIG_INVALID
    assert "olmayan" in str(excinfo.value.fields["setting"])


def test_unknown_key_is_rejected() -> None:
    with pytest.raises(UsageError) as excinfo:
        config_from_dict({"layout": {"scale_cm_to_unit": 10}})  # yazım hatası
    assert excinfo.value.code == CONFIG_INVALID
    assert "scale_cm_to_unit" in str(excinfo.value.fields["setting"])


# ── Tip ve aralık doğrulama (AC-4) ──────────────────────────────────────────


@pytest.mark.parametrize(
    "data",
    [
        {"layout": {"frame_mm": "kalın"}},
        {"layout": {"scale_cm_to_units": True}},
        {"background": {"enabled": "evet"}},
        {"background": {"color": "mavi"}},
        {"background": {"color": [1, 2]}},
        {"layers": {"grid_color": 1.5}},
        {"overflow": {"mode": "kırp"}},
        {"source": {"default_v_align": "ortala"}},
        {"source": {"stale_check_suffixes": "xlsx"}},
        {"text": {"style_name": 5}},
    ],
)
def test_type_errors_are_rejected(data: dict) -> None:
    with pytest.raises(UsageError) as excinfo:
        config_from_dict(data)
    assert excinfo.value.code == CONFIG_INVALID


@pytest.mark.parametrize(
    "data",
    [
        {"layout": {"frame_mm": -1.0}},
        {"layout": {"scale_cm_to_units": 0.0}},
        {"overflow": {"min_width_factor": -0.5}},
        {"overflow": {"min_width_factor": 2.0}},
        {"overflow": {"marker_char": "##"}},
        {"text": {"fallback_cap_ratio": 5.0}},
        {"text": {"style_name": "   "}},
        {"layers": {"grid_color": 0}},
        {"layers": {"grid_color": 300}},
        {"source": {"default_col_width_mm": 0.0}},
    ],
)
def test_range_errors_are_rejected(data: dict) -> None:
    with pytest.raises(UsageError) as excinfo:
        config_from_dict(data)
    assert excinfo.value.code == CONFIG_INVALID


def test_colliding_layer_names_are_rejected() -> None:
    """Aynı ada düşen iki katman birbirinin içeriğini gizler."""
    with pytest.raises(UsageError):
        config_from_dict({"layers": {"grid_suffix": "_X", "text_suffix": "_X"}})


# ── Round-trip (AC-10) ──────────────────────────────────────────────────────


def test_roundtrip_through_dict_is_lossless() -> None:
    config = Config()
    assert config_from_dict(config_to_dict(config)) == config


def test_roundtrip_through_file_is_lossless(tmp_path: Path) -> None:
    config = apply_overrides(
        Config(),
        [
            "layers.prefix=PROJE",
            "background.color=#123456",
            "background.enabled=false",
            "layout.frame_mm=1.25",
            "source.stale_check_suffixes=[]",
            "output.block_base_point=[1.0, 2.0]",
        ],
    )
    path = save_config(config, tmp_path / "out.toml")
    assert load_config(path) == config


def test_saved_file_covers_every_section() -> None:
    rendered = config_to_dict(Config())
    assert set(rendered) == {f.name for f in fields(Config)}


# ── Üzerine yazma (AC-5) ────────────────────────────────────────────────────


def test_overrides_reach_every_section() -> None:
    config = apply_overrides(
        Config(),
        [
            "source.default_padding_mm=2.0",
            "layout.frame_mm=0.8",
            "text.style_name=STIL",
            "overflow.mode=marker",
            "background.enabled=false",
            "layers.prefix=P",
            "output.write_report=false",
        ],
    )
    assert config.source.default_padding_mm == 2.0
    assert config.layout.frame_mm == 0.8
    assert config.text.style_name == "STIL"
    assert config.overflow.mode == "marker"
    assert config.background.enabled is False
    assert config.layers.prefix == "P"
    assert config.output.write_report is False


def test_unquoted_colour_is_accepted() -> None:
    """`#f5f5f5` TOML'da yorum başlatır; `--set` yine de kabul etmeli."""
    assert apply_overrides(Config(), ["background.color=#f5f5f5"]).background.color == (
        245,
        245,
        245,
    )


def test_overrides_do_not_mutate_the_original() -> None:
    original = Config()
    apply_overrides(original, ["layers.prefix=BASKA"])
    assert original.layers.prefix == "ONCU_TBL"


def test_empty_overrides_return_the_same_config() -> None:
    config = Config()
    assert apply_overrides(config, []) is config


@pytest.mark.parametrize(
    "override", ["prefix=X", "layers", "layers.=X", "olmayan.x=1", "layers.olmayan=1"]
)
def test_malformed_overrides_are_rejected(override: str) -> None:
    with pytest.raises(UsageError):
        apply_overrides(Config(), [override])


def test_override_validates_the_result() -> None:
    """Ezme sonrası da doğrulama çalışır; geçersiz değer sızmaz."""
    with pytest.raises(UsageError):
        apply_overrides(Config(), ["layout.frame_mm=-3"])
