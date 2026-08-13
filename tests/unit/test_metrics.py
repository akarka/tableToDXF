"""TTF ölçümü ve sığdırma sınırları."""

from __future__ import annotations

from pathlib import Path

import pytest

from tabletodxf.errors import FONT_NOT_FOUND, TableToDxfError
from tabletodxf.metrics import PT_TO_MM, FontMetrics, fits


def test_missing_font_is_an_error(tmp_path: Path) -> None:
    """Ölçüm yapılamadan çıktı üretmek anlamsız — bu ERROR, WARN değil."""
    with pytest.raises(TableToDxfError) as excinfo:
        FontMetrics.from_file(tmp_path / "yok.ttf")
    assert excinfo.value.code == FONT_NOT_FOUND


def test_non_font_file_is_reported_as_font_error(tmp_path: Path) -> None:
    fake = tmp_path / "sahte.ttf"
    fake.write_bytes(b"not a font at all")
    with pytest.raises(TableToDxfError) as excinfo:
        FontMetrics.from_file(fake)
    assert excinfo.value.code == FONT_NOT_FOUND


def test_width_scales_linearly_with_size(metrics: FontMetrics) -> None:
    at_10 = metrics.text_width_mm("Mahal", 10.0)
    at_20 = metrics.text_width_mm("Mahal", 20.0)
    assert at_20 == pytest.approx(at_10 * 2)


def test_width_is_additive_over_characters(metrics: FontMetrics) -> None:
    combined = metrics.text_width_mm("AB", 10.0)
    separate = metrics.text_width_mm("A", 10.0) + metrics.text_width_mm("B", 10.0)
    assert combined == pytest.approx(separate)


def test_empty_string_has_no_width(metrics: FontMetrics) -> None:
    assert metrics.text_width_mm("", 12.0) == 0.0


def test_longer_text_is_wider(metrics: FontMetrics) -> None:
    short = metrics.text_width_mm("Kod", 10.0)
    long = metrics.text_width_mm("Zemin kat koridoru", 10.0)
    assert long > short


def test_known_string_width_is_plausible(metrics: FontMetrics) -> None:
    """10pt'de 18 karakterlik bir dize kabaca 30–45 mm arasında olmalı.

    Kesin değer fonta bağlı; test ölçümün büyüklük mertebesini korur, böylece
    birim karışıklığı (pt ↔ mm ↔ em) sessizce geçmez.
    """
    width = metrics.text_width_mm("Zemin kat koridoru", 10.0)
    assert 30.0 < width < 45.0


def test_cap_height_is_below_em_size(metrics: FontMetrics) -> None:
    """DXF metin yüksekliği büyük harf yüksekliğidir, em boyu değil."""
    em_mm = 10.0 * PT_TO_MM
    cap = metrics.cap_height_mm(10.0)
    assert 0.5 * em_mm < cap < em_mm


def test_unknown_glyph_still_measures(metrics: FontMetrics) -> None:
    """Fontta olmayan kod noktası ölçümü çökertmemeli — yedek advance kullanılır."""
    assert metrics.text_width_mm("\U0001f600", 10.0) > 0.0


def test_fits_boundaries() -> None:
    assert fits(10.0, 10.0)  # tam sığan sığmış sayılır
    assert fits(9.999, 10.0)
    assert not fits(10.001, 10.0)


def test_fits_tolerates_float_noise() -> None:
    """Tolerans olmadan aynı girdi platforma göre farklı sonuç verebilirdi (AC-12)."""
    accumulated = sum(0.1 for _ in range(100))  # 9.999999999999998
    assert fits(accumulated, 10.0)
