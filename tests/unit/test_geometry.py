"""Geometri kuralları — kenarlık tekilleştirme, birleştirme, taşma.

Modeller doğrudan kurulur: kural tek bir hücre biçiminden değil, hücrelerin
birbirine göre konumundan doğuyor; `.ods` üzerinden gitmek testi bulanıklaştırır.
"""

from __future__ import annotations

import pytest

from tabletodxf import geometry
from tabletodxf.config import BackgroundConfig, LayoutConfig, OverflowConfig
from tabletodxf.metrics import FontMetrics
from tabletodxf.model import Border, Borders, Cell, FontSpec, SheetModel
from tabletodxf.report import Report

THIN = Border(0.25, (0, 0, 0))
THICK = Border(1.0, (0, 0, 0))
RED_THIN = Border(0.25, (255, 0, 0))


def make_model(rows: int, cols: int, cells: list[Cell]) -> SheetModel:
    model = SheetModel(
        source_ref="S!A1:Z99",
        col_widths_mm=[10.0] * cols,
        row_heights_mm=[5.0] * rows,
        sheet_name="S",
        row_refs=list(range(rows)),
        col_refs=list(range(cols)),
    )
    for cell in cells:
        model.cells[(cell.row, cell.col)] = cell
    return model


def build(  # noqa: ANN201
    model: SheetModel,
    metrics: FontMetrics,
    report: Report,
    *,
    scale_cm_to_units: float = 10.0,
    frame_mm: float = 0.0,
    line_spacing: float = 1.0,
    overflow: str = "condense",
    min_width_factor: float = OverflowConfig().min_width_factor,
    marker_char: str = OverflowConfig().marker_char,
    background: bool = True,
    background_color: tuple[int, int, int] = BackgroundConfig().color,
):
    """Config nesnelerini testler adına kuran yardımcı.

    Dış çerçeve burada varsayılan olarak **kapalı**: kenarlık kuralları
    (tekilleştirme, eş doğrultulu birleştirme, birleşik alanın bastırılması)
    tek başına sınanabilsin diye. Çerçeve her çizime dört çizgi ekleyip bu
    testlerdeki sayımları bozardı; çerçeveyi sınayan testler `frame_mm`'i
    açıkça geçiyor.
    """
    return geometry.build(
        model,
        metrics,
        report,
        layout=LayoutConfig(
            scale_cm_to_units=scale_cm_to_units,
            frame_mm=frame_mm,
            line_spacing=line_spacing,
        ),
        overflow=OverflowConfig(
            mode=overflow, min_width_factor=min_width_factor, marker_char=marker_char
        ),
        background=BackgroundConfig(enabled=background, color=background_color),
    )


# ── Izgara koordinatları ────────────────────────────────────────────────────


def test_origin_is_top_left_and_y_grows_downward(metrics, report) -> None:  # noqa: ANN001
    model = make_model(2, 2, [Cell(row=0, col=0, text="", borders=Borders(top=THIN))])
    drawing = build(model, metrics, report, scale_cm_to_units=10.0)
    line = drawing.lines[0]
    assert line.start == (0.0, 0.0)
    # 10 mm sütun, 1 cm = 10 birim → 10 birim
    assert line.end == (10.0, 0.0)


def test_scale_multiplies_every_coordinate(metrics, report) -> None:  # noqa: ANN001
    model = make_model(1, 1, [Cell(row=0, col=0, text="", borders=Borders(bottom=THIN))])
    at_10 = build(model, metrics, report, scale_cm_to_units=10.0).lines[0]
    at_20 = build(model, metrics, report, scale_cm_to_units=20.0).lines[0]
    assert at_20.end[0] == pytest.approx(at_10.end[0] * 2)
    assert at_20.start[1] == pytest.approx(at_10.start[1] * 2)


# ── Kenarlık kuralları ──────────────────────────────────────────────────────


def test_shared_edge_is_drawn_once(metrics, report) -> None:  # noqa: ANN001
    """A'nın sağ kenarı ile B'nin sol kenarı aynı çizgidir."""
    model = make_model(
        1,
        2,
        [
            Cell(row=0, col=0, text="", borders=Borders(right=THIN)),
            Cell(row=0, col=1, text="", borders=Borders(left=THIN)),
        ],
    )
    drawing = build(model, metrics, report)
    verticals = [line for line in drawing.lines if line.start[0] == line.end[0]]
    assert len(verticals) == 1
    assert verticals[0].start[0] == pytest.approx(10.0)


