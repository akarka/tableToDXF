# LibreOffice Calc (`.ods`) → DXF Tablo Üretici

> **Durum:** Bu repo'nun (`tableToDXF`) ana mimari dokümanı. Karar defteri aşağıda; gerekçeler
> ADR-001 ve ADR-002'de. Uygulanabilir spesifikasyon: `DOCS/Features/F-001.md`.
>
> **Suite ilişkisi:** Bağımsız yan proje — OncuCAD Suite'in kendi ADR ve Mandate zincirine tabi
> değil. Farklı stack (Python, out-of-process) ve farklı çalışma modeli (script → manuel AutoCAD
> adımı). Olgunlaşırsa bağlanması bir olasılık — bkz. son bölüm. Bu repodaki ADR numaraları
> Suite'inkilerden bağımsızdır.
>
> **Köken:** Bu doküman, `autocad-tablo-uretici-handoff.md` dosyasının karışık bağlamdan
> arındırılmış, tek bir izi (harici DXF üretimi) netleştiren hâlidir; o dosya referans olarak
> olduğu gibi korunuyor.

## Amaç

Çizim dökümantasyonundaki tabloları (mahal listesi, bağımsız bölüm listesi, hesap tabloları) kaynak
veride (LibreOffice Calc `.ods` ya da düz CSV) tutmaya devam ederken, çizim içinde kendi kendine
yeten yerel AutoCAD geometrisi üretmek. Kaynak veri doğruluk kaynağı olarak kalır; çizimle arasındaki
bağ bir dosya bağımlılığı değil, tekrarlanabilir bir DXF üretim adımıdır.

## Değişmez kısıtlar

1. **Teslim bağımsızlığı.** Çıktı DWG hiçbir harici dosyaya bağımlı olmamalı. `ETRANSMIT` raporu
   temiz çıkmalı, alıcıda "kaynak bulunamadı" uyarısı olmamalı.
2. **OLE kullanılmayacak.** Plot döndürme, dosya şişmesi ve render kalitesi sorunları getiriyor.
3. **Native AutoCAD `TABLE` nesnesi kullanılmayacak.** Stil kontrolü zayıf, görsel olarak arkaik.
   Üretilecek şey: çizgi + metin geometrisi, tipografisi tam kontrol edilebilir.
4. **Güncelleme mekanizması blok yeniden tanımlama olacak.** Tablo bir blok tanımı olarak yerleşir;
   tanım ezildiğinde çizimdeki tüm örnekleri güncellenir. "Canlı bağlantı" hissi harici referans
   olmadan böyle sağlanır.
5. **Microsoft Excel'in *kurulu olmasına* bağımlılık yok.** Yasak olan, Excel uygulamasının
   varlığını şart koşmak: COM otomasyonu (`Excel.Application`) ve AutoCAD `DATALINK` bunu yapar,
   ikisi de eleme dışı. Bir dosya formatını okumak bunu ihlal etmez — `.xlsx` açık bir formattır ve
   Excel kurulumu olmadan okunabilir. Bu kısıt daha önce "dosya formatı" ifadesiyle fazla geniş
   yazılmıştı; ADR-001 ile düzeltildi.

   Kabul edilen kaynak format **yalnızca `.ods`**'tir (ADR-001). Bu bir çalışma zamanı kısıtı değil,
   sadakat kararıdır: `.ods` hücrelerin görünen metnini, gerçek cm genişliklerini ve gerçek kenarlık
   kalınlıklarını saklar; `.xlsx` saklamaz. `.xlsx`/`.xls` kullanıcı tarafından Calc'ta `.ods`'e
   dönüştürülür.

6. **Görünüm kaynak dosyadan okunur** (ADR-002). Kenarlıklar, dolgular, hizalama, font ve sayı
   biçimleri sayfadan gelir; script ayarları yalnızca `.ods`'in taşıyamadığı şeyleri tanımlar.

## Elenen yollar (tekrar araştırmaya gerek yok)

| Yol | Durum |
|---|---|
| Excel/LibreOffice OLE gömme | Teslimde bağımlılık kopuyor — mevcut sorunun ta kendisi |
| AutoCAD `DATALINK` | Kurulu Excel şart koşuyor |
| LibreOffice UNO Automation Bridge | Sadece `IUnknown`+`IDispatch` sunuyor; `IOleObject`/`IOleInPlaceObject` yok. Veri okumak için kullanılabilir, gömme için değil |
| Native `TABLE` nesnesi | Kısıt 3 |
| Yapıştır Özel → AutoCAD Varlıkları | Çalışır ama her güncellemede elle tekrar; font eşlemesi zayıf |
| PDF → `PDFIMPORT` → blok | Çalışır, kodsuz alternatif. Tipografi kontrolü sınırlı — yedek plan olarak masada |
| Yerel `.xlsx` / `.xls` okuyucu | ADR-001 — görünen metin saklanmadığı için sayı biçimi renderer'ı gerekir; genişlikler karakter cinsinden, kenarlıklar enum |
| `soffice --headless` ile otomatik dönüştürme | ADR-001 — kullanıcı LibreOffice'i açıkken profil kilidi çakışıyor; dönüştürme kaymaları sessiz kalıyor |
| CSV kaynak | ADR-002 — genişlik/yükseklik/birleştirme/kenarlık taşımaz, WYSIWYG'e katılamaz |
| Satır başına ayrı blok tanımı | Dikey birleştirmeler satır sınırını aşar; ayrıca her satırın içeriği farklı olduğu için blok tekrar kullanımı sıfır |
| Hücre metni için `ATTDEF`/`ATTRIB` | Blok yeniden tanımlama mevcut `BlockReference`'ların attribute **değerlerini** güncellemez (`ATTSYNC` tanımları senkronize eder, değerleri değil) — kısıt 4'ün çalışmasını sessizce bozar |

