"""
Shared feature engineering used by both model training (management command)
and live prediction (DemandPredictor service), so train/predict stay in sync.
"""
import numpy as np
import pandas as pd

# India-ish fixed-date holiday set used only as a simple "is_holiday" seasonal signal.
# This is intentionally simple/approximate rather than a full holiday calendar.
FIXED_HOLIDAYS_MMDD = {
    (1, 1), (1, 26), (8, 15), (10, 2), (12, 25),
}

FEATURE_COLUMNS = [
    "selling_price",
    "discount_percentage",
    "day_of_week",
    "month",
    "is_weekend",
    "is_holiday",
    "category_code",
    "previous_day_sales",
    "previous_7day_avg",
    "stock_quantity",
]


def is_holiday(d: pd.Timestamp) -> int:
    return int((d.month, d.day) in FIXED_HOLIDAYS_MMDD)


def build_training_frame(sales_qs, product_category_map, product_stock_map):
    """
    Build a feature dataframe from a SalesRecord queryset.
    product_category_map: {product_id: category_string}
    product_stock_map: {product_id: current_stock_quantity} (approximation: we do not
        have historical daily stock snapshots, so current stock is used as a proxy
        feature representing typical inventory availability for that product).
    """
    rows = list(sales_qs.values(
        "product_id", "sale_date", "quantity_sold", "selling_price", "discount_percentage"
    ))
    if not rows:
        return pd.DataFrame(columns=FEATURE_COLUMNS + ["product_id", "quantity_sold"])

    df = pd.DataFrame(rows)
    df["sale_date"] = pd.to_datetime(df["sale_date"])
    df = df.sort_values(["product_id", "sale_date"]).reset_index(drop=True)

    # category encoding (stable ordering so train/predict agree)
    categories = sorted(set(product_category_map.values())) or ["other"]
    cat_to_code = {c: i for i, c in enumerate(categories)}

    df["category_code"] = df["product_id"].map(lambda pid: cat_to_code.get(product_category_map.get(pid, "other"), 0))
    df["stock_quantity"] = df["product_id"].map(lambda pid: product_stock_map.get(pid, 0))

    df["day_of_week"] = df["sale_date"].dt.dayofweek
    df["month"] = df["sale_date"].dt.month
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    df["is_holiday"] = df["sale_date"].apply(is_holiday)

    df["previous_day_sales"] = df.groupby("product_id")["quantity_sold"].shift(1)
    df["previous_7day_avg"] = (
        df.groupby("product_id")["quantity_sold"]
        .shift(1)
        .rolling(window=7, min_periods=1)
        .mean()
        .reset_index(level=0, drop=True)
    )

    df["previous_day_sales"] = df["previous_day_sales"].fillna(df["quantity_sold"].mean())
    df["previous_7day_avg"] = df["previous_7day_avg"].fillna(df["quantity_sold"].mean())

    df["selling_price"] = df["selling_price"].astype(float)
    df["discount_percentage"] = df["discount_percentage"].astype(float)

    return df, cat_to_code


def build_prediction_row(product, target_date, cat_to_code, recent_sales_df):
    """
    Build a single-row feature dict for predicting demand for `product` on `target_date`.
    recent_sales_df: DataFrame of that product's past sales sorted by date ascending
        (used to compute previous_day_sales / previous_7day_avg).
    """
    target_date = pd.Timestamp(target_date)

    if recent_sales_df is not None and len(recent_sales_df) > 0:
        previous_day_sales = float(recent_sales_df["quantity_sold"].iloc[-1])
        previous_7day_avg = float(recent_sales_df["quantity_sold"].tail(7).mean())
        avg_discount = float(recent_sales_df["discount_percentage"].tail(14).mean())
    else:
        previous_day_sales = 0.0
        previous_7day_avg = 0.0
        avg_discount = 0.0

    row = {
        "selling_price": float(product.current_price),
        "discount_percentage": avg_discount,
        "day_of_week": target_date.dayofweek,
        "month": target_date.month,
        "is_weekend": int(target_date.dayofweek in (5, 6)),
        "is_holiday": is_holiday(target_date),
        "category_code": cat_to_code.get(product.category, 0),
        "previous_day_sales": previous_day_sales,
        "previous_7day_avg": previous_7day_avg,
        "stock_quantity": float(product.stock_quantity),
    }
    return pd.DataFrame([row])[FEATURE_COLUMNS]
