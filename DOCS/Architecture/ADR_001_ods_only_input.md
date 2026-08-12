# ADR-001: Kaynak Format Olarak Yalnızca `.ods` Kabul Et

**Date:** 2026-08-12
**Status:** ACCEPTED
**Deciders:** Kadir Akar (human), Claude Code

---

## Context

Araç, tablo verisini bir hesap tablosu dosyasından okuyup DXF geometrisi üretiyor. Ofis
LibreOffice/OnlyOffice'e geçiyor, yani iç iş akışında üretilen dosyalar `.ods`. Ancak dışarıdan
(müşteri, müteahhit, müşavir) gelen dosyalar neredeyse her zaman `.xlsx`, bazen eski `.xls`.

`Tablo_Ureticisi_DXF_Generator.md` kısıt 5 şunu diyordu: *"Microsoft Excel'e (dosya formatı, COM
otomasyonu, `DATALINK`) hiçbir runtime bağımlılığı yok."* Bu ifade fazla geniş ve teknik olarak
yanlış. `.xlsx` açık bir format (ZIP + XML); `openpyxl` ile okumak Excel kurulumu gerektirmez.
Gerçek kısıt **"Excel'in *kurulu* olmasına bağımlılık yok"** — COM otomasyonu ve `DATALINK` bunu
ihlal eder, dosya formatını okumak etmez. Kısıt bu ADR ile yeniden ifade ediliyor.

ADR-002'de kararlaştırılan WYSIWYG yaklaşımı (görünüm doğrudan kaynak dosyadan okunur) formatlar
arasında ciddi bir asimetri yaratıyor:

| Gereken bilgi | `.ods` | `.xlsx` |
|---|---|---|
| Hücrenin **görünen metni** (biçimlenmiş hâli) | dosyada saklı | **yok** — sadece biçim kodu (`#,##0.00`) |
| Sütun genişliği | gerçek cm | varsayılan fontun karakter genişliği cinsinden |
| Kenarlık kalınlığı | gerçek sayı (pt) | enum (`thin` / `medium` / `thick` / `hair`) |
| Renk | doğrudan RGB | çoğunlukla tema-indeksli + tint, tema XML'i çözülmeli |
| Formül sonucu önbelleği | LibreOffice her zaman yazar | sıklıkla yok (kütüphane üretimi dosyalarda) |

En kritik satır ilki: `.xlsx` hücrenin görünen metnini saklamaz. WYSIWYG'i `.xlsx` üzerinde
gerçekleştirmek, **kendi sayı biçimi renderer'ımızı yazmak** demek (ondalık, binlik ayracı, yüzde,
para birimi, tarih, yerel ayar). Bu, ADR-002'nin ortadan kaldırmayı amaçladığı işin ta kendisi.

---

## Decision

Araç kaynak dosya olarak **yalnızca `.ods` kabul eder.** Başka bir uzantı verildiğinde iş,
kullanıcıya ne yapması gerektiğini söyleyen bir hata ile durur; dönüştürme kullanıcı tarafından,
LibreOffice Calc içinde elle yapılır.

CSV desteği kapsam dışıdır. `--convert` bayrağı (varsayılan kapalı) ileride bir kolaylık olarak
eklenebilir; çekirdek akışın parçası değildir.

---

## Options Considered

### Option A: Her Format İçin Yerel Okuyucu

`odfpy` ile `.ods`, `openpyxl` ile `.xlsx`, `xlrd` ile `.xls`.

**Pros:**
- Harici çalışma zamanı bağımlılığı yok
- Kullanıcı hangi dosyayı aldıysa doğrudan verebilir

**Cons:**
- `.xlsx` için sayı biçimi renderer'ı yazmak gerekir — başlı başına bir alt sistem, hiçbir zaman
  tam sadık olmaz
- Kenarlık enum → kalınlık eşleme tablosu (kayıplı)
- Tema-indeksli renklerin çözülmesi
- `.xls` (BIFF) `openpyxl` ile okunmaz; `xlrd` biçimlendirmeyi çok sınırlı verir
- Aynı sayfa üç okuyucuda üç farklı sonuç verebilir — test yüzeyi üçe katlanır

---

### Option B: LibreOffice ile Otomatik Normalizasyon

