"""`SheetModel` → çizilecek varlıkların listesi.

Bu modül `odfpy`'yi de `ezdxf`'i de görmez; girdisi normalize edilmiş model,
çıktısı saf geometridir. cm → çizim birimi çevrimi **yalnızca burada** ve tek
bir çarpanla yapılır (F-001).

Koordinat sistemi: origin seçimin sol üst köşesi `(0, 0)`; X sağa, Y aşağı doğru
negatif.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

from .metrics import FontMetrics, fits
from .model import Border, Cell, HAlign, Rgb, SheetModel, VAlign
from .report import Report

Point = tuple[float, float]

OverflowMode = Literal["mtext", "marker", "full"]
MARKER_CHAR = "#"

# Calc'ta "dolgu yok" olan hücre ekranda **beyaz** görünür, saydam değil.
# Dolgusuz hücre için hiç varlık üretmezsek çizimde altındaki geometri görünür
# ve tablo sayfadakine benzemez (ADR-002). Bu yüzden seçimin tamamına, her
# şeyin arkasına opak beyaz bir zemin serilir.
BACKGROUND_COLOR: Rgb = (255, 255, 255)


@dataclass(frozen=True)
class FillShape:
    """Dolu dörtgen; hücre kutusunun tamamını kaplar.

    Köşeler **halka sırasında**: sol-üst, sağ-üst, sağ-alt, sol-alt. DXF
    karşılığını `dxf_writer` seçer.
    """

    corners: tuple[Point, Point, Point, Point]
    color: Rgb


@dataclass(frozen=True)
class BorderLine:
    """Eş doğrultulu kenar parçalarının birleştirilmiş hâli — `LWPOLYLINE`."""

    start: Point
    end: Point
    color: Rgb
    width_mm: float


@dataclass(frozen=True)
class TextItem:
    text: str
    insert: Point  # taban çizgisi üzerinde, hizalama noktasında
    height: float  # çizim birimi; büyük harf yüksekliği
    h_align: HAlign
    v_align: VAlign
    color: Rgb
    rotation_deg: float = 0.0  # saat yönünün tersine
    is_marker: bool = False


@dataclass(frozen=True)
class TextBox:
    """`MTEXT` — genişliği AutoCAD'de tutamakla değiştirilebilen metin kutusu.

    Taşan hücreler için kullanılır: metin gizlenmez, ve alıcı sütuna sığdırmak
    için çizim üzerinde küçük düzeltmeler yapabilir. `TextItem`'dan farkı,
    çapanın taban çizgisi değil **bağlanma noktası** (attachment point) olması —
    `MTEXT` kendi kutusunu bu noktaya asar, satır bölmeyi AutoCAD yapar.
    """

    text: str  # satır sonları `\n`; DXF kaçışlarını yazıcı uygular
    insert: Point  # bağlanma noktası
    width: float  # referans dikdörtgen genişliği, çizim birimi
    height: float  # karakter yüksekliği
    h_align: HAlign
    v_align: VAlign
    color: Rgb
    rotation_deg: float = 0.0


@dataclass
class Drawing:
    # Seçimin tamamını kaplayan opak zemin. Ayrı bir alanda duruyor çünkü bir
    # hücre dolgusu değil; ve "en arkada" olması liste sırasına değil, yazıcının
    # onu ilk yazmasına bağlı — bunu veri modelinde görünür kılmak istiyoruz.
    background: FillShape | None = None
    fills: list[FillShape] = field(default_factory=list)
    lines: list[BorderLine] = field(default_factory=list)
    texts: list[TextItem] = field(default_factory=list)
    markers: list[TextItem] = field(default_factory=list)
    boxes: list[TextBox] = field(default_factory=list)  # taşan hücreler, `MTEXT`

    @property
    def entity_count(self) -> int:
        return (
            (1 if self.background is not None else 0)
            + len(self.fills)
            + len(self.lines)
            + len(self.texts)
            + len(self.markers)
            + len(self.boxes)
        )


def build(
    model: SheetModel,
    metrics: FontMetrics,
    report: Report,
    *,
    scale_cm_to_units: float = 10.0,
    overflow: OverflowMode = "mtext",
) -> Drawing:
    """Modeli çizilecek varlıklara çevirir. Üretim sırası F-001'deki sıradır."""
    units_per_mm = scale_cm_to_units / 10.0

    xs = _cumulative(model.col_widths_mm, units_per_mm, sign=1.0)
    ys = _cumulative(model.row_heights_mm, units_per_mm, sign=-1.0)

    drawing = Drawing()
    drawing.background = _background(model, xs, ys)
    _emit_fills(model, xs, ys, drawing)
    _emit_borders(model, xs, ys, drawing)
    _emit_texts(
        model,
        xs,
        ys,
        metrics,
        report,
        drawing,
        units_per_mm=units_per_mm,
        overflow=overflow,
    )
    return drawing


