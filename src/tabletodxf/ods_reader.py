"""`.ods` → `SheetModel`. `odfpy` yalnızca bu modülde geçer (F-001).

ADR-002 gereği görünümün tamamı buradan okunur: kenar başına kenarlık, dolgu,
hizalama, font, birleştirme, gizli satır/sütun ve her sayının **görünen** metni.
Uzunluklar kaynakta cm/inç/pt karışık gelir; hepsi mm'ye normalize edilir.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from pathlib import Path

from odf import teletype
from odf.namespaces import OFFICENS, STYLENS, TABLENS, TEXTNS
from odf.opendocument import load as load_odf

from .config import SourceConfig
from .errors import (
    FORMULA_NO_CACHE,
    MERGE_CROSSES_SELECTION,
    SELECTION_EMPTY,
    SRC_FORMAT,
    SRC_NOT_FOUND,
    SRC_RANGE_INVALID,
    SRC_SHEET_NOT_FOUND,
    TableToDxfError,
)
from .model import (
    BLACK,
    Border,
    Borders,
    Cell,
    FontSpec,
    HAlign,
    Rgb,
    SheetModel,
    VAlign,
    col_index_to_letters,
    letters_to_col_index,
)
from .report import Report

# ODF'in mutlak tavanı. Bunun ötesi ayrıştırma hatası değil, kullanım hatasıdır.
MAX_ROWS = 1_048_576
MAX_COLS = 16_384

# Sayı gibi davranan değer tipleri — hizalama kaynağı `value-type` olduğunda
# bunlar sağa, gerisi sola yaslanır (Calc'ın varsayılan davranışı).
_NUMERIC_VALUE_TYPES = frozenset({"float", "percentage", "currency", "date", "time"})

_LENGTH_RE = re.compile(r"^\s*(-?[0-9]*\.?[0-9]+)\s*([a-z%]*)\s*$", re.IGNORECASE)
_UNIT_TO_MM = {
    "mm": 1.0,
    "cm": 10.0,
    "in": 25.4,
    "pt": 25.4 / 72.0,
    "pc": 25.4 / 6.0,
    "px": 25.4 / 96.0,
    "": 1.0,
}

_RANGE_RE = re.compile(
    r"^\s*\$?([A-Za-z]{1,3})\$?([0-9]{1,7})"
    r"(?:\s*:\s*\$?([A-Za-z]{1,3})\$?([0-9]{1,7}))?\s*$"
)


# ── Uzunluk ve renk ayrıştırma ──────────────────────────────────────────────


def parse_length_mm(value: str | None, default: float = 0.0) -> float:
    """`"2.258cm"` → `22.58`. Birimsiz değer mm sayılır."""
    if not value:
        return default
    match = _LENGTH_RE.match(value)
    if match is None:
        return default
    number, unit = match.groups()
    factor = _UNIT_TO_MM.get(unit.lower())
    if factor is None:
        return default
    return float(number) * factor


def parse_color(value: str | None) -> Rgb | None:
    """`"#ff8800"` → `(255, 136, 0)`. `"transparent"` ve tanınmayan → `None`."""
    if not value:
        return None
    text = value.strip().lower()
    if text in ("transparent", "none", "auto"):
        return None
    if text.startswith("#") and len(text) == 7:
        try:
            return (int(text[1:3], 16), int(text[3:5], 16), int(text[5:7], 16))
        except ValueError:
            return None
    return None


def parse_border(
    value: str | None,
    *,
    default_color: Rgb = BLACK,
    borderless_width_pt: float = 0.5,
) -> Border:
    """`"0.06pt solid #000000"` → `Border(0.021, (0,0,0))`.

    `double` / `dashed` gibi çizgi biçimleri tek bir çizgiye indirgenir: DXF'te
    kenarlık bir `LWPOLYLINE` ve taşıdığı tek görsel nitelik kalınlık ile renk.
    """
    if not value:
        return Border(0.0, default_color)
    text = value.strip()
    if text.lower() in ("none", "hidden", ""):
        return Border(0.0, default_color)

    width_mm = 0.0
    color: Rgb = default_color
    for token in text.split():
        parsed_color = parse_color(token)
        if parsed_color is not None:
            color = parsed_color
            continue
        if _LENGTH_RE.match(token):
            width_mm = parse_length_mm(token)
    if width_mm <= 0.0:
        # "solid #000000" — kalınlık verilmemiş. Görünür bir kenarlık istendiği
        # kesin, o yüzden hairline kabul edilir; 0 döndürmek çizgiyi yok ederdi.
        # `borderless_width_pt = 0` verilirse böyle kenarlıklar çizilmez.
        width_mm = borderless_width_pt * (25.4 / 72.0)
    return Border(width_mm, color)


def parse_range(text: str) -> tuple[int, int, int, int]:
    """`"B3:C500"` → `(row0, col0, row1, col1)`, 0-tabanlı ve dahil.

    Ters verilen aralık (`C500:B3`) normalize edilir; kullanıcının seçim yönü
    çıktıyı değiştirmemeli.
    """
    match = _RANGE_RE.match(text or "")
    if match is None:
        raise TableToDxfError(
            SRC_RANGE_INVALID,
            op="parse_range",
            reason="range is not in A1:B2 form",
            range=text,
        )
    col_a, row_a, col_b, row_b = match.groups()
    if col_b is None:
        col_b, row_b = col_a, row_a
    try:
        c0, c1 = letters_to_col_index(col_a), letters_to_col_index(col_b)
    except ValueError as exc:
        raise TableToDxfError(
            SRC_RANGE_INVALID, op="parse_range", reason="invalid column reference", range=text
        ) from exc
    r0, r1 = int(row_a) - 1, int(row_b) - 1
    if r0 < 0 or r1 < 0:
        raise TableToDxfError(
            SRC_RANGE_INVALID, op="parse_range", reason="row numbers start at 1", range=text
        )
    r0, r1 = min(r0, r1), max(r0, r1)
    c0, c1 = min(c0, c1), max(c0, c1)
    if r1 >= MAX_ROWS or c1 >= MAX_COLS:
        raise TableToDxfError(
            SRC_RANGE_INVALID,
            op="parse_range",
            reason="range exceeds spreadsheet limits",
            range=text,
        )
    return r0, c0, r1, c1


# ── Stil çözümü ─────────────────────────────────────────────────────────────


@dataclass
class _StyleProps:
    """Bir hücre stilinin, kalıtım zinciri çözülmüş hâlde düz özellikleri."""

    cell: dict[str, str]
    paragraph: dict[str, str]
    text: dict[str, str]

    @classmethod
    def empty(cls) -> _StyleProps:
        return cls({}, {}, {})

    def merged_with(self, child: _StyleProps) -> _StyleProps:
        return _StyleProps(
            cell={**self.cell, **child.cell},
            paragraph={**self.paragraph, **child.paragraph},
            text={**self.text, **child.text},
        )


class _StyleResolver:
    """`style:style` adlarını çözülmüş özellik demetlerine çevirir.

    `style:parent-style-name` zinciri kökten yaprağa doğru birleştirilir; çözüm
    sonucu ada göre önbelleklenir çünkü aynı stil yüzlerce hücrede geçer.
    """

    def __init__(self, doc) -> None:  # noqa: ANN001 — odfpy tip vermiyor
        self._styles: dict[str, object] = {}
        self._cache: dict[str, _StyleProps] = {}
        self._default = _StyleProps.empty()

        for container in (doc.styles, doc.automaticstyles):
            if container is None:
                continue
            for element in container.childNodes:
                qname = getattr(element, "qname", None)
                if qname == (STYLENS, "style"):
                    name = element.getAttrNS(STYLENS, "name")
                    if name:
                        self._styles[name] = element
                elif qname == (STYLENS, "default-style"):
                    if element.getAttrNS(STYLENS, "family") == "table-cell":
                        self._default = self._extract(element)

    def _extract(self, element) -> _StyleProps:  # noqa: ANN001
        props = _StyleProps.empty()
        for child in element.childNodes:
            qname = getattr(child, "qname", None)
            if qname == (STYLENS, "table-cell-properties"):
                target = props.cell
            elif qname == (STYLENS, "paragraph-properties"):
                target = props.paragraph
            elif qname == (STYLENS, "text-properties"):
                target = props.text
            else:
                continue
            for (_ns, local), value in child.attributes.items():
                target[local] = value
        return props

    def resolve(self, name: str | None) -> _StyleProps:
        if not name:
            return self._default
        cached = self._cache.get(name)
        if cached is not None:
            return cached

        chain: list[object] = []
        seen: set[str] = set()
        current = name
        while current and current not in seen and current in self._styles:
            seen.add(current)
            element = self._styles[current]
            chain.append(element)
            current = element.getAttrNS(STYLENS, "parent-style-name")

        props = self._default
        for element in reversed(chain):  # kökten yaprağa
            props = props.merged_with(self._extract(element))
        self._cache[name] = props
        return props


# ── Sütun / satır iskeleti ──────────────────────────────────────────────────


@dataclass
class _Axis:
    """Genişletilmiş satır ya da sütun ekseni."""

    sizes_mm: list[float]
    hidden: list[bool]
    default_cell_style: list[str | None]


def _is_hidden(element) -> bool:  # noqa: ANN001
    return element.getAttrNS(TABLENS, "visibility") in ("collapse", "filter")


def _repeat_count(element, attr: str, limit: int) -> int:  # noqa: ANN001
    """Tekrar sayısı. Dosya sonundaki milyonluk tekrarlar `limit`'e kırpılır."""
    raw = element.getAttrNS(TABLENS, attr)
    if not raw:
        return 1
    try:
        count = int(raw)
    except ValueError:
        return 1
    return max(1, min(count, limit))


