"""CLI — argüman/config birleştirme, öncelik sırası, çıkış kodları.

CLI artık `api.convert()` üzerine ince bir sarmalayıcı (ADR-003); buradaki
testler o ince katmanı sınar: bayraklar doğru ayara mı gidiyor, öncelik sırası
doğru mu, çıkış kodları doğru mu.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tabletodxf.api import Job, resolve_font
from tabletodxf.cli import (
    EXIT_DATA_ERROR,
    EXIT_USAGE_ERROR,
    FLAG_TO_SETTING,
    build_config,
    build_job,
    build_parser,
    main,
    validate_dxf_version,
)
from tabletodxf.config import Config, SourceConfig, apply_overrides, save_profile
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
[layout]
scale_cm_to_units = 25.0
frame_mm = 1.5

[overflow]
mode = "full"

[text]
style_name = "CONFIG_STYLE"
font_file  = "ConfigFont.ttf"

[layers]
prefix = "CONFIG_PREFIX"

[output]
dxf_version = "R2018"
"""


def parse(extra: list[str] | None = None):  # noqa: ANN201
    return build_parser().parse_args(BASE_ARGS + (extra or []))


def write_config(tmp_path: Path, body: str = CONFIG_BODY) -> Path:
    path = tmp_path / "tabletodxf.toml"
    path.write_text(body, encoding="utf-8")
    return path


# ── Öncelik: --set > bayrak > dosya > varsayılan ────────────────────────────


def test_builtin_defaults_apply_when_nothing_is_given(tmp_path: Path) -> None:
    config = build_config(parse(), cwd=tmp_path)
    assert config == Config()


def test_config_file_overrides_builtin_defaults(tmp_path: Path) -> None:
    config = build_config(parse(["--config", str(write_config(tmp_path))]), cwd=tmp_path)

    assert config.layout.scale_cm_to_units == 25.0
    assert config.layout.frame_mm == 1.5
    assert config.overflow.mode == "full"
    assert config.text.style_name == "CONFIG_STYLE"
    assert config.layers.prefix == "CONFIG_PREFIX"
    assert config.output.dxf_version == "R2018"


def test_flag_overrides_config_file(tmp_path: Path) -> None:
    args = parse(
        ["--config", str(write_config(tmp_path)), "--scale", "5", "--overflow", "marker"]
    )
    config = build_config(args, cwd=tmp_path)

    assert config.layout.scale_cm_to_units == 5.0
    assert config.overflow.mode == "marker"
    # Bayrakla ezilmeyen anahtarlar dosyadan gelmeye devam eder.
    assert config.text.style_name == "CONFIG_STYLE"


def test_set_overrides_dedicated_flag(tmp_path: Path) -> None:
    """`--set` en açık niyet; bayrağı da ezmeli (F-002 AC-7)."""
    args = parse(["--scale", "5", "--set", "layout.scale_cm_to_units=99"])
    assert build_config(args, cwd=tmp_path).layout.scale_cm_to_units == 99.0


def test_set_reaches_settings_without_a_dedicated_flag(tmp_path: Path) -> None:
    args = parse(
        [
            "--set",
            "background.enabled=false",
            "--set",
            "background.color=#f5f5f5",
            "--set",
            "source.default_padding_mm=2.5",
            "--set",
            "layers.overflow_color=3",
        ]
    )
    config = build_config(args, cwd=tmp_path)

    assert config.background.enabled is False
    assert config.background.color == (245, 245, 245)
    assert config.source.default_padding_mm == 2.5
    assert config.layers.overflow_color == 3


def test_default_config_is_picked_up_from_cwd(tmp_path: Path) -> None:
    write_config(tmp_path)
    assert build_config(parse(), cwd=tmp_path).layout.scale_cm_to_units == 25.0


def test_absent_default_config_is_not_an_error(tmp_path: Path) -> None:
    assert build_config(parse(), cwd=tmp_path) == Config()


def test_explicitly_named_missing_config_is_a_usage_error(tmp_path: Path) -> None:
    """Kullanıcı bir yol verdiyse sessizce yok saymak yanlış ayarla üretim demek."""
    with pytest.raises(UsageError) as excinfo:
        build_config(parse(["--config", str(tmp_path / "yok.toml")]), cwd=tmp_path)
    assert excinfo.value.code == CONFIG_INVALID


# ── Profil ───────────────────────────────────────────────────────────────────


def test_profile_flag_loads_a_saved_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    saved = apply_overrides(Config(), ["layers.prefix=PROJE"])
    save_profile("Mahal Listesi", saved)

    config = build_config(parse(["--profile", "Mahal Listesi"]), cwd=tmp_path)
    assert config.layers.prefix == "PROJE"


def test_missing_profile_is_a_usage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    with pytest.raises(UsageError) as excinfo:
        build_config(parse(["--profile", "Yok Böyle Bir Şey"]), cwd=tmp_path)
    assert excinfo.value.code == CONFIG_INVALID


def test_profile_and_config_flags_are_mutually_exclusive() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(BASE_ARGS + ["--profile", "X", "--config", "y.toml"])


