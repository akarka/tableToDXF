# Repo Ayrılması — TAMAMLANDI

> **Durum:** `RESOLVED` (2026-08-12). Bu doküman artık tarihsel bir kayıt; bekleyen bir iş
> içermiyor. Ayrı repo (`tableToDXF`) açıldı ve içerik taşındı — bu dosyanın tarif ettiği
> `external-pending/tablo-uretici-dxf-generator/` bekleme alanı artık yok.

Bu not, içerik `oncuCad` (Suite reposu) içinde geçici bir klasörde beklerken yazılmıştı. Taşıma
gerçekleştiği için orijinal kontrol listesi kapatıldı; sonuçları aşağıda.

## Kapanan kontrol listesi

| Madde | Sonuç |
|---|---|
| Suite'in `Architectural_Mandates.md` / `System_Overview.md`'i değişti mi? | Artık ilgisiz — bu repo Suite'in ADR/Mandate zincirine tabi değil. Bağlanma ihtimali `Tablo_Ureticisi_DXF_Generator.md` son bölümünde duruyor ve gerçekleşirse **ayrı bir ADR** gerektirir |
| DXF `INSERT` ile blok yeniden tanımlama doğrulandı mı? | **Hayır — hâlâ açık.** Takip yeri değişti: `DOCS/Features/F-001.md` → Open Questions. İskeletten önce AutoCAD'de denenmeli |
| Kaynak okuma kütüphaneleri güncel mi? | Karara bağlandı: `odfpy` (ADR-001). `pandas` / `pyexcel-ods` elendi — stil bilgisini düşürüyorlar. CSV desteği kapsam dışı |
| `autocad-tablo-uretici-handoff.md` hâlâ gerekli mi? | Evet, referans olarak korunuyor. Excel odaklı ve "İz A / İz B" ikilemini içeriyor; ikisi de aşıldı, ama kararların nereden geldiğini gösteriyor |
| Script değişiklikleri dokümanlarla tutarlı mı? | Henüz kod yok. İlk kod F-001'e göre yazılacak |

## Numaralandırma uyarısı

Bu repodaki `ADR-001` ve `ADR-002`, **bu reponun** kararlarıdır. `oncuCad`'in aynı numaralı
ADR'leriyle hiçbir ilgisi yoktur. Suite'in ADR'lerine atıf yapılacaksa açıkça "Suite ADR-00N"
denmelidir.

## Bu dosya silinebilir

Tarihsel değeri düşük — içindeki her şey ya karara bağlandı ya da F-001'e taşındı. Repo temizliği
sırasında silinmesinde sakınca yok.
