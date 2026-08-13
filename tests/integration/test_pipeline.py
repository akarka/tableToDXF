"""Uçtan uca: referans `.ods` → DXF → `ezdxf` ile geri okuma (golden test).

Görsel doğruluk burada test edilemez; bu testler yapının doğruluğunu korur —
blok adı, katman dağılımı, varlık sayıları, metin içerikleri ve konumları.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import ezdxf
import pytest

from fixtures.ods_builder import CellSpec, RowSpec, SheetSpec, build_ods
from tabletodxf.cli import EXIT_DATA_ERROR, EXIT_OK, main

from conftest import OVERFLOW_TEXT, REFERENCE_RANGE, REFERENCE_SHEET

BLOCK = "ONCU_TBL_MAHAL"


def run_cli(source: Path, out: Path, *extra: str) -> int:
    return main(
        [
            str(source),
            "--sheet",
            REFERENCE_SHEET,
            "--range",
            REFERENCE_RANGE,
            "--out",
            str(out),
            "--block",
            BLOCK,
            *extra,
        ]
    )


@pytest.fixture
def generated(reference_ods: Path, tmp_path: Path) -> tuple[Path, "ezdxf.document.Drawing"]:
    out = tmp_path / "mahal.dxf"
    assert run_cli(reference_ods, out) == EXIT_OK
    return out, ezdxf.readfile(str(out))


# ── AC-1: blok tanımı ───────────────────────────────────────────────────────


def test_output_contains_exactly_one_named_block(generated) -> None:  # noqa: ANN001
    _, doc = generated
    named = [b.name for b in doc.blocks if not b.name.startswith("*")]
    assert named == [BLOCK]


def test_block_is_also_inserted_once_at_the_origin(generated) -> None:  # noqa: ANN001
    """Tanımı olup örneği olmayan bir DXF boş açılır; görsel doğrulama imkânsızlaşır."""
    _, doc = generated
    inserts = [e for e in doc.modelspace() if e.dxftype() == "INSERT"]
    assert len(inserts) == 1
    assert inserts[0].dxf.name == BLOCK
    assert tuple(inserts[0].dxf.insert)[:2] == (0.0, 0.0)


# ── AC-8: birimsiz çıktı ────────────────────────────────────────────────────


def test_insunits_is_zero(generated) -> None:  # noqa: ANN001
    _, doc = generated
    assert doc.header["$INSUNITS"] == 0


def test_dxf_version_is_r2013_by_default(generated) -> None:  # noqa: ANN001
    _, doc = generated
    assert doc.acad_release == "R2013"


# ── Katman şeması ───────────────────────────────────────────────────────────


def test_layers_carry_function_not_style(generated) -> None:  # noqa: ANN001
    _, doc = generated
    names = {layer.dxf.name for layer in doc.layers}
    assert {"ONCU_TBL_GRID", "ONCU_TBL_TEXT", "ONCU_TBL_FILL", "ONCU_TBL_OVERFLOW"} <= names


def test_entities_land_on_the_right_layers(generated) -> None:  # noqa: ANN001
    _, doc = generated
    seen = Counter((e.dxftype(), e.dxf.layer) for e in doc.blocks.get(BLOCK))

    assert seen[("HATCH", "ONCU_TBL_FILL")] == 4  # beyaz zemin + üç başlık hücresi
    assert seen[("TEXT", "ONCU_TBL_OVERFLOW")] == 1  # tek taşan hücre, sıkıştırılmış
    assert seen[("LWPOLYLINE", "ONCU_TBL_GRID")] > 0
    assert seen[("TEXT", "ONCU_TBL_TEXT")] > 0

    # Izgara ve dolgu asla metin katmanına düşmemeli.
    assert all(
        layer != "ONCU_TBL_TEXT"
        for (dxftype, layer) in seen
        if dxftype in ("LWPOLYLINE", "HATCH")
    )


def _hatch_corners(hatch) -> tuple:  # noqa: ANN001
    return tuple((round(v[0], 3), round(v[1], 3)) for v in hatch.paths.paths[0].vertices)


def test_fills_are_solid_filled_hatches(generated) -> None:  # noqa: ANN001
    """Dolgular `HATCH` — düz desen, gerçek renk, kapalı dörtgen sınır."""
    _, doc = generated
    hatches = [e for e in doc.blocks.get(BLOCK) if e.dxftype() == "HATCH"]
    assert len(hatches) == 4  # beyaz zemin + üç sarı başlık hücresi

    for hatch in hatches:
        assert hatch.dxf.solid_fill == 1
        boundary = hatch.paths.paths[0]
        assert boundary.is_closed
        assert len(boundary.vertices) == 4

    colours = sorted(tuple(h.rgb) for h in hatches)
    assert colours == [(255, 255, 0)] * 3 + [(255, 255, 255)]


def test_background_is_written_first_so_it_stays_behind(generated) -> None:  # noqa: ANN001
    """Blok içinde çizim sırası varlık sırasıdır — zemin ilk varlık olmalı."""
    _, doc = generated
    entities = list(doc.blocks.get(BLOCK))

    first = entities[0]
    assert first.dxftype() == "HATCH"
    assert tuple(first.rgb) == (255, 255, 255)
    # Tüm seçimi kaplar: 105 birim geniş, 24 birim yüksek.
    assert _hatch_corners(first) == (
        (0.0, 0.0),
        (105.0, 0.0),
        (105.0, -24.0),
        (0.0, -24.0),
    )


def test_no_fill_cells_are_backed_by_the_white_ground(generated) -> None:  # noqa: ANN001
    """Dolgusuz hücrenin kendi `HATCH`'i yoktur; beyazlığı zeminden gelir."""
    _, doc = generated
    coloured = [
        _hatch_corners(e)
        for e in doc.blocks.get(BLOCK)
        if e.dxftype() == "HATCH" and tuple(e.rgb) != (255, 255, 255)
    ]
    # Yalnızca başlık satırı (y: 0 → -6) renkli; gövde satırları zemine bırakılmış.
    assert all(
        {y for _, y in corners} == {0.0, -6.0} for corners in coloured
    )


