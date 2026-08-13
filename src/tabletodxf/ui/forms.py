"""Bir `Config` bölümünü (dataclass) otomatik forma çeviren üretici (F-003).

41 alanı elle widget'lamak yerine şemadan üretir: F-002'ye yeni bir ayar
eklendiğinde form otomatik büyür, ayrı bir "UI'ı da güncelle" adımı gerekmez.

Tip→widget eşlemesi ve metin↔değer dönüşümleri (`widget_kind_for`,
`coerce_from_text`, `format_for_display`) **saf fonksiyonlardır** — Tk
kurmadan test edilir. Yalnızca `SectionForm` gerçek widget oluşturur ve bir
Tk kökü ister; o kısım F-003'ün Manual Verification listesiyle doğrulanır.
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import fields, replace
from tkinter import colorchooser, ttk
from typing import Any, Literal, get_args, get_origin, get_type_hints

from .fields import field_meta

Rgb = tuple[int, int, int]

WidgetKind = Literal["bool", "combobox", "number", "text", "color", "point2", "strlist"]


def widget_kind_for(type_hint: Any) -> WidgetKind:  # noqa: ANN401
    """Bir alan tipinin hangi widget türüyle düzenleneceği. Saf, Tk'siz."""
    if type_hint is bool:
        return "bool"
    if get_origin(type_hint) is Literal:
        return "combobox"
    if type_hint in (float, int):
        return "number"
    if type_hint == Rgb:
        return "color"
    if type_hint == tuple[float, float]:
        return "point2"
    if type_hint == tuple[str, ...]:
        return "strlist"
    return "text"


def coerce_from_text(type_hint: Any, text: str) -> Any:  # noqa: ANN401
    """Metin kutusundaki ham metni alan tipine çevirir.

    Hatalı girdide `ValueError` atar — mesajı kullanıcıya doğrudan
    gösterilebilecek kadar açık tutulur (`SectionForm` bunu yakalayıp hangi
    alanda olduğunu ekler).
    """
    stripped = text.strip()
    if type_hint is float:
        try:
            return float(stripped)
        except ValueError as exc:
            raise ValueError(f"'{text}' bir sayı değil") from exc
    if type_hint is int:
        try:
            return int(stripped)
        except ValueError as exc:
            raise ValueError(f"'{text}' bir tam sayı değil") from exc
    if type_hint == Rgb:
        return parse_color_text(stripped)
    if type_hint == tuple[float, float]:
        parts = [p.strip() for p in stripped.strip("[]() ").split(",")]
        if len(parts) != 2:
            raise ValueError(f"'{text}' iki sayı olmalı, ör. 0.0, 0.0")
        try:
            return (float(parts[0]), float(parts[1]))
        except ValueError as exc:
            raise ValueError(f"'{text}' iki sayı olmalı, ör. 0.0, 0.0") from exc
    if type_hint == tuple[str, ...]:
        if not stripped:
            return ()
        return tuple(p.strip() for p in stripped.split(",") if p.strip())
    return text  # str ve Literal (Combobox zaten geçerli değeri verir)


def format_for_display(type_hint: Any, value: Any) -> str:  # noqa: ANN401
    """`coerce_from_text`'in tersi — bir değeri düzenlenebilir metne çevirir."""
    if type_hint == Rgb:
        return format_color(value)
    if type_hint == tuple[float, float]:
        return f"{value[0]}, {value[1]}"
    if type_hint == tuple[str, ...]:
        return ", ".join(value)
    if type_hint is float:
        return repr(float(value))
    return str(value)


def parse_color_text(text: str) -> Rgb:
    text = text.strip()
    if text.startswith("#") and len(text) == 7:
        try:
            return (int(text[1:3], 16), int(text[3:5], 16), int(text[5:7], 16))
        except ValueError as exc:
            raise ValueError(f"'{text}' geçerli bir #rrggbb rengi değil") from exc
    raise ValueError(f"'{text}' geçerli bir #rrggbb rengi değil")


def format_color(value: Rgb) -> str:
    return "#{:02x}{:02x}{:02x}".format(*value)


