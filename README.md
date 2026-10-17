# 🔋 Batarya Sağlığı Analiz Hattı (Battery Health Analysis Pipeline)

Gerçek dünya batarya sensör verilerini (voltaj, akım, sıcaklık) işleyen; **veri temizleme**, **özellik mühendisliği** ve **görselleştirme** odaklı, modüler bir veri analizi boru hattı (pipeline).

**Teknolojiler:** Python · Matplotlib · CSV tabanlı modüler veri hattı

---

## 📌 Proje Hakkında

Bu proje, ham batarya sensör verisinden başlayıp batarya sağlığına dair anlamlı metrikler üreten uçtan uca bir analiz hattıdır. Her aşama bağımsız bir modül olarak yazılmıştır; böylece hat hem okunabilir hem de yeniden kullanılabilirdir.

Hattın adımları:

1. **Veri Üretimi/Okuma** — Yapay (ama gerçekçi) batarya verisi üretilir veya hazır CSV okunur.
2. **Veri Temizleme** — Eksik değerler, aykırı ölçümler ve sensör gürültüsü giderilir.
3. **Özellik Mühendisliği** — İç direnç, kapasite ve sıcaklık değişim hızı gibi sağlık metrikleri türetilir.
4. **Görselleştirme** — Sonuçlar profesyonel grafiklerle raporlanır.

---

## 🗂️ Proje Yapısı

```text
battery_analysis/
├── data_generator.py        # Modül 0 — Yapay veri üreteci
├── module1_cleaning.py      # Modül 1 — Veri temizleme
├── module2_features.py      # Modül 2 — Özellik mühendisliği
├── module3_visualization.py # Modül 3 — Görselleştirme
├── main.py                  # Tüm boru hattını uçtan uca çalıştırır
├── data/                    # CSV çıktıları (otomatik oluşturulur)
│   ├── raw_battery_data.csv
│   ├── clean_battery_data.csv
│   ├── features_battery_data.csv
│   └── cycle_summary.csv
└── plots/                   # Grafik çıktıları (otomatik oluşturulur)
    ├── fig1_data_cleaning.png
    ├── fig2_features.png
    └── fig3_degradation.png
```

---

## 🚀 Kurulum ve Çalıştırma

**Gereksinim:** Python 3.10+ ve Matplotlib.

```bash
pip install matplotlib

# Windows PowerShell'de Türkçe karakterler için:
$env:PYTHONIOENCODING="utf-8"

python main.py
```

`main.py` tüm hattı sırayla çalıştırır; ara çıktılar `data/` klasörüne, grafikler `plots/` klasörüne yazılır.

---

## 🧹 Modül 1 — Veri Temizleme

**Girdi:** `data/raw_battery_data.csv`
Sütunlar: `time_s`, `cycle`, `voltage_V`, `current_A`, `temperature_C`

### 1. Eksik Değer (NaN) İşleme

| Strateji | Açıklama |
|----------|----------|
| `ffill` *(varsayılan)* | Boş değeri önceki geçerli ölçümle doldurur |
| `drop`  | NaN içeren satırı tamamen siler |

Anlık bir sensör kesintisi tüm sinyali yok etmemeli; bu yüzden varsayılan strateji `ffill`'dir.

### 2. Aykırı Değer (Outlier) Kaldırma

Fiziksel olarak imkânsız değerler filtrelenir:

| Sütun | Alt Sınır | Üst Sınır |
|-------|-----------|-----------|
| `voltage_V` | 0 V | 100 V |
| `current_A` | 0 A | 30 A |
| `temperature_C` | −20 °C | 100 °C |

### 3. Hareketli Ortalama (Moving Average)

```
SMA(n) = (x_{n-W+1} + ... + x_n) / W
```

- Pencere boyutu `W = 5` (ayarlanabilir)
- Ham değerler `_raw` son ekiyle korunur

---

## 🧪 Modül 2 — Özellik Mühendisliği

### 1. İç Direnç — R_int

```
R_int = |ΔV| / |ΔI|
```

- `|ΔI| < 0.05 A` ise ölçüm güvenilmez kabul edilir → `NaN`
- Yüksek R_int → yaşlanmış veya hasarlı batarya

### 2. Deşarj Kapasitesi — Coulomb Sayımı

```
Q(t) = ∫₀ᵗ I(τ) dτ        [As → Ah]
```

Yamuk (trapez) kuralı ile sayısal integrasyon:

```
ΔQ = (I_n + I_{n-1}) / 2 × Δt
```

Her döngü kendi içinde sıfırdan başlar.

### 3. Sıcaklık Değişim Hızı — dT/dt

Merkezi fark yöntemi (daha hassas):

```
dT/dt ≈ (T_{n+1} − T_{n-1}) / (t_{n+1} − t_{n-1})
```

`|dT/dt| > 2 °C/s` → termal kaçma (thermal runaway) riski.

---

## 📊 Örnek Çıktı — Döngü Özet Tablosu

| Döngü | V_min | V_max | Kapasite (Ah) | R_int (Ω) | T_ort (°C) |
|-------|-------|-------|---------------|-----------|------------|
| 1 | 3.09 | 4.13 | 0.1259 | 0.0802 | 31.60 |
| 2 | 3.14 | 4.12 | 0.1249 | 0.1248 | 32.64 |
| 3 | 3.17 | 4.12 | 0.1246 | 0.1213 | 33.60 |
| 4 | 3.20 | 4.11 | 0.1244 | 0.1092 | 34.59 |
| 5 | 3.24 | 4.13 | 0.1245 | 0.1419 | 35.70 |

**Gözlem:** Döngü sayısı arttıkça ortalama sıcaklık yükselir ve minimum voltaj artar — kapasitesini kaybeden batarya kesme voltajına daha erken ulaşır. Bu davranış, gerçek batarya degradasyonuyla örtüşür.

---

## 🖼️ Grafik Çıktıları

Çalıştırma sonunda `plots/` klasöründe üç grafik oluşur:

- `fig1_data_cleaning.png` — Ham ve temizlenmiş sinyalin karşılaştırması
- `fig2_features.png` — Türetilen sağlık metrikleri
- `fig3_degradation.png` — Döngüler boyunca kapasite kaybı (degradasyon)

---

## 🧱 Mimari Notu

Her sorumluluk ayrı bir modülde toplanmıştır (temizleme, özellik, görselleştirme). Ara çıktılar bağımsız CSV dosyaları olarak saklandığı için her aşama tek başına incelenebilir. Sayısal yöntemler (integrasyon, merkezi fark, hareketli ortalama) harici bir veri bilimi kütüphanesine bağımlı olmadan uygulanmıştır.