def test_fill_covers_the_header_cell_exactly(generated) -> None:  # noqa: ANN001
    """İlk başlık hücresi: B sütunu 30 mm, başlık satırı 6 mm → (0,0)–(30,-6)."""
    _, doc = generated
    corners = {
        _hatch_corners(e) for e in doc.blocks.get(BLOCK) if e.dxftype() == "HATCH"
    }
    assert ((0.0, 0.0), (30.0, 0.0), (30.0, -6.0), (0.0, -6.0)) in corners


def test_overflow_layer_isolates_the_overflowing_cells(generated) -> None:  # noqa: ANN001
    """Taşan hücreler hangi modda olursa olsun bu katmanda toplanır."""
    _, doc = generated
    overflow = [e for e in doc.blocks.get(BLOCK) if e.dxf.layer == "ONCU_TBL_OVERFLOW"]
    assert len(overflow) == 1
    assert overflow[0].dxftype() == "TEXT"  # varsayılan `condense`


def test_mtext_mode_produces_an_editable_box(reference_ods: Path, tmp_path: Path) -> None:
    """`--overflow mtext`: kutu genişliği AutoCAD'de tutamakla ayarlanabilir."""
    out = tmp_path / "kutu.dxf"
    assert run_cli(reference_ods, out, "--overflow", "mtext") == EXIT_OK

    doc = ezdxf.readfile(str(out))
    mtexts = [e for e in doc.blocks.get(BLOCK) if e.dxftype() == "MTEXT"]
    assert len(mtexts) == 1

    mtext = mtexts[0]
    assert OVERFLOW_TEXT in mtext.text  # tam metin, kırpılmamış, `###` değil
    assert mtext.dxf.layer == "ONCU_TBL_OVERFLOW"
    # C sütunu 50 mm, 1 cm = 10 birim, iki yandan 0.97 dolgu.
    assert mtext.dxf.width == pytest.approx(50.0 - 2 * 0.97)
    assert mtext.dxf.char_height > 0


def test_condense_mode_squeezes_the_text_into_the_cell(
    reference_ods: Path, tmp_path: Path
) -> None:
    """Taşan hücre tam metniyle, hücreye sığacak genişlik çarpanıyla çizilir."""
    out = tmp_path / "sikistir.dxf"
    assert run_cli(reference_ods, out, "--overflow", "condense") == EXIT_OK

    doc = ezdxf.readfile(str(out))
    block = doc.blocks.get(BLOCK)

    assert not [e for e in block if e.dxftype() == "MTEXT"]
    condensed = [
        e
        for e in block
        if e.dxftype() == "TEXT" and e.dxf.layer == "ONCU_TBL_OVERFLOW"
    ]
    assert len(condensed) == 1
    assert condensed[0].dxf.text == OVERFLOW_TEXT  # tam metin, `###` değil
    assert 0.0 < condensed[0].dxf.width < 1.0  # DXF genişlik çarpanı


