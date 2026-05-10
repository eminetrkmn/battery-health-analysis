import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_generator   import generate_battery_data
from module1_cleaning import clean_pipeline
from module2_features import feature_pipeline

RAW_CSV      = "data/raw_battery_data.csv"
CLEAN_CSV    = "data/clean_battery_data.csv"
FEATURES_CSV = "data/features_battery_data.csv"
SUMMARY_CSV  = "data/cycle_summary.csv"


def main() -> None:
    print("\n" + "╔" + "═" * 58 + "╗")
    print("║   BATARYA SAĞLIĞI VERİ ANALİZİ — TAM BORU HATTI        ║")
    print("╚" + "═" * 58 + "╝")

    print("\n[ ADIM 0 ] Yapay batarya verisi oluşturuluyor...")
    generate_battery_data(RAW_CSV)

    print("\n[ ADIM 1 ] Veri temizleme hattı çalışıyor...")
    clean_rows = clean_pipeline(
        input_path  =RAW_CSV,
        output_path =CLEAN_CSV,
        nan_strategy="ffill",
        ma_window   =5,
    )

    print("\n[ ADIM 2 ] Özellik mühendisliği hattı çalışıyor...")
    feature_rows, cycle_summaries = feature_pipeline(
        rows          =clean_rows,
        features_path =FEATURES_CSV,
        summary_path  =SUMMARY_CSV,
    )

    try:
        from module3_visualization import visualize_all
        print("\n[ ADIM 3 ] Grafikler oluşturuluyor...")
        visualize_all(feature_rows, cycle_summaries)
    except ImportError:
        print("\n[ ADIM 3 ] matplotlib bulunamadı — görselleştirme atlandı.")
        print("           Kurmak için: pip install matplotlib")
    except Exception as exc:
        print(f"\n[ ADIM 3 ] Görselleştirme hatası: {exc}")

    print("\n" + "╔" + "═" * 58 + "╗")
    print("║   BORU HATTI TAMAMLANDI                                  ║")
    print("╠" + "═" * 58 + "╣")
    print(f"║  Ham veri      : {RAW_CSV:<38} ║")
    print(f"║  Temiz veri    : {CLEAN_CSV:<38} ║")
    print(f"║  Özellikler    : {FEATURES_CSV:<38} ║")
    print(f"║  Döngü özeti   : {SUMMARY_CSV:<38} ║")
    print("╚" + "═" * 58 + "╝\n")


if __name__ == "__main__":
    main()