def test_thicker_edge_wins_on_conflict(metrics, report) -> None:  # noqa: ANN001
    model = make_model(
        1,
        2,
        [
            Cell(row=0, col=0, text="", borders=Borders(right=THIN)),
            Cell(row=0, col=1, text="", borders=Borders(left=THICK)),
        ],
    )
    drawing = build(model, metrics, report)
    verticals = [line for line in drawing.lines if line.start[0] == line.end[0]]
    assert len(verticals) == 1
    assert verticals[0].width == THICK.width_mm


def test_collinear_segments_merge_into_one_line(metrics, report) -> None:  # noqa: ANN001
    """Üç hücrenin üst kenarı tek bir çizgi olmalı — varlık sayısı patlamasın."""
    model = make_model(
        1,
        3,
        [Cell(row=0, col=col, text="", borders=Borders(top=THIN)) for col in range(3)],
    )
    drawing = build(model, metrics, report)
    horizontals = [line for line in drawing.lines if line.start[1] == line.end[1]]
    assert len(horizontals) == 1
    assert horizontals[0].start[0] == pytest.approx(0.0)
    assert horizontals[0].end[0] == pytest.approx(30.0)


def test_different_colours_break_the_run(metrics, report) -> None:  # noqa: ANN001
    """Kalınlık aynı ama renk farklıysa birleştirilemez — görünüm değişirdi."""
    model = make_model(
        1,
        3,
        [
            Cell(row=0, col=0, text="", borders=Borders(top=THIN)),
            Cell(row=0, col=1, text="", borders=Borders(top=RED_THIN)),
            Cell(row=0, col=2, text="", borders=Borders(top=THIN)),
        ],
    )
    drawing = build(model, metrics, report)
    horizontals = [line for line in drawing.lines if line.start[1] == line.end[1]]
    assert len(horizontals) == 3


def test_zero_width_border_is_not_drawn(metrics, report) -> None:  # noqa: ANN001
    model = make_model(1, 1, [Cell(row=0, col=0, text="", borders=Borders())])
    assert build(model, metrics, report).lines == []


def test_merged_area_suppresses_its_interior_grid(metrics, report) -> None:  # noqa: ANN001
    """Birleşik alanın yalnızca dış sınırı çizilir."""
    all_sides = Borders(left=THIN, right=THIN, top=THIN, bottom=THIN)
    model = make_model(
        2,
        1,
        [
            Cell(row=0, col=0, text="", borders=all_sides, row_span=2),
            Cell(row=1, col=0, text="", covered=True),
        ],
    )
    drawing = build(model, metrics, report)
    horizontals = sorted(
        line.start[1] for line in drawing.lines if line.start[1] == line.end[1]
    )
    # Üst (0) ve alt (-10) var; aradaki satır sınırı (-5) yok.
    assert horizontals == pytest.approx([-10.0, 0.0])


def test_unbordered_empty_row_occupies_height_but_draws_nothing(metrics, report) -> None:  # noqa: ANN001
    """AC-5 ile ADR-002'nin kesiştiği yer.

    Boş satır aralıktan düşürülmez — altındaki satırlar yerinde kalır. Ama
    sayfada kenarlığı yoksa çizimde de çizgisi olmaz: araç kaynağı düzeltmez,
    yansıtır. Kenarlık çekilmişse (referans sayfada olduğu gibi) çizilir.
    """
    all_sides = Borders(left=THIN, right=THIN, top=THIN, bottom=THIN)
    model = make_model(
        2,
        1,
        [Cell(row=0, col=0, text="üst", borders=all_sides)],  # 1. satır tanımsız = boş
    )
    drawing = build(model, metrics, report)

    lowest = min(line.start[1] for line in drawing.lines)
    assert lowest == pytest.approx(-5.0)  # boş satır (-10) çizgi üretmedi
    assert model.row_heights_mm == [5.0, 5.0]  # ama yüksekliği modelde duruyor


def test_covered_cells_emit_nothing(metrics, report) -> None:  # noqa: ANN001
    covered = Cell(
        row=0,
        col=0,
        text="görünmemeli",
        covered=True,
        fill=(255, 0, 0),
        borders=Borders(top=THIN),
    )
    drawing = build(make_model(1, 1, [covered]), metrics, report)
    assert drawing.fills == []
    assert drawing.lines == []
    assert drawing.texts == []
    assert drawing.markers == []
    # Zemin hücrelerden bağımsız; kapsanan hücre onu ortadan kaldırmaz.
    assert drawing.entity_count == 1