def test_unaffected_cells_keep_a_neutral_width_factor(
    reference_ods: Path, tmp_path: Path
) -> None:
    out = tmp_path / "sikistir2.dxf"
    assert run_cli(reference_ods, out, "--overflow", "condense") == EXIT_OK

    doc = ezdxf.readfile(str(out))
    normal = [
        e
        for e in doc.blocks.get(BLOCK)
        if e.dxftype() == "TEXT" and e.dxf.layer == "ONCU_TBL_TEXT"
    ]
    assert normal
    assert all(e.dxf.width == 1.0 for e in normal)


def test_marker_mode_still_available(reference_ods: Path, tmp_path: Path) -> None:
    """`###` davranışı kaybolmadı, varsayılan olmaktan çıktı."""
    out = tmp_path / "isaret.dxf"
    assert run_cli(reference_ods, out, "--overflow", "marker") == EXIT_OK

    doc = ezdxf.readfile(str(out))
    overflow = [e for e in doc.blocks.get(BLOCK) if e.dxf.layer == "ONCU_TBL_OVERFLOW"]
    assert len(overflow) == 1
    assert overflow[0].dxftype() == "TEXT"
    assert set(overflow[0].dxf.text) == {"#"}


# ── İçerik ──────────────────────────────────────────────────────────────────


def test_cell_texts_match_the_sheet(generated) -> None:  # noqa: ANN001
    _, doc = generated
    texts = {
        e.dxf.text
        for e in doc.blocks.get(BLOCK)
        if e.dxftype() == "TEXT" and e.dxf.layer == "ONCU_TBL_TEXT"
    }
    assert {"Kod", "Mahal Adı", "m²", "101", "Zemin kat koridoru", "Birleşik alan"} <= texts
    assert "12,50" in texts  # AC-3: görünen metin, ham 12.5 değil
    assert "gizli satır" not in texts  # AC-4: gizli satır çıktıda yok


def test_grid_spans_the_full_selection_width(generated) -> None:  # noqa: ANN001
    """30 + 50 + 25 mm, 1 cm = 10 birim → 105 birim (gizli D sütunu düşmüş hâliyle)."""
    _, doc = generated
    xs = [
        point[0]
        for e in doc.blocks.get(BLOCK)
        if e.dxftype() == "LWPOLYLINE"
        for point in e.get_points("xy")
    ]
    assert min(xs) == pytest.approx(0.0)
    assert max(xs) == pytest.approx(105.0)


def test_geometry_extends_to_the_trailing_empty_row(generated) -> None:  # noqa: ANN001
    """AC-5: 6.0 + 4.5×4 mm = 24 mm → -24 birim; boş son satır kırpılmamış."""
    _, doc = generated
    ys = [
        point[1]
        for e in doc.blocks.get(BLOCK)
        if e.dxftype() == "LWPOLYLINE"
        for point in e.get_points("xy")
    ]
    assert min(ys) == pytest.approx(-24.0)


def test_header_bottom_border_is_heavier_than_the_inner_grid(generated) -> None:  # noqa: ANN001
    """Kalınlık varlık üzerinde (ByObject) taşınır — BYLAYER olamaz (ADR-002).

    Karşılaştırma **iç** ızgaraya karşı: dış sınır çerçeveye yükseltildiği için
    tablonun en kalın çizgileri artık çerçevenin kendisi.
    """
    _, doc = generated
    lines = [e for e in doc.blocks.get(BLOCK) if e.dxftype() == "LWPOLYLINE"]

    def ys(entity) -> set[float]:  # noqa: ANN001
        return {round(point[1], 3) for point in entity.get_points("xy")}

    boundary_ys = {0.0, -24.0}
    header_bottom = [e for e in lines if ys(e) == {-6.0}]
    inner = [e for e in lines if not (ys(e) & boundary_ys) and e not in header_bottom]

    assert header_bottom
    assert inner
    assert header_bottom[0].dxf.lineweight > max(e.dxf.lineweight for e in inner)


