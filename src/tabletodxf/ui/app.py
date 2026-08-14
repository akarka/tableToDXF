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
from dataclasses import replace
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import get_type_hints

from .. import __version__
from ..api import Job, convert, resolve_font
from ..bookmarks import (
    JobBookmark,
    bookmarks_dir,
    delete_bookmark,
    list_bookmarks,
    load_bookmark,
    rename_bookmark,
    save_bookmark,
)
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
from .fields import TAB_ORDER, section_title
from .forms import SectionForm
from .streaming import QueueWriter, RunFailed, RunOk, RunOutcome, drain

_POLL_MS = 80

# DXF sembol tablosu adlarında (blok/katman/stil) sorun çıkaran karakterler.
_BLOCK_NAME_FORBIDDEN = frozenset('<>/\\":;?*|,=')


def strip_wrapping_quotes(text: str) -> str:
    """Windows Gezgini'nin "Yol olarak kopyala"sı yolu çift tırnak içine alır.

    Kullanıcı bunu olduğu gibi yapıştırırsa `Path(...).suffix` `.ods` değil
    `.ods"` döner ve uzantı denetimi haklı olarak reddeder — dosya sistemiyle
    hiçbir ilgisi yoktur, salt metin sorunudur. `"` Windows'ta dosya adında
    zaten yasak olduğu için, alanın başı ve sonunda eşleşen bir tırnak
    görmek her zaman bu yapıştırma kalıntısıdır; güvenle temizlenir.
    """
    stripped = text.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in ('"', "'"):
        return stripped[1:-1].strip()
    return stripped


def suggest_block_name(source: str, sheet: str) -> str:
    """`dosya_sayfa` biçiminde bir blok adı önerisi. Saf — Tk gerektirmez.

    Boşluk ve DXF sembol adlarında yasak karakterler alt çizgiye çevrilir,
    art arda gelen alt çizgiler tekilleştirilir. Kaynak ya da sayfa henüz
    bilinmiyorsa elde ne varsa o döner (ikisi de boşsa boş dize).
    """
    stem = Path(source).stem.strip() if source.strip() else ""
    sheet = sheet.strip()
    combined = f"{stem}_{sheet}" if stem and sheet else stem or sheet

    cleaned = "".join(
        "_" if ch.isspace() or ch in _BLOCK_NAME_FORBIDDEN else ch for ch in combined
    )
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_")


class MainWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title(f"tabletodxf {__version__}")
        root.geometry("880x720")
        root.minsize(720, 560)

        self._log_queue: queue.Queue[str] = queue.Queue()
        self._result_queue: queue.Queue[RunOutcome] = queue.Queue()
        self._current_out_path: Path | None = None
        self._loaded_source: str | None = None
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

        # Kayıtlı girdi kısayolu — Config profillerinden bağımsız (kullanıcı
        # kararı, 2026-08-14): .ods/sayfa/aralık/blok/çıktı adlandırılıp
        # kalıcı olarak saklanabilir, istenen ayar profiliyle serbestçe
        # birleştirilir. Bkz. bookmarks.py.
        bookmark_bar = ttk.Frame(outer)
        bookmark_bar.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        bookmark_bar.columnconfigure(1, weight=1)
        ttk.Label(bookmark_bar, text="Kayıtlı Girdi:").grid(row=0, column=0, sticky="w")
        self._bookmark_var = tk.StringVar(master=bookmark_bar)
        self._bookmark_combo = ttk.Combobox(
            bookmark_bar, textvariable=self._bookmark_var, state="readonly"
        )
        self._bookmark_combo.grid(row=0, column=1, sticky="ew", padx=(6, 6))
        self._bookmark_combo.bind("<<ComboboxSelected>>", self._on_bookmark_selected)
        ttk.Button(bookmark_bar, text="Kaydet", command=self._save_bookmark).grid(
            row=0, column=2, padx=2
        )
        ttk.Button(
            bookmark_bar, text="Farklı Kaydet…", command=self._save_bookmark_as
        ).grid(row=0, column=3, padx=2)
        ttk.Button(
            bookmark_bar, text="Yeniden Adlandır…", command=self._rename_bookmark
        ).grid(row=0, column=4, padx=2)
        ttk.Button(bookmark_bar, text="Sil…", command=self._delete_bookmark).grid(
            row=0, column=5, padx=2
        )
        self._refresh_bookmark_list()

        self._source_var = tk.StringVar(master=outer)
        self._sheet_var = tk.StringVar(master=outer)
        self._range_var = tk.StringVar(master=outer)
        self._block_var = tk.StringVar(master=outer)
        self._out_var = tk.StringVar(master=outer)
        # Blok adı kaynak+sayfa değiştikçe otomatik önerilir; kullanıcı alana
        # kendi eliyle yazınca öneri takibi durur (aşağıdaki trace).
        self._block_name_is_auto = True
        self._suppress_block_trace = False
        self._block_var.trace_add("write", self._on_block_var_written)

        ttk.Label(outer, text=".ods dosyası:").grid(row=1, column=0, sticky="w", pady=3)
        source_entry = ttk.Entry(outer, textvariable=self._source_var)
        source_entry.grid(row=1, column=1, sticky="ew", padx=(6, 6))
        # Yol Gözat dışında elle yazılıp/yapıştırılıp da girilebilir; sayfa
        # kutusunun dolması o zaman da tetiklenmeli. Her tuş vuruşunda değil
        # — alandan çıkılınca ya da Enter'a basılınca (mid-typing'te hata
        # kutusu patlamasın diye).
        source_entry.bind("<FocusOut>", self._on_source_entry_committed)
        source_entry.bind("<Return>", self._on_source_entry_committed)
        ttk.Button(outer, text="Gözat…", command=self._browse_source).grid(row=1, column=2)

        ttk.Label(outer, text="Sayfa:").grid(row=2, column=0, sticky="w", pady=3)
        self._sheet_combo = ttk.Combobox(outer, textvariable=self._sheet_var)
        self._sheet_combo.grid(row=2, column=1, sticky="ew", padx=(6, 6), columnspan=2)
        # Sayfa değişimi (listeden seçim, elle yazıp Tab/Enter) blok adı
        # önerisini tazeler.
        self._sheet_combo.bind("<<ComboboxSelected>>", self._on_sheet_changed)
        self._sheet_combo.bind("<FocusOut>", self._on_sheet_changed)
        self._sheet_combo.bind("<Return>", self._on_sheet_changed)

        ttk.Label(outer, text="Aralık:").grid(row=3, column=0, sticky="w", pady=3)
        ttk.Entry(outer, textvariable=self._range_var).grid(
            row=3, column=1, sticky="ew", padx=(6, 6)
        )
        ttk.Label(outer, text="ör. B3:C500", foreground="#888").grid(row=3, column=2, sticky="w")

        ttk.Label(outer, text="Blok adı:").grid(row=4, column=0, sticky="w", pady=3)
        ttk.Entry(outer, textvariable=self._block_var).grid(
            row=4, column=1, sticky="ew", padx=(6, 6), columnspan=2
        )

        ttk.Label(outer, text="Çıktı DXF:").grid(row=5, column=0, sticky="w", pady=3)
        ttk.Entry(outer, textvariable=self._out_var).grid(
            row=5, column=1, sticky="ew", padx=(6, 6)
        )
        ttk.Button(outer, text="Farklı Kaydet…", command=self._browse_output).grid(
            row=5, column=2
        )

    # ── Kayıtlı girdi kısayolları ────────────────────────────────────────
    # `Config` profillerinden bağımsız (kullanıcı kararı, 2026-08-14): bir
    # kısayol yalnızca .ods/sayfa/aralık/blok/çıktı hatırlar, ayar taşımaz.
    # Akış profil çubuğuyla bilinçli olarak birebir aynı (Kaydet / Farklı
    # Kaydet / Yeniden Adlandır / Sil) — kullanıcı zaten o örüntüyü biliyor.

    def _refresh_bookmark_list(self) -> None:
        self._bookmark_combo["values"] = list_bookmarks()

    def _on_bookmark_selected(self, _event: object = None) -> None:
        name = self._bookmark_var.get()
        if name:
            self._load_bookmark(name)

    def _load_bookmark(self, name: str) -> None:
        try:
            bookmark = load_bookmark(name)
        except TableToDxfError as exc:
            self._show_error("Kısayol yüklenemedi", exc)
            return

        self._bookmark_var.set(name)
        self._source_var.set(bookmark.source)
        self._loaded_source = None  # sayfa listesini zorla tazele
        if bookmark.source.strip():
            self._reload_sheets(bookmark.source)  # dosya artık yoksa hata gösterir, devam eder
            self._loaded_source = bookmark.source
        self._sheet_var.set(bookmark.sheet)  # kaydedilen sayfa, listede olmasa bile geçerli
        self._range_var.set(bookmark.range_text)

        self._suppress_block_trace = True
        try:
            self._block_var.set(bookmark.block)
        finally:
            self._suppress_block_trace = False
        # Kaydedilmiş bir ad kullanıcı niyetidir; kaynak/sayfa sonradan
        # değişse bile otomatik öneri bunun üzerine yazmamalı.
        self._block_name_is_auto = False

        self._out_var.set(bookmark.out)
        self._set_status(f"'{name}' girdisi yüklendi.")

    def _current_bookmark(self) -> JobBookmark:
        return JobBookmark(
            source=strip_wrapping_quotes(self._source_var.get()),
            sheet=self._sheet_var.get(),
            range_text=self._range_var.get(),
            block=self._block_var.get(),
            out=strip_wrapping_quotes(self._out_var.get()),
        )

    def _save_bookmark(self) -> None:
        name = self._bookmark_var.get()
        if not name:
            self._save_bookmark_as()
            return
        self._save_bookmark_to(name)

    def _save_bookmark_as(self) -> None:
        name = simpledialog.askstring(
            "Farklı Kaydet", "Yeni kısayol adı:", parent=self.root
        )
        if not name:
            return
        self._save_bookmark_to(name)

    def _save_bookmark_to(self, name: str) -> None:
        try:
            save_bookmark(name, self._current_bookmark())
        except TableToDxfError as exc:
            self._show_error("Kısayol kaydedilemedi", exc)
            return
        self._refresh_bookmark_list()
        self._bookmark_var.set(name)
        self._set_status(f"'{name}' girdisi kaydedildi.")

    def _rename_bookmark(self) -> None:
        old_name = self._bookmark_var.get()
        if not old_name:
            return
        new_name = simpledialog.askstring(
            "Yeniden Adlandır", "Yeni ad:", initialvalue=old_name, parent=self.root
        )
        if not new_name or new_name == old_name:
            return
        try:
            rename_bookmark(old_name, new_name)
        except TableToDxfError as exc:
            self._show_error("Yeniden adlandırılamadı", exc)
            return
        self._refresh_bookmark_list()
        self._bookmark_var.set(new_name)

    def _delete_bookmark(self) -> None:
        name = self._bookmark_var.get()
        if not name:
            return
        if not messagebox.askyesno(
            "Kısayolu sil", f"'{name}' girdi kısayolu silinsin mi? Bu işlem geri alınamaz."
        ):
            return
        delete_bookmark(name)
        self._bookmark_var.set("")
        self._refresh_bookmark_list()

    def _browse_source(self) -> None:
        path = filedialog.askopenfilename(
            title=".ods dosyası seç", filetypes=[(".ods dosyaları", "*.ods")]
        )
        if not path:
            return
        self._source_var.set(path)
        self._use_source_path(path)

    def _on_source_entry_committed(self, _event: object = None) -> None:
        """Alana elle yazılan/yapıştırılan yolu Gözat ile aynı yola sokar.

        Boş alan ve daha önce zaten yüklenmiş, değişmemiş bir yol için
        atlanır — her odak kaybında aynı dosyayı gereksiz yere yeniden
        açmamak, ve kullanıcının elle düzelttiği çıktı yolunu (aşağıda,
        yalnızca boşsa dolduruluyor) tekrar tekrar denemekten kaçınmak için.
        """
        path = strip_wrapping_quotes(self._source_var.get())
        if path != self._source_var.get():
            self._source_var.set(path)  # kullanıcı da düzeltilmiş hâli görsün
        if not path or path == self._loaded_source:
            return
        self._use_source_path(path)

    def _use_source_path(self, path: str) -> None:
        self._loaded_source = path
        self._reload_sheets(path)  # başarılıysa sayfa kutusunu ilk sayfayla doldurur
        if not self._out_var.get():
            self._out_var.set(str(Path(path).with_suffix(".dxf")))
        self._maybe_autofill_block_name()

    def _on_sheet_changed(self, _event: object = None) -> None:
        self._maybe_autofill_block_name()

    def _on_block_var_written(self, *_args: object) -> None:
        """Kullanıcı blok adını kendi eliyle değiştirince öneri takibi durur."""
        if not self._suppress_block_trace:
            self._block_name_is_auto = False

    def _maybe_autofill_block_name(self) -> None:
        """`dosya_sayfa` biçiminde bir blok adı önerir.

        Yalnızca kullanıcı alanı kendi eliyle değiştirmediği sürece
        (`_block_name_is_auto`) çalışır — kaynak ya da sayfa sonradan
        değişirse öneri tazelenir, ama kullanıcının yazdığı özel bir ad asla
        ezilmez.
        """
        if not self._block_name_is_auto:
            return
        suggestion = suggest_block_name(self._source_var.get(), self._sheet_var.get())
        if not suggestion:
            return
        self._suppress_block_trace = True
        try:
            self._block_var.set(suggestion)
        finally:
            self._suppress_block_trace = False
        self._block_name_is_auto = True  # trace bunu False yapmış olabilir

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
        # Yol alanları savunma amaçlı burada da temizlenir: kaynak alanı
        # FocusOut'ta zaten temizleniyor, ama çıktı alanının böyle bir olayı
        # yok (yalnızca Farklı Kaydet diyaloğu var) — biri oraya doğrudan
        # tırnaklı bir yol yapıştırırsa `Job` yine de doğru yolu almalı.
        source_text = strip_wrapping_quotes(self._source_var.get())
        out_text = strip_wrapping_quotes(self._out_var.get())

        missing = [
            label
            for label, value in (
                (".ods dosyası", source_text),
                ("Sayfa", self._sheet_var.get()),
                ("Aralık", self._range_var.get()),
                ("Blok adı", self._block_var.get()),
                ("Çıktı DXF", out_text),
            )
            if not value.strip()
        ]
        if missing:
            raise ValueError(f"Eksik alan(lar): {', '.join(missing)}")
        return Job(
            source=Path(source_text),
            sheet=self._sheet_var.get(),
            range_text=self._range_var.get(),
            out=Path(out_text),
            block=self._block_var.get(),
        )

    # ── Ayar sekmeleri ───────────────────────────────────────────────────

    def _build_settings_notebook(self) -> None:
        """Sekmeler `TAB_ORDER`'a göre kurulur — kullanıcının en sık dokunduğu

        bölüm önde (`fields.py`'de gerekçesi var). `Config`'in kendi alan
        sırasından **bilinçli olarak ayrı**: o sıra TOML/F-002 kataloğunu
        belirliyor, burada değişmesi onları etkilemez.
        """
        self._notebook = ttk.Notebook(self.root)
        self._notebook.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        self._section_forms: dict[str, SectionForm] = {}
        for section_key in TAB_ORDER:
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
