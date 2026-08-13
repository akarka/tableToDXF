"""Ortak test kurulumu ve referans sayfa tanımı."""

from __future__ import annotations

from pathlib import Path

import pytest

from fixtures.ods_builder import CellSpec, RowSpec, SheetSpec, build_ods
from tabletodxf.cli import resolve_font
from tabletodxf.errors import TableToDxfError
from tabletodxf.metrics import FontMetrics
from tabletodxf.report import Report

BORDER_THIN = "0.06pt solid #000000"
BORDER_THICK = "0.5pt solid #000000"

# Referans sayfa — `Mahal`, seçim `B2:E7`.
#
#      A       B         C                    D (gizli)   E
#  1   —       üst
#  2           Kod       Mahal Adı            Gizli       m²      ← başlık, dolgulu
#  3           101 ┐     Zemin kat koridoru   x           12,50
#  4           (kapsanan)│ Birleşik alan ────────────┐    8,00
#  5   ← gizli satır
#  6           103       (sığmayan uzun metin)        ─    3,00
#  7   ← seçimin sonunda boş satır (AC-5: kırpılmaz)
#
# Kapsanan alanlar: B3:B4 (dikey birleştirme), C4:D4 (yatay birleştirme).
REFERENCE_SHEET = "Mahal"
REFERENCE_RANGE = "B2:E7"
OVERFLOW_TEXT = "Bu metin hücreye kesinlikle sığmayacak kadar uzun bir açıklama"


def _header(text: str) -> CellSpec:
    return CellSpec(
        text=text,
        bold=True,
        align="center",
        valign="middle",
        fill="#ffff00",
        border=BORDER_THIN,
        border_bottom=BORDER_THICK,
    )


def _body(text: str = "", value: float | None = None, **kwargs) -> CellSpec:
    return CellSpec(text=text, value=value, border=BORDER_THIN, **kwargs)


def reference_spec() -> SheetSpec:
    return SheetSpec(
        name=REFERENCE_SHEET,
        col_widths=["1cm", "3cm", "5cm", "2cm", "2.5cm"],
        hidden_cols={3},  # D sütunu gizli
        rows=[
            RowSpec(height="0.45cm", cells=[CellSpec(), CellSpec(text="üst")]),
            RowSpec(
                height="0.6cm",
                cells=[
                    CellSpec(),
                    _header("Kod"),
                    _header("Mahal Adı"),
                    _header("Gizli"),
                    _header("m²"),
                ],
            ),
            RowSpec(
                height="0.45cm",
                cells=[
                    CellSpec(),
                    _body("101", row_span=2),
                    _body("Zemin kat koridoru"),
                    _body("x"),
                    _body("12,50", value=12.5),
                ],
            ),
            RowSpec(
                height="0.45cm",
                cells=[
                    CellSpec(),
                    CellSpec(covered=True),  # B3'ün dikey birleştirmesi
                    _body("Birleşik alan", col_span=2, align="center"),
                    CellSpec(covered=True),
                    _body("8,00", value=8.0),
                ],
            ),
            RowSpec(
                height="0.45cm",
                hidden=True,
                cells=[CellSpec(), _body("gizli satır"), _body("düşecek")],
            ),
            RowSpec(
                height="0.45cm",
                cells=[
                    CellSpec(),
                    _body("103"),
                    _body(OVERFLOW_TEXT),
                    _body(""),
                    _body("3,00", value=3.0),
                ],
            ),
            # AC-5: sondaki boş satır. İçeriği yok ama kullanıcı kenarlıklarını
            # çekmiş — "kendi yükseklikleri ve kenarlıklarıyla çizilir".
            RowSpec(
                height="0.45cm",
                cells=[CellSpec(), _body(), _body(), _body(), _body()],
            ),
        ],
    )


@pytest.fixture(scope="session")
def reference_ods(tmp_path_factory: pytest.TempPathFactory) -> Path:
    directory = tmp_path_factory.mktemp("reference")
    return build_ods(directory / "mahal.ods", [reference_spec()])


@pytest.fixture(scope="session")
def font_path() -> Path:
    """Varsayılan font sistemde yoksa ölçüme dayanan testler atlanır."""
    try:
        return resolve_font("NotoSans-Regular.ttf")
    except TableToDxfError:
        pytest.skip("NotoSans-Regular.ttf not installed on this machine")


@pytest.fixture(scope="session")
def metrics(font_path: Path) -> FontMetrics:
    return FontMetrics.from_file(font_path)


@pytest.fixture
def report() -> Report:
    import io

    return Report(stream=io.StringIO())
