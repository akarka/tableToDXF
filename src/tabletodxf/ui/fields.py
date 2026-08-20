"""Alan başına görünen ad ve yardım metni — F-002 kataloğunun UI yansıması.

**Tek doğru kaynak F-002.md'dir.** Buradaki metinler oradaki "Ayar Kataloğu"
tablosundan elle taşınmıştır (dataclass alanları `metadata=` taşımıyor —
F-003 Open Questions'ta kayıtlı bilinçli bir borç). F-002'ye yeni bir ayar
eklenip burası güncellenmezse UI o alanı ham adıyla gösterir — çirkin ama
işlevsel; `field_meta()` bunu garanti eder, asla `KeyError` atmaz.
"""

from __future__ import annotations

from dataclasses import dataclass

SECTION_TITLES: dict[str, str] = {
    "source": "Kaynak",
    "layout": "Yerleşim",
    "text": "Metin",
    "overflow": "Taşma",
    "background": "Zemin",
    "layers": "Katmanlar",
    "output": "Çıktı",
}

# Sekme sırası **bilinçli olarak** `Config`'in dataclass alan sırasından
# ayrıdır. O sıra (source, layout, text, overflow, background, layers,
# output) TOML çıktısını ve F-002 kataloğunu belirliyor, orada sabit kalması
# gerekiyor — burada değiştirmek TOML'u da karıştırırdı.
#
# UI sırası kullanıcının gerçekte en çok dokunduğu bölümlere göre (2026-08-14
# kullanıcı kararı): `overflow`/`layers`/`layout` sık ayarlanır (tablo
# başına farklı taşma davranışı, ofis katman standardı, çerçeve/ölçek);
# `source` en seyrek dokunulanıdır — yalnızca `.ods`'in söylemediği
# durumlarda devreye girer ve Calc bu bilgileri neredeyse her zaman zaten
# taşır, o yüzden en sona alınır.
TAB_ORDER: tuple[str, ...] = (
    "overflow",
    "layers",
    "layout",
    "background",
    "output",
    "text",
    "source",
)


@dataclass(frozen=True)
class FieldMeta:
    label: str
    help: str


