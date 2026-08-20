# tabletodxf: Biçimlendirilmiş `.ods` aralığından AutoCAD blok tanımı

## Project Mission

LibreOffice Calc'ta biçimlendirilmiş bir `.ods` tablo alanını, kendi kendine yeten bir AutoCAD
**blok tanımına** (DXF) çevirir. Hedef kullanıcı, mahal listesi / çizim listesi / metraj gibi
tabloları Calc'ta tutup çizime taşıyan mimarlık-mühendislik ofisi çalışanıdır.

Ayırt edici karar şudur: **stil sayfada düzenlenir, araçta değil.** Kenarlıklar, dolgular,
hizalamalar, birleştirmeler, döndürmeler ve sayı biçimleri doğrudan `.ods`'ten okunur; öğrenilecek
ikinci bir biçim dosyası yoktur (ADR-002). Bir değişikliğin kapsam içinde olup olmadığına karar
verirken ölçüt budur: araç kaynağı **yansıtır**, düzeltmez.

Üretim hedefi Windows 10+. Tek kullanıcılı, masaüstü, ağsız, veritabansız.

---

## CRITICAL RULES (Read before every task)

- **NEVER run PyInstaller / paketleme.** `.exe` üretimi her zaman insan tarafından yapılır
  (ADR-004). Paketleme gerekiyorsa kullanıcıya açıkça söyle.
- **NEVER commit or push** without explicit user request.
- **NEVER deploy** ya da kullanıcının makinesindeki `%LOCALAPPDATA%\OncuCAD\TableToDXF`
  altındaki profilleri/kısayolları silme veya üzerine yazma — bunlar kullanıcının gerçek
  verisidir, test verisi değil.
- **NEVER modify** `.env`, gizli anahtarlar, kimlik bilgisi dosyaları.
- **NEVER delete** dosya ya da veri; önce kullanıcıya sor.
- **NEVER force-push** ya da commit edilmemiş değişikliği olan dalı sıfırla.
- **Testleri çalıştırmak serbesttir ve beklenir:** `.venv/Scripts/python.exe -m pytest`.
- Yapısal bir değişiklikten önce `DOCS/Architecture/` altındaki **ADR-001…004**'ü oku.
  Kodda karşılığı olmayan bir desen getiriyorsan önce `ADR_TEMPLATE.md` ile yeni bir ADR aç.
- Geçerli mandate'ler **bu dosyadaki** "Architectural Mandates" bölümüdür. Şablondan gelen
  `Architectural_Mandates.md`, `ADR_000_EXAMPLE.md` ve `System_Overview.md` 2026-08-20'de
  `_sablon_arsiv/`'e taşındı (TypeScript/command-pattern örnekleriydi, bu projeyi tarif
  etmiyorlardı). Arşiv `.gitignore`'da; oradan kural alma.

---

## Technical Architecture

