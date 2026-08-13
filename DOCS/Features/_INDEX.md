# Feature Index

This is the single source of truth for all feature work. Agents must check this before starting a task and update it when status changes.

---

## Status Definitions

| Status | Meaning |
|--------|---------|
| `PLANNED` | Accepted for implementation; not started |
| `IN_PROGRESS` | Actively being worked on (include agent name) |
| `REVIEW` | Implementation done; awaiting code review |
| `TESTING` | In QA / test writing phase |
| `DONE` | Merged and deployed |
| `BLOCKED` | Cannot proceed; reason documented in feature file |
| `CANCELLED` | Will not be built; reason documented |

---

## Active Features

| ID | Feature | Status | Agent | Feature Doc |
|----|---------|--------|-------|-------------|
| F-001 | `.ods` seçiminden DXF tablo bloğu üretimi | `REVIEW` | Claude Code | [F-001.md](F-001.md) |
| F-002 | Ayar yüzeyi — tipli konfigürasyon katmanı | `REVIEW` | Claude Code | [F-002.md](F-002.md) |
| F-003 | Masaüstü UI | `REVIEW` | Claude Sonnet 5 | [F-003.md](F-003.md) |

`REVIEW` gerekçesi (F-001): kod tamam; **Manual Verification** adımları (AutoCAD'de görsel
karşılaştırma, blok yeniden tanımlama, `ETRANSMIT`) insana bağlı ve bekliyor.

`REVIEW` gerekçesi (F-002): kod ve testler tamam, 277 test geçiyor. Aracı bir masaüstü
uygulamasına dönüştürme yolunun ilk adımıydı: kodun içine gömülü her davranış değeri tipli bir
ayara çıktı, CLI korundu, UI ve suite'in bağlanacağı şema doğdu (`Config` / `Job` / `convert()`).
Ayrıca profil yönetimi eklendi (`%LOCALAPPDATA%\OncuCAD\TableToDXF\profiles\`). Mimari
gerekçeler ADR-003 ve ADR-004'te.

`REVIEW` gerekçesi (F-003): `tkinter` tabanlı masaüstü UI — profil çubuğu, `.ods`/sayfa/aralık
girdisi, `Config`'in yedi bölümünden otomatik üretilen ayar sekmeleri, ayrı iş parçacığında
çalışan dönüştürme ve canlı rapor akışı. Toplam 360 test geçiyor (83'ü UI'a özgü). Gerçek bir
Tk penceresiyle (görsel değil, programatik) ve gerçek bir `.ods`'le uçtan uca doğrulandı — bkz.
F-003 → Test Plan. **PyInstaller paketlemesi ve görsel manuel doğrulama** (F-003 → Manual
Verification) insana bağlı ve bekliyor.

---

## Completed Features

| ID | Feature | Completed | Notes |
|----|---------|-----------|-------|
| — | — | — | — |

---

## Adding a New Feature

1. Copy `FEATURE_TEMPLATE.md` → `F-[next number].md`
2. Fill in all sections
3. Add a row to the Active Features table above
4. Set status to `PLANNED`
5. Assign to an agent when work begins (status → `IN_PROGRESS`)
