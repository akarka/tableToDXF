"""`Report` satırlarını arka plan iş parçacığından ana Tk döngüsüne taşır.

Tk widget'larına yalnızca ana iş parçacığından dokunulabilir; `convert()` ise
büyük bir tabloda birkaç saniye sürebileceği için ayrı bir `threading.Thread`'de
çalışır (F-003 AC-6). Köprü bir `queue.Queue`: worker satırları buraya yazar,
ana döngü `root.after(...)` ile düzenli aralıklarla boşaltır.

Bu modül **Tk içe aktarmaz** — yalnızca `queue.Queue` ile çalışır, bu yüzden
Tk penceresi kurmadan test edilebilir.
"""

from __future__ import annotations

import queue
from dataclasses import dataclass
from typing import Union

from ..api import Result
from ..errors import TableToDxfError


class QueueWriter:
    """`Report(stream=...)`'e verilen, satırları kuyruğa yazan dosya-benzeri nesne.

    `print(line, file=stream)` bir metin yazımı ile bir `"\\n"` yazımını **ayrı
    ayrı** çağırır; `\\n`'i süzmezsek her satır için kuyrukta fazladan boş bir
    girdi birikir.
    """

    def __init__(self, sink: queue.Queue[str]) -> None:
        self._sink = sink

    def write(self, text: str) -> int:
        stripped = text.rstrip("\n")
        if stripped:
            self._sink.put(stripped)
        return len(text)

    def flush(self) -> None:  # `print()` çağırır; no-op yeterli
        pass


@dataclass(frozen=True)
class RunOk:
    result: Result


@dataclass(frozen=True)
class RunFailed:
    error: TableToDxfError


RunOutcome = Union[RunOk, RunFailed]


def drain(line_queue: queue.Queue[str], max_lines: int = 200) -> list[str]:
    """Kuyrukta bekleyen satırları alır. Tek seferde en çok `max_lines`.

    Sınır, çok hızlı üretilen bir raporun tek `after` turunda arayüzü
    kilitlemesini önler; kalan satırlar bir sonraki turda gelir.
    """
    lines: list[str] = []
    for _ in range(max_lines):
        try:
            lines.append(line_queue.get_nowait())
        except queue.Empty:
            break
    return lines
