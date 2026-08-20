"""`ui.app`'daki saf yardımcılar — Tk kurmadan test edilir (F-003).

`app.py` modül seviyesinde `tkinter` içe aktarır ama yalnızca içe aktarmak
bir Tk kökü gerektirmez; `MainWindow`'un asıl widget kurulumu burada değil,
gerçek Tk ile yapılan manuel doğrulamada kapsanır (F-003 → Test Plan).
"""

from __future__ import annotations

import queue
from pathlib import Path

import pytest

from tabletodxf.api import Job
from tabletodxf.config import Config
from tabletodxf.errors import SRC_NOT_FOUND, UNEXPECTED, TableToDxfError
from tabletodxf.ui.app import (
    MainWindow,
    _as_catalog_error,
    strip_wrapping_quotes,
    suggest_block_name,
)
from tabletodxf.ui.streaming import RunFailed, RunOutcome, drain


# ── strip_wrapping_quotes ────────────────────────────────────────────────


def test_strips_windows_copy_as_path_quoting() -> None:
    """Gezgin'in "Yol olarak kopyala"sı tam olarak bunu üretir."""
    assert strip_wrapping_quotes('"C:\\yol\\mahal.ods"') == "C:\\yol\\mahal.ods"


def test_strips_single_quotes_too() -> None:
    assert strip_wrapping_quotes("'C:\\yol\\mahal.ods'") == "C:\\yol\\mahal.ods"


def test_unquoted_path_is_untouched() -> None:
    assert strip_wrapping_quotes("C:\\yol\\mahal.ods") == "C:\\yol\\mahal.ods"


def test_surrounding_whitespace_is_trimmed() -> None:
    assert strip_wrapping_quotes('  "C:\\yol\\mahal.ods"  ') == "C:\\yol\\mahal.ods"


def test_mismatched_quotes_are_left_alone() -> None:
    """Yalnızca başta ve sonda **eşleşen** tırnak temizlenir."""
    assert strip_wrapping_quotes("\"C:\\yol\\mahal.ods'") == "\"C:\\yol\\mahal.ods'"


def test_a_single_quote_character_alone_is_not_stripped() -> None:
    assert strip_wrapping_quotes('"') == '"'


def test_empty_and_whitespace_only_text() -> None:
    assert strip_wrapping_quotes("") == ""
    assert strip_wrapping_quotes("   ") == ""


def test_quoted_path_now_has_the_ods_suffix_recognized() -> None:
    """Bu, gerçekte görülen hatanın kökeniydi: tırnaklı yolun `.suffix`'i
    `.ods` değil `.ods"` dönüyordu."""
    from pathlib import Path

    quoted = '"C:\\yol\\mahal.ods"'
    assert Path(quoted).suffix.lower() != ".ods"  # temizlenmeden hata verir
    assert Path(strip_wrapping_quotes(quoted)).suffix.lower() == ".ods"


def test_combines_filename_stem_and_sheet() -> None:
    assert suggest_block_name(r"C:\yol\mahal.ods", "Mahal") == "mahal_Mahal"


def test_spaces_become_underscores() -> None:
    assert (
        suggest_block_name(r"C:\yol\c.ods", "Numarataj_1692 Marina P")
        == "c_Numarataj_1692_Marina_P"
    )


def test_forbidden_symbol_characters_become_underscores() -> None:
    assert suggest_block_name("c.ods", 'Kat 1: "Zemin"') == "c_Kat_1_Zemin"


def test_consecutive_underscores_are_collapsed() -> None:
    assert suggest_block_name("c.ods", "  Mahal  ") == "c_Mahal"


def test_missing_sheet_falls_back_to_filename_only() -> None:
    assert suggest_block_name(r"C:\yol\mahal.ods", "") == "mahal"


def test_missing_source_falls_back_to_sheet_only() -> None:
    assert suggest_block_name("", "Mahal") == "Mahal"


def test_both_missing_is_empty_string() -> None:
    assert suggest_block_name("", "") == ""
    assert suggest_block_name("   ", "   ") == ""


def test_turkish_characters_survive() -> None:
    assert suggest_block_name("İç Mekan.ods", "Ölçü") == "İç_Mekan_Ölçü"


