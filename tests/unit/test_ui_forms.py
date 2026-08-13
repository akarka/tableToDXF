"""`ui.forms`'daki saf fonksiyonlar — Tk kurmadan test edilir (F-003).

`widget_kind_for` / `coerce_from_text` / `format_for_display` Tk'ye hiç
dokunmaz; `SectionForm`'un gerçek widget kurulumu burada değil, elle
doğrulama listesinde (F-003 → Manual Verification) kapsanır.
"""

from __future__ import annotations

from typing import Literal

import pytest

from tabletodxf.ui.forms import (
    coerce_from_text,
    format_color,
    format_for_display,
    parse_color_text,
    widget_kind_for,
)

_Overflow = Literal["condense", "mtext", "marker", "full"]


# ── widget_kind_for ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("type_hint", "expected"),
    [
        (bool, "bool"),
        (_Overflow, "combobox"),
        (float, "number"),
        (int, "number"),
        (tuple[int, int, int], "color"),
        (tuple[float, float], "point2"),
        (tuple[str, ...], "strlist"),
        (str, "text"),
    ],
)
def test_widget_kind_for_every_config_type(type_hint: object, expected: str) -> None:
    assert widget_kind_for(type_hint) == expected


# ── renk ─────────────────────────────────────────────────────────────────


def test_color_roundtrips_through_hex_text() -> None:
    assert parse_color_text(format_color((255, 136, 0))) == (255, 136, 0)


def test_color_parses_hash_rrggbb() -> None:
    assert parse_color_text("#ff8800") == (255, 136, 0)


@pytest.mark.parametrize("bad", ["mavi", "#fff", "#gggggg", "", "ff8800"])
def test_invalid_color_text_raises(bad: str) -> None:
    with pytest.raises(ValueError, match="rengi değil"):
        parse_color_text(bad)


# ── coerce_from_text / format_for_display round-trip ────────────────────────


@pytest.mark.parametrize(
    ("type_hint", "value"),
    [
        (float, 0.35),
        (float, -1.0),
        (int, 7),
        (tuple[int, int, int], (255, 255, 255)),
        (tuple[float, float], (0.0, 0.0)),
        (tuple[float, float], (100.5, -50.25)),
        (tuple[str, ...], (".xlsx", ".xls", ".xlsm")),
        (tuple[str, ...], ()),
        (str, "ONCU_TBL"),
    ],
)
def test_display_then_coerce_roundtrips(type_hint: object, value: object) -> None:
    text = format_for_display(type_hint, value)
    assert coerce_from_text(type_hint, text) == value


def test_float_rejects_non_numeric_text() -> None:
    with pytest.raises(ValueError, match="bir sayı değil"):
        coerce_from_text(float, "kalın")


def test_int_rejects_non_integer_text() -> None:
    with pytest.raises(ValueError, match="bir tam sayı değil"):
        coerce_from_text(int, "7.5")


def test_point2_requires_exactly_two_numbers() -> None:
    with pytest.raises(ValueError):
        coerce_from_text(tuple[float, float], "1.0")
    with pytest.raises(ValueError):
        coerce_from_text(tuple[float, float], "1.0, 2.0, 3.0")


def test_point2_accepts_bracketed_or_bare_form() -> None:
    assert coerce_from_text(tuple[float, float], "[1.0, 2.0]") == (1.0, 2.0)
    assert coerce_from_text(tuple[float, float], "1.0, 2.0") == (1.0, 2.0)


def test_strlist_splits_on_commas_and_trims_whitespace() -> None:
    assert coerce_from_text(tuple[str, ...], " .xlsx ,  .xls,.xlsm ") == (
        ".xlsx",
        ".xls",
        ".xlsm",
    )


def test_strlist_empty_text_is_empty_tuple() -> None:
    assert coerce_from_text(tuple[str, ...], "") == ()


def test_plain_str_passes_through_unchanged() -> None:
    assert coerce_from_text(str, "  ONCU_TBL  ") == "  ONCU_TBL  "
