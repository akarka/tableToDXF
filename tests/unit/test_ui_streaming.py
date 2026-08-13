"""`ui.streaming` — Tk kurmadan, saf `queue.Queue` üzerinde test edilir (F-003)."""

from __future__ import annotations

import queue

from tabletodxf.report import Report, format_line
from tabletodxf.ui.streaming import QueueWriter, drain


def test_report_lines_land_on_the_queue_in_order() -> None:
    q: queue.Queue[str] = queue.Queue()
    report = Report(stream=QueueWriter(q))

    report.info("read_selection", "selection read", rows=5)
    report.warn("render_cell", "text overflow", cell="Mahal!C17")

    assert drain(q) == [
        format_line("INFO", "read_selection", "selection read", rows=5),
        format_line("WARN", "render_cell", "text overflow", cell="Mahal!C17"),
    ]


def test_print_trailing_newline_does_not_produce_an_empty_entry() -> None:
    """`print(line, file=stream)` `write(line)` ve `write("\\n")`'ü ayrı çağırır."""
    q: queue.Queue[str] = queue.Queue()
    writer = QueueWriter(q)

    print("bir satır", file=writer)

    assert drain(q) == ["bir satır"]


def test_drain_respects_max_lines() -> None:
    q: queue.Queue[str] = queue.Queue()
    for i in range(10):
        q.put(str(i))

    first = drain(q, max_lines=4)
    assert first == ["0", "1", "2", "3"]

    rest = drain(q, max_lines=100)
    assert rest == ["4", "5", "6", "7", "8", "9"]


def test_drain_on_empty_queue_returns_empty_list() -> None:
    assert drain(queue.Queue()) == []


def test_flush_is_a_harmless_noop() -> None:
    QueueWriter(queue.Queue()).flush()  # patlamamalı
