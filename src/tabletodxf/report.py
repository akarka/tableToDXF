"""`[TBL …]` satırları — konsol + `.report.txt`.

Satırlar toplanır, dosyaya **yalnızca çalıştırma başarıyla bittiğinde** yazılır.
AC-10 hiçbir dosya bırakmadan durmayı şart koşuyor; rapor dosyası da bir dosya.
Konsola basma anlık olur, böylece uzun çalıştırmada kullanıcı ilerlemeyi görür.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import IO, Literal

Level = Literal["INFO", "WARN", "ERROR", "DEBUG"]

# `[TBL WARN]` ile `[TBL INFO]` aynı sütunda başlasın diye sabit genişlik.
_TAG_WIDTH = len("[TBL ERROR]")


def format_line(
    level: Level,
    op: str,
    reason: str,
    cell: str | None = None,
    **fields: object,
) -> str:
    """`[TBL WARN]  op=render_cell cell=Mahal!C17 reason="text overflow" avail_mm=21.0`

    Değerler tırnak içinde tutulmaz — yalnızca `reason` ve boşluk içerebilecek
    alanlar tırnaklanır; böylece `grep 'op=render_cell'` çalışır.
    """
    parts = [f"[TBL {level}]".ljust(_TAG_WIDTH), f"op={op}"]
    if cell is not None:
        parts.append(f"cell={cell}")
    parts.append(f'reason="{reason}"')
    for key, value in fields.items():
        parts.append(f"{key}={_render_value(value)}")
    return " ".join(parts)


def _render_value(value: object) -> str:
    if isinstance(value, float):
        text = f"{value:.1f}"
    else:
        text = str(value)
    # Boşluk içeren her şey tırnaklanır ki alan ayrıştırması bozulmasın.
    if any(ch.isspace() for ch in text) or text == "":
        return f'"{text}"'
    return text


class Report:
    def __init__(self, *, verbose: bool = False, stream: IO[str] | None = None) -> None:
        self.verbose = verbose
        self._stream = stream if stream is not None else sys.stdout
        self.lines: list[str] = []
        self.warn_count = 0
        self.error_count = 0

    def log(
        self,
        level: Level,
        op: str,
        reason: str,
        cell: str | None = None,
        **fields: object,
    ) -> None:
        if level == "DEBUG" and not self.verbose:
            return
        if level == "WARN":
            self.warn_count += 1
        elif level == "ERROR":
            self.error_count += 1
        line = format_line(level, op, reason, cell, **fields)
        self.lines.append(line)
        print(line, file=self._stream)

    def info(self, op: str, reason: str, cell: str | None = None, **fields: object) -> None:
        self.log("INFO", op, reason, cell, **fields)

    def warn(self, op: str, reason: str, cell: str | None = None, **fields: object) -> None:
        self.log("WARN", op, reason, cell, **fields)

    def error(self, op: str, reason: str, cell: str | None = None, **fields: object) -> None:
        self.log("ERROR", op, reason, cell, **fields)

    def debug(self, op: str, reason: str, cell: str | None = None, **fields: object) -> None:
        self.log("DEBUG", op, reason, cell, **fields)

    def write(self, path: Path) -> None:
        """Raporu diske yaz. Yalnızca başarılı çalıştırma sonunda çağrılır."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")
