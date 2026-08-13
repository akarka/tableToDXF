"""Uzunluk, renk, kenarlık ve aralık ayrıştırması."""

from __future__ import annotations

import pytest

from tabletodxf.errors import SRC_RANGE_INVALID, TableToDxfError
from tabletodxf.model import col_index_to_letters, letters_to_col_index
from tabletodxf.ods_reader import parse_border, parse_color, parse_length_mm, parse_range


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("2.258cm", 22.58),
        ("10mm", 10.0),
        ("1in", 25.4),
        ("72pt", 25.4),
        ("0.5pt", 25.4 / 144),
        ("3", 3.0),  # birimsiz → mm
    ],
)
def test_lengths_normalize_to_mm(source: str, expected: float) -> None:
    assert parse_length_mm(source) == pytest.approx(expected)


def test_unparseable_length_falls_back_to_default() -> None:
    assert parse_length_mm("optimal", 4.2) == 4.2
    assert parse_length_mm(None, 4.2) == 4.2


def test_colors() -> None:
    assert parse_color("#ff8800") == (255, 136, 0)
    assert parse_color("#FFFFFF") == (255, 255, 255)
    assert parse_color("transparent") is None
    assert parse_color(None) is None


def test_border_shorthand() -> None:
    border = parse_border("0.06pt solid #000000")
    assert border.width_mm == pytest.approx(0.06 * 25.4 / 72)
    assert border.color == (0, 0, 0)
    assert border.visible


def test_border_none_is_invisible() -> None:
    assert not parse_border("none").visible
    assert not parse_border(None).visible


def test_border_without_width_is_hairline_not_absent() -> None:
    """Görünür bir kenarlık istendiği kesin; 0 döndürmek çizgiyi yok ederdi."""
    border = parse_border("solid #ff0000")
    assert border.visible
    assert border.color == (255, 0, 0)


def test_column_letters_roundtrip() -> None:
    for index in (0, 25, 26, 27, 51, 52, 701, 702):
        assert letters_to_col_index(col_index_to_letters(index)) == index


def test_parse_range() -> None:
    assert parse_range("B3:C500") == (2, 1, 499, 2)
    assert parse_range("$B$3:$C$500") == (2, 1, 499, 2)
    assert parse_range("b3:c500") == (2, 1, 499, 2)


def test_parse_range_single_cell() -> None:
    assert parse_range("B3") == (2, 1, 2, 1)


def test_parse_range_normalizes_direction() -> None:
    """Kullanıcının seçim yönü çıktıyı değiştirmemeli."""
    assert parse_range("C500:B3") == parse_range("B3:C500")


@pytest.mark.parametrize("bad", ["", "3:5", "B0:C5", "B3-C5", "ABCD3:E5"])
def test_parse_range_rejects_garbage(bad: str) -> None:
    with pytest.raises(TableToDxfError) as excinfo:
        parse_range(bad)
    assert excinfo.value.code == SRC_RANGE_INVALID
