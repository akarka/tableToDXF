"""Yazıcı tarafındaki saf dönüşümler."""

from __future__ import annotations

import pytest
from ezdxf.lldxf import const

from tabletodxf.dxf_writer import escape_mtext, layer_names, snap_lineweight


def test_layer_names_use_the_prefix() -> None:
    names = layer_names("ONCU_TBL")
    assert set(names.values()) == {
        "ONCU_TBL_GRID",
        "ONCU_TBL_TEXT",
        "ONCU_TBL_FILL",
        "ONCU_TBL_OVERFLOW",
    }


@pytest.mark.parametrize(
    "width_mm",
    [0.01, 0.021, 0.05, 0.13, 0.176, 0.25, 0.5, 1.0, 2.11, 5.0],
)
def test_snapped_lineweight_is_always_a_legal_dxf_value(width_mm: float) -> None:
    """Ara değerler dosyayı geçersiz kılar — küme dışına asla çıkılmamalı."""
    assert snap_lineweight(width_mm) in const.VALID_DXF_LINEWEIGHT_VALUES


def test_exact_values_are_preserved() -> None:
    assert snap_lineweight(0.13) == 13
    assert snap_lineweight(0.50) == 50
    assert snap_lineweight(2.00) == 200


def test_hairline_never_snaps_to_zero() -> None:
    """Kaynakta görünür olan kenarlık çizimde de görünür kalmalı."""
    assert snap_lineweight(0.06 * 25.4 / 72) > 0  # .ods'teki tipik `0.06pt`
    assert snap_lineweight(0.0001) > 0


def test_heavier_source_border_stays_heavier_after_snapping() -> None:
    """Sıralama korunmazsa başlık çizgisi ızgaradan ince görünebilirdi."""
    assert snap_lineweight(0.5) > snap_lineweight(0.06 * 25.4 / 72)


def test_snapping_is_monotonic() -> None:
    widths = [0.02, 0.1, 0.2, 0.35, 0.7, 1.4, 2.0]
    snapped = [snap_lineweight(w) for w in widths]
    assert snapped == sorted(snapped)


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
