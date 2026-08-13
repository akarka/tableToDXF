"""Kütüphane giriş noktası — CLI, UI ve suite için tek yol (ADR-003).

`argparse` ve `tkinter` içe aktarılmaz: suite bu modülü doğrudan çağırabilir.

    from tabletodxf import Config, Job, convert

    result = convert(Job(source=…, sheet=…, range_text=…, out=…, block=…), Config())
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

from . import dxf_writer, geometry, ods_reader
from .config import Config
from .errors import FONT_NOT_FOUND, TableToDxfError
from .metrics import FontMetrics
from .report import Report


@dataclass
class Job:
    """Çalıştırmaya özgü girdiler.

    `Config`'ten ayrı durur: bunlar her çalıştırmada değişir, `Config` ise bir
    kez ayarlanıp saklanır (ADR-003). UI'da bu bir form, `Config` bir tercihler
    penceresi.
    """

    source: Path
    sheet: str
    range_text: str
    out: Path
    block: str
    report_path: Path | None = None
    verbose: bool = False

    def resolved_report_path(self) -> Path:
        """Verilmemişse DXF'in yanında aynı adla."""
        if self.report_path is not None:
            return self.report_path
        return Path(self.out).with_suffix(".report.txt")


@dataclass
class Result:
    """Başarılı bir dönüştürmenin sonucu."""

    out_path: Path
    report_path: Path | None
    warnings: int
    entities: int
    rows: int
    cols: int
    report_lines: list[str] = field(default_factory=list)


def resolve_font(font: str) -> Path:
    """Verilen yol → paketle gelen `fonts/` → sistem font klasörleri.

    Kullanıcı çıplak bir dosya adı verebiliyor; ölçüm yapılamadan çıktı üretmek
    anlamsız olduğu için bulunamama ERROR'dur.
    """
    candidate = Path(font)
    if candidate.is_file():
        return candidate

    searched = [str(candidate)]
    for directory in font_search_dirs():
        probe = directory / candidate.name
        searched.append(str(probe))
        if probe.is_file():
            return probe

    raise TableToDxfError(
        FONT_NOT_FOUND,
        op="load_font",
        reason="font file not found — set text.font_file to a full path to a .ttf",
        font=font,
        searched=len(searched),
    )


def font_search_dirs() -> list[Path]:
    dirs = [Path(__file__).resolve().parent / "fonts", Path.cwd() / "fonts"]
    windir = Path(sys.prefix).anchor
    dirs.append(Path(windir) / "Windows" / "Fonts")
    dirs.append(Path.home() / "AppData" / "Local" / "Microsoft" / "Windows" / "Fonts")
    dirs.append(Path("/usr/share/fonts"))
    dirs.append(Path("/Library/Fonts"))
    return [d for d in dirs if d.is_dir()]


def convert(job: Job, config: Config | None = None, report: Report | None = None) -> Result:
    """`.ods` aralığı → DXF blok tanımı.

    Hata durumunda **hiçbir dosya yazmadan** `TableToDxfError` atar (F-001 AC-10).
    `report` verilmezse içeride bir tane oluşturulur; UI kendi `Report`'unu
    enjekte edip satırları arayüzde gösterebilir.
    """
    config = config or Config()
    config.validate()
    report = report if report is not None else Report(verbose=job.verbose)

    font_path = resolve_font(config.text.font_file)
    metrics = FontMetrics.from_file(
        font_path, fallback_cap_ratio=config.text.fallback_cap_ratio
    )
    report.debug("load_font", "font loaded", font=font_path.name, upem=metrics.units_per_em)

    model = ods_reader.read(
        job.source, job.sheet, job.range_text, report, config.source
    )
    report.info(
        "read_selection",
        "selection read",
        cell=model.source_ref,
        rows=model.n_rows,
        cols=model.n_cols,
    )

    drawing = geometry.build(
        model,
        metrics,
        report,
        layout=config.layout,
        overflow=config.overflow,
        background=config.background,
    )

    out_path = Path(job.out)
    dxf_writer.write(
        drawing,
        out_path,
        report,
        block_name=job.block,
        font_file=font_path.name,
        layers_config=config.layers,
        text_config=config.text,
        output_config=config.output,
    )

    report_path: Path | None = None
    if config.output.write_report:
        report_path = job.resolved_report_path()
        report.write(report_path)

    return Result(
        out_path=out_path,
        report_path=report_path,
        warnings=report.warn_count,
        entities=drawing.entity_count,
        rows=model.n_rows,
        cols=model.n_cols,
        report_lines=list(report.lines),
    )