# ── Zemin ───────────────────────────────────────────────────────────────────


def test_background_covers_the_whole_selection(metrics, report) -> None:  # noqa: ANN001
    """Calc'ta "dolgu yok" olan hücre beyaz görünür, saydam değil."""
    model = make_model(2, 3, [])  # hiçbir hücrenin dolgusu yok
    drawing = build(model, metrics, report)

    assert drawing.fills == []  # hücre dolgusu üretilmedi
    background = drawing.background
    assert background is not None
    assert background.color == BackgroundConfig().color
    # 3 sütun × 10 mm, 2 satır × 5 mm, 1 cm = 10 birim.
    assert background.corners == (
        (0.0, 0.0),
        (30.0, 0.0),
        (30.0, -10.0),
        (0.0, -10.0),
    )


def test_background_is_a_single_entity_regardless_of_cell_count(metrics, report) -> None:  # noqa: ANN001
    small = build(make_model(1, 1, []), metrics, report)
    large = build(make_model(20, 20, []), metrics, report)
    assert small.entity_count == large.entity_count == 1


def test_coloured_fills_are_separate_from_the_background(metrics, report) -> None:  # noqa: ANN001
    """Renkli dolgu zemini değiştirmez; üstüne biner."""
    model = make_model(1, 2, [Cell(row=0, col=0, text="", fill=(255, 255, 0))])
    drawing = build(model, metrics, report)

    assert drawing.background is not None
    assert drawing.background.color == (255, 255, 255)
    assert [fill.color for fill in drawing.fills] == [(255, 255, 0)]


# ── Dış çerçeve ─────────────────────────────────────────────────────────────


def test_frame_wraps_the_table_even_without_sheet_borders(metrics, report) -> None:  # noqa: ANN001
    """Sayfada hiç kenarlık yoksa bile tablonun sınırı belli olmalı."""
    drawing = build(make_model(2, 3, []), metrics, report, frame_mm=0.35)

    assert drawing.lines == []  # ızgara yok, yalnızca çerçeve
    assert drawing.frame is not None
    assert drawing.frame.width == pytest.approx(0.35)


def test_frame_inner_edge_sits_exactly_on_the_table_boundary(metrics, report) -> None:  # noqa: ANN001
    """Asıl kural: bant dışarı büyür, tablodan içeri yemez.

    AutoCAD genişliği eksen çizgisinden iki yana açtığı için eksen sınırdan
    `width/2` dışarı kaydırılır. Eksen tam sınırda olsaydı bandın yarısı ilk
    hücrelerin kenarlığını ve metnini örterdi.
    """
    drawing = build(make_model(2, 3, []), metrics, report, frame_mm=1.0)
    frame = drawing.frame
    assert frame is not None

    half = frame.width / 2.0
    (left, top), _, (right, bottom), _ = frame.corners

    # Eksen dışarıda...
    assert (left, top) == pytest.approx((-half, half))
    assert (right, bottom) == pytest.approx((30.0 + half, -10.0 - half))
    # ...ama iç kenar tam tablo sınırında: 3 sütun × 10 mm, 2 satır × 5 mm.
    assert (left + half, top - half) == pytest.approx((0.0, 0.0))
    assert (right - half, bottom + half) == pytest.approx((30.0, -10.0))


def test_frame_is_a_single_closed_box_not_four_lines(metrics, report) -> None:  # noqa: ANN001
    """Tek kapalı kutu: köşeler gönyeli birleşsin, çentik kalmasın."""
    drawing = build(make_model(5, 5, []), metrics, report, frame_mm=0.35)
    assert drawing.frame is not None
    assert len(drawing.frame.corners) == 4
    assert drawing.lines == []


def test_frame_replaces_the_boundary_edges(metrics, report) -> None:  # noqa: ANN001
    """Sınır parçaları silinir; yoksa çerçeveyle çakışık çift çizgi olurdu."""
    all_sides = Borders(left=THIN, right=THIN, top=THIN, bottom=THIN)
    model = make_model(1, 1, [Cell(row=0, col=0, text="", borders=all_sides)])

    without = build(model, metrics, report, frame_mm=0.0)
    with_frame = build(model, metrics, report, frame_mm=0.9)

    assert len(without.lines) == 4  # çerçeve yokken sınır çizgileri duruyor
    assert with_frame.lines == []  # çerçeve varken sınır çizgileri yok
    assert with_frame.frame is not None


