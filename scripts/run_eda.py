"""
SolarCast AI - Exploratory Data Analysis Script
================================================
Generates comprehensive EDA visualizations and statistics for the solar power dataset.

Usage:
    python scripts/run_eda.py

Outputs saved to: ml/evaluation/reports/eda/
"""

import logging
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import seaborn as sns

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ml.preprocessing.ingestion import load_and_prepare
from ml.preprocessing.validation import generate_validation_report
from ml.preprocessing.cleaning import clean_dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

EDA_OUTPUT_DIR = PROJECT_ROOT / "ml" / "evaluation" / "reports" / "eda"
PROCESSED_DIR = PROJECT_ROOT / "ml" / "data" / "processed"


def setup_plot_style() -> None:
    """Configure matplotlib/seaborn for clean, professional visualizations."""
    plt.style.use("seaborn-v0_8-whitegrid")
    sns.set_palette("husl")
    plt.rcParams.update({
        "figure.figsize": (12, 6),
        "figure.dpi": 150,
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.labelsize": 12,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.2,
    })


def find_raw_csv() -> Path:
    """Find the raw CSV file in the data directory."""
    raw_dir = PROJECT_ROOT / "ml" / "data" / "raw"
    csv_files = list(raw_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(
            f"No CSV files found in {raw_dir}. "
            "Run 'python scripts/download_data.py' first."
        )
    # Prefer files with 'renewable' in the name
    for f in csv_files:
        if "renew" in f.name.lower():
            return f
    return csv_files[0]


def plot_generation_distribution(df: pd.DataFrame, target_col: str, output_dir: Path) -> None:
    """Plot distribution of solar energy generation."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Histogram
    axes[0].hist(df[target_col].dropna(), bins=80, edgecolor="white", alpha=0.8, color="#2196F3")
    axes[0].set_title("Solar Energy Generation Distribution")
    axes[0].set_xlabel("Energy (Wh per 15-min interval)")
    axes[0].set_ylabel("Frequency")
    axes[0].axvline(df[target_col].mean(), color="red", linestyle="--", label=f"Mean: {df[target_col].mean():.1f} Wh")
    axes[0].axvline(df[target_col].median(), color="orange", linestyle="--", label=f"Median: {df[target_col].median():.1f} Wh")
    axes[0].legend()

    # Box plot
    daytime = df[df[target_col] > 0][target_col]
    axes[1].boxplot([df[target_col].dropna(), daytime], labels=["All Hours", "Daytime Only"])
    axes[1].set_title("Generation Box Plot")
    axes[1].set_ylabel("Energy (Wh)")

    plt.tight_layout()
    plt.savefig(output_dir / "01_generation_distribution.png")
    plt.close(fig)
    logger.info("Saved: generation distribution plot")


def plot_hourly_trends(df: pd.DataFrame, target_col: str, output_dir: Path) -> None:
    """Plot average generation by hour of day."""
    df_copy = df.copy()
    df_copy["hour"] = df_copy.index.hour

    hourly_stats = df_copy.groupby("hour")[target_col].agg(["mean", "std", "median"])

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(hourly_stats.index, hourly_stats["mean"], "o-", color="#FF9800", linewidth=2, label="Mean")
    ax.plot(hourly_stats.index, hourly_stats["median"], "s--", color="#4CAF50", linewidth=2, label="Median")
    ax.fill_between(
        hourly_stats.index,
        hourly_stats["mean"] - hourly_stats["std"],
        hourly_stats["mean"] + hourly_stats["std"],
        alpha=0.2, color="#FF9800", label="±1 Std Dev"
    )
    ax.set_title("Average Solar Generation by Hour of Day")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Energy (Wh per 15-min interval)")
    ax.set_xticks(range(24))
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.savefig(output_dir / "02_hourly_trends.png")
    plt.close(fig)
    logger.info("Saved: hourly trends plot")


def plot_daily_monthly_trends(df: pd.DataFrame, target_col: str, output_dir: Path) -> None:
    """Plot daily and monthly generation trends."""
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))

    # Daily total generation
    daily = df[target_col].resample("D").sum() / 1000  # Convert Wh to kWh
    axes[0].plot(daily.index, daily.values, linewidth=0.8, color="#2196F3", alpha=0.7)
    # Add 30-day rolling average
    rolling_30 = daily.rolling(30, center=True).mean()
    axes[0].plot(rolling_30.index, rolling_30.values, linewidth=2, color="#F44336", label="30-day Rolling Mean")
    axes[0].set_title("Daily Total Solar Generation")
    axes[0].set_ylabel("Energy (kWh)")
    axes[0].legend()
    axes[0].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    axes[0].xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(axes[0].xaxis.get_majorticklabels(), rotation=45)

    # Monthly total generation
    monthly = df[target_col].resample("ME").sum() / 1000  # kWh
    bars = axes[1].bar(range(len(monthly)), monthly.values, color="#4CAF50", alpha=0.8)
    axes[1].set_title("Monthly Total Solar Generation")
    axes[1].set_ylabel("Energy (kWh)")
    # Label every 3rd month
    tick_positions = range(0, len(monthly), 3)
    tick_labels = [monthly.index[i].strftime("%Y-%m") for i in tick_positions if i < len(monthly)]
    axes[1].set_xticks(list(tick_positions)[:len(tick_labels)])
    axes[1].set_xticklabels(tick_labels, rotation=45)

    plt.tight_layout()
    plt.savefig(output_dir / "03_daily_monthly_trends.png")
    plt.close(fig)
    logger.info("Saved: daily and monthly trends plot")


def plot_seasonal_patterns(df: pd.DataFrame, target_col: str, output_dir: Path) -> None:
    """Plot seasonal generation patterns."""
    df_copy = df.copy()
    df_copy["month"] = df_copy.index.month
    df_copy["hour"] = df_copy.index.hour

    month_names = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
                   7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # Monthly box plot
    monthly_data = [df_copy[df_copy["month"] == m][target_col].dropna() for m in range(1, 13)]
    bp = axes[0].boxplot(monthly_data, labels=[month_names[m] for m in range(1, 13)], patch_artist=True)
    colors = plt.cm.RdYlGn(np.linspace(0.2, 0.8, 12))
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
    axes[0].set_title("Solar Generation by Month")
    axes[0].set_ylabel("Energy (Wh)")
    axes[0].tick_params(axis="x", rotation=45)

    # Seasonal hourly heatmap
    pivot = df_copy.groupby(["month", "hour"])[target_col].mean().unstack(level=0)
    pivot.columns = [month_names[m] for m in pivot.columns]
    sns.heatmap(pivot, ax=axes[1], cmap="YlOrRd", cbar_kws={"label": "Avg Energy (Wh)"})
    axes[1].set_title("Average Generation: Hour × Month Heatmap")
    axes[1].set_ylabel("Hour of Day")
    axes[1].set_xlabel("Month")

    plt.tight_layout()
    plt.savefig(output_dir / "04_seasonal_patterns.png")
    plt.close(fig)
    logger.info("Saved: seasonal patterns plot")


def plot_weather_vs_generation(df: pd.DataFrame, target_col: str, output_dir: Path) -> None:
    """Plot weather features against generation."""
    # Identify available weather columns
    weather_candidates = {
        "ghi": "GHI (W/m²)",
        "temperature": "Temperature (°C)",
        "humidity": "Humidity (%)",
        "ambient_temperature": "Ambient Temperature (°C)",
        "irradiation": "Irradiation",
    }

    available = {col: label for col, label in weather_candidates.items() if col in df.columns}

    if not available:
        logger.warning("No recognized weather columns found for weather vs generation plot.")
        return

    n_cols = min(len(available), 3)
    n_rows = (len(available) + n_cols - 1) // n_cols
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 5 * n_rows))
    if n_rows * n_cols == 1:
        axes = np.array([axes])
    axes = axes.flatten()

    daytime = df[df[target_col] > 0].copy()

    for idx, (col, label) in enumerate(available.items()):
        if idx >= len(axes):
            break
        # Subsample for scatter plot performance
        sample = daytime.sample(n=min(5000, len(daytime)), random_state=42)
        axes[idx].scatter(
            sample[col], sample[target_col],
            alpha=0.3, s=8, color="#1976D2"
        )
        axes[idx].set_xlabel(label)
        axes[idx].set_ylabel("Energy (Wh)")
        axes[idx].set_title(f"Generation vs {label}")

        # Add correlation coefficient
        valid = daytime[[col, target_col]].dropna()
        if len(valid) > 10:
            corr = valid[col].corr(valid[target_col])
            axes[idx].annotate(f"r = {corr:.3f}", xy=(0.05, 0.95),
                             xycoords="axes fraction", fontsize=12,
                             fontweight="bold", color="red")

    # Hide unused axes
    for idx in range(len(available), len(axes)):
        axes[idx].set_visible(False)

    plt.suptitle("Weather Features vs Solar Generation (Daytime Only)", fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig(output_dir / "05_weather_vs_generation.png")
    plt.close(fig)
    logger.info("Saved: weather vs generation plot")


def plot_correlation_matrix(df: pd.DataFrame, output_dir: Path) -> None:
    """Plot correlation matrix for numeric columns."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if len(numeric_cols) < 2:
        logger.warning("Not enough numeric columns for correlation matrix.")
        return

    corr_matrix = df[numeric_cols].corr()

    fig, ax = plt.subplots(figsize=(12, 10))
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
    sns.heatmap(
        corr_matrix, mask=mask, annot=True, fmt=".2f",
        cmap="RdBu_r", center=0, square=True, ax=ax,
        cbar_kws={"label": "Correlation Coefficient"},
        linewidths=0.5
    )
    ax.set_title("Feature Correlation Matrix")
    plt.tight_layout()
    plt.savefig(output_dir / "06_correlation_matrix.png")
    plt.close(fig)
    logger.info("Saved: correlation matrix plot")


def plot_missing_value_analysis(df: pd.DataFrame, output_dir: Path) -> None:
    """Plot missing value analysis."""
    missing = df.isnull().sum()
    missing_pct = (missing / len(df)) * 100

    # Only show columns with missing values (or all if none)
    has_missing = missing_pct[missing_pct > 0].sort_values(ascending=False)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    if len(has_missing) > 0:
        axes[0].barh(has_missing.index, has_missing.values, color="#F44336", alpha=0.8)
        axes[0].set_xlabel("Missing (%)")
        axes[0].set_title("Missing Values by Column")
        for i, v in enumerate(has_missing.values):
            axes[0].text(v + 0.1, i, f"{v:.2f}%", va="center", fontsize=9)
    else:
        axes[0].text(0.5, 0.5, "No missing values!", transform=axes[0].transAxes,
                    ha="center", va="center", fontsize=16, color="green")
        axes[0].set_title("Missing Values by Column")

    # Missing values over time (monthly)
    monthly_missing = df.isnull().resample("ME").mean() * 100
    if monthly_missing.shape[1] > 0:
        cols_to_plot = monthly_missing.columns[:5]  # Top 5
        for col in cols_to_plot:
            if monthly_missing[col].sum() > 0:
                axes[1].plot(monthly_missing.index, monthly_missing[col], label=col, linewidth=1.5)
        axes[1].set_title("Missing Values Over Time (Monthly %)")
        axes[1].set_ylabel("Missing (%)")
        axes[1].legend(fontsize=8)
        axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=45)
    else:
        axes[1].text(0.5, 0.5, "No temporal missing pattern", transform=axes[1].transAxes,
                    ha="center", va="center", fontsize=14)

    plt.tight_layout()
    plt.savefig(output_dir / "07_missing_values.png")
    plt.close(fig)
    logger.info("Saved: missing value analysis plot")


