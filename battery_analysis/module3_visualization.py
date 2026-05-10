from __future__ import annotations

import math
import os
from typing import Any

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    from matplotlib.lines import Line2D
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

Row = dict[str, Any]

CYCLE_COLORS = ["#4361EE", "#F72585", "#4CC9F0", "#7209B7", "#3A0CA3"]


def _f(row: Row, key: str, default: float = 0.0) -> float:
    try:
        val = float(row[key])
        return val if not math.isnan(val) else default
    except (KeyError, TypeError, ValueError):
        return default


def _split_by_cycle(rows: list[Row]) -> dict[int, list[Row]]:
    from collections import defaultdict
    groups: dict[int, list[Row]] = defaultdict(list)
    for row in rows:
        groups[row.get("cycle", 0)].append(row)
    return dict(sorted(groups.items()))


def _safe_values(rows: list[Row], key: str) -> list[float]:
    out = []
    for r in rows:
        try:
            val = float(r[key])
            out.append(val if not math.isnan(val) else 0.0)
        except (KeyError, TypeError, ValueError):
            out.append(0.0)
    return out


def plot_cleaning(rows: list[Row], out_dir: str) -> str:
    cycles = _split_by_cycle(rows)

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=False)
    fig.suptitle(
        "Modül 1 — Veri Temizleme: Ham vs Pürüzsüz Sinyal",
        fontsize=15, fontweight="bold", y=1.01
    )

    legend_handles = []

    for idx, (cycle_id, c_rows) in enumerate(cycles.items()):
        color = CYCLE_COLORS[idx % len(CYCLE_COLORS)]
        times = _safe_values(c_rows, "time_s")

        if "voltage_V_raw" in c_rows[0]:
            axes[0].plot(times, _safe_values(c_rows, "voltage_V_raw"),
                         color=color, alpha=0.25, linewidth=0.8)
        axes[0].plot(times, _safe_values(c_rows, "voltage_V"),
                     color=color, linewidth=1.8, label=f"Döngü {cycle_id}")

        if "current_A_raw" in c_rows[0]:
            axes[1].plot(times, _safe_values(c_rows, "current_A_raw"),
                         color=color, alpha=0.25, linewidth=0.8)
        axes[1].plot(times, _safe_values(c_rows, "current_A"),
                     color=color, linewidth=1.8)

        legend_handles.append(Line2D([0], [0], color=color, linewidth=2,
                                     label=f"Döngü {cycle_id}"))

    legend_handles.append(
        Line2D([0], [0], color="gray", alpha=0.4, linewidth=1.5,
               linestyle="-", label="Ham (gürültülü)")
    )

    for ax, ylabel, title in zip(
        axes,
        ["Voltaj (V)", "Akım (A)"],
        ["Voltaj Profili — Pürüzsüzleştirme Etkisi", "Akım Profili — CC-CV Deşarj"],
    ):
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(title, fontsize=11, pad=6)
        ax.grid(True, alpha=0.3, linestyle="--")
        ax.set_facecolor("#F8F9FA")

    axes[1].set_xlabel("Zaman (s)", fontsize=11)
    fig.legend(handles=legend_handles, loc="upper right",
               bbox_to_anchor=(1.13, 0.95), framealpha=0.9)

    plt.tight_layout()
    path = os.path.join(out_dir, "fig1_data_cleaning.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_features(rows: list[Row], out_dir: str) -> str:
    cycles = _split_by_cycle(rows)

    fig = plt.figure(figsize=(16, 11))
    gs  = gridspec.GridSpec(3, 1, hspace=0.45)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    ax3 = fig.add_subplot(gs[2])

    fig.suptitle(
        "Modül 2 — Özellik Mühendisliği: Türetilmiş Metrikler",
        fontsize=15, fontweight="bold"
    )

    for idx, (cycle_id, c_rows) in enumerate(cycles.items()):
        color = CYCLE_COLORS[idx % len(CYCLE_COLORS)]
        times = _safe_values(c_rows, "time_s")
        label = f"Döngü {cycle_id}"

        r_vals = []
        for r in c_rows:
            try:
                val = float(r.get("internal_resistance_ohm", float("nan")))
                r_vals.append(val if not math.isnan(val) else float("nan"))
            except (TypeError, ValueError):
                r_vals.append(float("nan"))

        valid_t = [t for t, v in zip(times, r_vals) if not math.isnan(v)]
        valid_r = [v for v in r_vals if not math.isnan(v)]
        if valid_t:
            ax1.scatter(valid_t, valid_r, s=4, color=color, alpha=0.6, label=label)

        cap = _safe_values(c_rows, "cumulative_capacity_Ah")
        ax2.plot(times, cap, color=color, linewidth=2, label=label)
        ax2.fill_between(times, 0, cap, alpha=0.12, color=color)

        dTdt = _safe_values(c_rows, "temp_rate_C_per_s")
        ax3.plot(times, dTdt, color=color, linewidth=1.4, alpha=0.85, label=label)

    ax3.axhline(y=2.0,  color="red", linestyle="--", alpha=0.7, linewidth=1.2,
                label="Termal Kaçma Eşiği (2 °C/s)")
    ax3.axhline(y=-2.0, color="red", linestyle="--", alpha=0.7, linewidth=1.2)

    for ax, ylabel, title in [
        (ax1, "İç Direnç (Ω)", "İç Direnç — R = ΔV/ΔI"),
        (ax2, "Kapasite (Ah)",  "Birikimli Kapasite — Coulomb Counting"),
        (ax3, "dT/dt (°C/s)",   "Sıcaklık Değişim Hızı"),
    ]:
        ax.set_ylabel(ylabel, fontsize=10)
        ax.set_title(title, fontsize=11, pad=5)
        ax.grid(True, alpha=0.3, linestyle="--")
        ax.set_facecolor("#F8F9FA")
        ax.legend(fontsize=8, loc="upper right")

    ax3.set_xlabel("Zaman (s)", fontsize=11)

    path = os.path.join(out_dir, "fig2_features.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_degradation(rows: list[Row], summaries: list[dict], out_dir: str) -> str:
    cycles = _split_by_cycle(rows)

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle(
        "Batarya Degradasyon Analizi — Döngüler Arası Karşılaştırma",
        fontsize=15, fontweight="bold"
    )

    ax = axes[0]
    for idx, (cycle_id, c_rows) in enumerate(cycles.items()):
        color = CYCLE_COLORS[idx % len(CYCLE_COLORS)]
        ax.plot(_safe_values(c_rows, "cumulative_capacity_Ah"),
                _safe_values(c_rows, "voltage_V"),
                color=color, linewidth=2.2, label=f"Döngü {cycle_id}")
    ax.set_xlabel("Kapasite (Ah)", fontsize=11)
    ax.set_ylabel("Voltaj (V)", fontsize=11)
    ax.set_title("Voltaj–Kapasite (V-Q) Eğrisi", fontsize=12)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.set_facecolor("#F8F9FA")

    ax = axes[1]
    cycle_ids = [s["cycle"] for s in summaries]
    r_means   = [s["r_int_mean_ohm"] for s in summaries]
    r_valid   = [(c, r) for c, r in zip(cycle_ids, r_means)
                 if not (isinstance(r, float) and math.isnan(r))]
    if r_valid:
        c_ids, r_vals = zip(*r_valid)
        bar_colors = [CYCLE_COLORS[i % len(CYCLE_COLORS)] for i in range(len(c_ids))]
        bars = ax.bar([f"D{c}" for c in c_ids], r_vals,
                      color=bar_colors, edgecolor="white", linewidth=1.2, width=0.55)
        for bar, val in zip(bars, r_vals):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.002,
                    f"{val:.4f} Ω", ha="center", va="bottom", fontsize=9)
    ax.set_xlabel("Döngü", fontsize=11)
    ax.set_ylabel("Ortalama İç Direnç (Ω)", fontsize=11)
    ax.set_title("Döngüye Göre İç Direnç", fontsize=12)
    ax.grid(True, alpha=0.3, linestyle="--", axis="y")
    ax.set_facecolor("#F8F9FA")

    ax = axes[2]
    caps = [s["discharge_cap_Ah"] for s in summaries]
    ax.plot(cycle_ids, caps, "o-", color="#4361EE", linewidth=2.5,
            markersize=9, markerfacecolor="white", markeredgewidth=2.5,
            markeredgecolor="#4361EE", zorder=5)
    ax.fill_between(cycle_ids, caps, alpha=0.12, color="#4361EE")
    if caps:
        ax.axhline(y=caps[0], color="#F72585", linestyle="--", alpha=0.6,
                   linewidth=1.2, label=f"İlk kapasite: {caps[0]:.3f} Ah")
    for c, cap in zip(cycle_ids, caps):
        ax.annotate(f"{cap:.3f} Ah", (c, cap),
                    textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=9, color="#4361EE")
    ax.set_xlabel("Döngü Numarası", fontsize=11)
    ax.set_ylabel("Deşarj Kapasitesi (Ah)", fontsize=11)
    ax.set_title("Kapasite Degradasyonu", fontsize=12)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.set_facecolor("#F8F9FA")

    plt.tight_layout()
    path = os.path.join(out_dir, "fig3_degradation.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def visualize_all(rows: list[Row], summaries: list[dict], out_dir: str = "plots") -> None:
    if not HAS_MPL:
        print("[Visualization] matplotlib kurulu değil. Atlanıyor.")
        return

    os.makedirs(out_dir, exist_ok=True)

    p1 = plot_cleaning(rows, out_dir)
    print(f"  ✓ Şekil 1 kaydedildi : '{p1}'")

    p2 = plot_features(rows, out_dir)
    print(f"  ✓ Şekil 2 kaydedildi : '{p2}'")

    p3 = plot_degradation(rows, summaries, out_dir)
    print(f"  ✓ Şekil 3 kaydedildi : '{p3}'")


if __name__ == "__main__":
    from module1_cleaning import clean_pipeline
    from module2_features  import feature_pipeline

    rows = clean_pipeline(
        input_path ="data/raw_battery_data.csv",
        output_path="data/clean_battery_data.csv",
    )
    rows, summaries = feature_pipeline(
        rows          =rows,
        features_path ="data/features_battery_data.csv",
        summary_path  ="data/cycle_summary.csv",
    )
    visualize_all(rows, summaries)
