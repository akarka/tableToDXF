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

`REVIEW` gerekçesi (F-001): kod tamam; **Manual Verification** adımları (AutoCAD'de görsel
karşılaştırma, blok yeniden tanımlama, `ETRANSMIT`) insana bağlı ve bekliyor.

`REVIEW` gerekçesi (F-002): kod ve testler tamam, 252 test geçiyor. Aracı bir masaüstü
uygulamasına dönüştürme yolunun ilk adımıydı: kodun içine gömülü her davranış değeri tipli bir
ayara çıktı, CLI korundu, UI ve suite'in bağlanacağı şema doğdu (`Config` / `Job` / `convert()`).
Mimari gerekçeler ADR-003 ve ADR-004'te.

Sıradaki: **F-003 — masaüstü UI.** F-002'nin açık bıraktığı iki soru UI'a başlamadan
netleşmeli (bkz. F-002 → Open Questions): ayar profilleri gerekecek mi, ve ayar dosyası
kullanıcı başına (`%APPDATA%`) da aranacak mı.

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