_RAW: dict[str, dict[str, tuple[str, str]]] = {
    "source": {
        "default_col_width_mm": (
            "Varsayılan sütun genişliği (mm)",
            ".ods'te tanımsız sütunun genişliği (Calc varsayılanı)",
        ),
        "default_row_height_mm": (
            "Varsayılan satır yüksekliği (mm)",
            "Tanımsız satırın yüksekliği",
        ),
        "default_padding_mm": (
            "Varsayılan hücre dolgusu (mm)",
            "fo:padding yoksa hücre iç boşluğu",
        ),
        "default_font_size_pt": (
            "Varsayılan font boyutu (pt)",
            "Font boyutu belirtilmemişse",
        ),
        "default_text_color": ("Varsayılan metin rengi", "Metin rengi belirtilmemişse"),
        "default_border_color": ("Varsayılan kenarlık rengi", "Kenarlık rengi belirtilmemişse"),
        "borderless_width_pt": (
            "Kalınlıksız kenarlık kalınlığı (pt)",
            '"solid #000" gibi kalınlık taşımayan kenarlık. 0 = böyle kenarlıklar çizilmez',
        ),
        "default_v_align": (
            "Varsayılan dikey hizalama",
            "Dikey hizalama belirtilmemişse (Calc davranışı)",
        ),
        "align_numeric": (
            "Sayı hizalaması",
            "Açık hizalaması olmayan sayı/tarih/para hücresi",
        ),
        "align_boolean": (
            "Mantıksal değer hizalaması",
            "Açık hizalaması olmayan mantıksal (TRUE/FALSE) hücre",
        ),
        "align_text": ("Metin hizalaması", "Açık hizalaması olmayan metin hücresi"),
        "stale_check_suffixes": (
            "Bayat kaynak kontrolü uzantıları",
            "SRC_STALE uyarısı için yanında aranan kardeş dosyalar. Boş = kontrol kapalı",
        ),
    },
    "layout": {
        "scale_cm_to_units": ("Ölçek (1 cm = ? birim)", "1 cm kaç çizim birimi"),
        "frame_mm": ("Dış çerçeve kalınlığı (mm)", "0 = çerçeve yok"),
        "line_spacing": (
            "Satır aralığı çarpanı",
            "Çok satırlı hücrede satır adımının em çarpanı",
        ),
    },
    "text": {
        "style_name": (
            "Metin stili adı",
            "DXF metin stili adı (hedef çizimdekini ezmemek için tekil olmalı)",
        ),
        "font_file": ("Font dosyası", "Ölçüm ve stil için TTF; çıplak ad ya da tam yol"),
        "fallback_cap_ratio": (
            "Yedek büyük harf oranı",
            "Fontta OS/2.sCapHeight yoksa kullanılan büyük harf yüksekliği oranı",
        ),
    },
    "overflow": {
        "mode": ("Taşma modu", "condense | mtext | marker | full — bkz. F-001"),
        "marker_char": ("İşaret karakteri", "marker modunda kullanılan tek karakter"),
        "min_width_factor": (
            "Sıkıştırma tabanı",
            "condense modunda okunabilirlik tabanı (0–1)",
        ),
    },
    "background": {
        "enabled": ("Zemin açık", "Seçimin tamamını kaplayan opak zemin çizilsin mi"),
        "color": ("Zemin rengi", "Zemin açıksa kullanılan renk"),
    },
    "layers": {
        "prefix": ("Katman öneki", "Tüm katman adlarının başına eklenir"),
        "grid_suffix": ("Izgara sonek", "Kenarlık katmanının soneki"),
        "text_suffix": ("Metin sonek", "Metin katmanının soneki"),
        "fill_suffix": ("Dolgu sonek", "Zemin ve dolgu katmanının soneki"),
        "overflow_suffix": ("Taşma sonek", "Taşan hücre katmanının soneki"),
        "grid_color": ("Izgara rengi (ACI)", "1–255 arası AutoCAD renk indeksi"),
        "text_color": ("Metin rengi (ACI)", "1–255 arası AutoCAD renk indeksi"),
        "fill_color": ("Dolgu rengi (ACI)", "1–255 arası AutoCAD renk indeksi"),
        "overflow_color": (
            "Taşma rengi (ACI)",
            "Varsayılan kırmızı (1) — ### içerik değil, teşhis çıktısıdır",
        ),
    },
    "output": {
        "dxf_version": ("DXF sürümü", "R2013 veya R2018 — eskisi TTF metin stili taşımaz"),
        "insert_block_reference": (
            "Model uzayına INSERT eklensin",
            "Kapalıysa yalnızca blok tanımı yazılır, dosya doğrudan açılınca boş görünür",
        ),
        "block_base_point": ("Blok taban noktası (X, Y)", "Blok tanımının orijini"),
        "write_report": (
            "Rapor dosyası yazılsın",
            "Başarılı çalıştırmada .report.txt yazılsın mı",
        ),
        "bylayer_defaults": (
            "Tam siyahı katmana bırak (BYLAYER)",
            "Yalnızca rengi tam siyah (0,0,0) olan kenarlık/metin katman rengine "
            "düşer — CTB/kalem tablosu uyumu için. Renkli hiçbir şeye dokunmaz",
        ),
    },
}


def field_meta(section: str, field: str) -> FieldMeta:
    """Etiket/yardım metni. Bilinmeyen alan için ham adı döner — asla patlamaz.

    F-002'ye eklenip burada karşılığı unutulan bir ayar, formda **çirkin ama
    işlevsel** görünür; sessizce kaybolmaz.
    """
    label, help_text = _RAW.get(section, {}).get(field, (field, ""))
    return FieldMeta(label=label, help=help_text)


def section_title(section: str) -> str:
    return SECTION_TITLES.get(section, section)
