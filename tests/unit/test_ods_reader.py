"""`.ods` → `SheetModel` okuma davranışı."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from fixtures.ods_builder import CellSpec, RowSpec, SheetSpec, build_ods
from tabletodxf import ods_reader
from tabletodxf.errors import (
    FORMULA_NO_CACHE,
    MERGE_CROSSES_SELECTION,
    SELECTION_EMPTY,
    SRC_FORMAT,
    SRC_NOT_FOUND,
    SRC_SHEET_NOT_FOUND,
    TableToDxfError,
)
from tabletodxf.report import Report

from conftest import OVERFLOW_TEXT, REFERENCE_RANGE, REFERENCE_SHEET


@pytest.fixture
def model(reference_ods: Path, report: Report):  # noqa: ANN201
    return ods_reader.read(reference_ods, REFERENCE_SHEET, REFERENCE_RANGE, report)


# ── Boyutlar ────────────────────────────────────────────────────────────────


def test_lengths_are_normalized_to_mm(model) -> None:  # noqa: ANN001
    """Kaynak cm yazıyor; model mm taşır."""
    assert model.col_widths_mm == pytest.approx([30.0, 50.0, 25.0])
    assert model.row_heights_mm == pytest.approx([6.0, 4.5, 4.5, 4.5, 4.5])


def test_hidden_rows_and_columns_are_dropped(model) -> None:  # noqa: ANN001
    """D sütunu ve 5. satır gizli; kalanlar aralarında boşluk bırakmadan bitişir."""
    assert model.n_cols == 3  # B, C, E — D düştü
    assert model.n_rows == 5  # 2,3,4,6,7 — 5 düştü
    assert model.col_refs == [1, 2, 4]
    assert model.row_refs == [1, 2, 3, 5, 6]


def test_trailing_empty_row_is_kept(model) -> None:  # noqa: ANN001
    """AC-5: aralık birebir onurlandırılır, sondaki boş satır kırpılmaz."""
    last = model.n_rows - 1
    assert model.row_heights_mm[last] == pytest.approx(4.5)
    assert all(model.cell(last, col).text == "" for col in range(model.n_cols))


def test_cell_refs_point_back_to_sheet_coordinates(model) -> None:  # noqa: ANN001
    """Gizli satır/sütunlar indeksleri kaydırır; rapor sayfadaki referansı basmalı."""
    assert model.ref(0, 0) == "Mahal!B2"
    assert model.ref(0, 2) == "Mahal!E2"  # D gizli, atlandı
    assert model.ref(3, 0) == "Mahal!B6"  # 5. satır gizli, atlandı


# ── İçerik ve biçim ─────────────────────────────────────────────────────────


def test_displayed_text_is_used_not_raw_value(model) -> None:  # noqa: ANN001
    """AC-3: `12,50` yazılır — ham `12.5` ya da yeniden biçimlenmiş hâli değil."""
    assert model.cell(1, 2).text == "12,50"


def test_numbers_default_to_right_alignment(model) -> None:  # noqa: ANN001
    """Sayfada sağa yaslı görünen sayı çizimde de sağa yaslı olmalı."""
    assert model.cell(1, 2).h_align == "right"  # 12,50
    assert model.cell(1, 1).h_align == "left"  # "Zemin kat koridoru"


def test_header_formatting_is_read(model) -> None:  # noqa: ANN001
    header = model.cell(0, 0)
    assert header.text == "Kod"
    assert header.font.bold
    assert header.h_align == "center"
    assert header.v_align == "middle"
    assert header.fill == (255, 255, 0)


def test_per_edge_border_widths_are_read(model) -> None:  # noqa: ANN001
    """Başlığın alt kenarı kalın, diğer kenarları ince."""
    borders = model.cell(0, 0).borders
    assert borders.bottom.width_mm > borders.top.width_mm
    assert borders.top.width_mm == pytest.approx(0.06 * 25.4 / 72)


def test_padding_has_a_default_when_absent(model) -> None:  # noqa: ANN001
    assert model.cell(1, 1).padding_mm == pytest.approx(ods_reader.DEFAULT_PADDING_MM)


# ── Birleştirmeler ──────────────────────────────────────────────────────────


def test_vertical_merge_spans_and_marks_covered(model) -> None:  # noqa: ANN001
    origin = model.cell(1, 0)  # B3:B4
    assert origin.row_span == 2
    assert not origin.covered
    assert model.cell(2, 0).covered


def test_merge_shrinks_when_it_spans_a_hidden_column(model) -> None:  # noqa: ANN001
    """C4:D4 birleşikti; D gizlenince görünür genişlik tek sütuna iner."""
    merged = model.cell(2, 1)
    assert merged.text == "Birleşik alan"
    assert merged.col_span == 1


def test_merge_crossing_the_selection_edge_stops(tmp_path: Path, report: Report) -> None:
    """AC-10: sessiz kırpma yok — seçimi kesen birleştirme üretimi durdurur."""
    path = build_ods(
        tmp_path / "kesen.ods",
        [
            SheetSpec(
                name="S",
                col_widths=["2cm", "2cm", "2cm"],
                rows=[
                    RowSpec(
                        cells=[
                            CellSpec(text="geniş", col_span=2),
                            CellSpec(covered=True),
                            CellSpec(text="c"),
                        ]
                    )
                ],
            )
        ],
    )
    with pytest.raises(TableToDxfError) as excinfo:
        ods_reader.read(path, "S", "B1:C1", report)  # birleştirme A1:B1, sol kenarı keser
    assert excinfo.value.code == MERGE_CROSSES_SELECTION
    assert excinfo.value.fields["merge"] == "A1:B1"


# ── Hata yolları ────────────────────────────────────────────────────────────


def test_non_ods_extension_stops(tmp_path: Path, report: Report) -> None:
    source = tmp_path / "tablo.xlsx"
    source.write_bytes(b"")
    with pytest.raises(TableToDxfError) as excinfo:
        ods_reader.read(source, "S", "A1:B2", report)
    assert excinfo.value.code == SRC_FORMAT


def test_missing_file_stops(tmp_path: Path, report: Report) -> None:
    with pytest.raises(TableToDxfError) as excinfo:
        ods_reader.read(tmp_path / "yok.ods", "S", "A1:B2", report)
    assert excinfo.value.code == SRC_NOT_FOUND


def test_unknown_sheet_lists_available_names(reference_ods: Path, report: Report) -> None:
    with pytest.raises(TableToDxfError) as excinfo:
        ods_reader.read(reference_ods, "Olmayan", REFERENCE_RANGE, report)
    assert excinfo.value.code == SRC_SHEET_NOT_FOUND
    assert REFERENCE_SHEET in str(excinfo.value.fields["available"])


def test_formula_without_cached_value_stops(tmp_path: Path, report: Report) -> None:
    path = build_ods(
        tmp_path / "formul.ods",
        [
            SheetSpec(
                name="S",
                col_widths=["2cm"],
                rows=[
                    RowSpec(cells=[CellSpec(formula="of:=SUM(A2:A3)", omit_cached_value=True)])
                ],
            )
        ],
    )
    with pytest.raises(TableToDxfError) as excinfo:
        ods_reader.read(path, "S", "A1", report)
    assert excinfo.value.code == FORMULA_NO_CACHE


def test_all_hidden_selection_stops(tmp_path: Path, report: Report) -> None:
    path = build_ods(
        tmp_path / "gizli.ods",
        [
            SheetSpec(
                name="S",
                col_widths=["2cm", "2cm"],
                hidden_cols={0, 1},
                rows=[RowSpec(cells=[CellSpec(text="a"), CellSpec(text="b")])],
            )
        ],
    )
    with pytest.raises(TableToDxfError) as excinfo:
        ods_reader.read(path, "S", "A1:B1", report)
    assert excinfo.value.code == SELECTION_EMPTY


def test_stale_sibling_workbook_warns_but_continues(
    reference_ods: Path, tmp_path: Path, report: Report
) -> None:
    """ADR-001'in ürettiği tek yeni hata modu: `.ods` bayat kalmış olabilir."""
    ods_copy = tmp_path / "mahal.ods"
    ods_copy.write_bytes(reference_ods.read_bytes())
    sibling = tmp_path / "mahal.xlsx"
    sibling.write_bytes(b"newer")
    # Aynı anda yazılan iki dosyanın mtime'ı eşit çıkabiliyor; uyarı "kesinlikle
    # daha yeni" koşuluna bağlı olduğu için fark açıkça kuruluyor.
    os.utime(ods_copy, (1_000_000, 1_000_000))
    os.utime(sibling, (2_000_000, 2_000_000))

    model = ods_reader.read(ods_copy, REFERENCE_SHEET, REFERENCE_RANGE, report)

    assert model.n_rows == 5  # uyarı üretimi durdurmaz
    assert any("newer sibling workbook" in line for line in report.lines)
    assert report.warn_count == 1