def test_frame_traces_the_background_boundary_exactly(generated) -> None:  # noqa: ANN001
    """Çerçeve, arkadaki zemin `HATCH`'inin sınırının ta kendisidir.

    Ofset yok, ek dikdörtgen yok: çerçeve ayrı bir varlık olarak eklenmiyor,
    var olan dış ızgara parçaları yükseltiliyor. Bu yüzden köşeleri zeminin
    köşeleriyle birebir çakışır — testin sabit koordinat yazmak yerine zeminden
    türetmesinin sebebi bu.
    """
    _, doc = generated
    block = doc.blocks.get(BLOCK)

    background = next(
        e for e in block if e.dxftype() == "HATCH" and tuple(e.rgb) == (255, 255, 255)
    )
    corners = [
        (round(v[0], 3), round(v[1], 3)) for v in background.paths.paths[0].vertices
    ]
    left = min(x for x, _ in corners)
    right = max(x for x, _ in corners)
    bottom = min(y for _, y in corners)
    top = max(y for _, y in corners)

    expected = {
        ((left, top), (right, top)),
        ((left, bottom), (right, bottom)),
        ((left, top), (left, bottom)),
        ((right, top), (right, bottom)),
    }

    def points(entity) -> tuple:  # noqa: ANN001
        return tuple((round(x, 3), round(y, 3)) for x, y in entity.get_points("xy"))

    lines = [e for e in block if e.dxftype() == "LWPOLYLINE"]
    drawn = {points(e) for e in lines}
    assert expected <= drawn

    weights = {e.dxf.lineweight for e in lines if points(e) in expected}
    assert len(weights) == 1  # çerçeve tek tip


def _top_edge_weight(path: Path) -> int:
    doc = ezdxf.readfile(str(path))
    tops = [
        e
        for e in doc.blocks.get(BLOCK)
        if e.dxftype() == "LWPOLYLINE"
        and all(round(point[1], 3) == 0.0 for point in e.get_points("xy"))
    ]
    assert tops
    return max(e.dxf.lineweight for e in tops)


def test_frame_can_be_switched_off(reference_ods: Path, tmp_path: Path) -> None:
    """Kapalıyken dış sınır sayfanın kendi (ince) kenarlığında kalır.

    Referans sayfanın dış kenarında zaten kenarlık var; çerçevenin işi onu
    yaratmak değil, tek tip bir kalınlığa yükseltmek.
    """
    framed, plain = tmp_path / "cerceveli.dxf", tmp_path / "cercevesiz.dxf"
    assert run_cli(reference_ods, framed) == EXIT_OK
    assert run_cli(reference_ods, plain, "--frame", "0") == EXIT_OK

    assert _top_edge_weight(framed) > _top_edge_weight(plain)


def test_frame_width_is_configurable(reference_ods: Path, tmp_path: Path) -> None:
    out = tmp_path / "kalincerceve.dxf"
    assert run_cli(reference_ods, out, "--frame", "1.4") == EXIT_OK

    doc = ezdxf.readfile(str(out))
    top = [
        e
        for e in doc.blocks.get(BLOCK)
        if e.dxftype() == "LWPOLYLINE"
        and all(round(point[1], 3) == 0.0 for point in e.get_points("xy"))
    ]
    assert top
    assert top[0].dxf.lineweight == 140  # 1.4 mm → 1/100 mm


def test_text_style_is_ttf_backed(generated) -> None:  # noqa: ANN001
    """AC-9: Kiril/CJK SHX ile çizilemez; stil bir TTF'e bağlı olmalı."""
    _, doc = generated
    style = doc.styles.get("ONCU_TBL_TEXT")
    assert style.dxf.font.lower().endswith(".ttf")


# ── AC-9: kodlama ───────────────────────────────────────────────────────────


def test_cyrillic_and_cjk_survive_the_round_trip(tmp_path: Path) -> None:
    cyrillic, cjk, turkish = "Привет мир", "図面表", "Şişli Ğüç"
    source = build_ods(
        tmp_path / "unicode.ods",
        [
            SheetSpec(
                name="U",
                col_widths=["8cm", "8cm", "8cm"],
                rows=[
                    RowSpec(
                        cells=[
                            CellSpec(text=cyrillic),
                            CellSpec(text=cjk),
                            CellSpec(text=turkish),
                        ]
                    )
                ],
            )
        ],
    )
    out = tmp_path / "unicode.dxf"
    assert (
        main(
            [
                str(source),
                "--sheet",
                "U",
                "--range",
                "A1:C1",
                "--out",
                str(out),
                "--block",
                "U_BLOCK",
            ]
        )
        == EXIT_OK
    )

    doc = ezdxf.readfile(str(out))
    texts = {e.dxf.text for e in doc.blocks.get("U_BLOCK") if e.dxftype() == "TEXT"}
    assert {cyrillic, cjk, turkish} <= texts