`soffice --headless --convert-to ods` ile her girdi `.ods`'e çevrilir, tek okuyucu kullanılır.

**Pros:**
- Tek okuyucu, sayı biçimi renderer'ı yok
- `.xls` dahil her şeyi kapsar
- Dönüştürme sırasında formül değerleri ve görünen metinler hesaplanır
- LibreOffice zaten ofise kuruluyor — yeni bir bağımlılık değil

**Cons:**
- **Headless `soffice`, kullanıcı LibreOffice'i açıkken çakışır** (paylaşılan kullanıcı profili
  kilidi). Kullanıcının sayfası Calc'ta açık olacak — dönüştürme ya başarısız olur ya kullanıcının
  oturumunu ele geçirir. Bu, ofis PC'lerinde tipik senaryo, istisna değil.
- `soffice` yolunu bulma, alt süreç yönetimi, sürüm farkları
- Tek dosyalık PyInstaller paketlemesini bozar
- LibreOffice'in `.xlsx` içe aktarımı bazen sütun genişliklerini kaydırır — ve bu **sessizce**
  olur; WYSIWYG altında doğrudan çizime yansır

---

### Option C (Chosen): Yalnızca `.ods`, Dönüştürme Kullanıcıda

Araç sadece `.ods` okur. Başka format gelirse net bir hata ile durur.

**Pros:**
- Tek okuyucu, sayı biçimi renderer'ı yok, kenarlık eşlemesi yok, tema rengi çözümü yok
- Alt süreç yok — `soffice` profil kilidi sorunu tamamen ortadan kalkar
- Temiz tek dosyalık PyInstaller paketlemesi
- **Dönüştürme görünür hâle gelir.** LibreOffice'in `.xlsx` içe aktarımındaki kaymayı kullanıcı
  `.ods`'i açtığında görür, düzeltir, sonra üretir. Option B'de aynı kayma sessizce çizime geçerdi.
- Ofisin kendi iş akışında `.ods` zaten yerel kayıt formatı — iç işler için ek adım yok

**Cons:**
- Dışarıdan gelen her dosya için elle bir dönüştürme adımı
- Bayat veri riski: kullanıcı `.xlsx`'i günceller, `.ods`'i yeniden dışa aktarmayı unutur

---

## Consequences

**Positive:**
- Okuma katmanı tek bir kod yoluna iner; test yüzeyi buna göre daralır
- ADR-002 (WYSIWYG) ucuza gelir — `.ods` görünen metni, gerçek cm genişlikleri, gerçek kenarlık
  kalınlıklarını ve doğrudan RGB'yi hazır verir
- Harici süreç, PATH keşfi, sürüm sürüklenmesi yok
- Kısıt 5 doğru ifadesine kavuşur: yasak olan **Excel'in kurulu olması**, dosya formatı değil

**Negative (accepted trade-offs):**
- `.xlsx`/`.xls` kullanıcı tarafından dönüştürülmeli (LibreOffice Calc → Farklı Kaydet → ODF)
- CSV desteklenmez; genişlik/yükseklik/birleştirme/kenarlık taşımadığı için WYSIWYG'e zaten
  katılamaz

**Risks:**
- **Bayat kaynak.** Kullanıcı `.xlsx`'i düzenler, `.ods` eski kalır, çizime yanlış sayı basılır.
  Bu, bu tasarımın ürettiği tek yeni hata modu ve projedeki en kötü sonuç (sessiz yanlış veri).
  *Azaltma:* `x.ods` okunurken yanında daha yeni `mtime`'a sahip `x.xlsx` varsa `SRC_STALE`
  uyarısı verilir (bkz. F-001 hata kataloğu).
- Kullanıcılar sürekli `.xlsx` verip hataya çarparsa iş akışı sürtünmesi doğar. *Bu koşulda
  gözden geçirilir:* `--convert` bayrağı eklenir (Option B, opt-in), varsayılan davranış
  değişmeden.

---

## Related

- ADR-002: Görünümü Kaynak Dosyadan Oku (WYSIWYG)
- `DOCS/Architecture/Tablo_Ureticisi_DXF_Generator.md` — kısıt 5
- `DOCS/Features/F-001.md` — hata kataloğu (`SRC_FORMAT`, `SRC_STALE`)