def _collect_columns(  # noqa: ANN001
    table, needed: int, resolver: _StyleResolver, default_width_mm: float
) -> _Axis:
    axis = _Axis([], [], [])

    def walk(node) -> None:  # noqa: ANN001
        for child in node.childNodes:
            if len(axis.sizes_mm) >= needed:
                return
            qname = getattr(child, "qname", None)
            if qname == (TABLENS, "table-column"):
                width = parse_length_mm(
                    _column_width(child, resolver), default_width_mm
                )
                hidden = _is_hidden(child)
                default_style = child.getAttrNS(TABLENS, "default-cell-style-name")
                remaining = needed - len(axis.sizes_mm)
                for _ in range(_repeat_count(child, "number-columns-repeated", remaining)):
                    axis.sizes_mm.append(width)
                    axis.hidden.append(hidden)
                    axis.default_cell_style.append(default_style)
            elif qname in (
                (TABLENS, "table-header-columns"),
                (TABLENS, "table-columns"),
                (TABLENS, "table-column-group"),
            ):
                walk(child)

    walk(table)
    while len(axis.sizes_mm) < needed:
        axis.sizes_mm.append(default_width_mm)
        axis.hidden.append(False)
        axis.default_cell_style.append(None)
    return axis


def _column_width(column, resolver: _StyleResolver) -> str | None:  # noqa: ANN001
    style_name = column.getAttrNS(TABLENS, "style-name")
    if not style_name:
        return None
    return resolver.resolve_column_width(style_name)