def test_frame_never_thins_a_heavier_sheet_border(metrics, report) -> None:  # noqa: ANN001
    """Sayfanın koyduğu vurgu çerçeve yüzünden kaybolmamalı."""
    heavy = Border(1.2, (0, 0, 0))
    model = make_model(1, 1, [Cell(row=0, col=0, text="", borders=Borders(top=heavy))])
    drawing = build(model, metrics, report, frame_mm=0.35)

    assert drawing.frame is not None
    assert drawing.frame.width == pytest.approx(1.2)


def test_frame_takes_the_colour_of_the_heaviest_boundary_border(metrics, report) -> None:  # noqa: ANN001
    model = make_model(
        1, 1, [Cell(row=0, col=0, text="", borders=Borders(top=Border(1.2, (255, 0, 0))))]
    )
    drawing = build(model, metrics, report, frame_mm=0.35)
    assert drawing.frame is not None
    assert drawing.frame.color == (255, 0, 0)


def test_frame_does_not_touch_interior_grid_lines(metrics, report) -> None:  # noqa: ANN001
    """Çerçeve yalnızca dış sınırı devralır; iç ızgara sayfadan geldiği gibi kalır."""
    cells = [
        Cell(row=r, col=c, text="", borders=Borders(left=THIN, top=THIN))
        for r in range(2)
        for c in range(2)
    ]
    drawing = build(make_model(2, 2, cells), metrics, report, frame_mm=0.9)

    assert drawing.lines  # iç çizgiler duruyor
    assert all(line.width == pytest.approx(THIN.width_mm) for line in drawing.lines)
    assert drawing.frame is not None
    assert drawing.frame.width == pytest.approx(0.9)


def test_frame_width_scales_with_the_drawing(metrics, report) -> None:  # noqa: ANN001
    normal = build(make_model(2, 2, []), metrics, report, frame_mm=0.5)
    big = build(make_model(2, 2, []), metrics, report, frame_mm=0.5, scale_cm_to_units=20.0)
    assert big.frame.width == pytest.approx(normal.frame.width * 2)


def test_frame_can_be_disabled(metrics, report) -> None:  # noqa: ANN001
    drawing = build(make_model(2, 2, []), metrics, report, frame_mm=0.0)
    assert drawing.frame is None
    assert drawing.lines == []


def test_frame_is_on_by_default(metrics, report) -> None:  # noqa: ANN001
    """Yerel `build` yardımcısını atlayarak gerçek varsayılanı sınar."""
    drawing = geometry.build(make_model(2, 2, []), metrics, report)
    assert drawing.frame is not None
    assert drawing.frame.width == pytest.approx(LayoutConfig().frame_mm)


# ── Dolgular ────────────────────────────────────────────────────────────────


def test_fill_covers_the_whole_merged_area(metrics, report) -> None:  # noqa: ANN001
    model = make_model(
        1,
        2,
        [
            Cell(row=0, col=0, text="", fill=(0, 128, 255), col_span=2),
            Cell(row=0, col=1, text="", covered=True),
        ],
    )
    fill = build(model, metrics, report).fills[0]
    left_top, right_top, right_bottom, left_bottom = fill.corners
    assert left_top == (0.0, 0.0)
    assert right_bottom == (20.0, -5.0)
    assert right_top == (20.0, 0.0)
    assert left_bottom == (0.0, -5.0)


# ── Metin ───────────────────────────────────────────────────────────────────


def _text_cell(text: str, **kwargs) -> Cell:
    return Cell(row=0, col=0, text=text, font=FontSpec(size_pt=10.0), **kwargs)


def test_alignment_anchors(metrics, report) -> None:  # noqa: ANN001
    for align, expected_x in (("left", 0.97), ("center", 5.0), ("right", 9.03)):
        model = make_model(1, 1, [_text_cell("A", h_align=align, padding_mm=0.97)])
        item = build(model, metrics, report).texts[0]
        assert item.insert[0] == pytest.approx(expected_x)


