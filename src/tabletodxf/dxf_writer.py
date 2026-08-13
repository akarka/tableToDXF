"""Varlıklar → `ezdxf` blok tanımı → dosya. `ezdxf` yalnızca bu modülde geçer.

Varlık eşlemesi: kenarlık → `LWPOLYLINE`, metin → `TEXT`, dolgu → düz desenli
`HATCH`.


Çıktı iki şeyi birden taşır: `--block` adlı **blok tanımı** (AC-1) ve model
uzayında bu bloğun origin'deki tek bir `INSERT`'ü. Tanım tek başına
`-INSERT blok=dosya` akışı için yeterli; `INSERT` ise dosya doğrudan açıldığında
tablonun görünmesini sağlar — tanımı olup örneği olmayan bir DXF boş açılır ve
görsel doğrulamayı imkânsız kılardı.
"""

from __future__ import annotations

from pathlib import Path

import ezdxf
from ezdxf.enums import TextEntityAlignment
from ezdxf.lldxf import const

from .geometry import BorderLine, Drawing, FillShape, TextBox, TextItem
from .model import HAlign, Rgb, VAlign
from .report import Report

# DXF `lineweight` 1/100 mm cinsindendir ve yalnızca sabit bir değer kümesini
# kabul eder; ara değerler dosyayı geçersiz kılar.
_VALID_LINEWEIGHTS = sorted(
    value for value in const.VALID_DXF_LINEWEIGHT_VALUES if value > 0
)

_ALIGN_MAP: dict[HAlign, TextEntityAlignment] = {
    "left": TextEntityAlignment.LEFT,
    "center": TextEntityAlignment.CENTER,
    "right": TextEntityAlignment.RIGHT,
}

# `MTEXT` bağlanma noktası, hücrenin (dikey, yatay) hizalama çiftine birebir
# oturuyor — taban çizgisi hesabına gerek kalmıyor.
_ATTACHMENT_MAP: dict[tuple[VAlign, HAlign], int] = {
    ("top", "left"): const.MTEXT_TOP_LEFT,
    ("top", "center"): const.MTEXT_TOP_CENTER,
    ("top", "right"): const.MTEXT_TOP_RIGHT,
    ("middle", "left"): const.MTEXT_MIDDLE_LEFT,
    ("middle", "center"): const.MTEXT_MIDDLE_CENTER,
    ("middle", "right"): const.MTEXT_MIDDLE_RIGHT,
    ("bottom", "left"): const.MTEXT_BOTTOM_LEFT,
    ("bottom", "center"): const.MTEXT_BOTTOM_CENTER,
    ("bottom", "right"): const.MTEXT_BOTTOM_RIGHT,
}


def escape_mtext(text: str) -> str:
    r"""Düz metni `MTEXT` içeriğine çevirir.

    `MTEXT` biçimlendirmeyi metnin içinde taşır: `\` kaçış karakteri, `{` ve `}`
    grup ayraçlarıdır. Kaçırılmazsa `{` içeren bir hücre — ör. bir açıklama
    notu — çizimde metnin bir kısmını yutar. Satır sonu `\P` ile verilir; bu
    dönüşüm en sonda yapılmalı, yoksa kendi eklediği ters bölü de kaçırılır.
    """
    escaped = text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
    return escaped.replace("\n", "\\P")


def layer_names(prefix: str) -> dict[str, str]:
    return {
        "grid": f"{prefix}_GRID",
        "text": f"{prefix}_TEXT",
        "fill": f"{prefix}_FILL",
        "overflow": f"{prefix}_OVERFLOW",
    }


def snap_lineweight(width_mm: float) -> int:
    """mm → en yakın geçerli DXF lineweight (1/100 mm).

    Sayfadan gelen kalınlıklar (`0.06pt`, `0.5pt`, `2.5pt` …) DXF'in kümesine
    düşmez; en yakın geçerli değere yuvarlanır. 0'a yuvarlanmaz — kaynakta
    görünür olan bir kenarlık çizimde de görünür kalmalı.
    """
    hundredths = width_mm * 100.0
    return min(_VALID_LINEWEIGHTS, key=lambda valid: abs(valid - hundredths))