def test_overflow_text_survives_reading_intact(model) -> None:  # noqa: ANN001
    """Okuyucu kırpmaz — sığdırma kararı geometri katmanının işi."""
    assert model.cell(3, 1).text == OVERFLOW_TEXT


# ── Kaydırma ve dönüş ───────────────────────────────────────────────────────


def test_wrap_and_rotation_are_read(tmp_path: Path, report: Report) -> None:
    path = build_ods(
        tmp_path / "biçim.ods",
        [
            SheetSpec(
                name="S",
                col_widths=["2cm", "2cm", "2cm"],
                rows=[
                    RowSpec(
                        cells=[
                            CellSpec(text="kaydırılan uzun metin", wrap=True),
                            CellSpec(text="Dikey başlık", rotation=90),
                            CellSpec(text="düz"),
                        ]
                    )
                ],
            )
        ],
    )
    model = ods_reader.read(path, "S", "A1:C1", report)

    assert model.cell(0, 0).wrap
    assert model.cell(0, 0).rotation_deg == 0.0

    assert model.cell(0, 1).rotation_deg == 90.0
    assert not model.cell(0, 1).wrap

    assert not model.cell(0, 2).wrap
    assert model.cell(0, 2).rotation_deg == 0.0


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("90", 90.0), ("90deg", 90.0), ("270", 270.0), ("-90", 270.0), ("", 0.0), (None, 0.0)],
)
def test_rotation_angle_parsing(raw: str | None, expected: float) -> None:
    assert ods_reader.parse_rotation_deg(raw) == expected
