"""
Part 2 — Python / Pandas Data Wrangling & EDA (40 marks)
Mamaearth Returns & Growth Intelligence Pipeline.

Runs directly against the RAW CSVs in data/ (not the SQL database): Part 2 is an
independent pandas pipeline over the same source files, so a grader can run Part 1
and Part 2 in either order.

Every intermediate result the brief references is printed to stdout. The script is
deterministic: re-running it regenerates identical numbers and an identical
narrator/findings.json (Part 3, Task 1), which is written by code at the very end so
it can never drift from the numbers computed here.

Run:  python analysis/clean_and_eda.py
"""

import json
import sys
from pathlib import Path

import pandas as pd

# Print UTF-8 cleanly even on a Windows console whose default code page is cp1252,
# so the em-dashes / section rules below don't render as mojibake when graded.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

# --- Paths (resolved relative to this file, so the script runs from anywhere) ---
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
FINDINGS_PATH = REPO_ROOT / "narrator" / "findings.json"


def order_value(df):
    """Revenue per row: quantity * price * (1 - discount_pct/100).

    Matches Part 1's revenue convention. Expects `price` and a non-null
    `discount_pct` column already present on the (merged) frame.
    """
    return df["quantity"] * df["price"] * (1 - df["discount_pct"] / 100.0)


