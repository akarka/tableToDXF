# ADR-002: Görünümü Kaynak Dosyadan Oku (Sayfa Stil Editörüdür)

**Date:** 2026-08-12
**Status:** ACCEPTED
**Deciders:** Kadir Akar (human), Claude Code

---

## Context

Üretilen tablonun görünümünü (çizgi kalınlıkları, başlık vurgusu, hizalama, dolgu, sayı biçimi)
bir yerin tanımlaması gerekiyor. İki aday var: **kaynak hesap tablosu** ya da **script'in kendi
ayar dosyası**.

Başlangıçtaki eğilim ayar dosyasıydı: katman şeması, çizgi hiyerarşisi, metin stili ve sayı
biçimleri `settings` içinde tanımlanacaktı. Ancak taşma davranışı için verilen karar — *"hücrede
sayfada göründüğü hâliyle gelsin"* — bu eğilimle çelişiyor. Taşma için "sayfada göründüğü gibi"
denip kenarlıklar için denmemesi tutarsız olur.

Belirleyici teknik gerçek: `.ods` (ADR-001 ile tek kaynak format) her hücre için **zaten**
şunları saklıyor —

- sütun genişlikleri ve satır yükseklikleri (gerçek cm)
- birleştirmeler (`table:number-columns-spanned` / `-rows-spanned`)
- yatay/dikey hizalama, kaydırma açık/kapalı
- **kenar başına kenarlık** — kalınlık ve renk ile
- arka plan dolgusu, font, boyut, kalın/italik, metin rengi
- gizli satır/sütunlar
- her sayının **görünen, biçimlenmiş metni**

Yani ayar dosyasıyla tanımlanacak her şey kaynak dosyada hazır duruyor. Ayar dosyası yolu, bu
bilgiyi okumamayı seçip yerine paralel bir şema icat etmek anlamına geliyor.

Ek bağlam: ofis zaten LibreOffice Calc kullanıyor. Kullanıcının stil için öğrenmesi gereken yeni
bir dosya formatı ya da sözdizimi yok — bildiği araçla biçimlendiriyor.

---

## Decision

Tablonun görsel niteliklerinin tamamı **kaynak `.ods` dosyasından okunur.** Sayfa, tablonun stil
editörüdür.

Script ayarları yalnızca `.ods`'in kavramsal olarak taşıyamayacağı şeylerle sınırlıdır: cm →
çizim birimi ölçek çarpanı, katman adları, hedef metin stili ve font, taşma işaretleyici davranışı,
DXF sürümü ve çıktı yolları.

---

## Options Considered

### Option A: Script Stil Editörüdür

Sayfa yalnızca içerik ve yapı verir (genişlikler, birleştirmeler); tüm görünüm ayar dosyasından.

**Pros:**
- Sayfa ne kadar dağınık olursa olsun çıktı tek tip görünür
- Ofis genelinde tek noktadan yeniden stillendirme

**Cons:**
- Katman şeması, çizgi hiyerarşisi, hizalama kuralları, sayı biçimleri için bir config şeması
  tasarlanmalı, dokümante edilmeli, sürdürülmeli — projenin kod hacminin büyük kısmı
- Kullanıcı stil değiştirmek için yeni bir dosya formatı öğrenir
- Sayfada gördüğü ile çizimde gördüğü sürekli ayrışır; hangi kuralın kazandığını kestirmek zor
- Sayı biçimi için `.ods`'teki görünen metin çöpe gider, yerine kendi renderer'ımız yazılır

---

### Option B: Sayfa Varsayılan, Ayarlar Ezer

Görünüm sayfadan okunur, ancak ayar dosyasındaki adlandırılmış kurallar belirli şeyleri ezebilir.

**Pros:**
- Esnek — aykırı durumlar için kaçış kapısı

**Cons:**
- Option A'nın config şemasını **yine de** tasarlamak gerekir, üstüne bir de öncelik/çakışma
  mantığı gelir
