# ADR-004: UI Araç Seti Olarak Tkinter, Paketleme Olarak PyInstaller

**Date:** 2026-08-13
**Status:** ACCEPTED
**Deciders:** Kadir Akar (human), Claude Code

---

## Context

Araç bir masaüstü uygulamasına dönüşecek. Kısıtlar:

1. **Win10+ PC'lerde hiçbir bağımlılık gerektirmeden çalışmalı.** Ofis makinelerinde Python
   kurulu değil ve kullanıcı IT sorumlusu değil (F-001'den gelen kısıt).
2. **Lightweight.**
3. Build/compile adımı **insan tarafından** yapılır (`CLAUDE.md` kritik kural).
4. İleride bir suite'e taşınacak; suite çekirdeği **UI olmadan** kullanabilmeli.

### Ölçülen bağımlılık ayak izi

`.venv/Lib/site-packages` üzerinden ölçüldü (2026-08-13):

| Paket | Boyut | Neden var |
|---|---|---|
| `numpy` + `numpy.libs` | **56 MB** | `ezdxf` bağımlılığı — kaldırılamaz |
| `fontTools` | 18 MB | metin genişliği ölçümü |
| `ezdxf` | 14 MB | DXF yazma |
| `odfpy` | 2 MB | `.ods` okuma |

**"Lightweight" ile gerçek arasında bir gerilim var ve bunu kayda geçirmek gerekiyor.** `ezdxf`
1.x `numpy`'ye bağlı; `numpy` tek başına diğer üç bağımlılığın toplamından büyük. Tek dosyalık
bir `.exe`'nin sıkıştırma sonrası **~40–60 MB** olması bekleniyor. Bu, bir CAD yardımcı aracı
için kabul edilebilir ama "küçük" değil; beklenti buna göre kurulmalı.

`tkinter` **CPython ile birlikte geliyor** (bu makinede Tk 8.6 doğrulandı) — yani UI katmanı
ayak izine yeni bir üçüncü parti bağımlılık **eklemiyor**.

---

## Decision

- **UI: `tkinter`** (`tkinter.ttk` widget'ları ile).
- **Paketleme: PyInstaller.** Ofis dağıtımı için `--onedir`, tek dosya kolaylığı istendiğinde
  `--onefile`. Build'i insan çalıştırır.
- **Çekirdek UI'dan bağımsız kalır.** UI kodu `tabletodxf/ui/` altında ayrı bir alt pakettir;
  `tabletodxf` çekirdeği `tkinter` içe aktarmaz. Suite, çekirdeği Tk olmadan kullanabilir
  (ADR-003'teki `convert()`).

---

## Options Considered

### Option A: PySide6 / Qt

**Pros:**
- Modern görünüm, zengin widget seti, iyi tablo/önizleme bileşenleri
- Yüksek DPI ve tema desteği olgun

**Cons:**
- **Paket boyutunu ~150 MB+ büyütür** — kısıt 2 ile doğrudan çelişir
- LGPL yükümlülükleri; ofis içi dağıtımda bile lisans metni ve dinamik bağlama dikkati ister
- PyInstaller ile Qt eklenti (`plugins/platforms`) toplama sorunları klasik bir tuzak
- Öğrenme ve bakım yükü, bu boyuttaki bir form uygulaması için orantısız

---

### Option B: Yerel Web UI (gömülü sunucu + tarayıcı)

Araç localhost'ta bir sunucu açar, kullanıcının tarayıcısında form gösterir.

**Pros:**
- Arayüz yazmak tanıdık (HTML/CSS)
- Paketlemeye UI araç seti girmez

**Cons:**
- Uygulama artık bir **süreç + tarayıcı sekmesi**; masaüstü aracı gibi davranmaz
- Dosya seçme diyalogları tarayıcı kumbarasında sınırlı — `.ods` ve çıktı yolu seçimi
  yerel dosya sisteminde rahat çalışmaz (aracın işi tam olarak bu)
- Ofis ortamında port çakışması, güvenlik duvarı ve kurumsal tarayıcı politikaları
- Kapanış yönetimi (sekme kapandı, süreç yaşıyor) ek karmaşıklık

---

### Option C (Chosen): Tkinter

**Pros:**
- **CPython ile geliyor** — üçüncü parti bağımlılık eklemez, kısıt 1 ve 2'yi birlikte karşılar
- PyInstaller ile en olgun ve en az sürprizli yol
- Bu uygulamanın şekli bir **form**: dosya seç, sayfa/aralık gir, ayarları düzenle, çalıştır,
  raporu göster. `ttk` bunun için fazlasıyla yeterli
- ADR-003'teki gruplanmış `Config`, `ttk.Notebook` sekmelerine doğrudan oturur

**Cons:**
- Görünüm tarih kokar; `ttk` temalarıyla kabul edilebilir seviyeye gelir ama modern değil
- Yüksek DPI ölçekleme Windows'ta elle ayar ister
- Karmaşık widget'lar (ağaç tablosu, canlı önizleme) yazması zahmetli — bugün gerekmiyor

---

## Consequences

**Positive:**
- Runtime bağımlılığı yok: kullanıcı `.exe`'yi (ya da klasörü) alır, Python kurmaz
- Çekirdek UI'sız kalır; suite `convert()`'i Tk yüklemeden çağırır
- CLI korunur (ADR-003); UI ve CLI aynı `Config`/`Job` üzerinden çalışır, davranış ayrışmaz

**Negative (accepted trade-offs):**
- **Artefakt ~40–60 MB.** Ana sebep `numpy`, `ezdxf` üzerinden geliyor ve kaldırılamaz.
  *Kısmi azaltma:* `fontTools`'un kullanılmayan alt modülleri (`varLib`, `pens`, `misc.plistlib`)
  PyInstaller `--exclude-module` ile atılabilir; UPX sıkıştırma denenebilir. Bunlar toplamı
  düşürür ama mertebeyi değiştirmez.
- `--onefile` her çalıştırmada geçici klasöre açılır: **başlangıç gecikmesi 1–3 sn.** Bir UI
  uygulamasında bu fark edilir. *Bu yüzden ofis dağıtımı için `--onedir` öneriliyor.*
- Tk görünümü modern değil.

**Risks:**
- **Antivirüs yanlış pozitifi.** PyInstaller `--onefile` çıktıları kurumsal Win10 makinelerinde
  sık karantinaya alınır. *Azaltma:* `--onedir` bu riski belirgin biçimde düşürür; gerekirse
  imzalama. Ofis dağıtımından önce denenmeli.
- Yüksek DPI'da bulanık/ölçeksiz arayüz. *Azaltma:* Windows'ta DPI farkındalığı açıkça
  ayarlanır; hedef makinede doğrulanmalı.
- `numpy`'nin PyInstaller tarafından eksik toplanması (gizli import'lar). *Azaltma:* build
  sonrası çıktı hedef makinede bir kez uçtan uca çalıştırılmalı — build insanda olduğu için
  bu adım da insanda.

---

## Related

- ADR-003: Ayarları Tipli Bir Konfigürasyon Katmanına Taşı
- `DOCS/Features/F-002.md` — ayar yüzeyi (UI'ın bağlanacağı şema)
- `DOCS/Features/F-001.md` — çekirdek davranış ve PyInstaller kısıtının kaynağı