def plot_daytime_nighttime(df: pd.DataFrame, target_col: str, output_dir: Path) -> None:
    """Analyze daytime vs nighttime generation patterns."""
    df_copy = df.copy()
    df_copy["hour"] = df_copy.index.hour

    # Use GHI to define daytime if available
    ghi_col = None
    for candidate in ["ghi", "irradiation", "global_horizontal_irradiance"]:
        if candidate in df_copy.columns:
            ghi_col = candidate
            break

    if ghi_col:
        df_copy["is_daytime"] = df_copy[ghi_col] > 0
    else:
        # Fallback: approximate daytime as 6am-7pm
        df_copy["is_daytime"] = df_copy["hour"].between(6, 18)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    # Pie chart: daytime vs nighttime records
    day_count = df_copy["is_daytime"].sum()
    night_count = len(df_copy) - day_count
    axes[0].pie([day_count, night_count], labels=["Daytime", "Nighttime"],
               autopct="%1.1f%%", colors=["#FFC107", "#3F51B5"], startangle=90)
    axes[0].set_title("Records: Daytime vs Nighttime")

    # Generation comparison
    day_gen = df_copy[df_copy["is_daytime"]][target_col]
    night_gen = df_copy[~df_copy["is_daytime"]][target_col]
    axes[1].boxplot([day_gen.dropna(), night_gen.dropna()],
                   labels=["Daytime", "Nighttime"])
    axes[1].set_title("Generation: Daytime vs Nighttime")
    axes[1].set_ylabel("Energy (Wh)")

    # Average generation by hour (daytime highlighted)
    hourly_mean = df_copy.groupby("hour")[target_col].mean()
    colors_h = ["#FFC107" if 6 <= h <= 18 else "#3F51B5" for h in range(24)]
    axes[2].bar(range(24), hourly_mean.values, color=colors_h, alpha=0.8)
    axes[2].set_title("Average Generation by Hour")
    axes[2].set_xlabel("Hour")
    axes[2].set_ylabel("Avg Energy (Wh)")
    axes[2].set_xticks(range(0, 24, 2))

    plt.tight_layout()
    plt.savefig(output_dir / "08_daytime_nighttime.png")
    plt.close(fig)
    logger.info("Saved: daytime/nighttime analysis plot")