def test_vertical_alignment_orders_top_middle_bottom(metrics, report) -> None:  # noqa: ANN001
    """Y aşağı doğru negatif: üste yaslı metnin taban çizgisi en büyük Y'dedir."""
    baselines = {}
    for valign in ("top", "middle", "bottom"):
        model = make_model(1, 1, [_text_cell("A", v_align=valign)])
        baselines[valign] = build(model, metrics, report).texts[0].insert[1]
    assert baselines["top"] > baselines["middle"] > baselines["bottom"]

    # Ve hepsi hücre kutusunun içinde kalır (satır yüksekliği 5 mm → 5 birim).
    assert all(-5.0 < baseline < 0.0 for baseline in baselines.values())


def test_multiline_text_stacks_downward(metrics, report) -> None:  # noqa: ANN001
    model = make_model(1, 1, [_text_cell("bir\niki\nüç", v_align="top")])
    items = build(model, metrics, report).texts
    assert [item.text for item in items] == ["bir", "iki", "üç"]
    assert items[0].insert[1] > items[1].insert[1] > items[2].insert[1]


def test_text_height_is_cap_height_not_em(metrics, report) -> None:  # noqa: ANN001
    model = make_model(1, 1, [_text_cell("A")])
    item = build(model, metrics, report).texts[0]
    assert item.height == pytest.approx(metrics.cap_height_mm(10.0))


def test_empty_cells_produce_no_text(metrics, report) -> None:  # noqa: ANN001
    assert build(make_model(1, 1, [_text_cell("")]), metrics, report).texts == []


# ── Taşma ───────────────────────────────────────────────────────────────────

LONG = "Bu metin bu dar hücreye kesinlikle sığmaz"


def test_overflow_marker_mode_fills_the_cell_with_hashes(metrics, report) -> None:  # noqa: ANN001
    model = make_model(1, 1, [_text_cell(LONG)])
    drawing = build(model, metrics, report, overflow="marker")

    assert drawing.texts == []  # metin normal katmana gitmez
    assert len(drawing.markers) == 1
    marker = drawing.markers[0]
    assert set(marker.text) == {"#"}
    assert marker.is_marker

    # İşaret kullanılabilir genişliği doldurur ama taşmaz.
    available_mm = 10.0 - 2 * 0.97
    width = metrics.text_width_mm(marker.text, 10.0)
    assert width <= available_mm
    assert width + metrics.char_width_mm("#", 10.0) > available_mm


def test_overflow_marker_reports_a_warning(metrics, report) -> None:  # noqa: ANN001
    build(make_model(1, 1, [_text_cell(LONG)]), metrics, report, overflow="marker")
    assert report.warn_count == 1
    assert any("text overflow" in line for line in report.lines)
    assert any("cell=S!A1" in line for line in report.lines)


def test_overflow_full_mode_writes_the_whole_text(metrics, report) -> None:  # noqa: ANN001
    """AC-7: hiçbir modda kırpma yok; `full` taşmasına izin verir."""
    model = make_model(1, 1, [_text_cell(LONG)])
    drawing = build(model, metrics, report, overflow="full")

    assert drawing.markers == []
    assert len(drawing.texts) == 1
    assert drawing.texts[0].text == LONG  # kırpılmamış


def test_fitting_text_produces_no_warning(metrics, report) -> None:  # noqa: ANN001
    build(make_model(1, 1, [_text_cell("ok")]), metrics, report)
    assert report.warn_count == 0


# ── Kaydırma (wrap) ─────────────────────────────────────────────────────────


def test_wrapped_cell_that_fits_after_wrapping_gets_no_marker(metrics, report) -> None:  # noqa: ANN001
    """Kaydırma sığdırdıysa taşma yoktur; işaret de olmaz."""
    model = make_model(1, 1, [_text_cell("bir iki uc dort", wrap=True)])
    drawing = build(model, metrics, report, overflow="marker")

    assert drawing.markers == []
    assert len(drawing.texts) > 1  # birden çok satıra bölündü
    # Taşma uyarısı yok. (Satır yüksekliği uyarısı olabilir — test hücresi
    # kasten alçak; o ayrı bir tanı.)
    assert not any("text overflow" in line for line in report.lines)


def test_wrapped_cell_still_overflowing_does_get_a_marker(metrics, report) -> None:  # noqa: ANN001
    """`overflowed` kaydırmadan **sonra** hesaplanır.

    Buraya düşen hücre kaydırmaya rağmen sığmıyor demektir (bölünemeyen uzun
    kelime); kullanıcı `marker` istediyse `###` görmeli. Bu muafiyet önceden
    vardı ve `marker` modunu kaydırmalı sayfalarda `full` ile aynı yapıyordu.
    """
    model = make_model(
        1, 1, [_text_cell("Kahramanmaraslilastiramadiklarimizdan", wrap=True)]
    )
    drawing = build(model, metrics, report, overflow="marker")

    assert len(drawing.markers) == 1
    assert set(drawing.markers[0].text) == {"#"}
    assert drawing.texts == []
    assert any("mode=marker" in line for line in report.lines)


