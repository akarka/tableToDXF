"""Çekirdek modüllerin UI'a bağımlı olmadığını sabitler (ADR-004, F-003 AC-9).

`tabletodxf.ui`'ın çekirdeğin **üstünde** bir yaprak olması (F-003) tersi
yönde de doğrulanmalı: `api.py`, `config.py`, `ods_reader.py` `tkinter`
görmemeli — suite bu üçünü UI hiç kurulu olmadan kullanabilmeli.

Statik kontrol: çalışma zamanı ölçümü yanıltıcı olurdu, çünkü herhangi bir alt
modülü içe aktarmak paketin `__init__`'ini tetikler ve o zaten `ui` dışındaki
her şeyi yükler. Buradaki iddia paketin değil, **her dosyanın kendisinin**
bağımsızlığı.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src" / "tabletodxf"
_FORBIDDEN = {"tkinter", "Tkinter"}


def _top_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    return imported


@pytest.mark.parametrize(
    "filename", ["api.py", "config.py", "ods_reader.py", "cli.py", "bookmarks.py"]
)
def test_core_module_does_not_import_tkinter(filename: str) -> None:
    imported = _top_level_imports(_SRC / filename)
    assert not imported & _FORBIDDEN, f"{filename} tkinter içe aktarıyor: {imported & _FORBIDDEN}"


def test_ui_package_is_the_only_place_tkinter_is_imported() -> None:
    """Tersi yön: `tkinter` yalnızca `ui/` altında geçmeli.

    Bu, gelecekte birinin `geometry.py`'ye "hızlıca bir mesaj kutusu" eklemek
    isteyip çekirdeği kirletmesine karşı bir kanarya.
    """
    offenders = [
        path.relative_to(_SRC)
        for path in _SRC.rglob("*.py")
        if "ui" not in path.relative_to(_SRC).parts
        and _top_level_imports(path) & _FORBIDDEN
    ]
    assert not offenders, f"tkinter, ui/ dışında içe aktarılmış: {offenders}"
