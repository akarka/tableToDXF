"""Yazıcı tarafındaki saf dönüşümler."""

from __future__ import annotations

import pytest
from tabletodxf.dxf_writer import escape_mtext, layer_names


def test_layer_names_use_the_prefix() -> None:
    names = layer_names("ONCU_TBL")
    assert set(names.values()) == {
        "ONCU_TBL_GRID",
        "ONCU_TBL_TEXT",
        "ONCU_TBL_FILL",
        "ONCU_TBL_OVERFLOW",
    }


# ── MTEXT kaçışları ─────────────────────────────────────────────────────────


def test_plain_text_passes_through_unchanged() -> None:
    assert escape_mtext("Zemin kat koridoru") == "Zemin kat koridoru"


def test_newlines_become_mtext_paragraph_breaks() -> None:
    assert escape_mtext("bir\niki") == r"bir\Piki"


def test_braces_are_escaped() -> None:
    r"""`{` kaçırılmazsa `MTEXT` onu grup başlangıcı sayar ve metni yutar."""
    assert escape_mtext("a{b}c") == r"a\{b\}c"


def test_backslash_is_escaped_before_paragraph_breaks_are_added() -> None:
    r"""Sıra önemli: `\P` kendi ters bölüsünü ekliyor, o yeniden kaçırılmamalı."""
    assert escape_mtext("a\\b\nc") == "a\\\\b\\Pc"


def test_turkish_text_is_untouched() -> None:
    assert escape_mtext("Şişli ğüç İÇ") == "Şişli ğüç İÇ"
