# LibreOffice/CSV → DXF Tablo Üretici

> **Durum:** Bağımsız yan proje — OncuCAD Suite mimarisinin (ADR-001..009, `Architectural_Mandates.md`
> Mandate 1-10) parçası değil ve onlara tabi değil. Farklı stack (Python, out-of-process) ve farklı
> çalışma modeli (script → manuel AutoCAD adımı) kullanıyor. Olgunlaşırsa Suite'e bağlanması bir
> olasılık — bkz. son bölüm "Suite'e olası bağlanma noktası." Bu doküman, aynı klasördeki
> `autocad-tablo-uretici-handoff.md` dosyasının karışık bağlamdan arındırılmış, tek bir izi
> (harici DXF üretimi) netleştiren hâlidir; o dosya olduğu gibi korunuyor.
>
> **Konum:** bu klasör (`external-pending/tablo-uretici-dxf-generator/`) ayrı bir repo açılana
> kadarki bekleme alanı. Repo açıldığında bu klasörün tamamı oraya taşınır — taşımadan önce
> yanındaki `README.md`'deki kontrol listesine bakılmalı.

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
5. **Kurulu ofis paketinden bağımsız okuma.** Kaynak veri LibreOffice Calc `.ods` ya da düz CSV
   olacak. Microsoft Excel'e (dosya formatı, COM otomasyonu, `DATALINK`) hiçbir runtime bağımlılığı
   yok — ofiste WPS kaldırılıyor, LibreOffice/OnlyOffice'e geçiliyor.

## Elenen yollar (tekrar araştırmaya gerek yok)

| Yol | Durum |
|---|---|
| Excel/LibreOffice OLE gömme | Teslimde bağımlılık kopuyor — mevcut sorunun ta kendisi |
| AutoCAD `DATALINK` | Kurulu Excel şart koşuyor |
| LibreOffice UNO Automation Bridge | Sadece `IUnknown`+`IDispatch` sunuyor; `IOleObject`/`IOleInPlaceObject` yok. Veri okumak için kullanılabilir, gömme için değil |
| Native `TABLE` nesnesi | Kısıt 3 |
| Yapıştır Özel → AutoCAD Varlıkları | Çalışır ama her güncellemede elle tekrar; font eşlemesi zayıf |
| PDF → `PDFIMPORT` → blok | Çalışır, kodsuz alternatif. Tipografi kontrolü sınırlı — yedek plan olarak masada |

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

Python tarafı:

- CSV: stdlib `csv` ya da `pandas.read_csv`
- `.ods` (LibreOffice Calc): `pandas` + `odf` engine (`odfpy` bağımlılığı) ya da `pyexcel-ods`

Adlandırılmış aralık desteği önemli — tablo sınırlarını Calc'ta (Ad Kutusu / Sheet → Named Ranges)
tanımlayıp script'in onu bulması, sabit hücre aralığı yazmaktan çok daha dayanıklı. CSV'de isimli
aralık kavramı yok; CSV kaynağı için sabit sütun sırası/başlık satırı sözleşmesi gerekir.

## Tasarım kararları — cevaplanması gerekenler

Kodlamadan önce netleşmeli, çünkü geometri üreticinin şeklini bunlar belirliyor:

- **Katman şeması:** dış çerçeve / iç ızgara / başlık satırı / gövde metni ayrı katmanlarda mı?
  Ofisin mevcut katman standardı ne?
- **Çizgi hiyerarşisi:** dış çerçeve, başlık altı ayracı ve hücre ayracı için kalem kalınlıkları
- **Metin:** hangi text style, yükseklik, hücre içi hizalama kuralları (sayısal sağa, metin sola?)
- **Ölçek:** tablo paper space'te mi model space'te mi duruyor? Metin yüksekliği anotasyon ölçekli
  mi, sabit mi?
- **Sayfa taşması:** uzun mahal listesi kaç satırda kırılacak, başlık satırı tekrar edecek mi,
  kırılan parçalar yan yana mı alt alta mı?
- **Ekleme noktası ve blok adlandırma:** güncellemenin doğru bloğu ezmesi için deterministik bir
  isim şeması (ör. `TBL_MAHAL_<blokAdı>`)
- **Sayı biçimlendirme:** ondalık ayracı, binlik ayracı, birim gösterimi — kaynak dosyadaki hücre
  biçimi mi izlenecek yoksa script'te mi tanımlanacak?

## Beklenen ilk çıktı

1. Tek bir tablo tipini (mahal listesi) CSV/`.ods`'ten uçtan uca üreten çalışan iskelet
2. Blok yeniden tanımlama döngüsünün doğrulanması — aynı bloğu iki kez üretip çizimdeki
   örneklerin güncellendiğinin teyidi
3. Sayfa kırma kuralının çalıştığının uzun bir liste üzerinde testi

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

Olgunlaşırsa şu yol düşünülebilir: CSV/`.ods` okuma + tablo geometrisi kurgusu çekirdek mantık
olarak kalır; Suite tarafında bir "tablo ekle" özelliği `OncuCad.Contracts`'a yeni bir arayüz (ör.
`ITableGenerator`) ve bir adaptör (Batch-Ops'a ya da shell'e) olarak eklenir, in-process çalışır,
`IOperationArbiter.Execute` üzerinden geçer ve `[ONCU]` run-history'ye yazar (ADR-002, ADR-003,
ADR-005 desenini izler). Bu ayrı bir ADR gerektirir ve orijinal handoff'taki "İz A" (.NET AutoCAD
eklentisi) fikrine benzer — ama script'in DXF/blok mantığı kararlı hale gelmeden bu adım atılmamalı.

## Yeni sessiona açılış cümlesi

> AutoCAD için LibreOffice Calc (`.ods`) / CSV kaynaklı tablo verisinden DXF geometrisi üreten bir
> araç geliştiriyorum (Python + `ezdxf`, Suite'ten bağımsız bir yan proje). Bağlam bu dosyada. Önce
> blok yeniden tanımlamanın DXF `INSERT` tarafında nasıl zorlanacağını netleştirelim.