def _row_height(row, resolver: _StyleResolver) -> str | None:  # noqa: ANN001
    style_name = row.getAttrNS(TABLENS, "style-name")
    if not style_name:
        return None
    return resolver.resolve_row_height(style_name)


def _iter_rows(table, needed: int):  # noqa: ANN001
    """Satır elemanlarını, gruplar içinden düzleştirerek, belge sırasında verir."""
    produced = 0

    def walk(node):  # noqa: ANN001
        nonlocal produced
        for child in node.childNodes:
            if produced >= needed:
                return
            qname = getattr(child, "qname", None)
            if qname == (TABLENS, "table-row"):
                remaining = needed - produced
                count = _repeat_count(child, "number-rows-repeated", remaining)
                for _ in range(count):
                    if produced >= needed:
                        return
                    produced += 1
                    yield child
            elif qname in (
                (TABLENS, "table-header-rows"),
                (TABLENS, "table-rows"),
                (TABLENS, "table-row-group"),
            ):
                yield from walk(child)

    yield from walk(table)


# ── Ham hücre ───────────────────────────────────────────────────────────────


@dataclass
class _RawCell:
    style_name: str | None
    text: str
    value_type: str | None
    col_span: int
    row_span: int
    covered: bool
    has_formula: bool
    has_cached_value: bool