def write(
    drawing: Drawing,
    out_path: Path,
    report: Report,
    *,
    block_name: str,
    layer_prefix: str,
    text_style: str,
    font_file: str,
    dxf_version: str = "R2013",
) -> None:
    doc = ezdxf.new(dxfversion=dxf_version, setup=False)

    # AC-8: birimsiz çıktı. Hedef çizime INSERT edildiğinde otomatik ölçekleme
    # devreye girmez; ölçek yalnızca `--scale` ile, üretim anında belirlenir.
    doc.header["$INSUNITS"] = 0

    # Stil tekil bir adla tanımlanır ki hedef çizimdeki aynı adlı bir stil onu
    # sessizce ezmesin (ADR-002). Kiril/CJK için TTF şart, SHX yetmez (AC-9).
    if text_style not in doc.styles:
        doc.styles.add(text_style, font=font_file)

    layers = layer_names(layer_prefix)
    for key, name in layers.items():
        if name not in doc.layers:
            # Katmanlar işlev taşır, stil değil. Renk yalnızca `_OVERFLOW` için
            # anlamlı: `###` içerik değil, teşhis çıktısıdır — kırmızı durur.
            doc.layers.add(name, color=1 if key == "overflow" else 7)

    block = doc.blocks.new(name=block_name, base_point=(0, 0))

    # Zemin ilk yazılır — blok içinde çizim sırası varlık sırasıdır, yani ilk
    # yazılan en arkada kalır.
    if drawing.background is not None:
        _add_fill(block, drawing.background, layers["fill"])
    for fill in drawing.fills:
        _add_fill(block, fill, layers["fill"])
    for line in drawing.lines:
        _add_line(block, line, layers["grid"])
    for text in drawing.texts:
        _add_text(block, text, layers["text"], text_style, use_true_color=True)
    for marker in drawing.markers:
        _add_text(block, marker, layers["overflow"], text_style, use_true_color=False)
    for box in drawing.boxes:
        _add_mtext(block, box, layers["overflow"], text_style)
    for item in drawing.condensed:
        # Sıkıştırılmış metin gerçek içeriktir — kendi rengini taşır. Yine de
        # `_OVERFLOW` katmanında durur ki hangi hücrelerin sıkıştırıldığı
        # katman seçimiyle görülebilsin.
        _add_text(block, item, layers["overflow"], text_style, use_true_color=True)

    doc.modelspace().add_blockref(block_name, (0, 0))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(str(out_path))

    report.info(
        "write_dxf",
        "block written",
        block=block_name,
        entities=drawing.entity_count,
        fills=len(drawing.fills) + (1 if drawing.background is not None else 0),
        lines=len(drawing.lines),
        texts=len(drawing.texts),
        markers=len(drawing.markers),
        mtexts=len(drawing.boxes),
        condensed=len(drawing.condensed),
    )


def _true_color(color: Rgb) -> int:
    return ezdxf.rgb2int(color)


def _add_fill(block, fill: FillShape, layer: str) -> None:  # noqa: ANN001
    """Arka plan dolgusu — düz desenli `HATCH`.

    `SOLID` yerine `HATCH`: dolgu düzenlenebilir bir sınıra sahip olur, saydamlık
    ve çizim sırası (draw order) taşıyabilir, ve AutoCAD tarafında hücre dolgusu
    için beklenen varlık tipidir. `SOLID` ayrıca köşeleri halka değil `Z`
    sırasında ister — sessizce papyona dönen bir tuzak; `HATCH` sınırı halka
    olarak aldığı için o tuzak da ortadan kalkar.

    Hücre başına bir `HATCH` üretilir. Aynı renkteki tüm dolguları tek bir
    varlıkta toplamak dosyayı küçültürdü, ama tek bir hücrenin dolgusunu seçip
    silmeyi imkânsız kılardı.
    """
    hatch = block.add_hatch(dxfattribs={"layer": layer})
    hatch.set_solid_fill(rgb=fill.color)
    hatch.paths.add_polyline_path(fill.corners, is_closed=True)


def _add_line(block, line: BorderLine, layer: str) -> None:  # noqa: ANN001
    """Kalınlık varlık üzerinde (ByObject) — kenar başına değiştiği için BYLAYER
    olamaz (ADR-002)."""
    block.add_lwpolyline(
        [line.start, line.end],
        format="xy",
        dxfattribs={
            "layer": layer,
            "true_color": _true_color(line.color),
            "lineweight": snap_lineweight(line.width_mm),
        },
    )


def _add_text(
    block,  # noqa: ANN001
    item: TextItem,
    layer: str,
    text_style: str,
    *,
    use_true_color: bool,
) -> None:
    attribs: dict[str, object] = {"layer": layer, "style": text_style}
    if use_true_color:
        attribs["true_color"] = _true_color(item.color)
    if item.width_factor != 1.0:
        # DXF `width`, TEXT'in yatay ölçek çarpanıdır (yükseklik değişmez).
        # AutoCAD otomatik heceleme yapmadığı için, uzun bir kelimeyi hücreye
        # sığdırmanın tek yolu bu.
        attribs["width"] = item.width_factor
    entity = block.add_text(item.text, height=item.height, dxfattribs=attribs)
    entity.set_placement(item.insert, align=_ALIGN_MAP[item.h_align])
    if item.rotation_deg:
        # Yerleştirmeden **sonra**: `set_placement` hizalama noktasını yeniden
        # yazıyor ve dönüşü de sıfırlayabilir.
        # DXF `rotation` da saat yönünün tersine derece — `.ods`'in
        # `style:rotation-angle` ile aynı yön ve birim, çevirme gerekmiyor.
        entity.dxf.rotation = item.rotation_deg


def _add_mtext(block, box: TextBox, layer: str, text_style: str) -> None:  # noqa: ANN001
    """Taşan hücre — `MTEXT`, tanımlı genişliği hücrenin metin alanı kadar.

    `width` hücre genişliğinden dolgu payı düşülerek verilir; yani sayfadaki
    metin alanının aynısı. Alıcı AutoCAD'de genişlik tutamağını çekerek
    yerleşimi düzeltebilir — `###` ile yapılamayan şey buydu.
    """
    attribs: dict[str, object] = {
        "layer": layer,
        "style": text_style,
        "char_height": box.height,
        "width": box.width,
        "true_color": _true_color(box.color),
    }
    mtext = block.add_mtext(escape_mtext(box.text), dxfattribs=attribs)
    mtext.set_location(
        box.insert,
        rotation=box.rotation_deg,
        attachment_point=_ATTACHMENT_MAP[(box.v_align, box.h_align)],
    )