class SectionForm:
    """Tek bir `Config` bölümü için form — her alan bir satır.

    `parent` zaten bir `ttk.Notebook` sekmesi (ya da içindeki bir `Frame`)
    olmalı; bu sınıf yalnızca içine widget yerleştirir, pencere yönetmez.
    """

    def __init__(self, parent: tk.Widget, section_key: str, section_type: type) -> None:
        self.section_key = section_key
        self.section_type = section_type
        self._type_hints = get_type_hints(section_type)
        self._vars: dict[str, tk.Variable | tk.StringVar] = {}
        self._kinds: dict[str, WidgetKind] = {}

        self.frame = ttk.Frame(parent, padding=10)
        self.frame.columnconfigure(1, weight=1)

        for row, field in enumerate(fields(section_type)):
            self._build_row(row, field.name)

    def _build_row(self, row: int, name: str) -> None:
        type_hint = self._type_hints[name]
        kind = widget_kind_for(type_hint)
        self._kinds[name] = kind
        meta = field_meta(self.section_key, name)

        label = ttk.Label(self.frame, text=meta.label)
        label.grid(row=row, column=0, sticky="w", padx=(0, 8), pady=3)
        if meta.help:
            _Tooltip(label, meta.help)

        if kind == "bool":
            var = tk.BooleanVar(master=self.frame)
            widget = ttk.Checkbutton(self.frame, variable=var)
            widget.grid(row=row, column=1, sticky="w", pady=3)
        elif kind == "combobox":
            var = tk.StringVar(master=self.frame)
            options = list(get_args(type_hint))
            widget = ttk.Combobox(
                self.frame, textvariable=var, values=options, state="readonly"
            )
            widget.grid(row=row, column=1, sticky="ew", pady=3)
        elif kind == "color":
            var = tk.StringVar(master=self.frame)
            entry = ttk.Entry(self.frame, textvariable=var, width=10)
            entry.grid(row=row, column=1, sticky="w", pady=3)
            swatch = tk.Label(self.frame, width=3, relief="solid", borderwidth=1)
            swatch.grid(row=row, column=2, sticky="w", padx=(4, 4))

            def sync_swatch(*_: object, sw: tk.Label = swatch, v: tk.StringVar = var) -> None:
                try:
                    sw.configure(background=v.get())
                except tk.TclError:
                    pass

            var.trace_add("write", sync_swatch)

            def pick(*, v: tk.StringVar = var) -> None:
                _rgb, hex_color = colorchooser.askcolor(color=v.get() or "#ffffff")
                if hex_color:
                    v.set(hex_color)

            picker = ttk.Button(self.frame, text="Seç…", command=pick, width=6)
            picker.grid(row=row, column=3, sticky="w")
        else:  # number, text, point2, strlist — hepsi Entry
            var = tk.StringVar(master=self.frame)
            widget = ttk.Entry(self.frame, textvariable=var)
            widget.grid(row=row, column=1, columnspan=3, sticky="ew", pady=3)

        self._vars[name] = var

    def load(self, section_instance: Any) -> None:  # noqa: ANN401
        """Bölümün değerlerini widget'lara yazar."""
        for name, var in self._vars.items():
            type_hint = self._type_hints[name]
            value = getattr(section_instance, name)
            kind = self._kinds[name]
            if kind == "bool":
                var.set(bool(value))
            elif kind == "combobox":
                var.set(str(value))
            else:
                var.set(format_for_display(type_hint, value))

    def read(self, base: Any) -> Any:  # noqa: ANN401
        """Widget'lardaki değerleri okuyup `base`'in üzerine yazılmış yeni bir
        bölüm nesnesi döndürür.

        Hatalı bir alan varsa `ValueError` atar; mesaj hangi alanın adını
        taşır ki kullanıcı formda nereyi düzelteceğini bilsin.
        """
        changes: dict[str, Any] = {}
        for name, var in self._vars.items():
            type_hint = self._type_hints[name]
            kind = self._kinds[name]
            meta = field_meta(self.section_key, name)
            try:
                if kind == "bool":
                    changes[name] = bool(var.get())
                elif kind == "combobox":
                    changes[name] = var.get()
                else:
                    changes[name] = coerce_from_text(type_hint, var.get())
            except ValueError as exc:
                raise ValueError(f"{meta.label}: {exc}") from exc
        return replace(base, **changes)


class _Tooltip:
    """Bir etiketin üzerine gelince yardım metnini gösteren minimal balon.

    Ayrı bir bağımlılık eklemeden (`idlelib` gibi) küçük, kendi kendine
    yeten bir uygulama; F-003'ün genişletilebilir olma amacına uygun.
    """

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self._widget = widget
        self._text = text
        self._popup: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _event: object) -> None:
        if self._popup is not None:
            return
        x = self._widget.winfo_rootx() + 12
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 4
        self._popup = tk.Toplevel(self._widget)
        self._popup.wm_overrideredirect(True)
        self._popup.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self._popup,
            text=self._text,
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            padx=6,
            pady=3,
            wraplength=320,
            justify="left",
        )
        label.pack()

    def _hide(self, _event: object) -> None:
        if self._popup is not None:
            self._popup.destroy()
            self._popup = None
