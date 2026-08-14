"""Adlandırılmış girdi kısayolları (kullanıcı kararı, 2026-08-14).

Bir "girdi" — kaynak `.ods`, sayfa, aralık, blok adı, çıktı yolu — `Config`
profillerinden **tamamen bağımsız** olarak adlandırılıp saklanabilir. İstenen
kısayol istenen ayar profiliyle birleştirilip kullanılabilir; ikisi birbirini
hiç bilmez. Bu, ADR-003'ün `Job`/`Config` ayrımının doğal bir uzantısı: bir
kısayol sonuçta kaydedilmiş bir `Job`'dır, kalıcı bir tercih (`Config`) değil.

Depolama profillerle aynı kökte, ayrı bir alt klasörde:
`%LOCALAPPDATA%\\OncuCAD\\TableToDXF\\inputs\\<ad>.toml`. Şema tek bir düz
kayıt olduğu için (bölümlere ayrılmaz), `config.py`'nin genel TOML
makinesinden bağımsız, kendi kendine yeten küçük bir yazıcıyla saklanır.

Bu modül **saf veridir** — `odfpy`/`ezdxf`/`tkinter` içe aktarmaz — ki CLI de
(`--profile` gibi bir `--input` bayrağıyla, ileride) UI hiç kurulu olmadan
kullanabilsin.
"""

from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

from .api import Job
from .config import app_data_dir
from .errors import CONFIG_INVALID, UsageError

_FORBIDDEN_NAME_CHARS = frozenset('\\/:*?"<>|')

_FIELDS = ("source", "sheet", "range_text", "block", "out")


@dataclass(frozen=True)
class JobBookmark:
    """`Job`'ın kalıcı, adlandırılmış bir anlık görüntüsü.

    `Job`'ın çalıştırmaya özgü alanlarını (`report_path`, `verbose`) taşımaz
    — bunlar bir kısayolun "girdisi" değil, her koşuda ayrıca belirlenir.
    """

    source: str
    sheet: str
    range_text: str
    block: str
    out: str

    @classmethod
    def from_job(cls, job: Job) -> JobBookmark:
        return cls(
            source=str(job.source),
            sheet=job.sheet,
            range_text=job.range_text,
            block=job.block,
            out=str(job.out),
        )

    def to_job(self) -> Job:
        return Job(
            source=Path(self.source),
            sheet=self.sheet,
            range_text=self.range_text,
            block=self.block,
            out=Path(self.out),
        )


def _invalid(key: str, value: object, reason: str) -> UsageError:
    return UsageError(CONFIG_INVALID, op="load_bookmark", reason=reason, setting=key, value=value)


def bookmarks_dir() -> Path:
    return app_data_dir() / "inputs"


def _sanitize_bookmark_name(name: str) -> str:
    """Profil adlandırmasıyla aynı kural (`config._sanitize_profile_name`):

    görünen ad = dosya adı, ayrı bir eşleme yok.
    """
    trimmed = name.strip()
    if not trimmed:
        raise _invalid("bookmark", name, "kısayol adı boş olamaz")
    bad = _FORBIDDEN_NAME_CHARS & set(trimmed)
    if bad:
        raise _invalid(
            "bookmark", name, 'kısayol adı şu karakterleri içeremez: \\ / : * ? " < > |'
        )
    return trimmed


def _bookmark_path(name: str) -> Path:
    return bookmarks_dir() / f"{_sanitize_bookmark_name(name)}.toml"


def list_bookmarks() -> list[str]:
    """Var olan kısayol adları, alfabetik değil kod noktasına göre sıralı

    (profillerle aynı gerekçe: `locale` bağımlılığı makineler arası
    tutarsız sıralamaya yol açardı).
    """
    directory = bookmarks_dir()
    if not directory.is_dir():
        return []
    return sorted(path.stem for path in directory.glob("*.toml"))


def load_bookmark(name: str) -> JobBookmark:
    path = _bookmark_path(name)
    if not path.is_file():
        raise _invalid(name, "", "kısayol bulunamadı")
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise UsageError(
            CONFIG_INVALID,
            op="load_bookmark",
            reason="kısayol dosyası geçerli TOML değil",
            bookmark=name,
            detail=str(exc).split("\n")[0],
        ) from exc

    missing = [field for field in _FIELDS if field not in data]
    if missing:
        raise _invalid(name, "", f"eksik alan(lar): {', '.join(missing)}")
    extra = set(data) - set(_FIELDS)
    if extra:
        raise _invalid(name, "", f"tanınmayan alan(lar): {', '.join(sorted(extra))}")
    non_str = [field for field in _FIELDS if not isinstance(data[field], str)]
    if non_str:
        raise _invalid(name, "", f"metin olmalı: {', '.join(non_str)}")

    return JobBookmark(**{field: data[field] for field in _FIELDS})


def save_bookmark(name: str, bookmark: JobBookmark) -> Path:
    """Kaydeder; aynı adlı kısayol sessizce üzerine yazılır.

    Alanların tamamının dolu olması **şart değil** — bir kısayol, henüz
    aralığı belli olmayan tekrarlayan bir kaynağın da yer tutucusu olabilir;
    tamlık denetimi yalnızca gerçek bir dönüştürme başlatılırken yapılır.
    """
    path = _bookmark_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f'{field} = {_toml_string(value)}' for field, value in asdict(bookmark).items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _toml_string(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def delete_bookmark(name: str) -> None:
    """Siler. Yoksa sessizce geçer — silme işleminin sonucu aynı."""
    path = _bookmark_path(name)
    if path.is_file():
        path.unlink()


def rename_bookmark(old_name: str, new_name: str) -> Path:
    old_path = _bookmark_path(old_name)
    new_path = _bookmark_path(new_name)
    if not old_path.is_file():
        raise _invalid(old_name, "", "kısayol bulunamadı")
    if new_path.exists():
        raise _invalid(new_name, "", "bu adda bir kısayol zaten var")
    old_path.rename(new_path)
    return new_path
