# Test Fixtures

Bu projede fixture demek, **kaynak `.ods` sayfası** demek. Veritabanı yok, seed yok, factory yok.

---

## Yapı

```
fixtures/
  ods_builder.py    — spec nesnelerinden gerçek bir .ods dosyası üretir
  __init__.py
```

Referans `.ods` depoya **ikili dosya olarak girmez**; kod olarak üretilir. Sebebi: golden testin
neyi doğruladığı diff'te görünür ve sayfayı değiştirmek için LibreOffice açmak gerekmez.

---

## Kullanım

```python
from fixtures.ods_builder import build_ods, SheetSpec, RowSpec, CellSpec

path = build_ods(tmp_path / "mahal.ods", [
    SheetSpec(
        name="Mahal",
        col_widths=["3.0cm", "2.0cm"],
        rows=[
            RowSpec(cells=[
                CellSpec(text="Mahal", bold=True, fill="#dddddd",
                         border="0.06pt solid #000000"),
                CellSpec(text="Alan", bold=True, border="0.06pt solid #000000"),
            ]),
            RowSpec(cells=[
                CellSpec(text="Zemin kat koridoru"),
                CellSpec(value=24.5, text="24,50"),
            ]),
        ],
    ),
])
```

`CellSpec` sayfanın söyleyebildiği her şeyi taşır: `bold`, `align`, `valign`, `fill`, `border`,
`border_bottom`, `font_size`, `padding`, `wrap`, `rotation`, `text_color`, `col_span`, `row_span`,
`covered`, `omit_cached_value`. `RowSpec` `height` ve `hidden`, `SheetSpec` `col_widths` ve
`hidden_cols` taşır.

`value` ile `text` **ayrı** verilir: `value` hücrenin `office:value-type`'ını belirler (hizalama
kararı buradan gelir), `text` ise sayfada **görünen** biçimlenmiş metindir (ADR-002, AC-3).

---

## Ortak fixture'lar

`tests/conftest.py` içinde:

| Fixture | Kapsam | Ne verir |
|---|---|---|
| `reference_spec()` | fonksiyon değil, düz çağrı | Golden testin referans sayfası — `Mahal`, seçim `B2:E7` |
| `reference_ods` | session | `reference_spec()`'ten üretilmiş gerçek bir `.ods` yolu |
| `font_path` | session | Ölçüm fontu; sistemde yoksa test `skip` olur, hata vermez |
| `metrics` | session | `font_path`'ten yüklenmiş `FontMetrics` |
| `report` | function | Boş bir `Report` (çıktıyı yutar) |

Referans sayfa bilinçli olarak zor: başlık satırı (dolgu + kalın alt kenarlık), dikey birleştirme
`B3:B4`, yatay birleştirme `C4:D4`, gizli `D` sütunu, gizli 5. satır, taşan bir hücre ve sonda
kenarlıklı boş bir satır.

---

## Kural

Yeni bir fixture yazarken **sabit** değer kullan — rastgele veri, tarih ya da `uuid` yok. AC-12
aynı girdinin baytı baytına aynı çıktıyı üretmesini şart koşuyor; testin kendisi de deterministik
olmalı. Teste özel bir değer gerekiyorsa onu açıkça geç.