- **Runtime:** Python 3.11+ (`tomllib` stdlib'de olsun diye; geliştirme 3.14 ile yapılıyor)
- **Framework:** yok — CLI `argparse`, UI `tkinter` (ikisi de stdlib)
- **Database:** yok. Kalıcı durum = kullanıcı başına TOML dosyaları
  (`%LOCALAPPDATA%\OncuCAD\TableToDXF\{profiles,inputs}\`)
- **Key Libraries:**
  - `odfpy` — `.ods` okuma, biçim bilgisiyle birlikte (ADR-001)
  - `ezdxf` — DXF blok tanımı yazma
  - `fontTools` — TTF ile metin genişliği/cap height ölçümü
- **Pattern:** Tek yönlü boru hattı (pipeline) + katman başına tek dış bağımlılık +
  saf veri modeli. Komut/undo katmanı **yoktur**; araç durum tutmaz, her çalıştırma
  `.ods` → `.dxf` saf bir dönüşümdür.

### Boru hattı

```
cli.py / ui/app.py  → argüman ya da form; ince sarmalayıcı, iş mantığı yok
api.py              → Job / Result / convert()  — TEK giriş noktası
config.py           → tipli ayar katmanı (saf veri, I/O yok, log yok)
ods_reader.py       → .ods → SheetModel        (odfpy YALNIZCA burada)
model.py            → SheetModel ve yardımcı tipler (saf veri)
metrics.py          → TTF ölçümü, sığdı/sığmadı  (fontTools YALNIZCA burada)
geometry.py         → SheetModel → çizilecek varlıklar (mm → çizim birimi burada)
dxf_writer.py       → varlıklar → ezdxf blok tanımı → dosya (ezdxf YALNIZCA burada)
report.py           → [TBL …] satırları, konsol + .report.txt
errors.py           → hata kataloğu
bookmarks.py        → adlandırılmış Job kısayolları (saf veri)
```

---

## Directory Structure

```
/src/tabletodxf      — paketin tamamı (yukarıdaki boru hattı)
/src/tabletodxf/ui   — tkinter masaüstü uygulaması; çekirdeğin ÜSTÜNDE durur,
                       çekirdek modüller bu paketi asla içe aktarmaz
/tests/unit          — I/O yok ya da tmp_path; saf dönüşümler
/tests/integration   — gerçek .ods → gerçek .dxf, uçtan uca
/tests/fixtures      — ods_builder.py: referans .ods'i KOD OLARAK üretir
                       (depoda ikili dosya yok, LibreOffice açmaya gerek yok)
/DOCS/Architecture   — ADR-001…004 + şablonlar (ADR_TEMPLATE)
/DOCS/Features       — F-001 (çekirdek), F-002 (ayarlar), F-003 (UI)
/DOCS/Testing        — strateji, test dizini
```

**`_sablon_arsiv/`** — şablondan kalan, bu projede karşılığı olmayan dosyalar (TypeScript
`src/commands`·`models`·`services`·`utils`, `Architectural_Mandates.md`, `System_Overview.md`,
`DEPLOY.md`, `INCIDENT_RESPONSE.md`, `TEST_PATTERNS.md`, `.env.example`, `scripts/`).
`.gitignore`'da; geri almak isteyen `mv` ile yerine koyar. **Buradan örnek ya da kural alma.**

---

## Architectural Mandates

Tam gerekçeler: `DOCS/Architecture/ADR_001…004` ve `DOCS/Features/F-001.md`.

1. **Katman saflığı.** `geometry.py` `odfpy` görmez, `ods_reader.py` `ezdxf` görmez,
   `config.py` hiçbirini görmez ve `tkinter`'ı hiçbir çekirdek modül görmez. Yeni bir dış
   bağımlılık tek bir modülde hapsedilir.
2. **Sayfa kazanır (ADR-002).** `.ods` bir değer veriyorsa o kullanılır. `Config`'teki
   varsayılanlar yalnızca sayfa **sessiz kaldığında** devreye girer. Kaynağı "düzeltmek"
   — ince kenarlığı kalınlaştırmak, hizalamayı güzelleştirmek — kapsam dışıdır.
3. **Kısmi çıktı yok (F-001 AC-10).** Hata durumunda ne DXF ne rapor yazılır. Doğrulama
   dosya yazımından **önce** biter.
4. **Kataloglu hatalar.** Kullanıcıya ulaşan her hata `errors.py`'deki bir `code` taşır ve
   `TableToDxfError` olarak atılır. Ham istisna kullanıcıya sızmaz — özellikle arka plan
   iş parçacığında: yakalanmayan bir istisna UI'ı sonsuza kadar "Çalışıyor…" durumunda
   bırakır (bkz. `ui/app.py::_as_catalog_error`).
5. **Doğrulama tip katmanında.** Kapalı uçlu bir ayar `Literal` olur (`OverflowMode`,
   `DxfVersion`). Denetimi tek bir giriş yoluna (ör. yalnızca CLI'a) koymak, diğer
   yolların — UI, kütüphane `convert()` — onu sessizce atlaması demektir.
6. **Determinizm (AC-12).** Aynı girdi → baytı baytına aynı çıktı. Sözlük sırasına,
   `locale`'e, saate ya da yuvarlanmamış kayan nokta kırıntısına bağlanma.
7. **Sessiz başarısızlık yok.** Tanınmayan bir ayar anahtarı **hatadır**; taşan bir hücre
   **uyarıdır**. İkisi de rapora düşer.
8. **Yeni bağımlılık eşiği yüksektir.** 20 satırla doğru yazılabilen şey için paket
   eklenmez (`config.py`'deki küçük TOML yazıcısı bunun örneğidir) — paketlenmiş `.exe`
   boyutu ADR-004'te açık bir kaygıdır.

---

## Error Reporting

- Log ön eki: `[TBL INFO]`, `[TBL WARN]`, `[TBL ERROR]`, `[TBL DEBUG]`
- Biçim: `[TBL WARN]   op=render_cell cell=Mahal!C17 reason="text overflow" avail_mm=21.0`
- Alan sırası: `op=` → `cell=` → `reason="…"` → serbest alanlar. Yalnızca `reason` ve boşluk
  içerebilen değerler tırnaklanır ki `grep 'op=render_cell'` çalışsın.
- Hücreye bağlı her satır **kullanıcının sayfada gördüğü** referansı basar (`Mahal!C17`),
  model içi 0-tabanlı indeksi değil (`SheetModel.ref()`).
- Rapor dosyası her zaman UTF-8; bozulabilecek tek yer konsoldur ve orada `errors="replace"`
  uygulanır — üretim `UnicodeEncodeError` ile yarıda kalmaz.

---

## Agent Coordination

`AGENTS.md` protokolü geçerlidir (henüz büyük ölçüde şablon; roster bölümü bu projeyi
tarif etmiyor).

- Herhangi bir göreve başlamadan `git status` çalıştır
- Başka bir agent'ın üzerinde çalıştığı dosyayı düzenleme
- Agent görevi başına bir özellik dalı; doğrudan `main`'e commit etme

---

*Özellik şartnameleri: `DOCS/Features/`*
*Mimari kararlar: `DOCS/Architecture/ADR_001…004`*
*Kullanıcıya dönük dokümantasyon: `README.md`*
