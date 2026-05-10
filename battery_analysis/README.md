# Batarya Sağlığı Veri Analizi Projesi

Gerçek dünya batarya sensör verilerini işleyen iki modüllü analiz boru hattı.

## Proje Yapısı

```
battery_analysis/
├── data_generator.py       # Modül 0 — Yapay veri üreteci
├── module1_cleaning.py     # Modül 1 — Veri temizleme
├── module2_features.py     # Modül 2 — Özellik mühendisliği
├── module3_visualization.py# Modül 3 — Görselleştirme
├── main.py                 # Tüm boru hattını çalıştırır
├── data/                   # CSV çıktıları (otomatik oluşturulur)
│   ├── raw_battery_data.csv
│   ├── clean_battery_data.csv
│   ├── features_battery_data.csv
│   └── cycle_summary.csv
└── plots/                  # Grafik çıktıları (otomatik oluşturulur)
    ├── fig1_data_cleaning.png
    ├── fig2_features.png
    └── fig3_degradation.png
```

## Kurulum ve Çalıştırma

```bash
pip install matplotlib
$env:PYTHONIOENCODING="utf-8"   # Windows PowerShell
python main.py
```

---

## Modül 1 — Veri Temizleme (Data Cleaning)

**Girdi:** `data/raw_battery_data.csv`  
Sütunlar: `time_s`, `cycle`, `voltage_V`, `current_A`, `temperature_C`

### Adım 1 — NaN İşleme

İki strateji desteklenir:

| Strateji | Açıklama |
|----------|----------|
| `ffill` | Boş değeri önceki geçerli ölçümle doldurur |
| `drop`  | NaN içeren satırı tamamen siler |

Örneğin bir sensörün momentanlık kesintisi sinyali tamamen yok etmemeli; bu yüzden varsayılan `ffill`'dir.

### Adım 2 — Outlier Kaldırma

Fiziksel olarak imkânsız değerler silinir:

| Sütun | Alt Sınır | Üst Sınır |
|-------|-----------|-----------|
| `voltage_V` | 0 V | 100 V |
| `current_A` | 0 A | 30 A |
| `temperature_C` | −20 °C | 100 °C |

### Adım 3 — Moving Average (Hareketli Ortalama)

```
SMA(n) = (x_{n-W+1} + ... + x_n) / W
```

- Pencere boyutu `W = 5` (değiştirilebilir)
- Ham değerler `_raw` son ekiyle korunur

---

## Modül 2 — Özellik Mühendisliği (Feature Engineering)

### 1. İç Direnç — R_int

```
R_int = |ΔV| / |ΔI|
```

- Akım değişimi `|ΔI| < 0.05 A` ise güvenilmez → `NaN`
- Yüksek R_int → yaşlı veya hasar görmüş batarya

### 2. Deşarj Kapasitesi — Coulomb Counting

```
Q(t) = ∫₀ᵗ I(τ) dτ       [As → Ah]
```

Yamuk kuralı (trapezoidal) ile sayısal integrasyon:

```
ΔQ = (I_n + I_{n-1}) / 2 × Δt
```

Her döngü kendi içinde sıfırdan başlar.

### 3. Sıcaklık Değişim Hızı — dT/dt

Merkezi fark yöntemi (daha hassas):

```
dT/dt ≈ (T_{n+1} - T_{n-1}) / (t_{n+1} - t_{n-1})
```

`|dT/dt| > 2 °C/s` → termal kaçma (thermal runaway) riski.

---

## Çıktı Örnekleri

### Döngü Özet Tablosu

| Döngü | V_min | V_max | Kapasite (Ah) | R_int (Ω) | T_ort (°C) |
|-------|-------|-------|---------------|-----------|-----------|
| 1 | 3.09 | 4.13 | 0.1259 | 0.0802 | 31.60 |
| 2 | 3.14 | 4.12 | 0.1249 | 0.1248 | 32.64 |
| 3 | 3.17 | 4.12 | 0.1246 | 0.1213 | 33.60 |
| 4 | 3.20 | 4.11 | 0.1244 | 0.1092 | 34.59 |
| 5 | 3.24 | 4.13 | 0.1245 | 0.1419 | 35.70 |

**Gözlem:** Döngü arttıkça ortalama sıcaklık yükselir, minimum voltaj artar (kapasiteyi kaybeden batarya daha erken kesme voltajına ulaşır) — gerçek degradasyon davranışıyla örtüşür.