def _read_raw_cell(element, covered: bool) -> _RawCell:  # noqa: ANN001
    paragraphs: list[str] = []
    for child in element.childNodes:
        if getattr(child, "qname", None) == (TEXTNS, "p"):
            paragraphs.append(teletype.extractText(child))
    value_type = element.getAttrNS(OFFICENS, "value-type")
    has_formula = element.getAttrNS(TABLENS, "formula") is not None
    # LibreOffice formül hücresine daima hem `office:value-type` hem de görünen
    # metni yazar. İkisi de yoksa dosya başka bir araçtan gelmiş ve önbellek yok.
    has_cached_value = value_type is not None or bool(paragraphs)
    return _RawCell(
        style_name=element.getAttrNS(TABLENS, "style-name"),
        text="\n".join(paragraphs),
        value_type=value_type,
        col_span=_span(element, "number-columns-spanned"),
        row_span=_span(element, "number-rows-spanned"),
        covered=covered,
        has_formula=has_formula,
        has_cached_value=has_cached_value,
    )


def _span(element, attr: str) -> int:  # noqa: ANN001
    raw = element.getAttrNS(TABLENS, attr)
    if not raw:
        return 1
    try:
        return max(1, int(raw))
    except ValueError:
        return 1


def _read_row_cells(row, needed: int) -> list[_RawCell | None]:  # noqa: ANN001
    """Bir satırın hücrelerini `needed` sütuna kadar genişletir."""
    cells: list[_RawCell | None] = []
    for child in row.childNodes:
        if len(cells) >= needed:
            break
        qname = getattr(child, "qname", None)
        if qname == (TABLENS, "table-cell"):
            covered = False
        elif qname == (TABLENS, "covered-table-cell"):
            covered = True
        else:
            continue
        raw = _read_raw_cell(child, covered)
        remaining = needed - len(cells)
        for _ in range(_repeat_count(child, "number-columns-repeated", remaining)):
            cells.append(raw)
    while len(cells) < needed:
        cells.append(None)
    return cells


# ── Ana giriş ───────────────────────────────────────────────────────────────


def read(
    path: str | Path,
    sheet_name: str,
    range_text: str,
    report: Report,
    config: SourceConfig | None = None,
) -> SheetModel:
    """`.ods` dosyasından seçilen aralığı okur ve `SheetModel` döndürür."""
    config = config or SourceConfig()
    source = Path(path)
    if source.suffix.lower() != ".ods":
        raise TableToDxfError(
            SRC_FORMAT,
            op="read_source",
            reason="input must be .ods — open it in LibreOffice Calc and save as ODF spreadsheet",
            file=source.name,
            suffix=source.suffix or "(none)",
        )
    if not source.is_file():
        raise TableToDxfError(
            SRC_NOT_FOUND, op="read_source", reason="file not found", file=str(source)
        )

    _warn_if_stale(source, report, config.stale_check_suffixes)

    r0, c0, r1, c1 = parse_range(range_text)
    source_ref = f"{sheet_name}!{range_text.strip().upper()}"

    try:
        doc = load_odf(str(source))
    except Exception as exc:  # noqa: BLE001 — zip/xml katmanı çok çeşitli hata atıyor
        raise TableToDxfError(
            SRC_NOT_FOUND,
            op="read_source",
            reason="file could not be opened as an ODF spreadsheet",
            file=str(source),
            detail=type(exc).__name__,
        ) from exc

    table, available = _find_table(doc, sheet_name)
    report.debug("read_source", "sheet opened", cell=source_ref, sheets=len(available))

    resolver = _CellStyleResolver(doc)
    columns = _collect_columns(table, c1 + 1, resolver, config.default_col_width_mm)

    # Satırlar: seçim sonuna kadar oku. Birleştirme tespiti seçimin üstündeki ve
    # solundaki hücreleri de gerektirdiği için 0'dan başlanır.
    rows_meta: list[tuple[float, bool, str | None]] = []
    grid: list[list[_RawCell | None]] = []
    for row_element in _iter_rows(table, r1 + 1):
        height = parse_length_mm(
            _row_height(row_element, resolver), config.default_row_height_mm
        )
        rows_meta.append(
            (
                height,
                _is_hidden(row_element),
                row_element.getAttrNS(TABLENS, "default-cell-style-name"),
            )
        )
        grid.append(_read_row_cells(row_element, c1 + 1))
    while len(rows_meta) <= r1:
        rows_meta.append((config.default_row_height_mm, False, None))
        grid.append([None] * (c1 + 1))

    _check_merges(grid, r0, c0, r1, c1, sheet_name)

    kept_rows = [r for r in range(r0, r1 + 1) if not rows_meta[r][1]]
    kept_cols = [c for c in range(c0, c1 + 1) if not columns.hidden[c]]
    dropped_rows = (r1 - r0 + 1) - len(kept_rows)
    dropped_cols = (c1 - c0 + 1) - len(kept_cols)
    if dropped_rows or dropped_cols:
        report.info(
            "read_selection",
            "hidden rows/columns dropped",
            cell=source_ref,
            rows=dropped_rows,
            cols=dropped_cols,
        )
    if not kept_rows or not kept_cols:
        raise TableToDxfError(
            SELECTION_EMPTY,
            op="read_selection",
            reason="no visible rows or columns remain in the selection",
            cell=source_ref,
            visible_rows=len(kept_rows),
            visible_cols=len(kept_cols),
        )

    row_pos = {sheet_row: i for i, sheet_row in enumerate(kept_rows)}
    col_pos = {sheet_col: i for i, sheet_col in enumerate(kept_cols)}

    model = SheetModel(
        source_ref=source_ref,
        col_widths_mm=[columns.sizes_mm[c] for c in kept_cols],
        row_heights_mm=[rows_meta[r][0] for r in kept_rows],
        sheet_name=sheet_name,
        row_refs=list(kept_rows),
        col_refs=list(kept_cols),
    )

    for sheet_row in kept_rows:
        for sheet_col in kept_cols:
            raw = grid[sheet_row][sheet_col]
            if raw is not None and raw.covered:
                continue  # kapsanan hücre hiçbir şey üretmez
            cell_ref = f"{sheet_name}!{col_index_to_letters(sheet_col)}{sheet_row + 1}"
            if raw is not None and raw.has_formula and not raw.has_cached_value:
                raise TableToDxfError(
                    FORMULA_NO_CACHE,
                    op="read_cell",
                    reason="formula has no cached value",
                    cell=cell_ref,
                )
            style_name = _effective_style_name(
                raw, rows_meta[sheet_row][2], columns.default_cell_style[sheet_col]
            )
            props = resolver.resolve(style_name)

            # Birleştirme, gizli satır/sütunlar düşünce daralır: kapsanan alanın
            # görünür kalan parçası kadar uzanır.
            col_span = _visible_span(sheet_col, raw.col_span if raw else 1, col_pos)
            row_span = _visible_span(sheet_row, raw.row_span if raw else 1, row_pos)

            cell = _build_cell(
                row=row_pos[sheet_row],
                col=col_pos[sheet_col],
                raw=raw,
                props=props,
                col_span=col_span,
                row_span=row_span,
                config=config,
            )
            model.cells[(cell.row, cell.col)] = cell

    _mark_covered(model)
    return model


