"""tabletodxf — `.ods` aralığından kendi kendine yeten AutoCAD blok tanımı üretir.

Katmanlar (F-001):

    cli          → argüman ayrıştırma, config birleştirme, çıkış kodu
    ods_reader   → .ods → SheetModel   (odfpy yalnızca burada)
    model        → SheetModel ve yardımcı tipler
    metrics      → TTF ile metin genişliği ölçümü
    geometry     → SheetModel → çizilecek varlıklar
    dxf_writer   → varlıklar → ezdxf blok tanımı → dosya  (ezdxf yalnızca burada)
    report       → [TBL …] satırları, konsol + .report.txt
"""

__version__ = "0.1.0"
