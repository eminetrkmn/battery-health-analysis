from __future__ import annotations

import csv
import os
import math
from typing import Any

Row = dict[str, Any]


def _f(row: Row, key: str, default: float = 0.0) -> float:
    try:
        val = float(row[key])
        return val if not math.isnan(val) else default
    except (KeyError, TypeError, ValueError):
        return default


def compute_internal_resistance(rows: list[Row]) -> list[Row]:
    DELTA_I_MIN = 0.05
    rows[0]["internal_resistance_ohm"] = float("nan")

    for idx in range(1, len(rows)):
        delta_v = _f(rows[idx], "voltage_V") - _f(rows[idx - 1], "voltage_V")
        delta_i = _f(rows[idx], "current_A") - _f(rows[idx - 1], "current_A")

        if abs(delta_i) >= DELTA_I_MIN:
            r_int = abs(delta_v) / abs(delta_i)
            rows[idx]["internal_resistance_ohm"] = r_int if r_int <= 10.0 else float("nan")
        else:
            rows[idx]["internal_resistance_ohm"] = float("nan")

    return rows


def compute_coulomb_counting(rows: list[Row]) -> list[Row]:
    current_cycle = None
    cumulative_as = 0.0

    for idx, row in enumerate(rows):
        cycle = row.get("cycle", 1)

        if cycle != current_cycle:
            cumulative_as = 0.0
            current_cycle = cycle

        if idx == 0 or rows[idx - 1].get("cycle") != cycle:
            delta_q_as = 0.0
        else:
            i_curr     = _f(row,           "current_A")
            i_prev     = _f(rows[idx - 1], "current_A")
            t_curr     = _f(row,           "time_s")
            t_prev     = _f(rows[idx - 1], "time_s")
            delta_t    = t_curr - t_prev
            delta_q_as = 0.5 * (i_curr + i_prev) * delta_t

        cumulative_as += delta_q_as
        row["cumulative_capacity_Ah"] = round(cumulative_as / 3600.0, 6)

    return rows


def compute_temperature_rate(rows: list[Row]) -> list[Row]:
    n = len(rows)

    for idx in range(n):
        if idx == 0:
            dt = _f(rows[1], "time_s")        - _f(rows[0], "time_s")
            dT = _f(rows[1], "temperature_C") - _f(rows[0], "temperature_C")
        elif idx == n - 1:
            dt = _f(rows[n - 1], "time_s")        - _f(rows[n - 2], "time_s")
            dT = _f(rows[n - 1], "temperature_C") - _f(rows[n - 2], "temperature_C")
        else:
            dt = _f(rows[idx + 1], "time_s")        - _f(rows[idx - 1], "time_s")
            dT = _f(rows[idx + 1], "temperature_C") - _f(rows[idx - 1], "temperature_C")

        rows[idx]["temp_rate_C_per_s"] = round((dT / dt) if dt != 0 else 0.0, 6)

    return rows


def compute_cycle_summary(rows: list[Row]) -> list[dict]:
    from collections import defaultdict

    cycles: dict[int, list[Row]] = defaultdict(list)
    for row in rows:
        cycles[row.get("cycle", 0)].append(row)

    summaries = []
    for cycle_id in sorted(cycles.keys()):
        cycle_rows = cycles[cycle_id]

        voltages   = [_f(r, "voltage_V")              for r in cycle_rows]
        r_ints     = [_f(r, "internal_resistance_ohm") for r in cycle_rows
                      if not math.isnan(_f(r, "internal_resistance_ohm", float("nan")))]
        temps      = [_f(r, "temperature_C")           for r in cycle_rows]
        temp_rates = [abs(_f(r, "temp_rate_C_per_s"))  for r in cycle_rows]
        max_cap    = max(_f(r, "cumulative_capacity_Ah") for r in cycle_rows)

        summaries.append({
            "cycle":             cycle_id,
            "n_samples":         len(cycle_rows),
            "voltage_min_V":     round(min(voltages), 4),
            "voltage_max_V":     round(max(voltages), 4),
            "voltage_mean_V":    round(sum(voltages) / len(voltages), 4),
            "discharge_cap_Ah":  round(max_cap, 4),
            "r_int_mean_ohm":    round(sum(r_ints) / len(r_ints), 6) if r_ints else float("nan"),
            "temp_mean_C":       round(sum(temps) / len(temps), 4),
            "temp_rate_max_C_s": round(max(temp_rates), 6),
        })

    return summaries


def feature_pipeline(
    rows:          list[Row],
    features_path: str,
    summary_path:  str,
) -> tuple[list[Row], list[dict]]:
    print("\n" + "═" * 60)
    print("  MODÜL 2: ÖZELLİK MÜHENDİSLİĞİ")
    print("═" * 60)

    rows = compute_internal_resistance(rows)
    print("[1/3] İç Direnç         : R_int = ΔV / ΔI  [Ω]  ✓")

    rows = compute_coulomb_counting(rows)
    print("[2/3] Coulomb Counting  : Q = ∫ I dt        [Ah] ✓")

    rows = compute_temperature_rate(rows)
    print("[3/3] Sıcaklık Değişimi : dT/dt             [°C/s] ✓")

    summaries = compute_cycle_summary(rows)

    print("\n  ┌─ Döngü Bazında Özet ─────────────────────────────────────────┐")
    header = (
        f"  │ {'Döngü':>5} │ {'V_min(V)':>8} │ {'V_max(V)':>8} │ "
        f"{'Kap(Ah)':>7} │ {'R_int(Ω)':>9} │ {'T_ort(°C)':>9} │ {'dT_max':>7} │"
    )
    print(header)
    print("  ├" + "─" * (len(header) - 4) + "┤")
    for s in summaries:
        r_str = f"{s['r_int_mean_ohm']:.4f}" if not (isinstance(s['r_int_mean_ohm'], float) and math.isnan(s['r_int_mean_ohm'])) else "  N/A  "
        print(
            f"  │ {s['cycle']:>5} │ {s['voltage_min_V']:>8.4f} │ {s['voltage_max_V']:>8.4f} │ "
            f"{s['discharge_cap_Ah']:>7.4f} │ {r_str:>9} │ {s['temp_mean_C']:>9.4f} │ "
            f"{s['temp_rate_max_C_s']:>7.4f} │"
        )
    print("  └" + "─" * (len(header) - 4) + "┘")

    os.makedirs(os.path.dirname(features_path), exist_ok=True)

    feature_cols = [
        "time_s", "cycle",
        "voltage_V", "current_A", "temperature_C",
        "internal_resistance_ohm", "cumulative_capacity_Ah", "temp_rate_C_per_s",
    ]
    with open(features_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=feature_cols, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n[✓]  Özellikli veri : '{features_path}'")

    summary_cols = [
        "cycle", "n_samples",
        "voltage_min_V", "voltage_max_V", "voltage_mean_V",
        "discharge_cap_Ah", "r_int_mean_ohm",
        "temp_mean_C", "temp_rate_max_C_s",
    ]
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=summary_cols)
        writer.writeheader()
        writer.writerows(summaries)
    print(f"[✓]  Döngü özeti   : '{summary_path}'")
    print("═" * 60 + "\n")

    return rows, summaries


if __name__ == "__main__":
    from module1_cleaning import clean_pipeline

    clean_rows = clean_pipeline(
        input_path  ="data/raw_battery_data.csv",
        output_path ="data/clean_battery_data.csv",
    )
    feature_pipeline(
        rows          =clean_rows,
        features_path ="data/features_battery_data.csv",
        summary_path  ="data/cycle_summary.csv",
    )
