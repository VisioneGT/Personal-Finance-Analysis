"""
analysis/insights.py
─────────────────────
Generates rule-based financial insights and flags
categories that are consistently over budget.
Run directly:  python insights.py
"""

import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../data")


def load_data():
    path = os.path.join(DATA_DIR, "cleaned.csv")
    if not os.path.exists(path):
        from cleaning import load_and_clean
        load_and_clean()
    return pd.read_csv(path, parse_dates=["date"])


def generate_insights():
    tx       = load_data()
    bud      = pd.read_csv(os.path.join(DATA_DIR, "budgets.csv"))
    expenses = tx[tx["type"] == "Expense"].copy()
    income   = tx[tx["type"] == "Income"].copy()

    insights = []

    # ── 1. Savings rate ───────────────────────────────────────────────
    monthly_income = income.groupby("month")["amount"].sum()
    monthly_expense = expenses.groupby("month")["amount"].sum()
    monthly_savings = (monthly_income - monthly_expense) / monthly_income * 100

    avg_savings_rate = monthly_savings.mean()
    if avg_savings_rate >= 20:
        insights.append(("✅", "Savings Rate",
            f"Average savings rate of {avg_savings_rate:.1f}% is healthy (target: 20%+)."))
    elif avg_savings_rate >= 10:
        insights.append(("⚠️", "Savings Rate",
            f"Savings rate of {avg_savings_rate:.1f}% is below the recommended 20%. "
            f"Try to reduce Food or Entertainment spending."))
    else:
        insights.append(("🔴", "Savings Rate",
            f"Savings rate of {avg_savings_rate:.1f}% is critically low. "
            f"Review all discretionary categories urgently."))

    # ── 2. Categories over budget ─────────────────────────────────────
    cat_monthly = (
        expenses.groupby(["month", "category"])["amount"]
        .sum().reset_index()
        .rename(columns={"amount": "actual"})
    )
    cat_monthly = cat_monthly.merge(bud, on="category", how="left")
    cat_monthly["over"] = cat_monthly["actual"] - cat_monthly["monthly_budget"]

    over_months = cat_monthly[cat_monthly["over"] > 0].groupby("category").size()
    for cat, count in over_months.items():
        avg_over = cat_monthly[
            (cat_monthly["category"] == cat) & (cat_monthly["over"] > 0)
        ]["over"].mean()
        if count >= 2:
            insights.append(("🔴", f"{cat} Overspend",
                f"Over budget in {count}/3 months, average overspend R {avg_over:,.0f}."))
        else:
            insights.append(("⚠️", f"{cat} Overspend",
                f"Over budget in 1 month by R {avg_over:,.0f}. Monitor closely."))

    # ── 3. Side income trend ──────────────────────────────────────────
    side = income[income["category"] == "Side Income"].groupby("month")["amount"].sum()
    if len(side) >= 2:
        trend = side.iloc[-1] - side.iloc[0]
        if trend > 0:
            insights.append(("✅", "Side Income",
                f"Side income grew from R {side.iloc[0]:,.0f} to R {side.iloc[-1]:,.0f}. "
                f"Growing this stream further will improve financial security."))
        else:
            insights.append(("⚠️", "Side Income",
                f"Side income dropped from R {side.iloc[0]:,.0f} to R {side.iloc[-1]:,.0f}. "
                f"Consider finding more freelance projects."))

    # ── 4. Biggest expense category ───────────────────────────────────
    top_cat = expenses.groupby("category")["amount"].sum().idxmax()
    top_total = expenses.groupby("category")["amount"].sum().max()
    total_expenses = expenses["amount"].sum()
    top_pct = top_total / total_expenses * 100
    insights.append(("📊", "Largest Expense",
        f"{top_cat} is the largest expense category at R {top_total:,.0f} "
        f"({top_pct:.1f}% of total spending over 3 months)."))

    # ── 5. Best and worst month ───────────────────────────────────────
    month_names = {1: "January", 2: "February", 3: "March"}
    best_month  = monthly_savings.idxmax()
    worst_month = monthly_savings.idxmin()
    insights.append(("📅", "Best Month",
        f"{month_names[best_month]} had the highest savings rate at "
        f"{monthly_savings[best_month]:.1f}%."))
    insights.append(("📅", "Worst Month",
        f"{month_names[worst_month]} had the lowest savings rate at "
        f"{monthly_savings[worst_month]:.1f}% — "
        f"review spending that month."))

    return insights, cat_monthly, avg_savings_rate


if __name__ == "__main__":
    insights, cat_monthly, savings_rate = generate_insights()
    print("── Financial Insights ──────────────────────────────────────")
    for icon, title, msg in insights:
        print(f"\n{icon} {title}")
        print(f"   {msg}")
