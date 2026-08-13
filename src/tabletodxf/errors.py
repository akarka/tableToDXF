"""Hata kataloğu (F-001).

Tek bir istisna tipi var; ayırt edici olan `code`. Kod, kullanıcıya basılan
mesajın içinde geçer ve dokümandaki tabloya birebir karşılık gelir.

`model.py` saf veri kaldığı için hata tipi ayrı bir modülde durur: hem okuyucu
hem geometri üreticisi buradan içe aktarır, birbirlerini görmezler.
"""

from __future__ import annotations


class TableToDxfError(Exception):
    """Çıktı üretilmeden durduran hata.

    `op`, `cell` ve ek alanlar `[TBL ERROR]` satırını oluşturmak için taşınır.
    """

    def __init__(
        self,
        code: str,
        op: str,
        reason: str,
        cell: str | None = None,
        **fields: object,
    ) -> None:
        self.code = code
        self.op = op
        self.reason = reason
        self.cell = cell
        self.fields = fields
        super().__init__(reason)


class UsageError(TableToDxfError):
    """Kullanım hatası — çıkış kodu 2 (doğrulama/veri hatasından ayrı)."""


# Katalog kodları. Kod adı sabit tutulur; mesaj metni değişebilir.
SRC_FORMAT = "SRC_FORMAT"
SRC_NOT_FOUND = "SRC_NOT_FOUND"
SRC_SHEET_NOT_FOUND = "SRC_SHEET_NOT_FOUND"
SRC_RANGE_INVALID = "SRC_RANGE_INVALID"
SRC_STALE = "SRC_STALE"  # WARN seviyesi
MERGE_CROSSES_SELECTION = "MERGE_CROSSES_SELECTION"
FORMULA_NO_CACHE = "FORMULA_NO_CACHE"
CELL_OVERFLOW = "CELL_OVERFLOW"  # WARN seviyesi
FONT_NOT_FOUND = "FONT_NOT_FOUND"
SELECTION_EMPTY = "SELECTION_EMPTY"
CONFIG_INVALID = "CONFIG_INVALID"