def _visible_span(start: int, span: int, keep: dict[int, int]) -> int:
    """Gizli satır/sütunlar düşünce birleştirmenin kaç görünür birime indiği."""
    if span <= 1:
        return 1
    return max(1, sum(1 for i in range(start, start + span) if i in keep))


def _effective_style_name(
    raw: _RawCell | None, row_default: str | None, col_default: str | None
) -> str | None:
    """Hücre > satır varsayılanı > sütun varsayılanı (ODF öncelik sırası)."""
    if raw is not None and raw.style_name:
        return raw.style_name
    return row_default or col_default


def _build_cell(
    *,
    row: int,
    col: int,
    raw: _RawCell | None,
    props: _StyleProps,
    col_span: int,
    row_span: int,
    config: SourceConfig,
) -> Cell:
    cell_props = props.cell
    text_props = props.text

    padding = _padding_mm(cell_props, config.default_padding_mm)
    borders = Borders(
        left=_border_side(cell_props, "left", config),
        right=_border_side(cell_props, "right", config),
        top=_border_side(cell_props, "top", config),
        bottom=_border_side(cell_props, "bottom", config),
    )
    font = FontSpec(
        size_pt=parse_length_pt(text_props.get("font-size"), config.default_font_size_pt),
        bold=text_props.get("font-weight", "normal") not in ("normal", "", "100", "200", "300"),
        italic=text_props.get("font-style", "normal") in ("italic", "oblique"),
        color=parse_color(text_props.get("color")) or config.default_text_color,
    )
    return Cell(
        row=row,
        col=col,
        text=raw.text if raw else "",
        h_align=_h_align(props, raw, config),
        v_align=_v_align(cell_props, config.default_v_align),
        font=font,
        borders=borders,
        fill=parse_color(cell_props.get("background-color")),
        padding_mm=padding,
        col_span=col_span,
        row_span=row_span,
        covered=False,
        wrap=(cell_props.get("wrap-option") or "no-wrap").lower() == "wrap",
        rotation_deg=parse_rotation_deg(cell_props.get("rotation-angle")),
    )


