"""Test için `.ods` üretici.

Referans sayfa depoya ikili dosya olarak değil, **kod olarak** girer: golden
testin neyi doğruladığı diff'te görünür, ve sayfayı değiştirmek için
LibreOffice açmak gerekmez.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from odf.opendocument import OpenDocumentSpreadsheet
from odf.style import (
    ParagraphProperties,
    Style,
    TableCellProperties,
    TableColumnProperties,
    TableRowProperties,
    TextProperties,
)
from odf.table import CoveredTableCell, Table, TableCell, TableColumn, TableRow
from odf.text import P


@dataclass
class CellSpec:
    text: str = ""
    value: float | None = None  # verilirse hücre `float` tipinde olur
    formula: str | None = None
    bold: bool = False
    align: str | None = None  # "center" | "start" | "end"
    valign: str | None = None  # "top" | "middle" | "bottom"
    fill: str | None = None  # "#ffff00"
    border: str | None = None  # kısayol: dört kenar
    border_bottom: str | None = None
    font_size: str | None = None  # "12pt"
    padding: str | None = None  # "0.1cm"
    wrap: bool = False  # "metni kaydır"
    rotation: int | None = None  # style:rotation-angle, derece
    text_color: str | None = None  # "#ff0000" — fo:color
    col_span: int = 1
    row_span: int = 1
    covered: bool = False
    omit_cached_value: bool = False


@dataclass
class RowSpec:
    height: str = "0.45cm"
    hidden: bool = False
    cells: list[CellSpec] = field(default_factory=list)


@dataclass
class SheetSpec:
    name: str
    col_widths: list[str]
    hidden_cols: set[int] = field(default_factory=set)
    rows: list[RowSpec] = field(default_factory=list)


class _StyleFactory:
    """Aynı görünüm için tek otomatik stil üretir — gerçek Calc çıktısı da böyle."""

    def __init__(self, doc: OpenDocumentSpreadsheet) -> None:
        self._doc = doc
        self._cache: dict[tuple, Style] = {}
        self._counter = 0

    def cell_style(self, spec: CellSpec) -> Style | None:
        key = (
            spec.bold,
            spec.align,
            spec.valign,
            spec.fill,
            spec.border,
            spec.border_bottom,
            spec.font_size,
            spec.padding,
            spec.wrap,
            spec.rotation,
            spec.text_color,
        )
        if not any(key):
            return None
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        self._counter += 1
        style = Style(name=f"ce{self._counter}", family="table-cell")

        cell_attrs: dict[str, str] = {}
        if spec.fill:
            cell_attrs["backgroundcolor"] = spec.fill
        if spec.border:
            cell_attrs["border"] = spec.border
        if spec.border_bottom:
            cell_attrs["borderbottom"] = spec.border_bottom
        if spec.valign:
            cell_attrs["verticalalign"] = spec.valign
        if spec.padding:
            cell_attrs["padding"] = spec.padding
        if spec.wrap:
            cell_attrs["wrapoption"] = "wrap"
        if spec.rotation is not None:
            cell_attrs["rotationangle"] = str(spec.rotation)
        if cell_attrs:
            style.addElement(TableCellProperties(**cell_attrs))

        if spec.align:
            style.addElement(ParagraphProperties(textalign=spec.align))

        text_attrs: dict[str, str] = {}
        if spec.bold:
            text_attrs["fontweight"] = "bold"
        if spec.font_size:
            text_attrs["fontsize"] = spec.font_size
        if spec.text_color:
            text_attrs["color"] = spec.text_color
        if text_attrs:
            style.addElement(TextProperties(**text_attrs))

        self._doc.automaticstyles.addElement(style)
        self._cache[key] = style
        return style

    def column_style(self, width: str) -> Style:
        key = ("col", width)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        self._counter += 1
        style = Style(name=f"co{self._counter}", family="table-column")
        style.addElement(TableColumnProperties(columnwidth=width))
        self._doc.automaticstyles.addElement(style)
        self._cache[key] = style
        return style

    def row_style(self, height: str) -> Style:
        key = ("row", height)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        self._counter += 1
        style = Style(name=f"ro{self._counter}", family="table-row")
        style.addElement(TableRowProperties(rowheight=height))
        self._doc.automaticstyles.addElement(style)
        self._cache[key] = style
        return style


def build_ods(path: Path, sheets: list[SheetSpec]) -> Path:
    """Verilen sayfaları `.ods` olarak yazar ve gerçek yolu döndürür."""
    doc = OpenDocumentSpreadsheet()
    factory = _StyleFactory(doc)

    for sheet in sheets:
        table = Table(name=sheet.name)
        for index, width in enumerate(sheet.col_widths):
            attrs: dict[str, str] = {"stylename": factory.column_style(width)}
            if index in sheet.hidden_cols:
                attrs["visibility"] = "collapse"
            table.addElement(TableColumn(**attrs))

        for row_spec in sheet.rows:
            row_attrs: dict[str, object] = {"stylename": factory.row_style(row_spec.height)}
            if row_spec.hidden:
                row_attrs["visibility"] = "collapse"
            row = TableRow(**row_attrs)
            for cell_spec in row_spec.cells:
                row.addElement(_build_cell(cell_spec, factory))
            table.addElement(row)

        doc.spreadsheet.addElement(table)

    # odfpy `save` uzantıyı kendisi ekler; iki kez eklenmesin diye çıkarılıyor.
    stem = path.with_suffix("")
    doc.save(str(stem), True)
    return stem.with_suffix(".ods")


def _build_cell(spec: CellSpec, factory: _StyleFactory):  # noqa: ANN202
    if spec.covered:
        return CoveredTableCell()

    attrs: dict[str, object] = {}
    style = factory.cell_style(spec)
    if style is not None:
        attrs["stylename"] = style
    if spec.col_span > 1:
        attrs["numbercolumnsspanned"] = str(spec.col_span)
    if spec.row_span > 1:
        attrs["numberrowsspanned"] = str(spec.row_span)
    if spec.formula is not None:
        attrs["formula"] = spec.formula

    # `omit_cached_value` LibreOffice dışı bir araçtan gelmiş dosyayı taklit
    # eder: formül var, önbelleklenmiş sonuç yok → FORMULA_NO_CACHE.
    if not spec.omit_cached_value:
        if spec.value is not None:
            attrs["valuetype"] = "float"
            attrs["value"] = str(spec.value)
        elif spec.text:
            attrs["valuetype"] = "string"

    cell = TableCell(**attrs)
    if spec.text and not spec.omit_cached_value:
        cell.addElement(P(text=spec.text))
    return cell