# ── AC-11 / AC-12: rapor ve determinizm ─────────────────────────────────────


def test_report_is_written_next_to_the_dxf(generated) -> None:  # noqa: ANN001
    out, _ = generated
    report_path = out.with_suffix(".report.txt")
    assert report_path.is_file()

    content = report_path.read_text(encoding="utf-8")
    assert "[TBL WARN]" in content  # taşan hücre raporlanmış
    assert "text overflow" in content
    assert "cell=Mahal!C6" in content  # sayfadaki gerçek referans


def test_two_runs_produce_identical_geometry(reference_ods: Path, tmp_path: Path) -> None:
    """AC-12: koordinatlar, katmanlar ve metin içerikleri aynı."""

    def fingerprint(path: Path) -> list[tuple]:
        doc = ezdxf.readfile(str(path))
        rows = []
        for entity in doc.blocks.get(BLOCK):
            kind = entity.dxftype()
            if kind == "LWPOLYLINE":
                geom = tuple(
                    (round(x, 6), round(y, 6)) for x, y in entity.get_points("xy")
                )
                extra = entity.dxf.lineweight
            elif kind == "TEXT":
                anchor = (
                    entity.dxf.align_point if entity.dxf.halign else entity.dxf.insert
                )
                geom = ((round(anchor[0], 6), round(anchor[1], 6)),)
                extra = entity.dxf.text
            elif kind == "MTEXT":
                insert = entity.dxf.insert
                geom = ((round(insert[0], 6), round(insert[1], 6)),)
                extra = (entity.text, round(entity.dxf.width, 6))
            else:  # HATCH — zemin ve hücre dolguları
                boundary = entity.paths.paths[0]
                geom = tuple(
                    (round(v[0], 6), round(v[1], 6)) for v in boundary.vertices
                )
                extra = entity.rgb
            rows.append((kind, entity.dxf.layer, geom, extra))
        return rows

    first, second = tmp_path / "bir.dxf", tmp_path / "iki.dxf"
    assert run_cli(reference_ods, first) == EXIT_OK
    assert run_cli(reference_ods, second) == EXIT_OK
    assert fingerprint(first) == fingerprint(second)


# ── AC-10: hata yolları dosya bırakmaz ──────────────────────────────────────


def test_failed_run_leaves_no_output_and_no_report(reference_ods: Path, tmp_path: Path) -> None:
    out = tmp_path / "olmamali.dxf"
    code = main(
        [
            str(reference_ods),
            "--sheet",
            "OlmayanSayfa",
            "--range",
            REFERENCE_RANGE,
            "--out",
            str(out),
            "--block",
            BLOCK,
        ]
    )
    assert code == EXIT_DATA_ERROR
    assert not out.exists()
    assert not out.with_suffix(".report.txt").exists()
    assert list(tmp_path.iterdir()) == []


def test_overflow_full_mode_changes_the_output(reference_ods: Path, tmp_path: Path) -> None:
    out = tmp_path / "full.dxf"
    assert run_cli(reference_ods, out, "--overflow", "full") == EXIT_OK

    doc = ezdxf.readfile(str(out))
    block = doc.blocks.get(BLOCK)
    assert not [e for e in block if e.dxf.layer == "ONCU_TBL_OVERFLOW"]

    texts = {e.dxf.text for e in block if e.dxftype() == "TEXT"}
    assert OVERFLOW_TEXT in texts  # tam metin, kırpılmamış


def test_scale_flag_changes_the_drawing_size(reference_ods: Path, tmp_path: Path) -> None:
    out = tmp_path / "olcek.dxf"
    assert run_cli(reference_ods, out, "--scale", "20") == EXIT_OK

    doc = ezdxf.readfile(str(out))
    xs = [
        point[0]
        for e in doc.blocks.get(BLOCK)
        if e.dxftype() == "LWPOLYLINE"
        for point in e.get_points("xy")
    ]
    assert max(xs) == pytest.approx(210.0)  # 105 × 2