def test_wrap_breaks_on_word_boundaries(metrics, report) -> None:  # noqa: ANN001
    model = make_model(1, 1, [_text_cell("bir iki üç dört beş altı", wrap=True)])
    drawing = build(model, metrics, report)

    # Hiçbir kelime bölünmemiş; sıra korunmuş.
    assert " ".join(item.text for item in drawing.texts) == "bir iki üç dört beş altı"


def test_wrapped_lines_each_fit_the_cell(metrics, report) -> None:  # noqa: ANN001
    model = make_model(1, 1, [_text_cell("bir iki üç dört beş altı yedi", wrap=True)])
    drawing = build(model, metrics, report)

    available_mm = 10.0 - 2 * 0.97
    for item in drawing.texts:
        assert metrics.text_width_mm(item.text, 10.0) <= available_mm + 1e-9


def test_wrapped_lines_stack_downward(metrics, report) -> None:  # noqa: ANN001
    model = make_model(1, 1, [_text_cell(LONG, wrap=True, v_align="top")])
    drawing = build(model, metrics, report)
    ys = [item.insert[1] for item in drawing.texts]
    assert ys == sorted(ys, reverse=True)


def test_unbreakable_word_overflows_in_full_mode(metrics, report) -> None:  # noqa: ANN001
    """`full` modunda tek başına sığmayan kelime kırpılmadan taşar."""
    model = make_model(1, 1, [_text_cell("Kahramanmaraşlılaştıramadıklarımızdan", wrap=True)])
    drawing = build(model, metrics, report, overflow="full")

    assert drawing.markers == []
    assert [item.text for item in drawing.texts] == [
        "Kahramanmaraşlılaştıramadıklarımızdan"
    ]
    assert any("mode=full" in line for line in report.lines)
    assert any("wrap=yes" in line for line in report.lines)


def test_wrap_off_still_produces_markers(metrics, report) -> None:  # noqa: ANN001
    """Kaydırma kapalıysa `marker` modunda eski davranış korunur."""
    drawing = build(make_model(1, 1, [_text_cell(LONG)]), metrics, report, overflow="marker")
    assert len(drawing.markers) == 1


# ── Taşma: `mtext` modu (varsayılan) ────────────────────────────────────────


def test_mtext_carries_the_full_untruncated_text(metrics, report) -> None:  # noqa: ANN001
    drawing = build(make_model(1, 1, [_text_cell(LONG)]), metrics, report, overflow="mtext")
    assert drawing.boxes[0].text == LONG


def test_mtext_width_matches_the_cell_text_area(metrics, report) -> None:  # noqa: ANN001
    """Tanımlı genişlik = hücre genişliği − iki yandan dolgu."""
    model = make_model(1, 1, [_text_cell(LONG, padding_mm=0.97)])
    box = build(model, metrics, report, overflow="mtext").boxes[0]
    assert box.width == pytest.approx(10.0 - 2 * 0.97)


def test_mtext_width_follows_a_merged_cell(metrics, report) -> None:  # noqa: ANN001
    model = make_model(
        1,
        2,
        [
            Cell(row=0, col=0, text=LONG, font=FontSpec(size_pt=10.0), col_span=2),
            Cell(row=0, col=1, text="", covered=True),
        ],
    )
    box = build(model, metrics, report, overflow="mtext").boxes[0]
    assert box.width == pytest.approx(20.0 - 2 * 0.97)


def test_mtext_anchor_follows_alignment(metrics, report) -> None:  # noqa: ANN001
    """Bağlanma noktası hizalama çiftine göre hücre kenarına oturur."""
    model = make_model(1, 1, [_text_cell(LONG, h_align="left", v_align="top")])
    box = build(model, metrics, report, overflow="mtext").boxes[0]
    assert box.insert == pytest.approx((0.97, -0.97))

    model = make_model(1, 1, [_text_cell(LONG, h_align="center", v_align="middle")])
    box = build(model, metrics, report, overflow="mtext").boxes[0]
    assert box.insert == pytest.approx((5.0, -2.5))


