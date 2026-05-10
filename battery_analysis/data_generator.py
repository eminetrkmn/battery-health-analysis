import random
import math
import csv
import os

random.seed(42)

NUM_CYCLES        = 5
SAMPLES_PER_CYCLE = 200
DT                = 1.0
INITIAL_VOLTAGE   = 4.2
CUTOFF_VOLTAGE    = 3.0
NOMINAL_CURRENT   = 2.5
AMBIENT_TEMP      = 25.0

DEGRADATION_RATE    = 0.03

NAN_PROBABILITY     = 0.04
OUTLIER_PROBABILITY = 0.03


def _add_noise(value: float, sigma: float) -> float:
    u1 = random.random()
    u2 = random.random()
    while u1 == 0:
        u1 = random.random()
    z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2 * math.pi * u2)
    return value + sigma * z


def _simulate_voltage(t_normalized: float, cycle_idx: int) -> float:
    degradation   = 1.0 - cycle_idx * DEGRADATION_RATE
    voltage_range = (INITIAL_VOLTAGE - CUTOFF_VOLTAGE) * degradation
    exponent      = 5.0 * (t_normalized - 0.5)
    sigmoid       = 1.0 / (1.0 + math.exp(-exponent))
    voltage       = INITIAL_VOLTAGE - voltage_range * sigmoid
    return _add_noise(voltage, sigma=0.02)


def _simulate_current(t_normalized: float) -> float:
    if t_normalized < 0.80:
        current = NOMINAL_CURRENT
    else:
        current = NOMINAL_CURRENT * (1.0 - (t_normalized - 0.80) / 0.20)
    return _add_noise(current, sigma=0.05)


def _simulate_temperature(t_normalized: float, cycle_idx: int) -> float:
    heat_factor = 4.0 * t_normalized * (1.0 - t_normalized)
    max_rise    = 10.0 + cycle_idx * 1.5
    temperature = AMBIENT_TEMP + max_rise * heat_factor
    return _add_noise(temperature, sigma=0.3)


def generate_battery_data(output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    rows        = []
    global_time = 0.0

    for cycle in range(NUM_CYCLES):
        for sample in range(SAMPLES_PER_CYCLE):
            t_norm      = sample / (SAMPLES_PER_CYCLE - 1)
            voltage     = _simulate_voltage(t_norm, cycle)
            current     = _simulate_current(t_norm)
            temperature = _simulate_temperature(t_norm, cycle)

            if random.random() < NAN_PROBABILITY:
                col = random.choice(["voltage", "current", "temperature"])
                if col == "voltage":
                    voltage = float("nan")
                elif col == "current":
                    current = float("nan")
                else:
                    temperature = float("nan")

            if random.random() < OUTLIER_PROBABILITY:
                col = random.choice(["voltage", "current", "temperature"])
                if col == "voltage":
                    voltage = random.choice([-0.5, 150.0])
                elif col == "current":
                    current = random.choice([-5.0, 50.0])
                else:
                    temperature = random.choice([-40.0, 200.0])

            rows.append({
                "time_s":        round(global_time, 2),
                "cycle":         cycle + 1,
                "voltage_V":     round(voltage, 4)     if not (isinstance(voltage, float)     and math.isnan(voltage))     else "",
                "current_A":     round(current, 4)     if not (isinstance(current, float)     and math.isnan(current))     else "",
                "temperature_C": round(temperature, 4) if not (isinstance(temperature, float) and math.isnan(temperature)) else "",
            })

            global_time += DT

    fieldnames = ["time_s", "cycle", "voltage_V", "current_A", "temperature_C"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    total     = NUM_CYCLES * SAMPLES_PER_CYCLE
    nan_count = sum(1 for r in rows if r["voltage_V"] == "" or r["current_A"] == "" or r["temperature_C"] == "")
    print(f"[DataGenerator] {total} satır üretildi → '{output_path}'")
    print(f"[DataGenerator] Tahmini NaN satır sayısı : ~{nan_count}")


if __name__ == "__main__":
    generate_battery_data("data/raw_battery_data.csv")
