from __future__ import annotations

import csv
import math
import os
from typing import Any

VOLTAGE_MIN     =   0.0
VOLTAGE_MAX     = 100.0
CURRENT_MIN     =   0.0
CURRENT_MAX     =  30.0
TEMPERATURE_MIN = -20.0
TEMPERATURE_MAX = 100.0

MA_WINDOW = 5

Row = dict[str, Any]


def load_csv(filepath: str) -> list[Row]:
    rows: list[Row] = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            row: Row = {}
            for key, val in raw.items():
                val = val.strip()
                if key == "cycle":
                    row[key] = int(val) if val else -1
                elif key in ("time_s", "voltage_V", "current_A", "temperature_C"):
                    try:
                        row[key] = float(val)
                    except ValueError:
                        row[key] = float("nan")
                else:
                    row[key] = val
            rows.append(row)
    return rows


def _is_nan(value: Any) -> bool:
    try:
        return math.isnan(float(value))
    except (TypeError, ValueError):
        return True


def handle_nan(
    rows: list[Row],
    numeric_cols: list[str],
    strategy: str = "ffill",
) -> tuple[list[Row], dict[str, int]]:
    stats: dict[str, int] = {col: 0 for col in numeric_cols}
    stats["rows_dropped"] = 0

    last_valid: dict[str, float] = {}

    cleaned: list[Row] = []
    for row in rows:
        has_nan = False
        for col in numeric_cols:
            if _is_nan(row.get(col)):
                stats[col] += 1
                has_nan = True
                if strategy == "ffill":
                    row[col] = last_valid.get(col, 0.0)
                else:
                    break

        if strategy == "drop" and has_nan:
            stats["rows_dropped"] += 1
            continue

        for col in numeric_cols:
            if not _is_nan(row.get(col)):
                last_valid[col] = float(row[col])

        cleaned.append(row)

    return cleaned, stats


def filter_outliers(rows: list[Row]) -> tuple[list[Row], int]:
    filtered: list[Row] = []
    removed = 0

    for row in rows:
        v = float(row.get("voltage_V", 0.0))
        i = float(row.get("current_A", 0.0))
        t = float(row.get("temperature_C", 0.0))

        if (
            VOLTAGE_MIN     <= v <= VOLTAGE_MAX     and
            CURRENT_MIN     <= i <= CURRENT_MAX     and
            TEMPERATURE_MIN <= t <= TEMPERATURE_MAX
        ):
            filtered.append(row)
        else:
            removed += 1

    return filtered, removed


def moving_average(values: list[float], window: int) -> list[float]:
    smoothed: list[float] = []
    for i, _ in enumerate(values):
        start = max(0, i - window + 1)
        window_vals = values[start : i + 1]
        smoothed.append(sum(window_vals) / len(window_vals))
    return smoothed


def smooth_data(rows: list[Row], cols: list[str], window: int = MA_WINDOW) -> list[Row]:
    for col in cols:
        raw_values = [float(row[col]) for row in rows]
        smoothed   = moving_average(raw_values, window)
        for row, smooth_val in zip(rows, smoothed):
            row[f"{col}_raw"] = row[col]
            row[col]          = smooth_val
    return rows


def clean_pipeline(
    input_path:   str,
    output_path:  str,
    nan_strategy: str = "ffill",
    ma_window:    int = MA_WINDOW,
) -> list[Row]:
    NUMERIC_COLS = ["voltage_V", "current_A", "temperature_C"]

    print("\n" + "═" * 60)
    print("  MODÜL 1: VERİ TEMİZLEME HATTI")
    print("═" * 60)

    rows = load_csv(input_path)
    print(f"\n[1/4] Yükleme      : {len(rows):>5} satır okundu  ← '{input_path}'")

    rows, nan_stats = handle_nan(rows, NUMERIC_COLS, strategy=nan_strategy)
    total_nan = sum(v for k, v in nan_stats.items() if k != "rows_dropped")
    print(f"[2/4] NaN İşleme   : {total_nan:>5} NaN bulundu  (strateji: '{nan_strategy}')")
    for col in NUMERIC_COLS:
        print(f"       └─ {col:<15}: {nan_stats[col]} NaN")
    if nan_strategy == "drop":
        print(f"       └─ Silinen satır : {nan_stats['rows_dropped']}")

    rows, removed = filter_outliers(rows)
    print(f"[3/4] Outlier      : {removed:>5} satır kaldırıldı (fiziksel sınır dışı)")
    print(f"       └─ Voltaj    : [{VOLTAGE_MIN}V, {VOLTAGE_MAX}V]")
    print(f"       └─ Akım      : [{CURRENT_MIN}A, {CURRENT_MAX}A]")
    print(f"       └─ Sıcaklık  : [{TEMPERATURE_MIN}°C, {TEMPERATURE_MAX}°C]")

    rows = smooth_data(rows, NUMERIC_COLS, window=ma_window)
    print(f"[4/4] Pürüzsüzleştirme : Moving Average (pencere={ma_window})")
    print(f"\n[✓]  Temiz veri   : {len(rows):>5} satır kaldı")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fieldnames = (
        ["time_s", "cycle"]
        + [f"{c}_raw" for c in NUMERIC_COLS]
        + NUMERIC_COLS
    )
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"[✓]  Kaydedildi   : '{output_path}'")
    print("═" * 60 + "\n")

    return rows


if __name__ == "__main__":
    clean_pipeline(
        input_path  ="data/raw_battery_data.csv",
        output_path ="data/clean_battery_data.csv",
        nan_strategy="ffill",
        ma_window   =MA_WINDOW,
    )