def test_mtext_keeps_rotation(metrics, report) -> None:  # noqa: ANN001
    model = make_model(1, 1, [_text_cell(LONG, rotation_deg=90.0)])
    box = build(model, metrics, report, overflow="mtext").boxes[0]
    assert box.rotation_deg == 90.0


def test_mtext_mode_still_reports_the_overflow(metrics, report) -> None:  # noqa: ANN001
    """Katman filtresi gibi rapor da hangi hücrelerin taştığını söylemeye devam eder."""
    build(make_model(1, 1, [_text_cell(LONG)]), metrics, report, overflow="mtext")
    assert report.warn_count == 1
    assert any("mode=mtext" in line for line in report.lines)


def test_fitting_cells_never_become_mtext(metrics, report) -> None:  # noqa: ANN001
    drawing = build(make_model(1, 1, [_text_cell("ok")]), metrics, report, overflow="mtext")
    assert drawing.boxes == []
    assert len(drawing.texts) == 1


# ── Taşma: `condense` modu ──────────────────────────────────────────────────


WIDE_CELL_MM = 40.0
WIDE_AVAILABLE_MM = WIDE_CELL_MM - 2 * 0.97


def make_wide_model(text: str, **cell_kw) -> SheetModel:
    """Çarpanın tabana dayanmayacağı kadar geniş tek hücre.

    Varsayılan 10 mm hücrede `LONG` ~7 kat taşıyor ve çarpan `MIN_WIDTH_FACTOR`'a
    kırpılıyor; sıkıştırmanın **tam oturduğu** yolu sınamak için daha geniş bir
    hücre gerekiyor.
    """
    model = SheetModel(
        source_ref="S!A1:A1",
        col_widths_mm=[WIDE_CELL_MM],
        row_heights_mm=[5.0],
        sheet_name="S",
        row_refs=[0],
        col_refs=[0],
    )
    model.cells[(0, 0)] = Cell(
        row=0, col=0, text=text, font=FontSpec(size_pt=10.0), **cell_kw
    )
    return model


def test_condense_is_the_default_overflow_mode(metrics, report) -> None:  # noqa: ANN001
    """Varsayılan mod elle düzeltme gerektirmeden sığdırmalı."""
    drawing = build(make_wide_model(LONG), metrics, report)

    assert drawing.texts == []
    assert drawing.markers == []
    assert drawing.boxes == []
    assert len(drawing.condensed) == 1


def test_condense_shrinks_the_text_to_fit(metrics, report) -> None:  # noqa: ANN001
    """AutoCAD heceleme yapmadığı için, sığdırmanın tek yolu yatay sıkıştırma."""
    drawing = build(make_wide_model(LONG), metrics, report, overflow="condense")

    assert drawing.texts == []
    assert drawing.markers == []
    assert drawing.boxes == []
    assert len(drawing.condensed) == 1

    item = drawing.condensed[0]
    assert item.text == LONG  # kırpma yok
    assert OverflowConfig().min_width_factor < item.width_factor < 1.0


def test_condensed_text_actually_fits_the_cell(metrics, report) -> None:  # noqa: ANN001
    item = build(make_wide_model(LONG), metrics, report, overflow="condense").condensed[0]

    drawn_mm = metrics.text_width_mm(item.text, 10.0) * item.width_factor
    assert drawn_mm == pytest.approx(WIDE_AVAILABLE_MM)


def test_condense_factor_is_clamped_at_the_readable_floor(metrics, report) -> None:  # noqa: ANN001
    """Okunmaz bir çarpan üretmektense taşmayı kabul edip uyarmak."""
    absurd = make_model(1, 1, [_text_cell("x" * 400)])
    item = build(absurd, metrics, report, overflow="condense").condensed[0]

    assert item.width_factor == OverflowConfig().min_width_factor
    assert any("clamped=yes" in line for line in report.lines)


def test_condense_reports_the_factor(metrics, report) -> None:  # noqa: ANN001
    build(make_model(1, 1, [_text_cell(LONG)]), metrics, report, overflow="condense")
    assert report.warn_count == 1
    assert any("mode=condense" in line for line in report.lines)
    assert any("width_factor=" in line for line in report.lines)


