"""Argüman/config birleştirme ve çıkış kodları."""

from __future__ import annotations

from pathlib import Path

import pytest

from tabletodxf.cli import (
    DEFAULTS,
    EXIT_DATA_ERROR,
    EXIT_USAGE_ERROR,
    build_parser,
    load_config,
    main,
    merge,
    resolve_font,
)
from tabletodxf.errors import CONFIG_INVALID, FONT_NOT_FOUND, TableToDxfError, UsageError

BASE_ARGS = [
    "kaynak.ods",
    "--sheet",
    "Mahal",
    "--range",
    "B3:C500",
    "--out",
    "cikti.dxf",
    "--block",
    "TBL",
]

CONFIG_BODY = """
scale_cm_to_units = 25.0
dxf_version       = "R2018"
overflow          = "full"

[text]
style_name = "CONFIG_STYLE"
font_file  = "ConfigFont.ttf"

[layers]
prefix = "CONFIG_PREFIX"
"""


def parse(extra: list[str] | None = None):  # noqa: ANN201
    return build_parser().parse_args(BASE_ARGS + (extra or []))


# ── Öncelik: bayrak > config > varsayılan ───────────────────────────────────


def test_builtin_defaults_apply_when_nothing_is_given() -> None:
    settings = merge(parse(), {})
    assert settings.scale == DEFAULTS["scale"]
    assert settings.overflow == DEFAULTS["overflow"]
    assert settings.text_style == DEFAULTS["text_style"]
    assert settings.layer_prefix == DEFAULTS["layer_prefix"]
    assert settings.dxf_version == DEFAULTS["dxf_version"]


def test_config_overrides_builtin_defaults(tmp_path: Path) -> None:
    config_path = tmp_path / "tabletodxf.toml"
    config_path.write_text(CONFIG_BODY, encoding="utf-8")
    settings = merge(parse(), load_config(str(config_path), tmp_path))

    assert settings.scale == 25.0
    assert settings.overflow == "full"
    assert settings.text_style == "CONFIG_STYLE"
    assert settings.font == "ConfigFont.ttf"
    assert settings.layer_prefix == "CONFIG_PREFIX"
    assert settings.dxf_version == "R2018"


def test_flag_overrides_config(tmp_path: Path) -> None:
    config_path = tmp_path / "tabletodxf.toml"
    config_path.write_text(CONFIG_BODY, encoding="utf-8")
    config = load_config(str(config_path), tmp_path)

    settings = merge(
        parse(["--scale", "5", "--overflow", "marker", "--layer-prefix", "FLAG"]), config
    )
    assert settings.scale == 5.0
    assert settings.overflow == "marker"
    assert settings.layer_prefix == "FLAG"
    # Bayrakla ezilmeyen anahtarlar config'ten gelmeye devam eder.
    assert settings.text_style == "CONFIG_STYLE"


def test_default_config_is_picked_up_from_cwd(tmp_path: Path) -> None:
    (tmp_path / "tabletodxf.toml").write_text(CONFIG_BODY, encoding="utf-8")
    assert load_config(None, tmp_path)["scale_cm_to_units"] == 25.0


def test_absent_default_config_is_not_an_error(tmp_path: Path) -> None:
    assert load_config(None, tmp_path) == {}


def test_explicitly_named_missing_config_is_a_usage_error(tmp_path: Path) -> None:
    """Kullanıcı bir yol verdiyse sessizce yok saymak yanlış ayarla üretim demek."""
    with pytest.raises(UsageError) as excinfo:
        load_config(str(tmp_path / "yok.toml"), tmp_path)
    assert excinfo.value.code == CONFIG_INVALID


def test_broken_toml_is_a_usage_error(tmp_path: Path) -> None:
    path = tmp_path / "bozuk.toml"
    path.write_text("scale_cm_to_units = = 3", encoding="utf-8")
    with pytest.raises(UsageError):
        load_config(str(path), tmp_path)


def test_invalid_overflow_in_config_is_rejected() -> None:
    with pytest.raises(UsageError):
        merge(parse(), {"overflow": "kırp"})


def test_overflow_defaults_to_mtext() -> None:
    """Taşan hücre gizlenmez; AutoCAD'de genişliği ayarlanabilen bir kutu olur."""
    assert merge(parse(), {}).overflow == "mtext"


@pytest.mark.parametrize("mode", ["mtext", "marker", "full"])
def test_every_overflow_mode_is_accepted(mode: str) -> None:
    assert merge(parse(["--overflow", mode]), {}).overflow == mode


# ── DXF sürümü ──────────────────────────────────────────────────────────────


def test_r2018_is_accepted() -> None:
    assert merge(parse(["--dxf-version", "R2018"]), {}).dxf_version == "R2018"


@pytest.mark.parametrize("old", ["R12", "R2000", "R2010"])
def test_versions_below_r2013_are_rejected(old: str) -> None:
    """AC-9 TTF metin stili gerektiriyor; eski sürümler bunu taşımaz."""
    with pytest.raises(UsageError) as excinfo:
        merge(parse(["--dxf-version", old]), {})
    assert excinfo.value.code == CONFIG_INVALID


def test_unknown_version_is_rejected() -> None:
    with pytest.raises(UsageError):
        merge(parse(["--dxf-version", "R9999"]), {})


# ── Türetilen yollar ────────────────────────────────────────────────────────


def test_report_path_defaults_next_to_the_dxf() -> None:
    settings = merge(parse(), {})
    assert settings.report_path == Path("cikti.report.txt")


def test_report_path_can_be_overridden() -> None:
    settings = merge(parse(["--report", "başka.txt"]), {})
    assert settings.report_path == Path("başka.txt")


# ── Font çözümü ─────────────────────────────────────────────────────────────


def test_explicit_font_path_wins(tmp_path: Path, font_path: Path) -> None:
    copy = tmp_path / "kopya.ttf"
    copy.write_bytes(font_path.read_bytes())
    assert resolve_font(str(copy)) == copy


def test_unresolvable_font_is_an_error() -> None:
    with pytest.raises(TableToDxfError) as excinfo:
        resolve_font("KesinlikleOlmayanBirFont-XYZ.ttf")
    assert excinfo.value.code == FONT_NOT_FOUND


# ── Çıkış kodları ───────────────────────────────────────────────────────────


def test_non_ods_input_exits_with_data_error(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    source = tmp_path / "tablo.xlsx"
    source.write_bytes(b"")
    out = tmp_path / "cikti.dxf"

    code = main(
        [str(source), "--sheet", "S", "--range", "A1:B2", "--out", str(out), "--block", "T"]
    )

    assert code == EXIT_DATA_ERROR
    assert "SRC_FORMAT" in capsys.readouterr().err
    assert not out.exists()


def test_bad_config_exits_with_usage_error(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    out = tmp_path / "cikti.dxf"
    code = main(
        [
            "kaynak.ods",
            "--sheet",
            "S",
            "--range",
            "A1:B2",
            "--out",
            str(out),
            "--block",
            "T",
            "--config",
            str(tmp_path / "yok.toml"),
        ]
    )
    assert code == EXIT_USAGE_ERROR
    assert not out.exists()


def test_missing_required_flag_exits_two() -> None:
    """argparse'ın kendi kullanım hatası da 2 ile çıkar."""
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args(["kaynak.ods"])
    assert excinfo.value.code == EXIT_USAGE_ERROR
