"""SheetModel ve yardımcı tipler.

Bu modül saf veridir: ne `odfpy`'yi ne `ezdxf`'i görür. Okuyucu burayı doldurur,
geometri üreticisi burayı okur. Tüm uzunluklar **mm** cinsindendir (F-001).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Rgb = tuple[int, int, int]

HAlign = Literal["left", "center", "right"]
VAlign = Literal["top", "middle", "bottom"]

BLACK: Rgb = (0, 0, 0)


@dataclass(frozen=True)
class Border:
    width_mm: float  # 0.0 = kenarlık yok
    color: Rgb = BLACK

    @property
    def visible(self) -> bool:
        return self.width_mm > 0.0


NO_BORDER = Border(0.0, BLACK)


@dataclass(frozen=True)
class Borders:
    left: Border = NO_BORDER
    right: Border = NO_BORDER
    top: Border = NO_BORDER
    bottom: Border = NO_BORDER


@dataclass(frozen=True)
class FontSpec:
    size_pt: float = 10.0
    bold: bool = False
    italic: bool = False
    color: Rgb = BLACK


@dataclass(frozen=True)
class Cell:
    row: int  # SheetModel içinde 0-tabanlı
    col: int
    text: str  # .ods'teki GÖRÜNEN metin (biçimlenmiş)
    h_align: HAlign = "left"
    v_align: VAlign = "bottom"
    font: FontSpec = field(default_factory=FontSpec)
    borders: Borders = field(default_factory=Borders)
    fill: Rgb | None = None
    padding_mm: float = 0.97
    col_span: int = 1  # 1 = birleştirme yok
    row_span: int = 1
    covered: bool = False  # başka bir hücrenin birleştirmesi tarafından kapsanıyor

    # Calc'ta "metni kaydır" açık: metin hücre genişliğinde satırlara bölünür.
    wrap: bool = False
    # `style:rotation-angle` — saat yönünün tersine derece. 90 = aşağıdan yukarı
    # okunan dikey başlık; dar sütunlarda yaygın.
    rotation_deg: float = 0.0


@dataclass
class SheetModel:
    source_ref: str  # "Mahal!B3:C500" — hata mesajlarında kullanılır
    col_widths_mm: list[float]  # gizli sütunlar çıkarılmış hâliyle
    row_heights_mm: list[float]  # gizli satırlar çıkarılmış hâliyle
    cells: dict[tuple[int, int], Cell] = field(default_factory=dict)

    # Model içi indeksin kaynak sayfadaki karşılığı. Gizli satır/sütunlar
    # düşürüldüğü için indeksler kayar; rapor satırları kullanıcının sayfada
    # gördüğü referansı basmak zorunda, bu yüzden eşleme modelle taşınır.
    sheet_name: str = ""
    row_refs: list[int] = field(default_factory=list)  # 0-tabanlı sayfa satırı
    col_refs: list[int] = field(default_factory=list)  # 0-tabanlı sayfa sütunu

    @property
    def n_rows(self) -> int:
        return len(self.row_heights_mm)

    @property
    def n_cols(self) -> int:
        return len(self.col_widths_mm)

    def cell(self, row: int, col: int) -> Cell:
        """Var olmayan hücre boş bir hücredir — `.ods` boş hücreleri hep yazmaz."""
        found = self.cells.get((row, col))
        if found is not None:
            return found
        return Cell(row=row, col=col, text="")

    def ref(self, row: int, col: int) -> str:
        """`Mahal!C17` — hata ve uyarı satırlarında kullanılan hücre referansı."""
        sheet = self.sheet_name or self.source_ref.partition("!")[0]
        sheet_row = self.row_refs[row] if row < len(self.row_refs) else row
        sheet_col = self.col_refs[col] if col < len(self.col_refs) else col
        return f"{sheet}!{col_index_to_letters(sheet_col)}{sheet_row + 1}"


# ── Hücre referansı biçimlendirme ───────────────────────────────────────────
# Hata mesajları model içi 0-tabanlı indeksleri değil, kullanıcının sayfada
# gördüğü referansı basmalı. Bu yüzden model, seçim içi konumu sayfa
# koordinatına çeviren bilgiyi taşımak zorunda değil; okuyucu çevirir.


def col_index_to_letters(index: int) -> str:
    """0 → A, 25 → Z, 26 → AA."""
    if index < 0:
        raise ValueError(f"negative column index: {index}")
    letters = ""
    n = index + 1
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters = chr(ord("A") + rem) + letters
    return letters


def letters_to_col_index(letters: str) -> int:
    """A → 0, Z → 25, AA → 26."""
    if not letters:
        raise ValueError("empty column reference")
    n = 0
    for ch in letters.upper():
        if not ("A" <= ch <= "Z"):
            raise ValueError(f"invalid column reference: {letters!r}")
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n - 1