- "Neden bu hücre böyle göründü?" sorusunun cevabı iki yere bakmayı gerektirir

---

### Option C (Chosen): Sayfa Stil Editörüdür

Görünümün tamamı `.ods`'ten. Ayarlar yalnızca formatın taşıyamadığı şeylerle sınırlı.

**Pros:**
- Config şemasının büyük kısmı hiç var olmaz — çizgi hiyerarşisi, hizalama kuralları, sayı
  biçimleri, başlık vurgusu: hepsi okunur, tanımlanmaz
- Sayı biçimi renderer'ı gerekmez (`.ods` görünen metni saklar)
- Kullanıcı stili bildiği araçla, anında geri bildirimle düzenler
- Çıktı öngörülebilir: çizimdeki tablo Calc'taki tabloya benzer, kural aramaya gerek yok
- ADR-001 ile birlikte, pahalı olan her şey ortadan kalkar — maliyetin tamamı `.xlsx`'ten
  geliyordu

**Cons:**
- Dağınık biçimlendirilmiş bir sayfa dağınık bir tablo üretir. (Tartışmalı biçimde doğru davranış:
  araç kaynağı düzeltmez, yansıtır.)
- Ofis geneli yeniden stillendirme tek bir dosyayı değil, sayfaları değiştirmeyi gerektirir
- Görünüm sürüm kontrolüne binary `.ods` olarak girer, metin config olarak değil

---

## Consequences

**Positive:**
- Config yüzeyi bir avuç anahtara iner (bkz. F-001)
- Geometri üreticinin girdisi tek bir normalize edilmiş model olur (`SheetModel`); üretici
  `odfpy`'yi doğrudan görmez
- "Şöyle görünsün" talepleri koda değil, sayfaya gider — geliştirme dışı çözülür

**Negative (accepted trade-offs):**
- **Kenarlıklar BYLAYER olamaz.** Kalınlık kenar başına sayfadan geliyor ve değişken; dolayısıyla
  çizgi kalınlığı varlık üzerinde açıkça (ByObject) yazılır. Bu, erken tartışmadaki "BYLAYER +
  katman hiyerarşisi" fikrini geçersiz kılar — o fikir Option A'ya aitti.
- Katmanlar görünüm taşımaz, **işlev** taşır: `_GRID`, `_TEXT`, `_FILL`, `_OVERFLOW`. Filtreleme
  ve donuklaştırma için, stil için değil.
- Metin stili script'e ait kalır. Kiril/CJK desteği SHX'i eler, TTF şart; ve stil **tekil bir adla**
  tanımlanır (ör. `ONCU_TBL_TEXT`) ki hedef çizimdeki aynı adlı bir stil onu sessizce ezmesin.
  Sayfadaki font adı bilgilendiricidir, doğrudan bağlanmaz.
- Sayfadaki kenarlık kalınlıkları ofisin kalem standardıyla (CTB/STB) uyumsuz olabilir; uyumu
  kuran sayfayı düzenleyen kişidir.

**Risks:**
- Kaynak sayfa "veri" ve "sunum" görevini birlikte üstlenir; veri amaçlı düzenleme yapan biri
  farkında olmadan çizimin görünümünü değiştirebilir. *Azaltma:* şimdilik yok — bilinçli kabul.
  Sorun çıkarsa Option B'ye (ayar ezmesi) geçilir.
- LibreOffice sürümleri arası `.ods` stil yorumlama farkları çıktıyı kaydırabilir. *Bu koşulda
  gözden geçirilir.*

---

## Related

- ADR-001: Kaynak Format Olarak Yalnızca `.ods` Kabul Et
- `DOCS/Features/F-001.md` — `SheetModel`, katman şeması, geometri kuralları
- `DOCS/Architecture/Tablo_Ureticisi_DXF_Generator.md` — kısıt 3 (native `TABLE` kullanılmayacak)