def parse_rotation_deg(value: str | None) -> float:
    """`style:rotation-angle` → derece, saat yönünün tersine, `[0, 360)`.

    ODF çıplak sayı da (`90`) birimli değer de (`90deg`) yazabiliyor.
    """
    if value is None:
        return 0.0
    text = str(value).strip().lower()
    for suffix in ("deg", "grad", "rad"):
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()
            break
    try:
        return float(text) % 360.0
    except ValueError:
        return 0.0


def parse_length_pt(value: str | None, default: float) -> float:
    """Font boyutu pt cinsinden istenir; kaynak `12pt` ya da `0.42cm` yazabilir."""
    if not value:
        return default
    mm = parse_length_mm(value, -1.0)
    if mm < 0:
        return default
    return mm / (25.4 / 72.0)


def _padding_mm(cell_props: dict[str, str], default_mm: float) -> float:
    """Yatay yerleşimde kullanılan tek bir dolgu değeri.

    Sol ve sağ ayrı verilmişse büyüğü alınır: metin her iki kenardan da güvenli
    mesafede kalsın diye. `Cell` tek bir `padding_mm` taşıyor (F-001).
    """
    sides = [
        parse_length_mm(cell_props.get(f"padding-{side}"), -1.0)
        for side in ("left", "right", "top", "bottom")
    ]
    present = [value for value in sides if value >= 0.0]
    uniform = parse_length_mm(cell_props.get("padding"), -1.0)
    if present:
        return max(present)
    if uniform >= 0.0:
        return uniform
    return default_mm


def _border_side(cell_props: dict[str, str], side: str, config: SourceConfig) -> Border:
    """Kenar başına değer, kısayol `fo:border`'ı ezer."""
    raw = cell_props.get(f"border-{side}")
    if raw is None:
        raw = cell_props.get("border")
    return parse_border(
        raw,
        default_color=config.default_border_color,
        borderless_width_pt=config.borderless_width_pt,
    )


_H_ALIGN_MAP: dict[str, HAlign] = {
    "start": "left",
    "left": "left",
    "end": "right",
    "right": "right",
    "center": "center",
    "justify": "left",
}


def _h_align(props: _StyleProps, raw: _RawCell | None, config: SourceConfig) -> HAlign:
    """Açık hizalama yoksa Calc'ın değer tipine göre kararı taklit edilir.

    Sayfada sağa yaslı görünen bir sayının çizimde sola kaymaması için gerekli;
    `.ods` bu durumda `fo:text-align` yazmaz, `style:text-align-source` alanını
    `value-type` bırakır. Tip başına hizalama `[source]` altından değiştirilebilir.
    """
    explicit = props.paragraph.get("text-align")
    source = props.cell.get("text-align-source", "fix")
    if explicit and source != "value-type":
        return _H_ALIGN_MAP.get(explicit.lower(), config.align_text)
    value_type = raw.value_type if raw else None
    if value_type in _NUMERIC_VALUE_TYPES:
        return config.align_numeric
    if value_type == "boolean":
        return config.align_boolean
    if explicit:
        return _H_ALIGN_MAP.get(explicit.lower(), config.align_text)
    return config.align_text


_V_ALIGN_MAP: dict[str, VAlign] = {
    "top": "top",
    "middle": "middle",
    "bottom": "bottom",
    # `automatic` haritada yok: yapılandırılmış varsayılana düşmesi gerekiyor,
    # `_v_align` onu ayrıca yakalıyor.
}


def _v_align(cell_props: dict[str, str], default: VAlign) -> VAlign:
    raw = (cell_props.get("vertical-align") or "").lower()
    if raw == "automatic":
        return default
    return _V_ALIGN_MAP.get(raw, default)


