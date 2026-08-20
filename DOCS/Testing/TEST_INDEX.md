# Test Index

Registry of all test suites. Update this when adding or removing test files.

Toplam: **443 test**, tamamı geçiyor (2026-08-20).

---

## Unit Tests

| Suite | File | Covers | Status |
|-------|------|--------|--------|
| Ayrıştırma | `tests/unit/test_parsing.py` | cm/inç/pt → mm, renk, kenarlık kısayolu, `A1:B2` aralığı, sütun harfleri | ✅ |
| Ölçüm | `tests/unit/test_metrics.py` | TTF genişlik ölçümü, cap height, sığdı/sığmadı sınırları, eksik font/glif | ✅ |
| Okuyucu | `tests/unit/test_ods_reader.py` | gizli satır/sütun, birleştirme + `covered`, görünen metin, hata kataloğu, `SRC_STALE` | ✅ |
| Geometri | `tests/unit/test_geometry.py` | kenar tekilleştirme, eş doğrultulu birleştirme, birleşik alan iç ızgarası, hizalama, taşma modları, determinizm | ✅ |
| Yazıcı | `tests/unit/test_dxf_writer.py` | `MTEXT` kaçışları, katman adları, `bylayer_defaults` renk kararı, diske yazmada `OSError` → `OUT_WRITE_FAILED` (çıktı AutoCAD'de açıkken) | ✅ |
| Ayarlar | `tests/unit/test_config.py` | varsayılanların bugünkü davranışa eşitliği, TOML yükleme, tanınmayan anahtar/tip/aralık reddi, round-trip, `--set`, profil CRUD (kaydet/yükle/sil/yeniden adlandır) | ✅ |
| CLI | `tests/unit/test_cli.py` | `--set` > bayrak > config > varsayılan önceliği, bayrak→ayar eşlemesi, DXF sürümünün her giriş yolunda reddi (bayrak/config/`--set`), bayrak değerlerinin TOML'a çevrimi (Windows yolları, kesme işareti), `Job`/`Config` ayrımı, `--profile`, çıkış kodları | ✅ |
| UI — formlar | `tests/unit/test_ui_forms.py` | tip→widget eşlemesi, metin↔değer round-trip (renk, nokta, liste, sayı), geçersiz girdi hataları — Tk kurmadan | ✅ |
| UI — Girdi bölmesi | `tests/unit/test_ui_app.py` | blok adı önerisi (`dosya_sayfa`, yasak/boşluk karakteri temizliği), Windows "Yol olarak kopyala" tırnak temizliği, **arka plan iş parçacığının her koşulda bir sonuç bildirmesi** (kataloğa girmeyen istisnada da) — Tk kurmadan | ✅ |
| Girdi kısayolları | `tests/unit/test_bookmarks.py` | `Job`↔`JobBookmark` round-trip, CRUD (kaydet/yükle/sil/yeniden adlandır), yasak ad, eksik/fazla/yanlış tipte alan, bozuk TOML, ters bölü/tırnak içeren yolların hayatta kalması | ✅ |
| UI — akış | `tests/unit/test_ui_streaming.py` | `Report` satırlarının kuyruğa sırayla düşmesi, `print`'in fazladan `"\n"`'i, `drain()` sınırı — Tk kurmadan | ✅ |
| UI — alan meta | `tests/unit/test_ui_fields.py` | bilinmeyen alan/bölüm çökmeden ham adına düşüyor; F-002 kataloğu ile `config.py`'nin gerçek alanları arasında kanarya testi | ✅ |
| Çekirdek yalıtımı | `tests/unit/test_core_purity.py` | `api`/`config`/`ods_reader`/`cli` `tkinter` içe aktarmıyor; `tkinter` yalnızca `ui/` altında geçiyor | ✅ |

## Integration Tests

| Suite | File | Covers | Requires |
|-------|------|--------|----------|
| Uçtan uca hat | `tests/integration/test_pipeline.py` | referans `.ods` → DXF → `ezdxf` geri okuma (golden): blok adı, katman dağılımı, koordinatlar, metin içerikleri, `$INSUNITS`, Kiril/CJK, determinizm, hata yolunda dosya bırakmama, `bylayer_defaults` (siyah→BYLAYER, renkli asla dokunulmaz, kalınlık etkilenmez) | `NotoSans-Regular.ttf` |

Harici altyapı yok — DB, sunucu ya da ağ gerekmez. Font sistemde yoksa ölçüme dayanan testler
`skip` olur (bkz. `tests/conftest.py::font_path`).

## E2E Tests

Ayrı bir otomatik E2E katmanı yok: CLI için integration testleri zaten `main()` üzerinden gerçek
dosya üretip geri okuyor. UI için de eşdeğer bir koşum bu görev sırasında **elle** yapıldı —
gerçek bir Tk kökü açılıp `MainWindow` kuruldu, gerçek bir `.ods` seçilip sayfa kutusu dolduruldu,
`Job`/`Config` toplandı ve `_run_worker` gerçek bir DXF üretti (bkz. F-003 → Test Plan). Bu koşum
otomatik pakette değil — CI/headless ortamda gerçek bir Tk kökü kurmak garanti olmadığı için.

---

## Fixtures

Referans `.ods` depoya **ikili dosya olarak girmez**; `tests/fixtures/ods_builder.py` ile kod
olarak üretilir (`tests/conftest.py::reference_spec`). Golden testin neyi doğruladığı diff'te
görünür ve sayfayı değiştirmek için LibreOffice açmak gerekmez.

Referans sayfa — `Mahal`, seçim `B2:E7`: başlık satırı (dolgu + kalın alt kenarlık), dikey
birleştirme `B3:B4`, yatay birleştirme `C4:D4`, gizli `D` sütunu, gizli 5. satır, taşan bir hücre
ve sonda kenarlıklı boş bir satır.

---

## Running Tests

```bash
# Tümü
.venv/Scripts/python.exe -m pytest

# Yalnızca birim testler (hızlı)
.venv/Scripts/python.exe -m pytest tests/unit -q

# Tek bir dosya
.venv/Scripts/python.exe -m pytest tests/unit/test_geometry.py -q
```

---

## Known Skips / TODOs

| Test | Reason Skipped | Owner | Deadline |
|------|---------------|-------|----------|
| Görsel doğruluk (DXF) | CI'da test edilemez — F-001 → Manual Verification'da AutoCAD adımı olarak duruyor | insan | — |
| Blok yeniden tanımlama | AutoCAD gerektirir; F-001 Open Questions'ta açık madde | insan | — |
| Görsel doğruluk (UI) | Tk penceresi headless ortamda anlamlı test edilemez — F-003 → Manual Verification | insan | — |
| PyInstaller paketleme | Build insan tarafından yapılır (CLAUDE.md); F-003 AC-10 | insan | — |
