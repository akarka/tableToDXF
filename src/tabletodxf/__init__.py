"""tabletodxf — `.ods` aralığından kendi kendine yeten AutoCAD blok tanımı üretir.

Katmanlar (F-001):

    cli          → argüman ayrıştırma, çıkış kodu (ince sarmalayıcı)
    api          → Job / Result / convert()  — tek giriş noktası
    config       → tipli ayar katmanı (saf veri)
    ods_reader   → .ods → SheetModel   (odfpy yalnızca burada)
    model        → SheetModel ve yardımcı tipler
    metrics      → TTF ile metin genişliği ölçümü
    geometry     → SheetModel → çizilecek varlıklar
    dxf_writer   → varlıklar → ezdxf blok tanımı → dosya  (ezdxf yalnızca burada)
    report       → [TBL …] satırları, konsol + .report.txt

Ayar katmanı ADR-003 ve F-002'de gerekçelendirildi. `convert()` CLI, UI ve
suite için tek giriş noktasıdır ve `argparse`/`tkinter` yüklemez.
"""

from .api import Job, Result, convert
from .config import (
    BackgroundConfig,
    Config,
    LayerConfig,
    LayoutConfig,
    OutputConfig,
    OverflowConfig,
    SourceConfig,
    TextConfig,
    apply_overrides,
    config_from_dict,
    config_to_dict,
    load_config,
    save_config,
)
from .errors import TableToDxfError, UsageError
from .report import Report

__version__ = "0.2.0"

__all__ = [
    "BackgroundConfig",
    "Config",
    "Job",
    "LayerConfig",
    "LayoutConfig",
    "OutputConfig",
    "OverflowConfig",
    "Report",
    "Result",
    "SourceConfig",
    "TableToDxfError",
    "TextConfig",
    "UsageError",
    "apply_overrides",
    "config_from_dict",
    "config_to_dict",
    "convert",
    "load_config",
    "save_config",
]
