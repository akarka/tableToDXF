# ADR-003: Ayarları Tipli Bir Konfigürasyon Katmanına Taşı

**Date:** 2026-08-13
**Status:** ACCEPTED
**Deciders:** Kadir Akar (human), Claude Code

---

## Context

Araç bugün çalışıyor ama ayarlanabilirliği CLI bayraklarıyla sınırlı. Görünümü ve davranışı
belirleyen değerlerin çoğu modül düzeyinde sabit:

| Nerede | Sabit |
|---|---|
| `ods_reader` | `DEFAULT_COL_WIDTH_MM`, `DEFAULT_ROW_HEIGHT_MM`, `DEFAULT_PADDING_MM`, `DEFAULT_FONT_SIZE_PT`, kenarlıksız `solid` için `0.5pt`, değer tipine göre hizalama, bayat kaynak uzantıları |
| `geometry` | `MARKER_CHAR`, `MIN_WIDTH_FACTOR`, `DEFAULT_FRAME_MM`, `BACKGROUND_COLOR`, satır adımı (em) |
| `dxf_writer` | katman renkleri (`7`, taşma için `1`), model uzayına `INSERT` eklenmesi, blok taban noktası |
| `metrics` | `_FALLBACK_CAP_RATIO` |
| `model` | `BLACK`, hücre varsayılanları |

Üç yeni gereksinim bu tabloyu sürdürülemez kılıyor:

1. **UI.** Araç bir masaüstü uygulamasına dönüşecek (ADR-004). UI'ın bağlanacağı, gruplanmış ve
   tipli bir ayar nesnesi gerekiyor; modül sabitlerine form bağlanamaz.
2. **Güçlü özelleştirme.** Varsayılan davranış aynen korunacak, ama her değer değiştirilebilir
   olacak.
3. **Suite'e taşınabilirlik.** Araç ileride bir suite içine girecek; oradan **çağrılabilir**
   olmalı. Bugün tek giriş noktası `cli.main()`; bir kütüphane tüketicisi `argparse`'tan geçmek
   ya da `cli.Settings`'i içe aktarmak zorunda kalır.

`cli.Settings` ayrıca iki farklı şeyi tek sınıfta topluyor: **çalıştırmaya özgü girdiler**
(kaynak dosya, sayfa, aralık, çıktı yolu, blok adı) ile **kalıcı ayarlar** (ölçek, renkler,
katman adları, sürüm). UI'da birincisi her seferinde doldurulan bir form, ikincisi bir kez
ayarlanıp saklanan bir tercihler kümesi — ikisinin ömrü farklı.

---

## Decision

Ayarlar `config.py` içinde, **alanlara göre gruplanmış tipli dataclass'lara** taşınır.
Çalıştırmaya özgü girdiler bundan ayrı bir `Job` tipinde durur.

```python
Config(source=…, layout=…, text=…, overflow=…, background=…, layers=…, output=…)
Job(source=Path, sheet=str, range_text=str, out=Path, block=str, …)
```

Paket kökünde tek bir giriş noktası bulunur:

```python
convert(job: Job, config: Config, report: Report | None = None) -> Result
```

`cli.py` bu API'nin ince bir sarmalayıcısı olur: argümanları ayrıştırır, `Job` ve `Config`
üretir, `convert()` çağırır, çıkış kodunu döndürür. **CLI kullanımı aynen korunur** — mevcut
bayrakların hiçbiri kaldırılmaz.

Kurallar:

- `Config` saf veridir: I/O yapmaz, `odfpy`/`ezdxf` görmez, log basmaz.
- Her `Config` alanının varsayılanı **bugünkü davranıştır.** `Config()` = mevcut çıktı.
- TOML, `Config`'in serileştirilmiş hâlidir; UI'ın kaydetme biçimi de aynı dosyadır.
- Çekirdek, UI olmadan içe aktarılabilir kalır (ADR-004).

---

## Options Considered

### Option A: Düz Bir Ayar Sözlüğü

Tüm ayarlar tek bir `dict`; modüller `settings["frame_mm"]` gibi okur.

**Pros:**
- Yazması en hızlısı; TOML'dan doğrudan gelir
- Yeni ayar eklemek tek satır