def _cumulative(sizes_mm: list[float], units_per_mm: float, *, sign: float) -> list[float]:
    """`n` uzunluktan `n+1` ızgara koordinatı. `xs[i]` i. hücrenin başlangıcı."""
    coords = [0.0]
    total = 0.0
    for size in sizes_mm:
        total += size * units_per_mm * sign
        coords.append(total)
    return coords


def _visible_cells(model: SheetModel) -> list[Cell]:
    """Kapsanmayan hücreler, deterministik sırada (AC-12)."""
    cells = [
        model.cell(row, col)
        for row in range(model.n_rows)
        for col in range(model.n_cols)
    ]
    return [cell for cell in cells if not cell.covered]


def _cell_box(
    cell: Cell, model: SheetModel, xs: list[float], ys: list[float]
) -> tuple[float, float, float, float]:
    """`(left, top, right, bottom)`. Birleştirilmiş hücrede kutu birleşik alandır."""
    col_end = min(cell.col + cell.col_span, model.n_cols)
    row_end = min(cell.row + cell.row_span, model.n_rows)
    return xs[cell.col], ys[cell.row], xs[col_end], ys[row_end]


# ── 4. Zemin ve dolgular ────────────────────────────────────────────────────


def _background(model: SheetModel, xs: list[float], ys: list[float]) -> FillShape | None:
    """Seçimin tamamını kaplayan tek bir opak beyaz dörtgen.

    Hücre başına beyaz dolgu üretmek yerine tek dörtgen: N yerine 1 varlık,
    hücreler arasında dikiş yok, ve renkli dolgular bunun üstüne bindiği için
    sonuç aynı. Kenarlıklar ve metinler de üstte kalır.

    **Sonuç opaktır:** blok bir çizime yerleştirildiğinde altındaki geometriyi
    örter. İstenen davranış bu — sayfada beyaz görünen hücre çizimde de beyaz
    olmalı — ama tabloyu mevcut çizimin üstüne bindirmek isteyen biri için
    dikkat edilecek bir nokta.
    """
    if model.n_rows == 0 or model.n_cols == 0:
        return None
    right, bottom = xs[-1], ys[-1]
    return FillShape(
        corners=((0.0, 0.0), (right, 0.0), (right, bottom), (0.0, bottom)),
        color=BACKGROUND_COLOR,
    )


def _emit_fills(model: SheetModel, xs: list[float], ys: list[float], drawing: Drawing) -> None:
    for cell in _visible_cells(model):
        if cell.fill is None:
            continue
        left, top, right, bottom = _cell_box(cell, model, xs, ys)
        drawing.fills.append(
            FillShape(
                corners=((left, top), (right, top), (right, bottom), (left, bottom)),
                color=cell.fill,
            )
        )


# ── 5. Kenarlıklar ──────────────────────────────────────────────────────────


def _stronger(current: Border | None, candidate: Border) -> Border | None:
    """Paylaşılan kenar tekilleştirmesi: kalın olan kazanır, eşitse ilk gelen.

    Aynı çizgi asla iki kez çizilmez — A'nın sağ kenarı ile B'nin sol kenarı
    aynı ızgara parçasıdır ve `.ods` ikisini de saklar.
    """
    if not candidate.visible:
        return current
    if current is None:
        return candidate
    return candidate if candidate.width_mm > current.width_mm else current


