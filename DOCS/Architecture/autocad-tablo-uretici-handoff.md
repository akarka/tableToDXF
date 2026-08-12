# Handoff: Excel → AutoCAD Tablo Üretici (script tabanlı)

## Amaç

Çizim dökümantasyonunu (mahal listesi, bağımsız bölüm listesi, hesap tabloları) Excel'de
tutmaya devam ederken, çizim içinde **kendi kendine yeten yerel AutoCAD geometrisi**
üretmek. Excel doğruluk kaynağı olarak kalır; çizimle arasındaki bağ bir dosya bağımlılığı
değil, **tekrarlanabilir bir üretim adımıdır**.

## Değişmez kısıtlar

1. **Teslim bağımsızlığı.** Teslim edilen DWG hiçbir harici dosyaya bağımlı olmamalı.
   `ETRANSMIT` raporu temiz çıkmalı, alıcıda "kaynak bulunamadı" uyarısı olmamalı.
2. **OLE kullanılmayacak.** Mevcut sorunun kaynağı bu; ayrıca plot döndürme, dosya şişmesi
   ve render kalitesi problemleri getiriyor.
3. **Yerel AutoCAD TABLE nesnesi kullanılmayacak.** Stil kontrolü zayıf, görsel olarak arkaik.
   Üretilecek şey: çizgi + metin geometrisi, tipografisi tam kontrol edilebilir.
4. **Güncelleme mekanizması blok yeniden tanımlama olacak.** Tablo bir blok tanımı olarak
   yerleşir; tanım ezildiğinde çizimdeki tüm örnekleri güncellenir. "Canlı bağlantı" hissi
   harici referans olmadan böyle sağlanır.
5. **Microsoft Excel'e çalışma zamanı bağımlılığı olmamalı.** Ofiste WPS kaldırılıyor,
   LibreOffice/OnlyOffice değerlendiriliyor. Bu yüzden Excel COM otomasyonu (`Excel.Application`)
   ve AutoCAD `DATALINK` özelliği **eleme dışı** — ikisi de kurulu Excel şart koşuyor.
   Dosya, kurulu ofis paketinden bağımsız bir kütüphaneyle okunmalı.

## Denenmiş / elenmiş yollar (tekrar araştırmaya gerek yok)

| Yol | Durum |
|---|---|
| Excel OLE nesnesi | Teslimde bağımlılık kopuyor — mevcut sorunun ta kendisi |
| AutoCAD `DATALINK` | Makinede kurulu Excel şart koşuyor |
| LibreOffice/OpenOffice OLE sunucusu | AutoCAD'de "Paste Link" çıkmıyor, gömülen nesne simge olarak görünüyor |
| LibreOffice UNO Automation Bridge | Sadece `IUnknown` + `IDispatch` sunuyor; `IOleObject`/`IOleInPlaceObject` yok. Belge sunucusu değil, betikleme köprüsü. Veri **okumak** için kullanılabilir ama gömme için değil |
| PDF → `PDFIMPORT` → blok | Çalışır, kodsuz alternatif. Tipografi kontrolü sınırlı. Yedek plan olarak masada |
| Yapıştır Özel → AutoCAD Varlıkları | Çalışır ama her güncellemede elle tekrar; font eşlemesi zayıf |

## İki uygulama izi — bu sessionda karar verilecek

### İz A — AutoCAD .NET eklentisi (in-process)

Geometriyi doğrudan çizim veritabanında kurar. Araştırılacak API yüzeyi:

- `Autodesk.AutoCAD.DatabaseServices`: `Database`, `Transaction`, `BlockTable`,
  `BlockTableRecord`, `MText`, `Polyline` / `Line`, `TextStyleTableRecord`
- `Autodesk.AutoCAD.Runtime.CommandMethod` ile komut kaydı
- Blok tanımını **yerinde yeniden kurma**: mevcut `BlockTableRecord` içeriğini silip yeniden
  doldurduğunda tüm `BlockReference`'lar güncellenir. `RecordGraphicsModified` /
  regen davranışı araştırılmalı.
- Dağıtım: `NETLOAD`, otomatik yükleme için plugin bundle (`.bundle` klasör yapısı,
  `PackageContents.xml`)

