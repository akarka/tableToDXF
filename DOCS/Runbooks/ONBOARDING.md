# Onboarding

Bu projeyi anlamak ve katkı vermeye başlamak için gereken her şey — hem insan geliştirici hem
AI agent için.

---

## Agent'lar için: ilk okuma sırası

1. `CLAUDE.md` — misyon, kritik kurallar, teknoloji yığını, dizin yapısı, **geçerli mandate'ler**
2. `README.md` — aracın ne yaptığı, iki arayüz, çıktının anatomisi, bilinen sınırlar
3. `DOCS/Features/_INDEX.md` — ne yapıldı, ne sürüyor, ne planlandı
4. İlgili özellik şartnamesi: `F-001` (çekirdek), `F-002` (ayarlar), `F-003` (UI)
5. `DOCS/Architecture/ADR_001…004` — neden böyle, hangi alternatif neden elendi
6. `AGENTS.md` ve `DOCS/Agents/` — birden çok agent çalışıyorsa koordinasyon

**En az 1–3'ü okumadan göreve başlama.** Sonra hafızana bak (`.claude/memory/MEMORY.md`).

> `_sablon_arsiv/` klasörü şablondan kalan, bu projede karşılığı olmayan dosyaları tutuyor
> (TypeScript iskeleti, command-pattern mandate'leri, deploy runbook'ları). `.gitignore`'da.
> **Oradan örnek ya da kural alma.**

---

## İnsan geliştirici için: ortam kurulumu

### Ön koşullar

- [ ] Python 3.11+ (`tomllib` stdlib'de olsun diye). Geliştirme 3.14 ile yapılıyor.
- [ ] Git yapılandırılmış (`git config user.email`)
- [ ] Windows 10+ — üretim hedefi bu. Linux/macOS'ta geliştirme çalışır; `%LOCALAPPDATA%`
      yoksa profiller `~/.local/share/OncuCAD/TableToDXF` altına düşer.

Veritabanı, sunucu, Docker, ortam değişkeni **yok**. Araç tek kullanıcılı ve ağsız.

### Kurulum

```bash
git clone https://github.com/akarka/tableToDXF.git
cd tableToDXF

python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev]"     # Windows
# python -m pip install -e ".[dev]"                     # Linux/macOS

.venv/Scripts/python.exe -m pytest
```

Beklenen çıktı:

```
443 passed
```

Kurulum iki komut bırakır: `tabletodxf-ui` (masaüstü uygulaması) ve `tabletodxf` (komut satırı).

Font sistemde bulunamazsa ölçüme dayanan testler `skip` olur, hata vermez
(bkz. `tests/conftest.py::font_path`). Varsayılan `NotoSans-Regular.ttf`.

---

## Çalıştırma

```bash
tabletodxf-ui                            # masaüstü uygulaması (konsol penceresi açmaz)
.venv/Scripts/python.exe -m tabletodxf.ui   # aynısı, konsol açık — teşhis için
```

```bash
tabletodxf mahal.ods --sheet Mahal --range B2:E7 --out mahal.dxf --block ONCU_TBL_MAHAL
```

```bash
.venv/Scripts/python.exe -m pytest                      # tüm testler
.venv/Scripts/python.exe -m pytest tests/unit -q        # yalnızca birim (hızlı)
```

**Paketleme (`.exe`) her zaman insan tarafından yapılır** — PyInstaller, ADR-004. Agent
paketleme çalıştırmaz.

Ayrı bir linter/tip denetleyici koşumu yok; stil, çevresindeki koda uymakla sağlanıyor.

---

## Anlaşılması gereken dosyalar

| Dosya | Neden önemli |
|---|---|
| `CLAUDE.md` | Agent'ın birincil talimat seti; kurallar ve geçerli mandate'ler |
| `src/tabletodxf/api.py` | `Job` / `Result` / `convert()` — çekirdeğin **tek** giriş noktası; CLI de UI de buradan geçer |
| `src/tabletodxf/config.py` | Tipli ayar katmanı. Yeni bir ayar buraya eklenir; UI formu ve `--set` kendiliğinden büyür |
| `src/tabletodxf/errors.py` | Hata kataloğu. Kullanıcıya ulaşan her hata buradan bir `code` taşır |
| `DOCS/Features/_INDEX.md` | Ne yapıldı, ne sürüyor, ne planlandı |
| `DOCS/Architecture/ADR_002_sheet_is_style_editor.md` | Projenin ayırt edici kararı: görünüm sayfadan okunur, araçta ayarlanmaz |
| `tests/fixtures/ods_builder.py` | Referans `.ods` kod olarak üretilir; sayfayı değiştirmek için LibreOffice açmak gerekmez |

---

## Proje gelenekleri

### Dosya adlandırma

- Kaynak: `snake_case.py` (ör. `ods_reader.py`)
- Test: `test_[modül].py` (ör. `test_ods_reader.py`)
- Özellik şartnamesi: `F-[N].md` (ör. `F-001.md`)
- ADR: `ADR_[N]_[kısa_başlık].md` (ör. `ADR_002_sheet_is_style_editor.md`) — **alt çizgi**, tire değil

### Dil

Kod ve tanımlayıcılar İngilizce; **yorumlar, docstring'ler ve dokümantasyon Türkçe.** Kullanıcıya
görünen metinler (UI etiketleri, rapor `reason` alanları) mevcut kalıba uyar — rapor satırları
İngilizce, UI Türkçe.

### Dal adlandırma

- Özellik: `feature/[kısa-ad]`
- Hata: `fix/[kısa-ad]`
- Doküman: `docs/[kısa-ad]`

Doğrudan `main`'e commit edilmez.

### Commit mesajı

```
<tip>: <kısa açıklama>

Tipler: feat | fix | refactor | test | docs | chore
Örnekler:
  feat: output.bylayer_defaults — tam siyah varlıkları BYLAYER'a bırak
  fix: marker kaydırmalı hücreleri kapsasın
  docs: F-001'e uygulama sırasında alınan kararları işle
```

Bir davranış değiştiyse ilgili şartnameyi (`F-00N.md`) ve gerekiyorsa `README.md`'yi aynı
commit'te güncelle. Test sayısı değiştiyse `DOCS/Testing/TEST_INDEX.md`'yi de.

---

## Yardım

1. `DOCS/Architecture/` — desen ve kararlar; "neden böyle" sorusunun cevabı ADR'larda
2. `DOCS/Features/` — ilgili özelliğin şartnamesi ve kabul kriterleri
3. Dokümanlarda olmayan alan bilgisi (AutoCAD iş akışı, ofis çizim standardı) için insana sor
4. Dokümanda yanlış bir şey görüyorsan **söyle** — sessizce etrafından dolaşma