def _collect_edges(
    model: SheetModel,
) -> tuple[dict[tuple[int, int], Border], dict[tuple[int, int], Border]]:
    """Yatay ve dikey ızgara parçalarının kazanan kenarlıkları.

    Yatay anahtar `(row_boundary, col)`, dikey anahtar `(col_boundary, row)`.
    Birleştirilmiş alanın içindeki parçalar hiç anahtar almaz: kapsanan hücreler
    kenar üretmez, birleştiren hücre ise yalnızca dış sınırına yazar.
    """
    horizontal: dict[tuple[int, int], Border] = {}
    vertical: dict[tuple[int, int], Border] = {}

    def claim(edges: dict[tuple[int, int], Border], key: tuple[int, int], border: Border) -> None:
        winner = _stronger(edges.get(key), border)
        if winner is not None:
            edges[key] = winner

    for cell in _visible_cells(model):
        col_end = min(cell.col + cell.col_span, model.n_cols)
        row_end = min(cell.row + cell.row_span, model.n_rows)

        for col in range(cell.col, col_end):
            claim(horizontal, (cell.row, col), cell.borders.top)
            claim(horizontal, (row_end, col), cell.borders.bottom)

        for row in range(cell.row, row_end):
            claim(vertical, (cell.col, row), cell.borders.left)
            claim(vertical, (col_end, row), cell.borders.right)

    return horizontal, vertical


def _emit_borders(
    model: SheetModel, xs: list[float], ys: list[float], drawing: Drawing
) -> None:
    horizontal, vertical = _collect_edges(model)

    for row, run_start, run_end, border in _merge_runs(horizontal):
        drawing.lines.append(
            BorderLine(
                start=(xs[run_start], ys[row]),
                end=(xs[run_end + 1], ys[row]),
                color=border.color,
                width_mm=border.width_mm,
            )
        )
    for col, run_start, run_end, border in _merge_runs(vertical):
        drawing.lines.append(
            BorderLine(
                start=(xs[col], ys[run_start]),
                end=(xs[col], ys[run_end + 1]),
                color=border.color,
                width_mm=border.width_mm,
            )
        )


def _merge_runs(
    edges: dict[tuple[int, int], Border],
) -> list[tuple[int, int, int, Border]]:
    """Eş doğrultulu birleştirme: aynı kalınlık ve renkteki ardışık parçalar tek çizgi.

    Hücre başına ayrı `LINE` üretmek varlık sayısını patlatır — 500 satırlık bir
    tabloda binlerce yerine yüzlerce varlık kalır.
    """
    runs: list[tuple[int, int, int, Border]] = []
    by_track: dict[int, list[int]] = {}
    for track, index in edges:
        by_track.setdefault(track, []).append(index)

    for track in sorted(by_track):
        indices = sorted(by_track[track])
        run_start = indices[0]
        previous = indices[0]
        current = edges[(track, run_start)]
        for index in indices[1:]:
            border = edges[(track, index)]
            contiguous = index == previous + 1
            same_look = (
                border.width_mm == current.width_mm and border.color == current.color
            )
            if contiguous and same_look:
                previous = index
                continue
            runs.append((track, run_start, previous, current))
            run_start, previous, current = index, index, border
        runs.append((track, run_start, previous, current))
    return runs


# ── 6. Metinler ─────────────────────────────────────────────────────────────


