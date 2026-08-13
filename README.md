# tabletodxf

LibreOffice Calc'ta biçimlendirilmiş bir `.ods` tablo alanını, kendi kendine yeten bir AutoCAD
**blok tanımına** çevirir. Çizim hiçbir harici dosyaya bağımlı kalmaz; kaynak veri değiştiğinde
aynı komut yeniden çalıştırılır ve blok yeniden tanımlandığında çizimdeki tüm örnekler güncellenir.

Stil, kullanıcının zaten bildiği araçta — Calc'ta — düzenlenir. Öğrenilecek yeni bir biçim dosyası
yoktur: kenarlıklar, dolgular, hizalamalar, birleştirmeler ve sayı biçimleri doğrudan sayfadan
okunur ([ADR-002](DOCS/Architecture/ADR_002_sheet_is_style_editor.md)).

Tam şartname: [`DOCS/Features/F-001.md`](DOCS/Features/F-001.md)

---

## Kurulum

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev]"     # Windows
# python -m pip install -e ".[dev]"                     # Linux/macOS
```

Python 3.11+ gerekir (`tomllib` stdlib'de).

---

## Kullanım

```bash
tabletodxf mahal.ods --sheet Mahal --range B2:E7 --out mahal.dxf --block ONCU_TBL_MAHAL
```

Kurulum yapılmadan da çalışır:

```bash
PYTHONPATH=src python -m tabletodxf mahal.ods --sheet Mahal --range B2:E7 \
    --out mahal.dxf --block ONCU_TBL_MAHAL
```

| Bayrak | Varsayılan | Açıklama |
|---|---|---|
| `--sheet` | — | zorunlu; sayfa adı |
| `--range` | — | zorunlu; `B3:C500` biçiminde |
| `--out` | — | zorunlu; çıktı DXF yolu |
| `--block` | — | zorunlu; blok adı |
| `--config` | `./tabletodxf.toml` varsa | config dosyası yolu |
| `--scale` | `10.0` | 1 cm kaç çizim birimi |
| `--frame` | `0.35` | tablonun dış sınırındaki çerçeve kalınlığı, mm (`0` = kapalı) |
| `--overflow` | `condense` | `condense` \| `mtext` \| `marker` \| `full` — aşağıya bakın |
| `--text-style` | `ONCU_TBL_TEXT` | DXF metin stili adı |
| `--font` | `NotoSans-Regular.ttf` | ölçüm ve stil için TTF |
| `--layer-prefix` | `ONCU_TBL` | katman ad alanı |
| `--dxf-version` | `R2013` | R2013 ve üstü |
| `--report` | `<out>.report.txt` | rapor dosyası yolu |
| `--verbose` | kapalı | `[TBL DEBUG]` satırlarını da bas |

Öncelik: **CLI bayrağı > config dosyası > yerleşik varsayılan.**

Çıkış kodları: `0` başarılı (uyarılar olabilir), `1` doğrulama/veri hatası, `2` kullanım hatası.

Örnek config için [`tabletodxf.example.toml`](tabletodxf.example.toml).

---

## Çıktı

| Katman | İçerik |
|---|---|
| `<prefix>_GRID` | Tüm kenarlık çizgileri. Kalınlık varlık üzerinde (ByObject) |
| `<prefix>_TEXT` | Hücre metinleri |
| `<prefix>_FILL` | Opak beyaz zemin + arka plan dolguları (düz desenli `HATCH`) |
| `<prefix>_OVERFLOW` | Yalnızca taşan hücreler. **Boş katman = çizimde hiç taşma yok** |

### Taşan hücreler

Dört mod var; hiçbirinde metin kırpılmaz ve hepsi `_OVERFLOW` katmanını kullanır, yani hangi
hücrelerin taştığını her zaman katman seçimiyle görebilirsiniz. Her taşan hücre rapora bir
`[TBL WARN] … mode=<mod>` satırı düşer.

| Mod | Davranış |
|---|---|
| `condense` (varsayılan) | Metin **hücreye sığacak şekilde yatay sıkıştırılır** — DXF genişlik çarpanı ayarlanır, yükseklik değişmez. Elle düzeltme gerekmez |
| `mtext` | Tanımlı genişliği hücrenin metin alanına eşit bir `MTEXT`. Satır bölmeyi AutoCAD yapar; genişlik tutamağıyla elle düzeltebilirsiniz |
| `marker` | Hücreyi dolduran `###` |
| `full` | Metin olduğu gibi yazılır, hücre sınırını aşar |

**Neden `condense` varsayılan:** AutoCAD otomatik heceleme yapmaz. Uzun ve boşluksuz bir metin
`mtext` modunda kutu genişliğini ne yaparsanız yapın kutudan taşmaya devam eder — bölünecek bir
yer yoktur. `condense` metni yatayda daraltarak sığdırır ve çizim üzerinde elle düzeltme
gerektirmez; tablo doğrudan basıma hazır çıkar.

Metnin bölünebileceği yerler varsa `mtext` daha okunaklı bir sonuç verir — o hücrelerde
`--overflow mtext` tercih edilebilir.

Çarpan en geniş satırdan türetilir ve hücredeki **tüm satırlara aynısı** uygulanır; satır başına
ayrı çarpan harf genişliklerini satırdan satıra zıplatırdı. Rapor çarpanı `width_factor=` alanında
yazar.

