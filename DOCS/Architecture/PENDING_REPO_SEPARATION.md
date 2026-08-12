# Tablo Üretici — Harici Repo Bekleme Alanı

> **Durum:** Bu klasördeki içerik gelecekte ayrı bir repo olacak (session kararı: 2026-08-12).
> Repo henüz açılmadı. Bu klasör, o repo açılana kadar ilgili notların `oncuCad`'i (Suite reposunu)
> kirletmeden bir arada tutulduğu bekleme alanı — `DOCS/` yapısına ya da repo köküne dağılmış değil.

## Repo açıldığında yapılacaklar

1. Bu klasörün tüm içeriği yeni repo'ya taşınır; bu klasör `oncuCad`'den silinir.
2. Yeni repo, OncuCAD Suite ile ilişkilendirilmek isteniyorsa (`Tablo_Ureticisi_DXF_Generator.md`
   → "Suite'e olası bağlanma noktası") `external/` altına submodule olarak eklenir (ADR-002
   deseni) — bu adım için ayrı bir ADR açılır, önceden açılmaz.
3. Taşımadan önce **aşağıdaki kontrol listesi** gözden geçirilir: bu klasördeki kararlar bu
   session'ın (ADR-001..009 baseline) enstantanesidir; taşıma anına kadar `oncuCad`'in
   mimarisi ilerlemiş olabilir.

## Taşıma öncesi kontrol listesi

- [ ] `Architectural_Mandates.md` ve `System_Overview.md` bu session'dan bu yana değişti mi?
      Değiştiyse, `Tablo_Ureticisi_DXF_Generator.md`'deki "Suite'e olası bağlanma noktası"
      bölümü hâlâ doğru mu (Mandate/ADR numaraları, arbiter/contracts deseni)?
- [ ] DXF `INSERT` ile blok yeniden tanımlama sözdizimi doğrulandı mı? (Dokümanda hâlâ açık
      nokta olarak işaretli — script geliştirilirken netleşmiş olmalı.)
- [ ] Script'in kaynak okuma kütüphaneleri (`odfpy` / `pandas` / `pyexcel-ods`) hâlâ güncel ve
      bakımda mı — Python ekosistemi hızlı değişir.
- [ ] `autocad-tablo-uretici-handoff.md` (orijinal, karışık bağlamlı not) yeni repo'da hâlâ
      gerekli mi, yoksa `Tablo_Ureticisi_DXF_Generator.md` (arındırılmış hâli) tek başına
      yeterli mi? Gerekliyse ikisi de taşınır; değilse orijinal handoff arşivlenip silinebilir.
- [ ] Bu bekleme alanındayken script üzerinde yapılan tüm değişiklikler (varsa) yeni repo'nun
      ilk commit'ine taşınmadan önce bu dokümanlarla tutarlı mı?

## İçerik

- `autocad-tablo-uretici-handoff.md` — orijinal, karışık bağlamlı handoff notu (referans için
  korunuyor, düzenlenmedi)
- `Tablo_Ureticisi_DXF_Generator.md` — arındırılmış, tek izli (harici DXF üretimi) doküman;
  geliştirme buradan devam eder