def _emit_texts(
    model: SheetModel,
    xs: list[float],
    ys: list[float],
    metrics: FontMetrics,
    report: Report,
    drawing: Drawing,
    *,
    units_per_mm: float,
    overflow: OverflowMode,
) -> None:
    for cell in _visible_cells(model):
        if not cell.text:
            continue
        box = _cell_box(cell, model, xs, ys)
        padding_units = cell.padding_mm * units_per_mm
        size_pt = cell.font.size_pt

        # Metin kendi ekseninde ölçülür. 90° döndürülmüş bir başlıkta metnin
        # uzadığı yön hücrenin **yüksekliğidir**; genişliğe bakmak dar sütundaki
        # her dikey başlığı sahte bir taşma yapardı.
        direction, up = _text_axes(cell.rotation_deg)
        along_min, along_max = _project(box, direction)
        across_min, across_max = _project(box, up)

        available_mm = ((along_max - along_min) - 2 * padding_units) / units_per_mm

        lines = cell.text.split("\n")
        if cell.wrap:
            lines = _wrap(lines, metrics, size_pt, available_mm)

        widest_mm = max(metrics.text_width_mm(line, size_pt) for line in lines)
        overflowed = not fits(widest_mm, available_mm)

        cap_units = metrics.cap_height_mm(size_pt) * units_per_mm
        step_units = metrics.line_height_mm(size_pt) * units_per_mm

        use_box = overflowed and overflow == "mtext"
        # Kaydırma açıkken işaret basılmaz: kaydırma zaten sığdırma yöntemidir,
        # `###` onu görünmez kılardı. Geriye tek bir kelimenin satıra sığmadığı
        # durum kalır; orada da metni yazmak `###`ten bilgilendiricidir.
        use_marker = overflowed and overflow == "marker" and not cell.wrap

        if overflowed:
            report.warn(
                "render_cell",
                "text overflow",
                cell=model.ref(cell.row, cell.col),
                avail_mm=available_mm,
                text_mm=widest_mm,
                mode="mtext" if use_box else ("marker" if use_marker else ("wrap" if cell.wrap else "full")),
                text=cell.text.replace("\n", " "),
            )

        if use_box:
            # Satır bölmeyi AutoCAD yapar; ölçtüğümüz satırlar değil, hücrenin
            # **özgün** metni gönderilir. Kutu genişliği hücreninki kadardır —
            # alıcı tutamakla değiştirip yerleşimi düzeltebilir.
            drawing.boxes.append(
                TextBox(
                    text=cell.text,
                    insert=_frame_point(
                        _anchor_along(cell.h_align, along_min, along_max, padding_units),
                        _anchor_across(cell.v_align, across_min, across_max, padding_units),
                        direction,
                        up,
                    ),
                    width=(along_max - along_min) - 2 * padding_units,
                    height=cap_units,
                    h_align=cell.h_align,
                    v_align=cell.v_align,
                    color=cell.font.color,
                    rotation_deg=cell.rotation_deg,
                )
            )
            continue

        if use_marker:
            lines = [_marker_run(metrics, size_pt, available_mm)]

        block_units = (len(lines) - 1) * step_units + cap_units
        across_units = (across_max - across_min) - 2 * padding_units
        if cell.wrap and block_units > across_units + 1e-9:
            # Calc satırı büyütür; `.ods` büyümüş yüksekliği saklar. Buraya
            # düşüyorsak kaynak satır elle küçültülmüş demektir — metin çizilir
            # ama hücreyi taşar.
            report.warn(
                "render_cell",
                "wrapped text taller than cell",
                cell=model.ref(cell.row, cell.col),
                lines=len(lines),
                need_mm=block_units / units_per_mm,
                avail_mm=across_units / units_per_mm,
            )

        anchor = _anchor_along(cell.h_align, along_min, along_max, padding_units)
        offsets = _across_offsets(
            line_count=len(lines),
            across_min=across_min,
            across_max=across_max,
            padding=padding_units,
            cap_height=cap_units,
            line_step=step_units,
            v_align=cell.v_align,
        )

        target = drawing.markers if use_marker else drawing.texts
        for line, offset in zip(lines, offsets, strict=True):
            if not line:
                continue
            target.append(
                TextItem(
                    text=line,
                    insert=(
                        anchor * direction[0] + offset * up[0],
                        anchor * direction[1] + offset * up[1],
                    ),
                    height=cap_units,
                    h_align=cell.h_align,
                    v_align=cell.v_align,
                    color=cell.font.color,
                    rotation_deg=cell.rotation_deg,
                    is_marker=use_marker,
                )
            )


def _text_axes(rotation_deg: float) -> tuple[Point, Point]:
    """Metnin uzadığı yön ve glif'lerin yukarı yönü — birim, dik iki vektör.

    Bileşenler yuvarlanır: `cos(90°)` kayan noktada `6.1e-17` çıkıyor ve o
    kırıntı koordinatlara sızıp AC-12'yi (aynı girdi → aynı çıktı) gürültülü
    hâle getiriyor. 90'ın katlarında tam `0.0` ve `±1.0` isteniyor.
    """
    theta = math.radians(rotation_deg)
    cos_t = round(math.cos(theta), 12)
    sin_t = round(math.sin(theta), 12)
    return (cos_t, sin_t), (-sin_t, cos_t)


