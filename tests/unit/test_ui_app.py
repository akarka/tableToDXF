"""`ui.app`'daki saf yardımcılar — Tk kurmadan test edilir (F-003).

`app.py` modül seviyesinde `tkinter` içe aktarır ama yalnızca içe aktarmak
bir Tk kökü gerektirmez; `MainWindow`'un asıl widget kurulumu burada değil,
gerçek Tk ile yapılan manuel doğrulamada kapsanır (F-003 → Test Plan).
"""

from __future__ import annotations

import pytest

from tabletodxf.ui.app import strip_wrapping_quotes, suggest_block_name


# ── strip_wrapping_quotes ────────────────────────────────────────────────


def test_strips_windows_copy_as_path_quoting() -> None:
    """Gezgin'in "Yol olarak kopyala"sı tam olarak bunu üretir."""
    assert strip_wrapping_quotes('"C:\\yol\\mahal.ods"') == "C:\\yol\\mahal.ods"


def test_strips_single_quotes_too() -> None:
    assert strip_wrapping_quotes("'C:\\yol\\mahal.ods'") == "C:\\yol\\mahal.ods"


def test_unquoted_path_is_untouched() -> None:
    assert strip_wrapping_quotes("C:\\yol\\mahal.ods") == "C:\\yol\\mahal.ods"


def test_surrounding_whitespace_is_trimmed() -> None:
    assert strip_wrapping_quotes('  "C:\\yol\\mahal.ods"  ') == "C:\\yol\\mahal.ods"


def test_mismatched_quotes_are_left_alone() -> None:
    """Yalnızca başta ve sonda **eşleşen** tırnak temizlenir."""
    assert strip_wrapping_quotes("\"C:\\yol\\mahal.ods'") == "\"C:\\yol\\mahal.ods'"


def test_a_single_quote_character_alone_is_not_stripped() -> None:
    assert strip_wrapping_quotes('"') == '"'


def test_empty_and_whitespace_only_text() -> None:
    assert strip_wrapping_quotes("") == ""
    assert strip_wrapping_quotes("   ") == ""


def test_quoted_path_now_has_the_ods_suffix_recognized() -> None:
    """Bu, gerçekte görülen hatanın kökeniydi: tırnaklı yolun `.suffix`'i
    `.ods` değil `.ods"` dönüyordu."""
    from pathlib import Path

    quoted = '"C:\\yol\\mahal.ods"'
    assert Path(quoted).suffix.lower() != ".ods"  # temizlenmeden hata verir
    assert Path(strip_wrapping_quotes(quoted)).suffix.lower() == ".ods"


def test_combines_filename_stem_and_sheet() -> None:
    assert suggest_block_name(r"C:\yol\mahal.ods", "Mahal") == "mahal_Mahal"


def test_spaces_become_underscores() -> None:
    assert (
        suggest_block_name(r"C:\yol\c.ods", "Numarataj_1692 Marina P")
        == "c_Numarataj_1692_Marina_P"
    )


def test_forbidden_symbol_characters_become_underscores() -> None:
    assert suggest_block_name("c.ods", 'Kat 1: "Zemin"') == "c_Kat_1_Zemin"


def test_consecutive_underscores_are_collapsed() -> None:
    assert suggest_block_name("c.ods", "  Mahal  ") == "c_Mahal"


def test_missing_sheet_falls_back_to_filename_only() -> None:
    assert suggest_block_name(r"C:\yol\mahal.ods", "") == "mahal"


def test_missing_source_falls_back_to_sheet_only() -> None:
    assert suggest_block_name("", "Mahal") == "Mahal"


def test_both_missing_is_empty_string() -> None:
    assert suggest_block_name("", "") == ""
    assert suggest_block_name("   ", "   ") == ""


def test_turkish_characters_survive() -> None:
    assert suggest_block_name("İç Mekan.ods", "Ölçü") == "İç_Mekan_Ölçü"


@pytest.mark.parametrize(
    "sheet",
    ["Kat/1", "Kat<1>", "Kat|1", "Kat*1", "Kat?1", "Kat;1", "Kat=1", "Kat,1"],
)
def test_every_forbidden_character_is_scrubbed(sheet: str) -> None:
    result = suggest_block_name("c.ods", sheet)
    assert not set(result) & {"<", ">", "/", "\\", '"', ";", "?", "*", "|", ",", "="}