def test_all_lines_share_one_factor(metrics, report) -> None:  # noqa: ANN001
    """Satır başına çarpan harf genişliklerini satırdan satıra zıplatırdı."""
    model = make_model(1, 1, [_text_cell(f"kısa\n{LONG}")])
    drawing = build(model, metrics, report, overflow="condense")

    factors = {item.width_factor for item in drawing.condensed}
    assert len(factors) == 1


def test_fitting_cells_are_never_condensed(metrics, report) -> None:  # noqa: ANN001
    drawing = build(make_model(1, 1, [_text_cell("ok")]), metrics, report, overflow="condense")
    assert drawing.condensed == []
    assert len(drawing.texts) == 1
    assert drawing.texts[0].width_factor == 1.0


def test_condense_keeps_rotation(metrics, report) -> None:  # noqa: ANN001
    """Dikey başlık sıkıştırıldığında da dikey kalmalı."""
    model = make_model(1, 1, [_text_cell(LONG, rotation_deg=90.0)])
    item = build(model, metrics, report, overflow="condense").condensed[0]
    assert item.rotation_deg == 90.0


# ── Döndürülmüş metin ───────────────────────────────────────────────────────


def test_rotation_measures_against_cell_height_not_width(metrics, report) -> None:  # noqa: ANN001
    """Asıl hata buydu: dar sütundaki dikey başlık sahte taşma sayılıyordu.

    Hücre 10 birim geniş, 5 birim yüksek. Aynı metin döndürülmemişken sığmaz;
    90° döndürülünce metnin ekseni **yükseklik** olur.
    """
    tall = SheetModel(
        source_ref="S!A1:A1",
        col_widths_mm=[5.0],
        row_heights_mm=[40.0],
        sheet_name="S",
        row_refs=[0],
        col_refs=[0],
    )
    tall.cells[(0, 0)] = Cell(
        row=0, col=0, text="Published by", font=FontSpec(size_pt=10.0), rotation_deg=90.0
    )
    drawing = build(tall, metrics, report)

    assert drawing.markers == []
    assert [item.text for item in drawing.texts] == ["Published by"]
    assert report.warn_count == 0


def test_rotation_is_carried_to_the_text_item(metrics, report) -> None:  # noqa: ANN001
    model = make_model(1, 1, [_text_cell("A", rotation_deg=90.0)])
    assert build(model, metrics, report).texts[0].rotation_deg == 90.0


def test_rotated_text_runs_along_the_cell_height(metrics, report) -> None:  # noqa: ANN001
    """90°'de metin ekseni +Y; hizalama noktası da o eksende hareket etmeli."""
    lower = make_model(1, 1, [_text_cell("A", rotation_deg=90.0, h_align="left")])
    upper = make_model(1, 1, [_text_cell("A", rotation_deg=90.0, h_align="right")])

    low = build(lower, metrics, report).texts[0].insert
    high = build(upper, metrics, report).texts[0].insert

    assert low[1] < high[1]  # "sol" alttan, "sağ" üstten başlar
    assert low[0] == pytest.approx(high[0])  # dik eksende ikisi de aynı yerde


def test_unrotated_placement_is_unchanged(metrics, report) -> None:  # noqa: ANN001
    """Dönüş çerçevesi 0°'de eski formüle birebir indirgenmeli."""
    for align, expected_x in (("left", 0.97), ("center", 5.0), ("right", 9.03)):
        model = make_model(1, 1, [_text_cell("A", h_align=align, padding_mm=0.97)])
        assert build(model, metrics, report).texts[0].insert[0] == pytest.approx(expected_x)


def test_rotation_axes_are_exact_at_right_angles() -> None:
    """`cos(90°)` kırıntısı koordinatlara sızarsa AC-12 gürültülenir."""
    direction, up = geometry._text_axes(90.0)
    assert direction == (0.0, 1.0)
    assert up == (-1.0, 0.0)

    direction, up = geometry._text_axes(0.0)
    assert direction == (1.0, 0.0)
    assert up == (0.0, 1.0)


# ── Determinizm ─────────────────────────────────────────────────────────────


def test_same_model_produces_identical_geometry(metrics, report) -> None:  # noqa: ANN001
    """AC-12: aynı girdi → aynı koordinatlar, aynı sıra."""
    cells = [
        Cell(row=r, col=c, text=f"{r}{c}", borders=Borders(top=THIN, left=THIN))
        for r in range(3)
        for c in range(3)
    ]
    first = build(make_model(3, 3, cells), metrics, report)
    second = build(make_model(3, 3, cells), metrics, report)
    assert first == second