**Doğrulanması gereken sürüm bağımlılıkları:** hedef AutoCAD sürümünün beklediği .NET
sürümü (2025+ sürümler .NET 8 tarafına geçti, daha eskiler .NET Framework 4.x).
ObjectARX SDK sürümü AutoCAD sürümüyle eşleşmeli. **AutoCAD LT'de .NET API yok.**

### İz B — Harici DXF üretimi (out-of-process)

Python + `ezdxf` ile bağımsız bir DXF üretilir, AutoCAD'e `INSERT` ile blok olarak girer.

- AutoCAD'e hiç kod yüklenmez → kurulum yetkisi gerekmez (ofis PC'lerinde IT sorumlusu
  kullanıcı değil, bu ciddi bir avantaj)
- Sürüm bağımlılığı yok, sürüm kontrolüne rahat girer, CI'da test edilebilir
- Bedeli: iki adımlı iş akışı, AutoCAD içinden tek tuşla tetiklenemez

**Muhtemelen doğru cevap ikisinin birleşimi:** geometri kurgusunu üreten çekirdek mantık
ortak, İz B ile prototiplenir, olgunlaşınca İz A ile AutoCAD içine sarılır.

## Excel okuma katmanı

Kurulu ofis paketinden bağımsız olmalı. Değerlendirilecekler:

- .NET tarafı: **ClosedXML**, **EPPlus** (lisans modeline dikkat), **OpenXML SDK**
- Python tarafı: **openpyxl**, **pandas**

Adlandırılmış aralık (named range) okuma desteği önemli — tablo sınırlarını Excel'de
tanımlayıp script'in onu bulması, sabit hücre aralığı yazmaktan çok daha dayanıklı.

## Tasarım kararları — cevaplanması gerekenler

Bunlar kodlamadan önce netleşmeli, çünkü geometri üreticinin şeklini bunlar belirliyor:

- **Katman şeması:** dış çerçeve / iç ızgara / başlık satırı / gövde metni ayrı katmanlarda mı?
  Ofisin mevcut katman standardı ne?
- **Çizgi hiyerarşisi:** dış çerçeve, başlık altı ayracı ve hücre ayracı için kalem kalınlıkları
- **Metin:** hangi text style, yükseklik, hücre içi hizalama kuralları (sayısal sağa, metin sola?)
- **Ölçek:** tablo paper space'te mi model space'te mi duruyor? Metin yüksekliği anotasyon
  ölçekli mi, sabit mi?
- **Sayfa taşması:** uzun mahal listesi kaç satırda kırılacak, başlık satırı tekrar edecek mi,
  kırılan parçalar yan yana mı alt alta mı?
- **Ekleme noktası ve blok adlandırma:** güncellemenin doğru bloğu ezmesi için deterministik
  bir isim şeması (ör. `TBL_MAHAL_<blokAdı>`)
- **Sayı biçimlendirme:** ondalık ayracı, binlik ayracı, birim gösterimi — Excel'deki hücre
  biçimi mi izlenecek yoksa script'te mi tanımlanacak?

## Bu sessiondan beklenen çıktı

1. İz A / İz B kararı (veya kademeli plan)
2. Tek bir tablo tipini (mahal listesi) uçtan uca üreten çalışan iskelet
3. Blok yeniden tanımlama döngüsünün doğrulanması — aynı bloğu iki kez üretip çizimdeki
   örneklerin güncellendiğinin teyidi
4. Sayfa kırma kuralının çalıştığının uzun bir liste üzerinde testi

## Ortam notları

- Ofis PC'lerinde kullanıcı IT sorumlusu değil; AutoCAD'e eklenti yüklemek veya SDK kurmak
  izin gerektirebilir. İz B bu engeli tamamen atlar.
- Ev makinesinde Windows tarafında AutoCAD var (dual-boot kurgusunda AutoCAD Windows
  bölümünde tutuluyor) — geliştirme ve test orada yapılabilir.
- Hedef AutoCAD sürümü henüz teyit edilmedi; İz A için ilk belirlenecek şey bu.

## Yeni sessiona açılış cümlesi

> AutoCAD için Excel'den tablo geometrisi üreten bir araç geliştiriyorum. Bağlam ekteki
> handoff dosyasında. .NET API dökümantasyonundan faydalanarak İz A'yı irdelemek istiyorum;
> önce sürüm/SDK eşleşmesini ve blok yeniden tanımlama mekanizmasını netleştirelim.