**Cons:**
- Tip yok, doğrulama yok — `frame_mm = "0.35"` çalışma anında patlar
- UI bağlanacak bir şema bulamaz; hangi anahtarın hangi gruba ait olduğu koda gömülü kalır
- Yazım hatası sessizce varsayılana düşer (`frame_mmm`), kullanıcı neden değişmediğini anlamaz
- Otomatik tamamlama ve tip denetimi kaybolur

---

### Option B: CLI Bayraklarını Genişletmeye Devam Et

Her ayar için bir bayrak.

**Pros:**
- Tek bir mekanizma; öğrenilecek ikinci kavram yok
- Betiklemede doğrudan kullanılabilir

**Cons:**
- 40+ bayrak; `--help` okunamaz hâle gelir
- UI yine de bir yerde durum tutmak zorunda — bayraklar kalıcı tercih taşımaz
- Suite'ten çağrı hâlâ `argparse` üzerinden olur; kütüphane API'si doğmaz
- Nadiren değişen değerler (katman rengi, cap oranı) sık kullanılanları boğar

---

### Option C (Chosen): Tipli, Gruplanmış `Config` + Ayrık `Job` + `convert()` API

**Pros:**
- UI grupları doğrudan `Config` bölümlerine karşılık gelir (sekme/başlık başına bir dataclass)
- Tipler ve doğrulama tek yerde; hatalı ayar **çıktı üretilmeden** yakalanır (AC-10 ile uyumlu)
- Suite `from tabletodxf import convert, Config, Job` ile çağırır; `argparse` görmez
- `Job`/`Config` ayrımı UI'da "her seferinde doldurulan form" ile "bir kez ayarlanan tercihler"
  ayrımına birebir oturur
- Varsayılanlar tek yerde toplanır; "mevcut davranış" tek bir `Config()` ile ifade edilir
- TOML round-trip UI'ın kaydetme formatını bedavaya verir
- CLI korunur: bayraklar `Config` üzerine yazan ince bir katman olur

**Cons:**
- Modüller artık ilgili config bölümünü parametre olarak alır — imzalar uzar
- Ayar adları bir **uyumluluk yüzeyi** hâline gelir; anahtar yeniden adlandırmak kullanıcı
  TOML'larını bozar
- Dolaylılık artar: bir değerin nereden geldiğini görmek için config'e bakmak gerekir

---

## Consequences

**Positive:**
- Sabitler modüllerden çıkar; "bu sayı neden 0.25?" sorusunun cevabı tek dosyada toplanır
- UI ve suite entegrasyonu, çekirdeği değiştirmeden yazılabilir
- Test edilebilirlik artar: bir davranışı sınamak için `Config` alanını değiştirmek yeterli,
  monkeypatch gerekmez
- Bayrak > config dosyası > yerleşik varsayılan önceliği korunur

**Negative (accepted trade-offs):**
- **Aşırı konfigürasyon riski.** Kimsenin değiştirmediği ama herkesin bakmak, test etmek ve
  dokümante etmek zorunda olduğu ayarlar birikebilir. *Azaltma:* F-002 her ayarı gerekçesiyle
  listeler; gerekçesi olmayan ayar eklenmez.
- Ayar adları sürüm uyumluluğu taşır. *Azaltma:* yeniden adlandırma yerine ekleme; kaldırma
  ayrı bir ADR gerektirir.
- Bazı şeyler bilinçli olarak **ayarlanabilir yapılmaz** (bkz. F-002 → "Ayarlanamayanlar"):
  `PT_TO_MM`, ODF satır/sütun tavanları, geçerli DXF lineweight kümesi, kayan nokta toleransı,
  `MTEXT` kaçış kuralları, hata kodları. Bunlar tercih değil, doğruluk koşulu.

**Risks:**
- `Config` alan adı ile TOML anahtarı arasında sapma. *Azaltma:* TOML anahtarı = alan adı,
  istisnasız; yükleyici bilinmeyen anahtarı **hata** sayar, sessizce yutmaz.
- Varsayılanların kayması. *Azaltma:* `Config()` çıktısının bugünküyle aynı olduğunu sabitleyen
  bir golden test (bkz. F-002 AC).

---

## Related

- ADR-004: UI Araç Seti ve Paketleme
- `DOCS/Features/F-002.md` — ayar yüzeyinin tam listesi
- `DOCS/Features/F-001.md` — mevcut davranış; `Config()` varsayılanları buna eşittir