def generate_summary_statistics(df: pd.DataFrame, target_col: str, output_dir: Path) -> dict:
    """Generate and save comprehensive summary statistics."""
    stats = {
        "dataset_shape": {"rows": len(df), "columns": len(df.columns)},
        "time_range": {
            "start": str(df.index.min()),
            "end": str(df.index.max()),
            "duration_days": (df.index.max() - df.index.min()).days,
        },
        "target_statistics": {
            "mean_wh": float(df[target_col].mean()),
            "median_wh": float(df[target_col].median()),
            "std_wh": float(df[target_col].std()),
            "min_wh": float(df[target_col].min()),
            "max_wh": float(df[target_col].max()),
            "zero_percentage": float((df[target_col] == 0).mean() * 100),
        },
        "missing_values": {
            col: {"count": int(df[col].isnull().sum()),
                  "percentage": float(df[col].isnull().mean() * 100)}
            for col in df.columns
        },
        "column_dtypes": {col: str(df[col].dtype) for col in df.columns},
    }

    import json
    with open(output_dir / "summary_statistics.json", "w") as f:
        json.dump(stats, f, indent=2, default=str)

    logger.info("Saved: summary statistics JSON")
    return stats


def main() -> None:
    """Run complete EDA pipeline."""
    setup_plot_style()
    EDA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load data
    logger.info("=" * 60)
    logger.info("SolarCast AI — Exploratory Data Analysis")
    logger.info("=" * 60)

    raw_path = find_raw_csv()
    logger.info(f"Loading data from: {raw_path}")
    df = load_and_prepare(raw_path)

    logger.info(f"Loaded dataset: {df.shape[0]} rows × {df.shape[1]} columns")
    logger.info(f"Time range: {df.index.min()} to {df.index.max()}")
    logger.info(f"Columns: {list(df.columns)}")

    # 2. Validation report
    logger.info("\nRunning data validation...")
    validation_report = generate_validation_report(df)
    import json
    with open(EDA_OUTPUT_DIR / "validation_report.json", "w") as f:
        json.dump(validation_report, f, indent=2, default=str)
    logger.info("Saved: validation report")

    # 3. Identify target column
    target_candidates = ["energy_delta_wh", "energy_delta__wh_", "energy_delta", "power", "generation"]
    target_col = None
    for candidate in target_candidates:
        matching = [c for c in df.columns if candidate in c.lower().replace(" ", "_")]
        if matching:
            target_col = matching[0]
            break

    if target_col is None:
        # Fallback: use first numeric column that's not obviously a weather variable
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if any(kw in col.lower() for kw in ["energy", "power", "generation", "yield", "wh"]):
                target_col = col
                break
        if target_col is None and len(numeric_cols) > 0:
            target_col = numeric_cols[0]
            logger.warning(f"Could not identify target column. Using first numeric: '{target_col}'")

    logger.info(f"Target column identified: '{target_col}'")

    # 4. Clean data
    logger.info("\nCleaning dataset...")
    df_clean, cleaning_report = clean_dataset(df)
    with open(EDA_OUTPUT_DIR / "cleaning_report.json", "w") as f:
        json.dump(cleaning_report, f, indent=2, default=str)

    # Save cleaned data
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df_clean.to_csv(PROCESSED_DIR / "cleaned_solar_data.csv")
    logger.info(f"Saved cleaned dataset: {df_clean.shape[0]} rows")

    # 5. Generate all EDA plots
    logger.info("\nGenerating EDA visualizations...")
    plot_generation_distribution(df_clean, target_col, EDA_OUTPUT_DIR)
    plot_hourly_trends(df_clean, target_col, EDA_OUTPUT_DIR)
    plot_daily_monthly_trends(df_clean, target_col, EDA_OUTPUT_DIR)
    plot_seasonal_patterns(df_clean, target_col, EDA_OUTPUT_DIR)
    plot_weather_vs_generation(df_clean, target_col, EDA_OUTPUT_DIR)
    plot_correlation_matrix(df_clean, EDA_OUTPUT_DIR)
    plot_missing_value_analysis(df, EDA_OUTPUT_DIR)  # Use original for missing analysis
    plot_daytime_nighttime(df_clean, target_col, EDA_OUTPUT_DIR)

    # 6. Summary statistics
    stats = generate_summary_statistics(df_clean, target_col, EDA_OUTPUT_DIR)

    # 7. Print summary
    logger.info("\n" + "=" * 60)
    logger.info("EDA SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Dataset: {stats['dataset_shape']['rows']} rows × {stats['dataset_shape']['columns']} columns")
    logger.info(f"Time range: {stats['time_range']['start']} to {stats['time_range']['end']}")
    logger.info(f"Duration: {stats['time_range']['duration_days']} days")
    logger.info(f"Target ('{target_col}'):")
    logger.info(f"  Mean:   {stats['target_statistics']['mean_wh']:.2f} Wh")
    logger.info(f"  Median: {stats['target_statistics']['median_wh']:.2f} Wh")
    logger.info(f"  Std:    {stats['target_statistics']['std_wh']:.2f} Wh")
    logger.info(f"  Range:  [{stats['target_statistics']['min_wh']:.2f}, {stats['target_statistics']['max_wh']:.2f}] Wh")
    logger.info(f"  Zero %: {stats['target_statistics']['zero_percentage']:.1f}%")
    logger.info(f"\nAll outputs saved to: {EDA_OUTPUT_DIR}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
