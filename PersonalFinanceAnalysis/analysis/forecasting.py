"""
analysis/forecasting.py
───────────────────────
Uses linear regression to forecast next month's
spending per category based on 3-month history.
Run directly:  python forecasting.py
"""

import pandas as pd
import numpy as np
import os
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../data")


def load_data():
    path = os.path.join(DATA_DIR, "cleaned.csv")
    if not os.path.exists(path):
        from cleaning import load_and_clean
        load_and_clean()
    return pd.read_csv(path, parse_dates=["date"])


def forecast_next_month(expenses_by_category_month):
    """
    For each category, fit a simple linear regression
    over 3 data points (months 1, 2, 3) and predict month 4.
    Returns a DataFrame with category and predicted spend.
    """
    forecasts = []
    for cat, group in expenses_by_category_month.groupby("category"):
        group = group.sort_values("month")
        X = group["month"].values.reshape(-1, 1)
        y = group["actual"].values

        if len(X) >= 2:
            model = LinearRegression()
            model.fit(X, y)
            pred = max(0, model.predict([[4]])[0])  # month 4 = April
            trend = "↑ Increasing" if model.coef_[0] > 50 else (
                    "↓ Decreasing" if model.coef_[0] < -50 else "→ Stable")
        else:
            pred  = y[0]
            trend = "→ Stable"

        forecasts.append({
            "category":     cat,
            "jan_actual":   group[group["month"] == 1]["actual"].values[0] if 1 in group["month"].values else 0,
            "feb_actual":   group[group["month"] == 2]["actual"].values[0] if 2 in group["month"].values else 0,
            "mar_actual":   group[group["month"] == 3]["actual"].values[0] if 3 in group["month"].values else 0,
            "apr_forecast": round(pred, 2),
            "trend":        trend,
        })

    return pd.DataFrame(forecasts)


def run_forecast():
    tx       = load_data()
    expenses = tx[tx["type"] == "Expense"].copy()

    cat_monthly = (
        expenses.groupby(["month", "category"])["amount"]
        .sum().reset_index()
        .rename(columns={"amount": "actual"})
    )

    forecast_df = forecast_next_month(cat_monthly)

    # Load budgets for comparison
    bud = pd.read_csv(os.path.join(DATA_DIR, "budgets.csv"))
    forecast_df = forecast_df.merge(bud, on="category", how="left")
    forecast_df["vs_budget"] = forecast_df["apr_forecast"] - forecast_df["monthly_budget"]
    forecast_df["flag"] = forecast_df["vs_budget"].apply(
        lambda v: "⚠️  Over Budget" if v > 0 else "✅ Within Budget"
    )

    total_forecast = forecast_df["apr_forecast"].sum()
    total_budget   = forecast_df["monthly_budget"].sum()

    print("── April 2024 Spending Forecast ────────────────────────────")
    cols = ["category","jan_actual","feb_actual","mar_actual","apr_forecast","trend","flag"]
    print(forecast_df[cols].to_string(index=False))
    print()
    print(f"   Total forecast spend : R {total_forecast:,.2f}")
    print(f"   Total budget         : R {total_budget:,.2f}")
    print(f"   Difference           : R {total_forecast - total_budget:+,.2f}")

    return forecast_df


if __name__ == "__main__":
    run_forecast()