def _mark_covered(model: SheetModel) -> None:
    """Birleştirme kaynaklarının kapsadığı hücreleri `covered` işaretler.

    Okuma sırasında `.ods` zaten `covered-table-cell` veriyor, ama gizli
    satır/sütun düşürmesi kapsama alanını kaydırabiliyor; model kendi içinde
    tutarlı olsun diye yeniden hesaplanır.
    """
    for (row, col), cell in list(model.cells.items()):
        if cell.col_span == 1 and cell.row_span == 1:
            continue
        for r in range(row, min(row + cell.row_span, model.n_rows)):
            for c in range(col, min(col + cell.col_span, model.n_cols)):
                if (r, c) == (row, col):
                    continue
                existing = model.cells.get((r, c))
                base = existing if existing is not None else Cell(row=r, col=c, text="")
                model.cells[(r, c)] = replace(base, covered=True, col_span=1, row_span=1)


def _check_merges(
    grid: list[list[_RawCell | None]],
    r0: int,
    c0: int,
    r1: int,
    c1: int,
    sheet_name: str,
) -> None:
    """Seçim sınırını kesen birleştirme → durur (AC-10). Sessiz kırpma yok."""
    for row_index, row in enumerate(grid):
        for col_index, raw in enumerate(row):
            if raw is None or raw.covered:
                continue
            if raw.col_span == 1 and raw.row_span == 1:
                continue
            mr0, mc0 = row_index, col_index
            mr1, mc1 = row_index + raw.row_span - 1, col_index + raw.col_span - 1
            overlaps = not (mr1 < r0 or mr0 > r1 or mc1 < c0 or mc0 > c1)
            if not overlaps:
                continue
            contained = mr0 >= r0 and mc0 >= c0 and mr1 <= r1 and mc1 <= c1
            if contained:
                continue
            merge_ref = (
                f"{col_index_to_letters(mc0)}{mr0 + 1}:"
                f"{col_index_to_letters(mc1)}{mr1 + 1}"
            )
            raise TableToDxfError(
                MERGE_CROSSES_SELECTION,
                op="read_selection",
                reason="merge crosses selection edge",
                cell=f"{sheet_name}!{col_index_to_letters(mc0)}{mr0 + 1}",
                merge=merge_ref,
            )


def _find_table(doc, sheet_name: str):  # noqa: ANN001
    from odf.table import Table

    tables = doc.getElementsByType(Table)
    names = [t.getAttrNS(TABLENS, "name") for t in tables]
    for table, name in zip(tables, names, strict=True):
        if name == sheet_name:
            return table, names
    raise TableToDxfError(
        SRC_SHEET_NOT_FOUND,
        op="read_source",
        reason="sheet not found in workbook",
        sheet=sheet_name,
        available=", ".join(n for n in names if n),
    )


def _warn_if_stale(source: Path, report: Report, suffixes: tuple[str, ...]) -> None:
    """ADR-001'in ürettiği tek yeni hata modu: `.ods` bayat kalmış olabilir.

    `suffixes` boş verilirse kontrol tamamen kapanır.
    """
    for suffix in suffixes:
        sibling = source.with_suffix(suffix)
        try:
            if sibling.is_file() and sibling.stat().st_mtime > source.stat().st_mtime:
                report.warn(
                    "check_source",
                    "newer sibling workbook found",
                    ods=source.name,
                    sibling=sibling.name,
                )
        except OSError:
            continue


class _CellStyleResolver(_StyleResolver):
    """`_StyleResolver` + sütun genişliği / satır yüksekliği aramaları."""

    def __init__(self, doc) -> None:  # noqa: ANN001
        super().__init__(doc)
        self._column_widths: dict[str, str] = {}
        self._row_heights: dict[str, str] = {}
        for container in (doc.styles, doc.automaticstyles):
            if container is None:
                continue
            for element in container.childNodes:
                if getattr(element, "qname", None) != (STYLENS, "style"):
                    continue
                name = element.getAttrNS(STYLENS, "name")
                family = element.getAttrNS(STYLENS, "family")
                if not name:
                    continue
                for child in element.childNodes:
                    qname = getattr(child, "qname", None)
                    if family == "table-column" and qname == (
                        STYLENS,
                        "table-column-properties",
                    ):
                        width = child.getAttrNS(STYLENS, "column-width")
                        if width:
                            self._column_widths[name] = width
                    elif family == "table-row" and qname == (
                        STYLENS,
                        "table-row-properties",
                    ):
                        height = child.getAttrNS(STYLENS, "row-height")
                        if height:
                            self._row_heights[name] = height

    def resolve_column_width(self, style_name: str) -> str | None:
        return self._column_widths.get(style_name)

    def resolve_row_height(self, style_name: str) -> str | None:
        return self._row_heights.get(style_name)
