"""TTF ile metin genişliği ölçümü — sığdı / sığmadı kararı.

`ezdxf`'in font yardımcıları yerine `fontTools` doğrudan kullanılıyor (F-001 Open
Question). Gerekçe: `ezdxf.fonts` isimle çözüm yapar ve sistem font önbelleğine
bakar; burada kullanıcı `--font` ile **açık bir dosya yolu** veriyor ve ölçümün
paketlenmiş `.exe` içinde de birebir aynı çıkması gerekiyor (AC-12).

DXF'te TTF tabanlı bir metin stilinde `height` **büyük harf yüksekliğidir**, em
boyu değil. Calc ise em boyuna (`font-size`) göre çizer. İkisini karıştırmak
metni sistematik olarak büyük gösterir; bu yüzden yükseklik `capHeight/upem`
oranıyla çevrilir, genişlik ise em boyuyla ölçülür.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fontTools.ttLib import TTFont

from .errors import FONT_NOT_FOUND, TableToDxfError

PT_TO_MM = 25.4 / 72.0

# OS/2 tablosu yoksa ya da sCapHeight boşsa kullanılan oran. Latin fontlarda
# tipik değer 0.70–0.73 arasında.
_FALLBACK_CAP_RATIO = 0.70


@dataclass
class FontMetrics:
    """Tek bir TTF dosyasının ölçüm yüzeyi. Örnek başına bir kez yüklenir."""

    path: Path
    units_per_em: int
    cap_ratio: float
    _advances: dict[int, int]
    _cmap: dict[int, str]
    _hmtx: dict[str, tuple[int, int]]
    _fallback_advance: int

    @classmethod
    def from_file(cls, path: str | Path) -> FontMetrics:
        font_path = Path(path)
        if not font_path.is_file():
            raise TableToDxfError(
                FONT_NOT_FOUND,
                op="load_font",
                reason="font file not found",
                font=str(font_path),
            )
        try:
            ttf = TTFont(str(font_path), fontNumber=0, lazy=True)
            units_per_em = int(ttf["head"].unitsPerEm)
            cmap = ttf.getBestCmap()
            hmtx = dict(ttf["hmtx"].metrics)
        except TableToDxfError:
            raise
        except Exception as exc:  # noqa: BLE001 — kütüphane çok çeşitli hata atıyor
            raise TableToDxfError(
                FONT_NOT_FOUND,
                op="load_font",
                reason="font file is not a readable TTF",
                font=str(font_path),
                detail=type(exc).__name__,
            ) from exc

        cap_ratio = _FALLBACK_CAP_RATIO
        os2 = ttf.get("OS/2")
        cap_height = getattr(os2, "sCapHeight", 0) or 0
        if cap_height > 0:
            cap_ratio = cap_height / units_per_em

        # Bilinmeyen kod noktaları için makul bir yedek: boşluk, yoksa em/2.
        fallback_glyph = cmap.get(ord(" "))
        fallback_advance = (
            hmtx[fallback_glyph][0] if fallback_glyph in hmtx else units_per_em // 2
        )

        return cls(
            path=font_path,
            units_per_em=units_per_em,
            cap_ratio=cap_ratio,
            _advances={},
            _cmap=cmap,
            _hmtx=hmtx,
            _fallback_advance=fallback_advance,
        )

    # ── Ölçüm ───────────────────────────────────────────────────────────────

    def _advance(self, codepoint: int) -> int:
        cached = self._advances.get(codepoint)
        if cached is not None:
            return cached
        glyph = self._cmap.get(codepoint)
        metrics = self._hmtx.get(glyph) if glyph is not None else None
        advance = metrics[0] if metrics is not None else self._fallback_advance
        self._advances[codepoint] = advance
        return advance

    def text_width_mm(self, text: str, size_pt: float) -> float:
        """Kerning uygulanmaz — ölçüm advance toplamıdır.

        Kerning genişliği ancak binde birkaç oynatır; sığdı/sığmadı kararında
        gözle görülür bir fark yaratmaz ve `fontTools`'un GPOS çözümlemesini
        her hücre için çalıştırmak ölçüm maliyetini katlar.
        """
        if not text:
            return 0.0
        total_units = sum(self._advance(ord(ch)) for ch in text)
        return total_units / self.units_per_em * size_pt * PT_TO_MM

    def char_width_mm(self, char: str, size_pt: float) -> float:
        return self.text_width_mm(char, size_pt)

    def cap_height_mm(self, size_pt: float) -> float:
        """DXF `TEXT.height` — em boyu değil, büyük harf yüksekliği."""
        return size_pt * PT_TO_MM * self.cap_ratio

    def line_height_mm(self, size_pt: float) -> float:
        """Çok satırlı hücrede satır adımı. Calc'ın tek aralık davranışı."""
        return size_pt * PT_TO_MM


def fits(text_width_mm: float, available_mm: float) -> bool:
    """Sığdırma kontrolü. Kayan nokta gürültüsüne karşı küçük bir tolerans.

    Tolerans olmadan, tam sığan bir metin (ölçülen genişlik = kullanılabilir
    genişlik) makineye göre bazen taşmış sayılırdı; bu da AC-12'yi (aynı girdi →
    aynı çıktı) farklı platformlarda bozardı.
    """
    return text_width_mm <= available_mm + 1e-9