## Uygulama yaklaşımı: harici DXF üretimi (Python + ezdxf)

Bağımsız bir Python script'i CSV/`.ods` okur, `ezdxf` ile DXF üretir; AutoCAD'e blok olarak
`INSERT` edilir. AutoCAD'e hiç kod yüklenmez.

- Kurulum/yetki gerekmez — ofis PC'lerinde kullanıcı IT sorumlusu değil, bu ciddi bir avantaj
- Sürüm bağımlılığı yok (ObjectARX/.NET SDK sürüm eşleşmesi devre dışı), versiyon kontrolüne
  rahat girer, CI'da test edilebilir
- Bedeli: iki adımlı iş akışı (script çalıştır → AutoCAD'de ekle), tek tuşla tetiklenemez

**Netleşmesi gereken kritik nokta:** blok yeniden tanımlamanın (kısıt 4) DXF `INSERT` tarafında
nasıl zorlanacağı — ör. `INSERT ad=yol.dxf` zorla yeniden tanımlama sözdizimi, ya da ek bir
AutoLISP/script adımı gerekip gerekmediği. Bu, çalışan iskeletten önce doğrulanması gereken ilk şey.

## Kaynak veri okuma katmanı

Tek format, tek okuyucu: `.ods` (ADR-001). Kütüphane `odfpy` — biçim bilgisine (kenarlık, dolgu,
hizalama, sütun genişliği) erişim gerektiği için `pandas` yeterli değil; `pandas` yalnızca hücre
değerlerini verir, stil bilgisini düşürür.

Okuyucu, formatı bilmeyen normalize bir ara modele (`SheetModel`) yazar; geometri üreticisi
`odfpy`'yi doğrudan görmez. Bugün tek okuyucu var, dolayısıyla polimorfizme gerek yok — bu yalnızca
bir yalıtım dikişi, spekülatif bir soyutlama katmanı değil. `SheetModel` alanları için bkz.
`DOCS/Features/F-001.md`.

**Seçim aralığı CLI argümanıdır**, dosyadan tespit edilmez: `.ods`, kullanıcının o an neyi seçili
bıraktığını güvenilir biçimde saklamaz. Adlandırılmış aralık desteği ileride bir kolaylık olarak
eklenebilir; çekirdek sözleşme `--sheet` + `--range`.

**Formüller:** yalnızca önbellekteki değer okunur, hiçbir formül değerlendirilmez. Formül motoru
yok, bağımlılık grafiği yok. Önbellek değeri yoksa iş durur (`FORMULA_NO_CACHE`).

## Karar defteri

Bu kararlar kapalıdır. Değiştirilecekse ADR açılır, doküman üzerinde sessizce düzeltilmez.

| Konu | Karar |
|---|---|
| Kaynak format | Yalnızca `.ods`. CSV yok, `.xlsx` yok (kullanıcı dönüştürür). ADR-001 |
| Görünüm kaynağı | Sayfa (WYSIWYG). Kenarlık, dolgu, hizalama, font, sayı biçimi hep `.ods`'ten. ADR-002 |
| Seçim | CLI argümanı: `--sheet` + `--range`. Tek çalıştırma = tek tablo. Batch sonraya |
| Sayfa kırma | Yok. Kırma = kullanıcının seçim yapması. İleride Calc'ın manuel sayfa sonlarından otomasyon düşünülebilir |
| Boş satırlar | Aralık **birebir** onurlandırılır, sondaki boş satırlar kırpılmaz. Seçim doğruluğu kullanıcının sorumluluğu |
| Gizli satır/sütun | Seçim içinde olsa da atlanır (WYSIWYG) |
| Blok yapısı | Tablo = tek düz blok tanımı. Satır başına blok yok, iç içe blok yok |
| Birleştirmeler | Birleşik alanın sınır kutusu hesaplanır, iç ızgara parçaları bastırılır, tek metin kendi hizalamasıyla yerleşir |
| Seçimi kesen birleştirme | Hata, iş durur (`MERGE_CROSSES_SELECTION`). Sessiz kırpma yok |
| Metin | Blok tanımı içinde düz `TEXT`/`MTEXT`. **Attribute kullanılmaz** — kısıt 4 ile çakışır |
| Taşma | Sığmayan hücre, hücre genişliğini dolduran `###` ile gösterilir; str ve sayı ayrımı yok. Kapatılırsa metin tam hâliyle, hücre sınırını taşarak yazılır (kırpma yok — kırpma veriyi gizler) |
| Taşma işareti | Kendi katmanında: `<prefix>_OVERFLOW`. Katman boş = çizimde hiç taşma yok |
| Origin | Seçimin sol üst köşesi, (0,0) |
| Ölçek | Birimsiz (`$INSUNITS = 0`), ekleme sırasında otomatik ölçekleme olmaz. 1 cm = 10 birim (yapılandırılabilir) |
| DXF sürümü | R2013+ (UTF-8 yerel). Kiril ve CJK desteklenir |
| Metin stili | Script'e ait, **tekil adlı** (ör. `ONCU_TBL_TEXT`), TTF. SHX elenir — Unicode kapsamı yetersiz. Tekil ad, hedef çizimdeki aynı adlı bir stilin sessizce ezmesini engeller |
| Katmanlar | İşlevsel, stil taşımaz: `_GRID`, `_TEXT`, `_FILL`, `_OVERFLOW`. Kenarlık kalınlığı varlık üzerinde (ByObject), çünkü kalınlık sayfadan gelir ve kenar başına değişir |
| Blok adlandırma | Config'teki tablo kimliğinden deterministik üretilir, dosya adından değil. Ad alanı öneki zorunlu |
| Hata davranışı | Yüksek sesle başarısız ol. Kısmi çıktı yok — eksik satırlı bir tablo, hiç tablo olmamasından kötüdür |
| Log biçimi | `[TBL] / [TBL ERROR] / [TBL WARN] / [TBL DEBUG]`, `op= cell= reason=` alanlarıyla. DXF'in yanına `.report.txt` de yazılır |
| Üretilen DXF | Build artifact, `.gitignore`'da. Tek bir örnek dosya referans olarak commit'lenir |

## Beklenen ilk çıktı

1. Tek bir seçimi (`--sheet` + `--range`) `.ods`'ten uçtan uca DXF'e çeviren çalışan iskelet
2. Blok yeniden tanımlama döngüsünün doğrulanması — aynı bloğu iki kez üretip çizimdeki
   örneklerin güncellendiğinin teyidi
3. WYSIWYG sadakat kontrolü — kenarlık, dolgu, hizalama ve birleştirmelerin sayfadakiyle
   eşleştiğinin bir referans sayfa üzerinde teyidi
4. Taşma davranışının doğrulanması — dar sütunda `###`, `_OVERFLOW` katmanında, raporda `[TBL WARN]`

*Not:* sayfa kırma artık bir çıktı kalemi değil — kırma, kullanıcının seçim yapmasıyla oluyor
(karar defteri).

## Ortam notları

- Ofis PC'lerinde kullanıcı IT sorumlusu değil; AutoCAD'e eklenti yüklemek veya SDK kurmak izin
  gerektirebilir — harici script yaklaşımı bu engeli tamamen atlar.
- Ev makinesinde Windows tarafında AutoCAD var (dual-boot kurgusunda AutoCAD Windows bölümünde
  tutuluyor) — geliştirme ve test orada yapılabilir.

## Suite'e olası bağlanma noktası (şimdi değil)

Bu proje bugün OncuCAD Suite'in ADR/Mandate zincirine tabi değil: harici bir Python script,
in-process bir AutoCAD eklentisi değil, `IOperationArbiter`'dan geçmiyor, `[ONCU]` run-history'ye
yazmıyor (`Architectural_Mandates.md` Mandate 4, Mandate 7). Suite'in "Out of Scope" listesi zaten
"a non-AutoCAD standalone host"u kapsam dışı sayıyor (`System_Overview.md`).

Olgunlaşırsa şu yol düşünülebilir: `.ods` okuma + tablo geometrisi kurgusu çekirdek mantık olarak
kalır; Suite tarafında bir "tablo ekle" özelliği `OncuCad.Contracts`'a yeni bir arayüz (ör.
`ITableGenerator`) ve bir adaptör (Batch-Ops'a ya da shell'e) olarak eklenir, in-process çalışır,
`IOperationArbiter.Execute` üzerinden geçer ve `[ONCU]` run-history'ye yazar. Bu ayrı bir ADR
gerektirir ve orijinal handoff'taki "İz A" (.NET AutoCAD eklentisi) fikrine benzer — ama script'in
DXF/blok mantığı kararlı hâle gelmeden bu adım atılmamalı.

*Numara çakışmasına dikkat:* buradaki ADR-001/ADR-002 bu reponun kararlarıdır; Suite'in aynı
numaralı ADR'leriyle ilgisi yoktur.

---

## Nereden devam edilir

1. `DOCS/Features/F-001.md` — uygulanabilir spesifikasyon (CLI, config, `SheetModel`, geometri
   kuralları, hata kataloğu, kabul kriterleri)
2. İlk doğrulanacak teknik nokta: blok yeniden tanımlamanın DXF `INSERT` tarafında nasıl
   zorlanacağı. Yüksek engel değil, ama iskeletten önce ev makinesindeki AutoCAD'de denenmeli.