def banner(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def main():
    # ========================================================================
    # Task 1 — Load and inspect (2 marks)
    # ========================================================================
    banner("Task 1 — Load and inspect")
    customers = pd.read_csv(DATA_DIR / "customers.csv")
    products = pd.read_csv(DATA_DIR / "products.csv")
    orders = pd.read_csv(DATA_DIR / "orders.csv")

    print(f"customers.shape = {customers.shape}")
    print(f"products.shape  = {products.shape}")
    print(f"orders.shape    = {orders.shape}   (must be (180, 9) before any cleaning)")
    assert orders.shape == (180, 9), "raw orders must be (180, 9)"

    # Raw total revenue (COALESCE NULL discount -> 0), computed from the raw CSVs
    # so we never hardcode Part 1's number — this must equal 99860.20.
    raw_merged = orders.merge(products, on="product_id", how="left").copy()
    raw_merged["discount_pct"] = raw_merged["discount_pct"].fillna(0)
    raw_total_revenue = round(order_value(raw_merged).sum(), 2)
    print(f"raw total revenue (NULL discount = 0) = {raw_total_revenue:.2f}   (Part 1 report (a) = 99860.20)")

    # ========================================================================
    # Task 2 — Standardize payment_method casing (4 marks)
    # ========================================================================
    banner("Task 2 — Standardize payment_method casing")
    raw_methods = sorted(orders["payment_method"].unique())
    print(f"BEFORE: {len(raw_methods)} distinct raw values -> {raw_methods}")
    assert len(raw_methods) == 7, "expected 7 raw payment_method spellings"

    orders["payment_method"] = orders["payment_method"].str.strip().str.upper()
    after_counts = orders["payment_method"].value_counts()
    print(f"AFTER:  {orders['payment_method'].nunique()} distinct values")
    print(after_counts.to_string())
    assert orders["payment_method"].nunique() == 3
    assert after_counts["CARD"] == 70 and after_counts["UPI"] == 55 and after_counts["COD"] == 55

    # ========================================================================
    # Task 3 — Remove duplicate orders (4 marks)
    # ========================================================================
    banner("Task 3 — Remove duplicate orders")
    # Natural key = everything EXCEPT order_id (which differs on the double-submits).
    natural_key = ["customer_id", "product_id", "order_date", "quantity",
                   "discount_pct", "payment_method", "rating", "returned"]
    dup_mask = orders.duplicated(subset=natural_key, keep="first")
    dropped_ids = orders.loc[dup_mask, "order_id"].tolist()
    print(f"duplicate rows flagged: {int(dup_mask.sum())}")
    print(f"dropped order_id values: {dropped_ids}")
    orders_clean = orders.loc[~dup_mask].copy()
    print(f"orders_clean.shape = {orders_clean.shape}   (must be (175, 9))")
    assert int(dup_mask.sum()) == 5
    assert dropped_ids == ["O0176", "O0177", "O0178", "O0179", "O0180"]
    assert orders_clean.shape == (175, 9)

    # ========================================================================
    # Task 4 — Impute missing values (4 marks)  [on the deduplicated frame]
    # ========================================================================
    banner("Task 4 — Impute missing values")
    n_disc_missing = int(orders_clean["discount_pct"].isna().sum())
    n_rating_missing = int(orders_clean["rating"].isna().sum())
    rating_median = orders_clean["rating"].median()
    print(f"discount_pct missing (dedup frame): {n_disc_missing}  -> filling with 0 (no promo code)")
    print(f"rating median (non-null, dedup frame): {rating_median}")
    print(f"rating missing (dedup frame): {n_rating_missing}  -> filling with the median")

    orders_clean["discount_pct"] = orders_clean["discount_pct"].fillna(0)
    orders_clean["rating"] = orders_clean["rating"].fillna(rating_median)

    nulls_after = orders_clean[["discount_pct", "rating"]].isnull().sum()
    print("nulls after imputation:")
    print(nulls_after.to_string())
    assert n_disc_missing == 12 and n_rating_missing == 15 and rating_median == 3.0
    assert nulls_after["discount_pct"] == 0 and nulls_after["rating"] == 0

    # ========================================================================
    # Task 5 — Merge and reconcile against Part 1 (5 marks)
    # ========================================================================
    banner("Task 5 — Merge and reconcile")
    merged = (orders_clean
              .merge(products, on="product_id", how="left")
              .merge(customers, on="customer_id", how="left"))
    merged["order_value"] = order_value(merged)
    cleaned_total = round(merged["order_value"].sum(), 2)
    print(f"cleaned total order_value across {len(merged)} rows = {cleaned_total:.2f}   (must be 97358.30)")

    delta = round(raw_total_revenue - cleaned_total, 2)
    # Independent check: sum the order_value of exactly the 5 dropped duplicate rows.
    dropped_rows = orders.loc[dup_mask].merge(products, on="product_id", how="left").copy()
    dropped_rows["discount_pct"] = dropped_rows["discount_pct"].fillna(0)
    dropped_value = round(order_value(dropped_rows).sum(), 2)

    print("\nReconciliation note:")
    print(
        f"  The cleaned total of INR {cleaned_total:,.2f} is INR {delta:,.2f} lower than Part 1's\n"
        f"  raw total of INR {raw_total_revenue:,.2f}. This entire INR {delta:,.2f} gap is attributable to\n"
        f"  the 5 duplicate (double-submitted) orders removed in Task 3 — their combined order_value\n"
        f"  is exactly INR {dropped_value:,.2f}, which matches the delta. The missing-value imputation\n"
        f"  in Task 4 does NOT change any order_value total: filling discount_pct with 0 only affects\n"
        f"  rows that already had no promo code (0% discount is the identity for the (1 - d/100) factor\n"
        f"  when d=0), and filling rating never enters the revenue formula at all."
    )
    assert cleaned_total == 97358.30
    assert delta == 2501.90 and dropped_value == 2501.90

    # ========================================================================
    # Task 6 — IQR outlier detection on quantity (4 marks)
    # ========================================================================
    banner("Task 6 — IQR outlier detection on quantity")
    q1 = merged["quantity"].quantile(0.25)
    q3 = merged["quantity"].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    print(f"Q1 = {q1}, Q3 = {q3}, IQR = {iqr}, lower = {lower}, upper = {upper}")

    merged["is_outlier"] = (merged["quantity"] < lower) | (merged["quantity"] > upper)
    outliers = merged.loc[merged["is_outlier"], ["order_id", "order_date", "quantity"]]
    print("outlier rows (flagged, NOT dropped):")
    print(outliers.to_string(index=False))
    assert q1 == 1.0 and q3 == 2.0 and iqr == 1.0 and lower == -0.5 and upper == 3.5
    assert sorted(outliers["order_id"].tolist()) == ["O0011", "O0098"]

    # ========================================================================
    # Task 7 — Hypothesis: does COD have a higher return rate? (4 marks)
    # ========================================================================
    banner("Task 7 — Hypothesis: does COD have a higher return rate?")
    print("Hypothesis: Cash-on-Delivery (COD) orders are returned at a higher rate than")
    print("            prepaid (CARD / UPI) orders.")
    by_pay = merged.groupby("payment_method")["returned"].agg(["count", "mean"])
    by_pay["return_rate_pct"] = (by_pay["mean"] * 100).round(1)
    print(by_pay.to_string())
    return_rate_by_payment = by_pay["return_rate_pct"].to_dict()
    assert return_rate_by_payment["CARD"] == 14.7
    assert return_rate_by_payment["COD"] == 44.4
    assert return_rate_by_payment["UPI"] == 18.9
    print("\nVerdict: CONFIRMED — COD (44.4%) returns at roughly 3x the CARD rate (14.7%).")

    # ========================================================================
    # Task 8 — Multi-level segmentation (4 marks)
    # ========================================================================
    banner("Task 8 — Multi-level segmentation (payment_method x city_tier)")
    seg = merged.groupby(["payment_method", "city_tier"])["returned"].agg(["count", "mean"])
    seg["return_rate_pct"] = (seg["mean"] * 100).round(1)
    print(seg.to_string())
    top_seg = seg["return_rate_pct"].idxmax()
    top_rate = seg["return_rate_pct"].max()
    print(f"\nHighest-risk segment: payment_method={top_seg[0]}, city_tier={top_seg[1]} "
          f"at {top_rate}% return rate.")
    print("Note: COD risk is NOT uniform across tiers — Tier-1 COD is 37.5% vs Tier-2 COD 54.5%, "
          "so a single blended COD rate hides where the real problem is concentrated.")
    assert top_seg == ("COD", 2) and top_rate == 54.5

    # ========================================================================
    # Task 9 — Correlation analysis (2 marks)
    # ========================================================================
    banner("Task 9 — Correlation analysis")
    corr = merged[["rating", "returned", "discount_pct", "quantity"]].corr()
    print(corr.round(3).to_string())

    def band(r):
        a = abs(r)
        if a < 0.2:
            return "negligible"
        if a < 0.4:
            return "weak"
        if a < 0.7:
            return "moderate"
        return "strong"

    print("\nPairwise strength bands (0-0.19 negligible / 0.2-0.39 weak / 0.4-0.69 moderate / 0.7-1.0 strong):")
    cols = ["rating", "returned", "discount_pct", "quantity"]
    all_negligible = True
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            r = corr.loc[cols[i], cols[j]]
            label = band(r)
            all_negligible = all_negligible and (label == "negligible")
            print(f"  {cols[i]:<12} vs {cols[j]:<12}: r = {r:+.3f}  -> {label}")
    disc_ret = corr.loc["discount_pct", "returned"]
    print(f"\nHypothesis 'higher discounts reduce returns': BUSTED "
          f"(discount_pct vs returned r = {disc_ret:+.3f}, negligible).")
    assert all_negligible, "every pair must be negligible (|r| < 0.2)"

    # ========================================================================
    # Task 10 — Outlier-corrected time series (4 marks)
    # ========================================================================
    banner("Task 10 — Outlier-corrected monthly revenue")
    merged["order_date"] = pd.to_datetime(merged["order_date"])
    merged["year_month"] = merged["order_date"].dt.strftime("%Y-%m")

    monthly_all = merged.groupby("year_month")["order_value"].sum().round(2)
    monthly_corrected = (merged.loc[~merged["is_outlier"]]
                         .groupby("year_month")["order_value"].sum().round(2))

    print("(1) Monthly revenue INCLUDING the two bulk outliers:")
    print(monthly_all.to_string())
    print("\n(2) Monthly revenue EXCLUDING the two outliers (corrected):")
    print(monthly_corrected.to_string())

    inflated_month = monthly_all.idxmax()
    true_peak_month = monthly_corrected.idxmax()
    print(f"\nWith outliers, the apparent top month is {inflated_month} "
          f"(INR {monthly_all.max():,.2f}).")
    print(f"That lead is an ARTIFACT of the two bulk orders landing in January "
          f"(O0011 on 2026-01-28, O0098 on 2026-01-10).")
    print(f"Once excluded, the genuine peak month is {true_peak_month} "
          f"(INR {monthly_corrected.max():,.2f}). This is exactly why Task 6 (outliers) "
          f"runs before Task 10 (trend), not after.")
    assert inflated_month == "2026-01" and monthly_all.max() == 29582.10
    assert true_peak_month == "2026-03" and monthly_corrected.max() == 20318.90

    # ========================================================================
    # Export findings.json for Part 3 (Task 1) — written by code, never typed.
    # ========================================================================
    banner("Export narrator/findings.json")
    findings = {
        "cleaned_total_revenue_inr": cleaned_total,
        "raw_total_revenue_inr": raw_total_revenue,
        "duplicate_reconciliation_delta_inr": delta,
        "return_rate_by_payment": {
            "COD": return_rate_by_payment["COD"],
            "CARD": return_rate_by_payment["CARD"],
            "UPI": return_rate_by_payment["UPI"],
        },
        "highest_risk_segment": {
            "payment_method": top_seg[0],
            "city_tier": int(top_seg[1]),
            "return_rate_pct": float(top_rate),
        },
        "true_peak_month": {
            "month": true_peak_month,
            "revenue_inr": float(monthly_corrected.max()),
        },
        "outlier_inflated_month": {
            "month": inflated_month,
            "apparent_revenue_inr": float(monthly_all.max()),
            "corrected_revenue_inr": float(monthly_corrected.loc[inflated_month]),
        },
    }
    FINDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(FINDINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(findings, f, indent=2)
    print(f"wrote {FINDINGS_PATH}")
    print(json.dumps(findings, indent=2))

    banner("Part 2 complete — all acceptance checks passed")


if __name__ == "__main__":
    main()
