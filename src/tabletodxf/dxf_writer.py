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

from .config import LayerConfig, OutputConfig, TextConfig
from .geometry import BorderLine, Drawing, FillShape, FrameBox, TextBox, TextItem
from .model import BLACK, HAlign, Rgb, VAlign
from .report import Report

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
    """Yalnızca önek verildiğinde varsayılan soneklerle katman adları.

    Tam denetim `LayerConfig.names()` üzerinden; bu yardımcı kısa yol olarak
    duruyor.
    """
    return LayerConfig(prefix=prefix).names()


def write(
    drawing: Drawing,
    out_path: Path,
    report: Report,
    *,
    block_name: str,
    font_file: str,
    layers_config: LayerConfig | None = None,
    text_config: TextConfig | None = None,
    output_config: OutputConfig | None = None,
) -> None:
    layers_config = layers_config or LayerConfig()
    text_config = text_config or TextConfig()
    output_config = output_config or OutputConfig()

    doc = ezdxf.new(dxfversion=output_config.dxf_version, setup=False)

    # AC-8: birimsiz çıktı. Hedef çizime INSERT edildiğinde otomatik ölçekleme
    # devreye girmez; ölçek yalnızca üretim anında belirlenir.
    doc.header["$INSUNITS"] = 0

    # Stil tekil bir adla tanımlanır ki hedef çizimdeki aynı adlı bir stil onu
    # sessizce ezmesin (ADR-002). Kiril/CJK için TTF şart, SHX yetmez (AC-9).
    text_style = text_config.style_name
    if text_style not in doc.styles:
        doc.styles.add(text_style, font=font_file)

    layers = layers_config.names()
    colors = layers_config.colors()
    for key, name in layers.items():
        if name not in doc.layers:
            # Katmanlar işlev taşır, stil değil. Renk yalnızca `_OVERFLOW` için
            # anlamlı: `###` içerik değil, teşhis çıktısıdır — kırmızı durur.
            doc.layers.add(name, color=colors[key])

    block = doc.blocks.new(name=block_name, base_point=output_config.block_base_point)

    # Zemin ilk yazılır — blok içinde çizim sırası varlık sırasıdır, yani ilk
    # yazılan en arkada kalır.
    if drawing.background is not None:
        _add_fill(block, drawing.background, layers["fill"])
    for fill in drawing.fills:
        _add_fill(block, fill, layers["fill"])
    bylayer = output_config.bylayer_defaults
    for line in drawing.lines:
        _add_line(block, line, layers["grid"], use_true_color=_wants_true_color(line.color, bylayer))
    if drawing.frame is not None:
        _add_frame(
            block,
            drawing.frame,
            layers["grid"],
            use_true_color=_wants_true_color(drawing.frame.color, bylayer),
        )
    for text in drawing.texts:
        _add_text(
            block,
            text,
            layers["text"],
            text_style,
            use_true_color=_wants_true_color(text.color, bylayer),
        )
    for marker in drawing.markers:
        # Markerlar sentetiktir — hücrenin font rengini hiç taşımaz, her
        # zaman `_OVERFLOW` katmanının kendi (kırmızı) rengine düşer. Bu,
        # `bylayer_defaults`'tan bağımsız, F-001'den beri değişmeyen bir
        # tasarım kararı.
        _add_text(block, marker, layers["overflow"], text_style, use_true_color=False)
    for box in drawing.boxes:
        _add_mtext(
            block,
            box,
            layers["overflow"],
            text_style,
            use_true_color=_wants_true_color(box.color, bylayer),
        )
    for item in drawing.condensed:
        # Sıkıştırılmış metin gerçek içeriktir — kendi rengini taşır. Yine de
        # `_OVERFLOW` katmanında durur ki hangi hücrelerin sıkıştırıldığı
        # katman seçimiyle görülebilsin.
        _add_text(
            block,
            item,
            layers["overflow"],
            text_style,
            use_true_color=_wants_true_color(item.color, bylayer),
        )

    if output_config.insert_block_reference:
        doc.modelspace().add_blockref(block_name, output_config.block_base_point)

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


def _wants_true_color(color: Rgb, bylayer_defaults: bool) -> bool:
    """`output.bylayer_defaults` açıkken tam siyah varlıklar katmana bırakılır.

    Bkz. `OutputConfig.bylayer_defaults` — yalnızca `(0, 0, 0)` etkilenir;
    başka hiçbir renk bu bayraktan etkilenmez.
    """
    return not (bylayer_defaults and color == BLACK)


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


def _add_line(block, line: BorderLine, layer: str, *, use_true_color: bool) -> None:  # noqa: ANN001
    """Kalınlık polyline'ın **global genişliğiyle** taşınır, `lineweight` ile değil.

    `lineweight` bir görüntüleme/çizdirme niteliğidir: `LWDISPLAY` kapalıysa
    ekranda görünmez ve baskıda CTB/STB kalem tablosu onu ezebilir. Global
    genişlik ise gerçek geometridir — her zoom'da görünür, her kalem tablosunda
    aynı basar. Sayfadaki kalınlık hiyerarşisi (başlık altı kalın, ızgara ince)
    böylece çizimde birebir korunur (ADR-002). Bu, `bylayer_defaults`'tan
    bağımsız — kalınlık asla katmana bırakılmaz, yalnızca renk.

    `lineweight` bilinçli olarak hiç yazılmıyor; BYLAYER varsayılanında kalıyor.
    """
    attribs: dict[str, object] = {"layer": layer, "const_width": line.width}
    if use_true_color:
        attribs["true_color"] = _true_color(line.color)
    block.add_lwpolyline([line.start, line.end], format="xy", dxfattribs=attribs)


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


def _add_frame(block, frame: FrameBox, layer: str, *, use_true_color: bool) -> None:  # noqa: ANN001
    """Dış çerçeve — tek **kapalı** `LWPOLYLINE`.

    Kapalı olması köşelerin gönyeli birleşmesini sağlar; dört ayrı çizgide
    genişlik eksen çizgisinden açıldığı için köşelerde çentik kalırdı.
    """
    attribs: dict[str, object] = {"layer": layer, "const_width": frame.width}
    if use_true_color:
        attribs["true_color"] = _true_color(frame.color)
    block.add_lwpolyline(frame.corners, format="xy", close=True, dxfattribs=attribs)


def _add_mtext(
    block,  # noqa: ANN001
    box: TextBox,
    layer: str,
    text_style: str,
    *,
    use_true_color: bool,
) -> None:
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
    }
    if use_true_color:
        attribs["true_color"] = _true_color(box.color)
    mtext = block.add_mtext(escape_mtext(box.text), dxfattribs=attribs)
    mtext.set_location(
        box.insert,
        rotation=box.rotation_deg,
        attachment_point=_ATTACHMENT_MAP[(box.v_align, box.h_align)],
    )