def test_dedicated_flags_still_override_a_loaded_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    save_profile("P", apply_overrides(Config(), ["layout.scale_cm_to_units=25"]))

    config = build_config(
        parse(["--profile", "P", "--scale", "5"]), cwd=tmp_path
    )
    assert config.layout.scale_cm_to_units == 5.0


def test_broken_toml_is_a_usage_error(tmp_path: Path) -> None:
    path = tmp_path / "bozuk.toml"
    path.write_text("[layout]\nscale_cm_to_units = = 3", encoding="utf-8")
    with pytest.raises(UsageError):
        build_config(parse(["--config", str(path)]), cwd=tmp_path)


# ── Bayrak eşlemesi ─────────────────────────────────────────────────────────


def test_every_mapped_flag_exists_on_the_parser() -> None:
    """Eşleme tablosu ile parser'ın ayrışmasını engeller."""
    known = {action.dest for action in build_parser()._actions}  # noqa: SLF001
    assert set(FLAG_TO_SETTING) <= known


def test_every_mapped_setting_exists_on_config() -> None:
    config = Config()
    for setting in FLAG_TO_SETTING.values():
        section, _, key = setting.partition(".")
        assert hasattr(getattr(config, section), key), setting


@pytest.mark.parametrize("mode", ["condense", "mtext", "marker", "full"])
def test_every_overflow_mode_is_accepted(mode: str, tmp_path: Path) -> None:
    assert build_config(parse(["--overflow", mode]), cwd=tmp_path).overflow.mode == mode


def test_overflow_defaults_to_condense(tmp_path: Path) -> None:
    """Taşan hücre kendiliğinden sığar; elle düzeltme gerektirmemeli."""
    assert build_config(parse(), cwd=tmp_path).overflow.mode == "condense"


def test_negative_frame_is_rejected(tmp_path: Path) -> None:
    """`0` çerçeveyi kapatır; negatif değer bir yazım hatasıdır."""
    with pytest.raises(UsageError):
        build_config(parse(["--frame", "-1"]), cwd=tmp_path)


def test_unknown_setting_in_set_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(UsageError):
        build_config(parse(["--set", "layout.olmayan=1"]), cwd=tmp_path)


def test_malformed_set_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(UsageError):
        build_config(parse(["--set", "scale=10"]), cwd=tmp_path)


# ── DXF sürümü ──────────────────────────────────────────────────────────────


def test_r2018_is_accepted() -> None:
    assert validate_dxf_version("R2018") == "R2018"


@pytest.mark.parametrize("old", ["R12", "R2000", "R2010"])
def test_versions_below_r2013_are_rejected(old: str) -> None:
    """AC-9 TTF metin stili gerektiriyor; eski sürümler bunu taşımaz."""
    with pytest.raises(UsageError) as excinfo:
        validate_dxf_version(old)
    assert excinfo.value.code == CONFIG_INVALID


def test_unknown_version_is_rejected() -> None:
    with pytest.raises(UsageError):
        validate_dxf_version("R9999")


# ── Job ─────────────────────────────────────────────────────────────────────


def test_report_path_defaults_next_to_the_dxf() -> None:
    assert build_job(parse()).resolved_report_path() == Path("cikti.report.txt")


def test_report_path_can_be_overridden() -> None:
    job = build_job(parse(["--report", "başka.txt"]))
    assert job.resolved_report_path() == Path("başka.txt")


def test_job_carries_the_per_run_inputs() -> None:
    job = build_job(parse())
    assert (job.sheet, job.range_text, job.block) == ("Mahal", "B3:C500", "TBL")
    assert job.source == Path("kaynak.ods")
    assert job.out == Path("cikti.dxf")


def test_config_carries_no_per_run_inputs() -> None:
    """ADR-003'ün ayrımı: `Config` kalıcı tercihler, `Job` her çalıştırmanın girdisi.

    Bir alan `Config`'e sızarsa UI'da yanlış yere düşer — kaydedilen tercihler
    arasında dosya yolu ya da aralık görünür.
    """
    per_run = {"sheet", "range_text", "out", "block", "report_path"}
    config_fields = set(vars(Config()))
    assert not per_run & config_fields

    # `Config.source` bir **bölümdür** (okuma varsayılanları), `Job.source` ise
    # dosya yolu; ad benzerliği kasıtlı, tipleri ayrı.
    assert isinstance(Config().source, SourceConfig)
    assert isinstance(Job(Path("a.ods"), "S", "A1", Path("o.dxf"), "B").source, Path)


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


def test_bad_config_exits_with_usage_error(tmp_path: Path) -> None:
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


def test_invalid_setting_exits_with_usage_error(tmp_path: Path) -> None:
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
            "--set",
            "overflow.min_width_factor=-5",
        ]
    )
    assert code == EXIT_USAGE_ERROR
    assert not out.exists()


def test_missing_required_flag_exits_two() -> None:
    """argparse'ın kendi kullanım hatası da 2 ile çıkar."""
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args(["kaynak.ods"])
    assert excinfo.value.code == EXIT_USAGE_ERROR