Okunabilirlik için bir taban vardır (`0.25`). Metin bundan fazla sıkıştırma gerektiriyorsa çarpan
tabanda tutulur, hücre taşmaya devam eder ve rapora `clamped=yes` düşer — okunamayan bir tablo
üretmektense taşmayı bildirmek doğru olan.

Metin sayfadaki gibi çizilir: **"metni kaydır"** açık hücreler kelime sınırlarında satırlara
bölünür, **döndürülmüş** hücreler (dar sütunlardaki dikey başlıklar) aynı açıyla döndürülür.
Sığdırma kontrolü metnin kendi ekseninde yapılır — 90° döndürülmüş bir başlık sütun genişliğine
değil, satır yüksekliğine göre ölçülür. Bu iki hücre tipi `###` üretmez.

DXF hem `--block` adlı blok tanımını hem de bu bloğun origin'e yerleştirilmiş tek bir `INSERT`'ünü
içerir; böylece dosya doğrudan açıldığında tablo görünür. `$INSUNITS = 0` yazılır — hedef çizime
eklerken otomatik ölçekleme devreye girmez.

Tablonun dış sınırında tek tip bir **çerçeve** döner. Çerçeve ayrı bir dikdörtgen değildir: var
olan dış ızgara parçalarının kalınlığı yükseltilir, dolayısıyla arkadaki zemin `HATCH`'inin
sınırıyla **birebir çakışır** — ofset yok, çakışık çift çizgi yok. Tek tip olduğu için dört
çizgiye birleşir (üst, alt, sol, sağ).

Kalınlık `max(--frame, sınırda sayfanın koyduğu en kalın kenarlık)`: çerçeve bir taban getirir,
sayfadaki bir vurguyu asla inceltmez. Rengi de sınırdaki en kalın kenarlığın rengidir, sayfada hiç
kenarlık yoksa siyah. `--frame 0` ile kapatılır ve dış sınır tamamen sayfadan gelir.

Bloğun en arkasında, seçimin tamamını kaplayan **opak beyaz bir zemin** vardır. Calc'ta "dolgu yok"
olan hücre ekranda beyaz görünür, saydam değil; zemin olmadan o hücreler çizimde altlarındaki
geometriyi gösterirdi. Tablo bu yüzden üzerine bindiği her şeyi örter — mevcut bir çizimin üstüne
şeffaf bindirmek isteniyorsa dikkat edilecek nokta budur.

Her başarılı çalıştırma, DXF'in yanına aynı adlı bir `.report.txt` bırakır (UTF-8). Hata durumunda
**hiçbir dosya yazılmaz** — ne DXF ne rapor.

---

## Kaynak dosya hazırlama

Araç yalnızca `.ods` okur ([ADR-001](DOCS/Architecture/ADR_001_ods_only_input.md)). Dışarıdan gelen
`.xlsx` / `.xls` dosyalarını LibreOffice Calc'ta açıp **Farklı Kaydet → ODF Hesap Tablosu** ile
dönüştürün. Dönüştürme sırasında sütun genişlikleri kayarsa bunu `.ods`'i açtığınızda görür ve
düzeltirsiniz; araç sessizce kaymış bir tablo üretmez.

`x.ods`'in yanında daha yeni tarihli bir `x.xlsx` varsa `SRC_STALE` uyarısı basılır — üretim durmaz.

---

## Geliştirme

```bash
.venv/Scripts/python.exe -m pytest          # 191 test
.venv/Scripts/python.exe -m pytest tests/unit -q
```

Referans `.ods` depoya ikili dosya olarak girmez; `tests/fixtures/ods_builder.py` ile kod olarak
üretilir. Sayfayı değiştirmek için LibreOffice açmak gerekmez.

### Katmanlar

```
cli.py          → argüman ayrıştırma, config birleştirme, çıkış kodu
ods_reader.py   → .ods → SheetModel        (odfpy yalnızca burada)
model.py        → SheetModel ve yardımcı tipler (saf veri)
metrics.py      → TTF ile metin genişliği ölçümü, sığdı/sığmadı
geometry.py     → SheetModel → çizilecek varlıklar
dxf_writer.py   → varlıklar → ezdxf blok tanımı → dosya  (ezdxf yalnızca burada)
report.py       → [TBL …] satırları, konsol + .report.txt
errors.py       → hata kataloğu
```

`geometry.py` `odfpy`'yi görmez, `ods_reader.py` `ezdxf`'i görmez.

---

## Bilinen sınırlar

- **Kalın/italik görsel olarak ayrışmaz.** Tek bir TTF'e bağlanıyoruz; sayfadaki kalın başlık
  çizimde normal ağırlıkta çıkar. Ölçüm de normal metriklerle yapılır (kalın metin bir miktar
  dar ölçülür).
- **Kaydırma kelime sınırında yapılır, kelime bölünmez.** Tek başına satıra sığmayan bir kelime
  kendi satırında taşar (`###` olmaz). Calc uzun kelimeyi ortadan bölebiliyor; bölme noktası
  fonta ve sürüme göre değiştiği için taklit edilmedi.
- **Metin stili hedef makineye bağlıdır.** DXF, TTF'i gömmez, adıyla anar; `--font` ile verilen
  yazı tipi hedef AutoCAD makinesinde de kurulu olmalı.
- **CJK için CJK kapsayan bir font gerekir.** Varsayılan `NotoSans-Regular.ttf` Kiril içerir,
  CJK içermez — CJK tablolarda `--font` ile uygun bir TTF verin.
- **`double` / `dashed` kenarlıklar tek düz çizgiye iner**; kalınlık ve renk korunur.
