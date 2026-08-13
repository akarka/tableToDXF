"""Ana pencere (F-003).

`convert()` dışında hiçbir dönüştürme mantığı burada yoktur (AC-1) — bu
modülün tek işi form/queue/thread yönetimi. Çekirdek çağrıları tek bir yerden,
`_run_worker`'dan yapılır.
"""

from __future__ import annotations

import os
import queue
import sys
import threading
import tkinter as tk
from dataclasses import fields, replace
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import get_type_hints

from .. import __version__
from ..api import Job, convert, resolve_font
from ..config import (
    DEFAULT_PROFILE_NAME,
    Config,
    delete_profile,
    ensure_default_profile,
    list_profiles,
    load_profile,
    profiles_dir,
    rename_profile,
    save_profile,
)
from ..errors import TableToDxfError, UsageError
from ..ods_reader import list_sheets
from ..report import Report, format_line
from .fields import section_title
from .forms import SectionForm
from .streaming import QueueWriter, RunFailed, RunOk, RunOutcome, drain

_POLL_MS = 80


class MainWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title(f"tabletodxf {__version__}")
        root.geometry("880x720")
        root.minsize(720, 560)

        self._log_queue: queue.Queue[str] = queue.Queue()
        self._result_queue: queue.Queue[RunOutcome] = queue.Queue()
        self._current_out_path: Path | None = None
        self._section_hints = get_type_hints(Config)
        self._current_config = Config()

        self._build_menu()
        self._build_profile_bar()
        self._build_job_frame()
        self._build_settings_notebook()
        self._build_run_bar()
        self._build_report_pane()
        self._build_status_bar()

        ensure_default_profile()
        self._refresh_profile_list()
        self._load_profile(DEFAULT_PROFILE_NAME)

        self.root.after(_POLL_MS, self._poll_queues)

    # ── Menü ─────────────────────────────────────────────────────────────

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Çıktı Klasörünü Aç", command=self._open_output_folder)
        file_menu.add_command(label="Profil Klasörünü Aç", command=self._open_profiles_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Çıkış", command=self.root.quit)
        menubar.add_cascade(label="Dosya", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="Hakkında", command=self._show_about)
        menubar.add_cascade(label="Yardım", menu=help_menu)
        self.root.config(menu=menubar)

    def _open_output_folder(self) -> None:
        target = self._current_out_path.parent if self._current_out_path else None
        if target is None or not target.is_dir():
            messagebox.showinfo("Çıktı klasörü", "Henüz bir çıktı üretilmedi.")
            return
        _open_in_explorer(target)

    def _open_profiles_folder(self) -> None:
        directory = profiles_dir()
        directory.mkdir(parents=True, exist_ok=True)
        _open_in_explorer(directory)

    def _show_about(self) -> None:
        messagebox.showinfo(
            "Hakkında",
            f"tabletodxf {__version__}\n\n"
            "LibreOffice Calc'ta biçimlendirilmiş bir .ods aralığını,\n"
            "kendi kendine yeten bir AutoCAD blok tanımına çevirir.\n\n"
            "DOCS/Features/F-001.md, F-002.md, F-003.md",
        )

    # ── Profil çubuğu ────────────────────────────────────────────────────

    def _build_profile_bar(self) -> None:
        bar = ttk.Frame(self.root, padding=(10, 8))
        bar.pack(fill="x")

        ttk.Label(bar, text="Profil:").pack(side="left")
        self._profile_var = tk.StringVar(master=bar)
        self._profile_combo = ttk.Combobox(
            bar, textvariable=self._profile_var, state="readonly", width=30
        )
        self._profile_combo.pack(side="left", padx=(6, 12))
        self._profile_combo.bind("<<ComboboxSelected>>", self._on_profile_selected)

        ttk.Button(bar, text="Kaydet", command=self._save_profile).pack(side="left", padx=2)
        ttk.Button(
            bar, text="Farklı Kaydet…", command=self._save_profile_as
        ).pack(side="left", padx=2)
        ttk.Button(
            bar, text="Yeniden Adlandır…", command=self._rename_profile
        ).pack(side="left", padx=2)
        ttk.Button(bar, text="Sil…", command=self._delete_profile).pack(side="left", padx=2)

    def _refresh_profile_list(self) -> None:
        names = list_profiles()
        self._profile_combo["values"] = names
        if self._profile_var.get() not in names and names:
            self._profile_var.set(names[0])

    def _on_profile_selected(self, _event: object = None) -> None:
        name = self._profile_var.get()
        if name:
            self._load_profile(name)

    def _load_profile(self, name: str) -> None:
        try:
            config = load_profile(name)
        except TableToDxfError as exc:
            self._show_error("Profil yüklenemedi", exc)
            return
        self._current_config = config
        self._profile_var.set(name)
        for section_key, form in self._section_forms.items():
            form.load(getattr(config, section_key))

    def _collect_config(self) -> Config:
        """Tüm sekmelerdeki değerleri toplayıp yeni bir `Config` kurar.

        Bir alan geçersizse hangi sekme/etiket olduğunu taşıyan bir
        `ValueError` fırlatır — çağıran bunu yakalayıp kullanıcıya gösterir.
        """
        sections: dict[str, object] = {}
        for section_key, form in self._section_forms.items():
            base = getattr(self._current_config, section_key)
            try:
                sections[section_key] = form.read(base)
            except ValueError as exc:
                raise ValueError(f"[{section_title(section_key)}] {exc}") from exc
        config = replace(self._current_config, **sections)
        config.validate()
        return config

    def _save_profile(self) -> None:
        name = self._profile_var.get() or DEFAULT_PROFILE_NAME
        self._save_as(name)

    def _save_profile_as(self) -> None:
        name = simpledialog.askstring(
            "Farklı Kaydet", "Yeni profil adı:", parent=self.root
        )
        if not name:
            return
        self._save_as(name)

    def _save_as(self, name: str) -> None:
        try:
            config = self._collect_config()
            save_profile(name, config)
        except (ValueError, TableToDxfError) as exc:
            self._show_error("Profil kaydedilemedi", exc)
            return
        self._current_config = config
        self._refresh_profile_list()
        self._profile_var.set(name)
        self._set_status(f"'{name}' kaydedildi.")

    def _rename_profile(self) -> None:
        old_name = self._profile_var.get()
        if not old_name:
            return
        new_name = simpledialog.askstring(
            "Yeniden Adlandır", "Yeni ad:", initialvalue=old_name, parent=self.root
        )
        if not new_name or new_name == old_name:
            return
        try:
            rename_profile(old_name, new_name)
        except TableToDxfError as exc:
            self._show_error("Yeniden adlandırılamadı", exc)
            return
        self._refresh_profile_list()
        self._profile_var.set(new_name)

    def _delete_profile(self) -> None:
        name = self._profile_var.get()
        if not name:
            return
        if not messagebox.askyesno(
            "Profili sil", f"'{name}' profili silinsin mi? Bu işlem geri alınamaz."
        ):
            return
        delete_profile(name)
        self._refresh_profile_list()
        remaining = list_profiles()
        if remaining:
            self._load_profile(remaining[0])
        else:
            ensure_default_profile()
            self._refresh_profile_list()
            self._load_profile(DEFAULT_PROFILE_NAME)

    # ── Girdi (Job) ──────────────────────────────────────────────────────

    def _build_job_frame(self) -> None:
        outer = ttk.LabelFrame(self.root, text="Girdi", padding=10)
        outer.pack(fill="x", padx=10, pady=(0, 8))
        outer.columnconfigure(1, weight=1)

        self._source_var = tk.StringVar(master=outer)
        self._sheet_var = tk.StringVar(master=outer)
        self._range_var = tk.StringVar(master=outer)
        self._block_var = tk.StringVar(master=outer)
        self._out_var = tk.StringVar(master=outer)

        ttk.Label(outer, text=".ods dosyası:").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Entry(outer, textvariable=self._source_var).grid(
            row=0, column=1, sticky="ew", padx=(6, 6)
        )
        ttk.Button(outer, text="Gözat…", command=self._browse_source).grid(row=0, column=2)

        ttk.Label(outer, text="Sayfa:").grid(row=1, column=0, sticky="w", pady=3)
        self._sheet_combo = ttk.Combobox(outer, textvariable=self._sheet_var)
        self._sheet_combo.grid(row=1, column=1, sticky="ew", padx=(6, 6), columnspan=2)

        ttk.Label(outer, text="Aralık:").grid(row=2, column=0, sticky="w", pady=3)
        ttk.Entry(outer, textvariable=self._range_var).grid(
            row=2, column=1, sticky="ew", padx=(6, 6)
        )
        ttk.Label(outer, text="ör. B3:C500", foreground="#888").grid(row=2, column=2, sticky="w")

        ttk.Label(outer, text="Blok adı:").grid(row=3, column=0, sticky="w", pady=3)
        ttk.Entry(outer, textvariable=self._block_var).grid(
            row=3, column=1, sticky="ew", padx=(6, 6), columnspan=2
        )

        ttk.Label(outer, text="Çıktı DXF:").grid(row=4, column=0, sticky="w", pady=3)
        ttk.Entry(outer, textvariable=self._out_var).grid(
            row=4, column=1, sticky="ew", padx=(6, 6)
        )
        ttk.Button(outer, text="Farklı Kaydet…", command=self._browse_output).grid(
            row=4, column=2
        )

    def _browse_source(self) -> None:
        path = filedialog.askopenfilename(
            title=".ods dosyası seç", filetypes=[(".ods dosyaları", "*.ods")]
        )
        if not path:
            return
        self._source_var.set(path)
        self._reload_sheets(path)
        if not self._out_var.get():
            self._out_var.set(str(Path(path).with_suffix(".dxf")))

    def _reload_sheets(self, path: str) -> None:
        try:
            sheets = list_sheets(path)
        except TableToDxfError as exc:
            self._show_error("Sayfa listesi alınamadı", exc)
            return
        self._sheet_combo["values"] = sheets
        if sheets:
            self._sheet_var.set(sheets[0])

    def _browse_output(self) -> None:
        initial = self._out_var.get() or "cikti.dxf"
        path = filedialog.asksaveasfilename(
            title="Çıktı DXF",
            defaultextension=".dxf",
            filetypes=[("DXF dosyaları", "*.dxf")],
            initialfile=Path(initial).name,
            initialdir=str(Path(initial).parent) if Path(initial).parent.is_dir() else None,
        )
        if path:
            self._out_var.set(path)

    def _collect_job(self) -> Job:
        missing = [
            label
            for label, var in (
                (".ods dosyası", self._source_var),
                ("Sayfa", self._sheet_var),
                ("Aralık", self._range_var),
                ("Blok adı", self._block_var),
                ("Çıktı DXF", self._out_var),
            )
            if not var.get().strip()
        ]
        if missing:
            raise ValueError(f"Eksik alan(lar): {', '.join(missing)}")
        return Job(
            source=Path(self._source_var.get()),
            sheet=self._sheet_var.get(),
            range_text=self._range_var.get(),
            out=Path(self._out_var.get()),
            block=self._block_var.get(),
        )

    # ── Ayar sekmeleri ───────────────────────────────────────────────────

    def _build_settings_notebook(self) -> None:
        self._notebook = ttk.Notebook(self.root)
        self._notebook.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        self._section_forms: dict[str, SectionForm] = {}
        for section_field in fields(Config):
            section_key = section_field.name
            section_type = self._section_hints[section_key]
            form = SectionForm(self._notebook, section_key, section_type)
            self._notebook.add(form.frame, text=section_title(section_key))
            self._section_forms[section_key] = form

    def _select_tab(self, section_key: str) -> None:
        form = self._section_forms.get(section_key)
        if form is not None:
            self._notebook.select(form.frame)

    # ── Çalıştırma ───────────────────────────────────────────────────────

    def _build_run_bar(self) -> None:
        bar = ttk.Frame(self.root, padding=(10, 4))
        bar.pack(fill="x")
        self._run_button = ttk.Button(bar, text="▶ Çalıştır", command=self._on_run_clicked)
        self._run_button.pack(side="left")
        self._progress = ttk.Progressbar(bar, mode="indeterminate", length=140)
        # Yalnızca çalışırken paketlenir (pack); boşta yer kaplamasın.

    def _on_run_clicked(self) -> None:
        try:
            job = self._collect_job()
            config = self._collect_config()
        except (ValueError, TableToDxfError) as exc:
            self._show_error("Çalıştırılamadı", exc)
            return

        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.configure(state="disabled")

        self._run_button.configure(state="disabled")
        self._progress.pack(side="left", padx=10)
        self._progress.start(12)
        self._set_status("Çalışıyor…")

        thread = threading.Thread(
            target=self._run_worker, args=(job, config), daemon=True
        )
        thread.start()

    def _run_worker(self, job: Job, config: Config) -> None:
        """Arka plan iş parçacığı — hiçbir widget'a doğrudan dokunmaz (AC-6).

        Sonuç `_result_queue`'ya konur; ana döngü `_poll_queues` ile alır.
        """
        report = Report(verbose=False, stream=QueueWriter(self._log_queue))
        try:
            result = convert(job, config, report)
        except (TableToDxfError, UsageError) as exc:
            self._result_queue.put(RunFailed(exc))
        else:
            self._result_queue.put(RunOk(result))

    def _poll_queues(self) -> None:
        for line in drain(self._log_queue):
            self._append_log(line)

        try:
            outcome = self._result_queue.get_nowait()
        except queue.Empty:
            pass
        else:
            self._finish_run(outcome)

        self.root.after(_POLL_MS, self._poll_queues)

    def _finish_run(self, outcome: RunOutcome) -> None:
        self._run_button.configure(state="normal")
        self._progress.stop()
        self._progress.pack_forget()

        if isinstance(outcome, RunOk):
            self._current_out_path = outcome.result.out_path
            warnings = outcome.result.warnings
            suffix = f" — {warnings} uyarı" if warnings else ""
            self._set_status(f"Tamamlandı: {outcome.result.out_path.name}{suffix}")
        else:
            self._current_out_path = None
            self._append_log(
                format_line(
                    "ERROR",
                    outcome.error.op,
                    outcome.error.reason,
                    outcome.error.cell,
                    code=outcome.error.code,
                    **outcome.error.fields,
                )
            )
            self._set_status("Durdu — hiçbir dosya üretilmedi.")

    # ── Rapor bölmesi ────────────────────────────────────────────────────

    def _build_report_pane(self) -> None:
        outer = ttk.Frame(self.root, padding=(10, 0, 10, 8))
        outer.pack(fill="both", expand=False)

        self._log_text = tk.Text(outer, height=10, state="disabled", wrap="none")
        y_scroll = ttk.Scrollbar(outer, orient="vertical", command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=y_scroll.set)
        self._log_text.pack(side="left", fill="both", expand=True)
        y_scroll.pack(side="right", fill="y")

    def _append_log(self, line: str) -> None:
        self._log_text.configure(state="normal")
        self._log_text.insert("end", line + "\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    # ── Durum çubuğu ─────────────────────────────────────────────────────

    def _build_status_bar(self) -> None:
        self._status_var = tk.StringVar(master=self.root, value="Hazır.")
        bar = ttk.Label(
            self.root, textvariable=self._status_var, relief="sunken", anchor="w", padding=(6, 3)
        )
        bar.pack(fill="x", side="bottom")

    def _set_status(self, text: str) -> None:
        self._status_var.set(text)

    def _show_error(self, title: str, error: Exception) -> None:
        if isinstance(error, TableToDxfError):
            message = f"{error.reason}\n\nkod: {error.code}"
        else:
            message = str(error)
        messagebox.showerror(title, message)


def _open_in_explorer(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(path)  # noqa: S606 — kullanıcının kendi dosya sistemi
    else:
        import subprocess

        subprocess.run(["xdg-open", str(path)], check=False)  # noqa: S603, S607


def run() -> int:
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()
    return 0
