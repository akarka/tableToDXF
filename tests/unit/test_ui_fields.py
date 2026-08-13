"""`ui.fields` — etiket/yardım eşlemesi ve F-002 ile senkronizasyonu (F-003)."""

from __future__ import annotations

from dataclasses import fields as dc_fields
from typing import get_type_hints

import pytest

from tabletodxf.config import Config
from tabletodxf.ui.fields import SECTION_TITLES, _RAW, field_meta, section_title


def test_unknown_field_falls_back_to_its_raw_name_not_a_crash() -> None:
    """F-002'ye eklenip burada unutulan bir ayar sessizce kaybolmamalı."""
    meta = field_meta("layout", "hic_boyle_bir_ayar_yok")
    assert meta.label == "hic_boyle_bir_ayar_yok"
    assert meta.help == ""


def test_unknown_section_falls_back_too() -> None:
    meta = field_meta("hic_boyle_bir_bolum_yok", "x")
    assert meta.label == "x"


def test_section_title_falls_back_to_the_key() -> None:
    assert section_title("hic_boyle_bir_bolum_yok") == "hic_boyle_bir_bolum_yok"


# ── F-002 ile senkronizasyon (kanarya testi) ────────────────────────────────
#
# `_RAW` elle tutuluyor (F-003 Open Questions — tek doğru kaynak değil). Bu
# testler `config.py` değiştiğinde `fields.py`'nin unutulmadığını garanti
# etmiyor (eksik alan sessizce ham adıyla gösterilir, hata değildir) ama
# "hiç kimse fark etmedi" durumunu görünür kılıyor: CI'da kırmızı olur.


def _all_config_fields() -> set[tuple[str, str]]:
    hints = get_type_hints(Config)
    pairs: set[tuple[str, str]] = set()
    for section_field in dc_fields(Config):
        section_type = hints[section_field.name]
        for f in dc_fields(section_type):
            pairs.add((section_field.name, f.name))
    return pairs


def test_every_section_has_a_ui_title() -> None:
    for section_field in dc_fields(Config):
        assert section_field.name in SECTION_TITLES, section_field.name


def test_every_config_field_has_a_label_and_help_entry() -> None:
    missing = _all_config_fields() - set().union(
        *({(section, key) for key in keys} for section, keys in _RAW.items())
    )
    assert not missing, f"fields.py'de eksik: {sorted(missing)}"


def test_raw_table_does_not_reference_fields_that_no_longer_exist() -> None:
    """Silinmiş bir ayarın etiketi ölü kod olarak kalmamalı."""
    real = _all_config_fields()
    stale = {
        (section, key)
        for section, keys in _RAW.items()
        for key in keys
        if (section, key) not in real
    }
    assert not stale, f"fields.py'de artık var olmayan alanlar: {sorted(stale)}"


@pytest.mark.parametrize("section,key", sorted(_all_config_fields()))
def test_every_real_field_has_a_non_empty_label(section: str, key: str) -> None:
    assert field_meta(section, key).label.strip()
