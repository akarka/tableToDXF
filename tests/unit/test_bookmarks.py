"""Adlandırılmış girdi kısayolları — `Config` profillerinden bağımsız (F-003)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tabletodxf.api import Job
from tabletodxf.bookmarks import (
    JobBookmark,
    bookmarks_dir,
    delete_bookmark,
    list_bookmarks,
    load_bookmark,
    rename_bookmark,
    save_bookmark,
)
from tabletodxf.config import app_data_dir
from tabletodxf.errors import CONFIG_INVALID, UsageError

SAMPLE = JobBookmark(
    source=r"C:\yol\mahal.ods",
    sheet="Mahal",
    range_text="B2:E7",
    block="mahal_Mahal",
    out=r"C:\yol\mahal.dxf",
)


@pytest.fixture
def isolated_app_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    return app_data_dir()


# ── Job ↔ JobBookmark ────────────────────────────────────────────────────


def test_from_job_and_back_roundtrips() -> None:
    job = Job(
        source=Path(r"C:\yol\mahal.ods"),
        sheet="Mahal",
        range_text="B2:E7",
        block="mahal_Mahal",
        out=Path(r"C:\yol\mahal.dxf"),
    )
    bookmark = JobBookmark.from_job(job)
    restored = bookmark.to_job()

    assert restored.source == job.source
    assert restored.sheet == job.sheet
    assert restored.range_text == job.range_text
    assert restored.block == job.block
    assert restored.out == job.out


def test_to_job_does_not_carry_runtime_only_fields() -> None:
    """`report_path`/`verbose` bir kısayolun parçası değil, her koşuda ayrıca belirlenir."""
    job = SAMPLE.to_job()
    assert job.report_path is None
    assert job.verbose is False


# ── Depolama konumu ──────────────────────────────────────────────────────


def test_bookmarks_dir_sits_next_to_profiles(isolated_app_data: Path) -> None:
    assert bookmarks_dir().parent == isolated_app_data
    assert bookmarks_dir().name == "inputs"


def test_bookmarks_dir_does_not_exist_until_something_is_saved(
    isolated_app_data: Path,
) -> None:
    assert not bookmarks_dir().exists()
    assert list_bookmarks() == []


# ── CRUD ─────────────────────────────────────────────────────────────────


def test_save_then_load_roundtrips(isolated_app_data: Path) -> None:
    save_bookmark("Blok A - Mahal", SAMPLE)
    assert load_bookmark("Blok A - Mahal") == SAMPLE
    assert list_bookmarks() == ["Blok A - Mahal"]


def test_saving_the_same_name_overwrites(isolated_app_data: Path) -> None:
    save_bookmark("X", SAMPLE)
    changed = JobBookmark(
        source="c.ods", sheet="S2", range_text="A1:B2", block="c_S2", out="c.dxf"
    )
    save_bookmark("X", changed)

    assert load_bookmark("X") == changed
    assert list_bookmarks() == ["X"]


def test_incomplete_bookmark_can_still_be_saved(isolated_app_data: Path) -> None:
    """Aralığı henüz belli olmayan tekrarlayan bir kaynağın yer tutucusu olabilir."""
    partial = JobBookmark(source="c.ods", sheet="", range_text="", block="", out="")
    save_bookmark("Yarım", partial)
    assert load_bookmark("Yarım") == partial


def test_loading_a_missing_bookmark_is_an_error(isolated_app_data: Path) -> None:
    with pytest.raises(UsageError) as excinfo:
        load_bookmark("Yok Böyle Bir Şey")
    assert excinfo.value.code == CONFIG_INVALID


def test_delete_removes_it(isolated_app_data: Path) -> None:
    save_bookmark("Silinecek", SAMPLE)
    delete_bookmark("Silinecek")
    assert list_bookmarks() == []


def test_deleting_a_missing_bookmark_does_not_raise(isolated_app_data: Path) -> None:
    delete_bookmark("Zaten Yok")


def test_rename(isolated_app_data: Path) -> None:
    save_bookmark("Eski Ad", SAMPLE)
    rename_bookmark("Eski Ad", "Yeni Ad")
    assert list_bookmarks() == ["Yeni Ad"]
    assert load_bookmark("Yeni Ad") == SAMPLE


def test_renaming_a_missing_bookmark_is_an_error(isolated_app_data: Path) -> None:
    with pytest.raises(UsageError):
        rename_bookmark("Yok", "Yeni")


def test_renaming_onto_an_existing_bookmark_is_an_error(isolated_app_data: Path) -> None:
    save_bookmark("A", SAMPLE)
    save_bookmark("B", SAMPLE)
    with pytest.raises(UsageError):
        rename_bookmark("A", "B")
    assert set(list_bookmarks()) == {"A", "B"}


@pytest.mark.parametrize("bad_name", ["", "   ", "a/b", "a\\b", "a:b", "a*b", 'a"b', "a<b>c", "a|b"])
def test_forbidden_names_are_rejected(isolated_app_data: Path, bad_name: str) -> None:
    with pytest.raises(UsageError):
        save_bookmark(bad_name, SAMPLE)


def test_turkish_characters_in_names_work(isolated_app_data: Path) -> None:
    save_bookmark("Şişli Ğüç İç Ölçü", SAMPLE)
    assert "Şişli Ğüç İç Ölçü" in list_bookmarks()
    assert load_bookmark("Şişli Ğüç İç Ölçü") == SAMPLE


# ── Bozuk dosya ──────────────────────────────────────────────────────────


def test_missing_field_is_rejected(isolated_app_data: Path) -> None:
    path = bookmarks_dir() / "eksik.toml"
    path.parent.mkdir(parents=True)
    path.write_text('source = "c.ods"\nsheet = "S"\n', encoding="utf-8")
    with pytest.raises(UsageError) as excinfo:
        load_bookmark("eksik")
    assert excinfo.value.code == CONFIG_INVALID


def test_unknown_field_is_rejected(isolated_app_data: Path) -> None:
    path = bookmarks_dir() / "fazla.toml"
    path.parent.mkdir(parents=True)
    path.write_text(
        'source = "c.ods"\nsheet = "S"\nrange_text = "A1"\nblock = "b"\nout = "c.dxf"\n'
        'fazladan = "x"\n',
        encoding="utf-8",
    )
    with pytest.raises(UsageError):
        load_bookmark("fazla")


def test_non_string_field_is_rejected(isolated_app_data: Path) -> None:
    path = bookmarks_dir() / "yanlistip.toml"
    path.parent.mkdir(parents=True)
    path.write_text(
        'source = "c.ods"\nsheet = "S"\nrange_text = "A1"\nblock = "b"\nout = 5\n',
        encoding="utf-8",
    )
    with pytest.raises(UsageError):
        load_bookmark("yanlistip")


def test_broken_toml_is_rejected(isolated_app_data: Path) -> None:
    path = bookmarks_dir() / "bozuk.toml"
    path.parent.mkdir(parents=True)
    path.write_text("source = = c.ods", encoding="utf-8")
    with pytest.raises(UsageError):
        load_bookmark("bozuk")


def test_backslashes_and_quotes_in_paths_survive_the_roundtrip(
    isolated_app_data: Path,
) -> None:
    """Windows yolları ters bölü doludur; TOML kaçışı bunu bozmamalı."""
    tricky = JobBookmark(
        source=r'C:\yol\"garip" dosya.ods',
        sheet="S",
        range_text="A1:B2",
        block="b",
        out=r"C:\yol\çıktı.dxf",
    )
    save_bookmark("Tuhaf", tricky)
    assert load_bookmark("Tuhaf") == tricky