@pytest.mark.parametrize(
    "sheet",
    ["Kat/1", "Kat<1>", "Kat|1", "Kat*1", "Kat?1", "Kat;1", "Kat=1", "Kat,1"],
)
def test_every_forbidden_character_is_scrubbed(sheet: str) -> None:
    result = suggest_block_name("c.ods", sheet)
    assert not set(result) & {"<", ">", "/", "\\", '"', ";", "?", "*", "|", ",", "="}


# ── Arka plan iş parçacığı: hiçbir çalıştırma yarıda kalmamalı ───────────────


def _job() -> Job:
    return Job(
        source=Path("mahal.ods"),
        sheet="Mahal",
        range_text="B2:E7",
        out=Path("mahal.dxf"),
        block="TBL",
    )


def _worker_outcome(monkeypatch, raiser) -> RunOutcome:  # noqa: ANN001
    """`_run_worker`'ı Tk kurmadan çalıştırır.

    Metot yalnızca iki kuyruğa dokunuyor (AC-6 gereği hiçbir widget'a
    dokunmuyor), bu yüzden sahte bir `self` yeterli.
    """

    class _Stub:
        def __init__(self) -> None:
            self._log_queue: queue.Queue[str] = queue.Queue()
            self._result_queue: queue.Queue[RunOutcome] = queue.Queue()

    stub = _Stub()
    monkeypatch.setattr("tabletodxf.ui.app.convert", raiser)
    MainWindow._run_worker(stub, _job(), Config())
    return stub._result_queue.get_nowait()


def test_unexpected_exception_still_finishes_the_run(monkeypatch) -> None:  # noqa: ANN001
    """Regresyon: kataloğa girmeyen istisna iş parçacığıyla sessizce ölüyordu.

    `_result_queue`'ya hiçbir şey konmadığı için `_finish_run` hiç çağrılmıyor,
    pencere "Çalışıyor…" durumunda — Çalıştır düğmesi devre dışı, ilerleme
    çubuğu dönerken — sonsuza kadar asılı kalıyordu.
    """

    def boom(*_args: object, **_kwargs: object) -> None:
        raise PermissionError("cikti.dxf AutoCAD'de açık")

    outcome = _worker_outcome(monkeypatch, boom)
    assert isinstance(outcome, RunFailed)
    assert outcome.error.code == UNEXPECTED
    assert outcome.error.fields["detail"] == "PermissionError"


def test_catalog_errors_still_take_the_normal_path(monkeypatch) -> None:  # noqa: ANN001
    """Yakalama dalı eklenirken bilinen hataların yolu değişmemeli."""

    def stop(*_args: object, **_kwargs: object) -> None:
        raise TableToDxfError(
            SRC_NOT_FOUND, op="read_source", reason="file not found", file="mahal.ods"
        )

    outcome = _worker_outcome(monkeypatch, stop)
    assert isinstance(outcome, RunFailed)
    assert outcome.error.code == SRC_NOT_FOUND


def test_unexpected_exception_leaves_a_traceback_in_the_log(monkeypatch) -> None:  # noqa: ANN001
    """Beklenmedik istisna bir kusurdur; teşhis edilebilir kalmalı."""

    class _Stub:
        def __init__(self) -> None:
            self._log_queue: queue.Queue[str] = queue.Queue()
            self._result_queue: queue.Queue[RunOutcome] = queue.Queue()

    def boom(*_args: object, **_kwargs: object) -> None:
        raise ZeroDivisionError("bolme hatasi")

    stub = _Stub()
    monkeypatch.setattr("tabletodxf.ui.app.convert", boom)
    MainWindow._run_worker(stub, _job(), Config())

    logged = "\n".join(drain(stub._log_queue))
    assert "Traceback" in logged
    assert "ZeroDivisionError" in logged


# ── _as_catalog_error ────────────────────────────────────────────────────


def test_exception_message_is_carried_into_the_report_line() -> None:
    error = _as_catalog_error(PermissionError("dosya kullanımda"))
    assert error.code == UNEXPECTED
    assert "dosya kullanımda" in error.reason


def test_exception_without_a_message_falls_back_to_its_type_name() -> None:
    assert _as_catalog_error(RuntimeError()).reason == "RuntimeError"
