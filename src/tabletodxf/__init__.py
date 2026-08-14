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
from .bookmarks import (
    JobBookmark,
    bookmarks_dir,
    delete_bookmark,
    list_bookmarks,
    load_bookmark,
    rename_bookmark,
    save_bookmark,
)
from .config import (
    DEFAULT_PROFILE_NAME,
    BackgroundConfig,
    Config,
    LayerConfig,
    LayoutConfig,
    OutputConfig,
    OverflowConfig,
    SourceConfig,
    TextConfig,
    app_data_dir,
    apply_overrides,
    config_from_dict,
    config_to_dict,
    delete_profile,
    ensure_default_profile,
    list_profiles,
    load_config,
    load_profile,
    profiles_dir,
    rename_profile,
    save_config,
    save_profile,
)
from .errors import TableToDxfError, UsageError
from .ods_reader import list_sheets
from .report import Report

__version__ = "0.3.0"

__all__ = [
    "DEFAULT_PROFILE_NAME",
    "BackgroundConfig",
    "Config",
    "Job",
    "JobBookmark",
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
    "app_data_dir",
    "apply_overrides",
    "bookmarks_dir",
    "config_from_dict",
    "config_to_dict",
    "convert",
    "delete_bookmark",
    "delete_profile",
    "ensure_default_profile",
    "list_bookmarks",
    "list_profiles",
    "list_sheets",
    "load_bookmark",
    "load_config",
    "load_profile",
    "profiles_dir",
    "rename_bookmark",
    "rename_profile",
    "save_bookmark",
    "save_config",
    "save_profile",
]
