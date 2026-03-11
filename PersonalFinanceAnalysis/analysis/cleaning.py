"""
analysis/cleaning.py
────────────────────
Loads transactions.csv and budgets.csv, cleans and
enriches them, then exports data/cleaned.csv.
Run directly:  python cleaning.py
"""

import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../data")


def load_and_clean():
    # ── Load raw files ────────────────────────────────────────────────
    tx  = pd.read_csv(os.path.join(DATA_DIR, "transactions.csv"))
    bud = pd.read_csv(os.path.join(DATA_DIR, "budgets.csv"))

    # ── Parse and enrich dates ────────────────────────────────────────
    tx["date"]       = pd.to_datetime(tx["date"])
    tx["month"]      = tx["date"].dt.month
    tx["month_name"] = tx["date"].dt.month_name()
    tx["week"]       = tx["date"].dt.to_period("W").astype(str)
    tx["day_name"]   = tx["date"].dt.day_name()

    # ── Clean text fields ─────────────────────────────────────────────
    tx["category"]    = tx["category"].str.strip()
    tx["type"]        = tx["type"].str.strip()
    tx["description"] = tx["description"].str.strip()
    tx["notes"]       = tx["notes"].fillna("").str.strip()

    # ── Split income and expenses ─────────────────────────────────────
    income   = tx[tx["type"] == "Income"].copy()
    expenses = tx[tx["type"] == "Expense"].copy()

    # ── Monthly summaries ─────────────────────────────────────────────
    monthly_income = (
        income.groupby(["month", "month_name"])["amount"]
        .sum().reset_index()
        .rename(columns={"amount": "total_income"})
    )

    monthly_salary = (
        income[income["category"] == "Salary"]
        .groupby(["month", "month_name"])["amount"]
        .sum().reset_index()
        .rename(columns={"amount": "salary_income"})
    )

    monthly_side = (
        income[income["category"] == "Side Income"]
        .groupby(["month", "month_name"])["amount"]
        .sum().reset_index()
        .rename(columns={"amount": "side_income"})
    )

    monthly_expenses = (
        expenses.groupby(["month", "month_name"])["amount"]
        .sum().reset_index()
        .rename(columns={"amount": "total_expenses"})
    )

    # Merge monthly summaries
    monthly = monthly_income.merge(monthly_salary, on=["month", "month_name"], how="left")
    monthly = monthly.merge(monthly_side,          on=["month", "month_name"], how="left")
    monthly = monthly.merge(monthly_expenses,      on=["month", "month_name"], how="left")
    monthly["side_income"]  = monthly["side_income"].fillna(0)
    monthly["net_savings"]  = monthly["total_income"] - monthly["total_expenses"]
    monthly["savings_rate"] = (monthly["net_savings"] / monthly["total_income"] * 100).round(2)
    monthly = monthly.sort_values("month")

    # ── Budget vs actual per category per month ───────────────────────
    cat_monthly = (
        expenses.groupby(["month", "month_name", "category"])["amount"]
        .sum().reset_index()
        .rename(columns={"amount": "actual"})
    )
    cat_monthly = cat_monthly.merge(bud, on="category", how="left")
    cat_monthly["variance"]    = cat_monthly["actual"] - cat_monthly["monthly_budget"]
    cat_monthly["over_budget"]  = cat_monthly["variance"] > 0
    cat_monthly["pct_of_budget"]= (
        cat_monthly["actual"] / cat_monthly["monthly_budget"] * 100
    ).round(2)

    # ── Export cleaned transactions ───────────────────────────────────
    out = os.path.join(DATA_DIR, "cleaned.csv")
    tx.to_csv(out, index=False)

    print("✅ Cleaning complete")
    print(f"   Transactions : {len(tx)}")
    print(f"   Income rows  : {len(income)}")
    print(f"   Expense rows : {len(expenses)}")
    print(f"   Date range   : {tx['date'].min().date()} → {tx['date'].max().date()}")
    print(f"   Categories   : {sorted(expenses['category'].unique().tolist())}")

    return tx, income, expenses, monthly, cat_monthly, bud


if __name__ == "__main__":
    tx, income, expenses, monthly, cat_monthly, bud = load_and_clean()
    print("\nMonthly Summary:")
    print(monthly.to_string(index=False))
    print("\nBudget vs Actual (all months):")
    print(cat_monthly.sort_values(["month","variance"], ascending=[True,False]).to_string(index=False))
