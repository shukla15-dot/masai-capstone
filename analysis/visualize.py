"""
Part 2, Task 11 — Two visualizations (3 marks)
Mamaearth Returns & Growth Intelligence Pipeline.

Recomputes the two headline findings from the RAW CSVs (the same cleaning steps
as clean_and_eda.py, kept here so this script re-runs end-to-end on its own) and
saves two PNGs to visualizations/:

  1. return_rate_by_payment.png  — return rate by cleaned payment_method (desc),
                                    COD highlighted, exact % on each bar.
  2. monthly_revenue_trend.png   — outlier-CORRECTED monthly revenue, peak labelled.

Run (after clean_and_eda.py):  python analysis/visualize.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless: write PNGs, never open a window
import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
VIZ_DIR = REPO_ROOT / "visualizations"

# --- Design tokens (dataviz palette, light surface) --------------------------
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
SERIES_BLUE = "#2a78d6"
CRITICAL = "#d03b3b"   # status: the at-risk category (COD)
NEUTRAL = "#b7c3d0"    # recessive fill for the not-at-risk categories

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": MUTED,
    "text.color": INK,
    "axes.labelcolor": INK_SECONDARY,
    "xtick.color": INK_SECONDARY,
    "ytick.color": INK_SECONDARY,
})

MONTH_LABELS = {
    "2026-01": "Jan", "2026-02": "Feb", "2026-03": "Mar",
    "2026-04": "Apr", "2026-05": "May", "2026-06": "Jun",
}


def load_clean_merged():
    """Raw CSVs -> cleaned, merged frame with order_value and is_outlier.

    Mirrors Part 2 Tasks 2-6 (casing, dedup, impute, merge, outlier flag) so the
    numbers plotted here match clean_and_eda.py exactly.
    """
    customers = pd.read_csv(DATA_DIR / "customers.csv")
    products = pd.read_csv(DATA_DIR / "products.csv")
    orders = pd.read_csv(DATA_DIR / "orders.csv")

    orders["payment_method"] = orders["payment_method"].str.strip().str.upper()

    natural_key = ["customer_id", "product_id", "order_date", "quantity",
                   "discount_pct", "payment_method", "rating", "returned"]
    orders = orders.loc[~orders.duplicated(subset=natural_key, keep="first")].copy()

    orders["discount_pct"] = orders["discount_pct"].fillna(0)
    orders["rating"] = orders["rating"].fillna(orders["rating"].median())

    merged = (orders
              .merge(products, on="product_id", how="left")
              .merge(customers, on="customer_id", how="left"))
    merged["order_value"] = merged["quantity"] * merged["price"] * (1 - merged["discount_pct"] / 100.0)

    q1, q3 = merged["quantity"].quantile(0.25), merged["quantity"].quantile(0.75)
    iqr = q3 - q1
    merged["is_outlier"] = (merged["quantity"] < q1 - 1.5 * iqr) | (merged["quantity"] > q3 + 1.5 * iqr)
    merged["order_date"] = pd.to_datetime(merged["order_date"])
    merged["year_month"] = merged["order_date"].dt.strftime("%Y-%m")
    return merged


def chart_return_rate(merged):
    rates = (merged.groupby("payment_method")["returned"].mean() * 100).round(1)
    rates = rates.sort_values(ascending=False)
    colors = [CRITICAL if m == "COD" else NEUTRAL for m in rates.index]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(rates.index, rates.values, color=colors, width=0.62, zorder=3)
    for bar, val in zip(bars, rates.values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.8, f"{val:.1f}%",
                ha="center", va="bottom", fontsize=12, fontweight="bold", color=INK)

    ax.set_title("COD Returns at 44.4% — 3x the Card Rate",
                 fontsize=15, fontweight="bold", color=INK, pad=14, loc="left")
    ax.set_ylabel("Return rate (%)", fontsize=11)
    ax.set_ylim(0, max(rates.values) * 1.18)
    ax.yaxis.grid(True, color=GRID, linewidth=1, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.tick_params(length=0)

    out = VIZ_DIR / "return_rate_by_payment.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"saved {out}")


def chart_monthly_trend(merged):
    monthly = (merged.loc[~merged["is_outlier"]]
               .groupby("year_month")["order_value"].sum().round(2).sort_index())
    peak_month = monthly.idxmax()
    peak_val = monthly.max()
    labels = [MONTH_LABELS.get(m, m) for m in monthly.index]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(labels, monthly.values, color=SERIES_BLUE, linewidth=2, zorder=3)
    ax.scatter(labels, monthly.values, s=42, color=SERIES_BLUE, zorder=4)

    # Direct-label the true peak point only (selective labelling).
    peak_idx = list(monthly.index).index(peak_month)
    ax.annotate(f"Peak: INR {peak_val:,.2f}",
                xy=(peak_idx, peak_val), xytext=(peak_idx, peak_val + peak_val * 0.07),
                ha="center", fontsize=11, fontweight="bold", color=INK)

    ax.set_title("March is the True Peak — INR 20,318.90 (Outlier-Corrected)",
                 fontsize=12.5, fontweight="bold", color=INK, pad=14, loc="left")
    ax.set_xlabel("Month (2026)", fontsize=11)
    ax.set_ylabel("Revenue (INR)", fontsize=11)
    ax.set_ylim(0, peak_val * 1.25)
    ax.yaxis.grid(True, color=GRID, linewidth=1, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(MUTED)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(length=0)
    ax.yaxis.set_major_formatter(lambda x, _: f"{x:,.0f}")

    out = VIZ_DIR / "monthly_revenue_trend.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"saved {out}")


def main():
    VIZ_DIR.mkdir(parents=True, exist_ok=True)
    merged = load_clean_merged()
    chart_return_rate(merged)
    chart_monthly_trend(merged)
    print("Part 2 Task 11 complete — 2 PNGs written to visualizations/")


if __name__ == "__main__":
    main()