def _project(box: tuple[float, float, float, float], axis: Point) -> tuple[float, float]:
    """Hücre kutusunun bir eksen üzerindeki izdüşümü.

    `direction` ve `up` birim ve dik olduğu için, bir noktanın bu iki eksendeki
    izdüşümü onun o çerçevedeki koordinatlarıdır; yerleşim böylece dönüş
    açısından bağımsız tek bir formülle yazılabiliyor.
    """
    left, top, right, bottom = box
    corners = ((left, top), (right, top), (right, bottom), (left, bottom))
    values = [x * axis[0] + y * axis[1] for x, y in corners]
    return min(values), max(values)


def _wrap(
    paragraphs: list[str], metrics: FontMetrics, size_pt: float, available_mm: float
) -> list[str]:
    """Kelime sınırlarında açgözlü kaydırma — Calc'ın "metni kaydır"ı.

    Kelime bölünmez: tek başına satıra sığmayan bir kelime kendi satırında
    taşar. Calc uzun kelimeyi ortadan bölebiliyor, ama bölme noktası fonta ve
    sürüme göre değiştiği için tabloda öngörülemeyen bir yer değiştirme
    yaratırdı; taşmasına izin vermek daha sadık.
    """
    if available_mm <= 0:
        return paragraphs

    wrapped: list[str] = []
    for paragraph in paragraphs:
        words = paragraph.split(" ")
        current = ""
        for word in words:
            candidate = f"{current} {word}" if current else word
            if not current or fits(metrics.text_width_mm(candidate, size_pt), available_mm):
                current = candidate
            else:
                wrapped.append(current)
                current = word
        wrapped.append(current)
    return wrapped


def _marker_run(metrics: FontMetrics, size_pt: float, available_mm: float) -> str:
    """Kullanılabilir genişliği dolduracak kadar `#`.

    Kırpma yok: `###` verinin gizlendiğini söyler, kırpılmış metin söylemez.
    """
    char_mm = metrics.char_width_mm(MARKER_CHAR, size_pt)
    if char_mm <= 0 or available_mm <= 0:
        return MARKER_CHAR * 3
    return MARKER_CHAR * max(1, int(available_mm // char_mm))


def _frame_point(along: float, across: float, direction: Point, up: Point) -> Point:
    """Metin çerçevesindeki `(along, across)` koordinatını dünya koordinatına çevirir."""
    return (
        along * direction[0] + across * up[0],
        along * direction[1] + across * up[1],
    )


def _anchor_across(
    v_align: VAlign, across_min: float, across_max: float, padding: float
) -> float:
    """`MTEXT` bağlanma noktasının metin eksenine dik konumu.

    `TextItem`'ın taban çizgisi hesabından ayrı: `MTEXT` kutuyu bu noktaya asar,
    satırları kendi yerleştirir — bize üst/orta/alt kenarı vermek düşer.
    """
    if v_align == "middle":
        return (across_min + across_max) / 2.0
    if v_align == "top":
        return across_max - padding
    return across_min + padding


def _anchor_along(
    h_align: HAlign, along_min: float, along_max: float, padding: float
) -> float:
    """Yatay hizalama metnin **kendi ekseninde** uygulanır.

    Döndürülmemiş hücrede bu sola/sağa yaslamadır; 90° döndürülmüş hücrede
    metnin alttan mı üstten mi başladığını belirler — Calc'ın davranışı da bu.
    """
    if h_align == "center":
        return (along_min + along_max) / 2.0
    if h_align == "right":
        return along_max - padding
    return along_min + padding


def _across_offsets(
    *,
    line_count: int,
    across_min: float,
    across_max: float,
    padding: float,
    cap_height: float,
    line_step: float,
    v_align: VAlign,
) -> list[float]:
    """Satırların metin eksenine dik konumları, ilk satır önde.

    Blok bir bütün olarak hizalanır: `middle` tek satırı da çok satırı da hücre
    ortasına oturtur.
    """
    block_height = (line_count - 1) * line_step + cap_height
    if v_align == "top":
        first = across_max - padding - cap_height
    elif v_align == "middle":
        center = (across_min + across_max) / 2.0
        first = center + block_height / 2.0 - cap_height
    else:  # bottom
        first = across_min + padding + (line_count - 1) * line_step
    return [first - index * line_step for index in range(line_count)]


