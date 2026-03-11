# 💰 Personal Finance Analysis

A data analytics project tracking income, expenses, budget performance, and savings
for a single professional in Johannesburg — salary plus freelance side income —
across January, February, and March 2024. Built to demonstrate data analysis,
forecasting, and business insight skills for a junior data analyst portfolio.

---

## What This Project Does

- Tracks total income split between salary and freelance side income per month
- Analyses spending across 11 categories (Housing, Food, Transport, etc.)
- Compares actual spending against monthly budget targets with variance analysis
- Calculates savings rate and benchmarks against the 20% target
- Uses linear regression to forecast April 2024 spending per category
- Flags categories consistently going over budget
- Generates automated financial insights and actionable recommendations
- Presents everything in a 5-page interactive Dash dashboard

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| Python | Core language |
| pandas | Data loading, cleaning, aggregation |
| scikit-learn | Linear regression, forecasting |
| Plotly | Interactive charts and heatmaps |
| Dash | 5-page web dashboard |
| Jupyter Notebooks | Step-by-step documented analysis |
| openpyxl | Excel file support |

---

## Project Structure

```
PersonalFinanceAnalysis/
│
├── data/
│   ├── transactions.csv    ← 69 income and expense transactions (Jan–Mar 2024)
│   ├── budgets.csv         ← Monthly budget targets per category
│   └── cleaned.csv         ← Auto-generated on first run
│
├── notebooks/
│   ├── 01_data_cleaning.ipynb         ← Load, clean, enrich datasets
│   ├── 02_exploratory_analysis.ipynb  ← Income trends, spending patterns
│   ├── 03_budget_analysis.ipynb       ← Budget vs actual per category
│   ├── 04_forecasting.ipynb           ← Linear regression spending forecast
│   └── 05_insights.ipynb              ← Automated insights and recommendations
│
├── analysis/
│   ├── cleaning.py     ← Reusable data loading and cleaning functions
│   ├── forecasting.py  ← Linear regression model and scenario forecasting
│   └── insights.py     ← Rule-based insight and recommendation generation
│
├── dashboard/
│   └── app.py          ← 5-page Dash dashboard (orange and black theme)
│
├── requirements.txt
└── README.md
```

---

## Dashboard Pages

**Home** — Project overview, methodology, and tech stack

**Dashboard** — 7 KPI cards, monthly income vs expenses, savings rate trend,
salary vs side income breakdown, category pie chart, and daily transaction timeline

**Budget** — Per-month budget vs actual bar charts, variance heatmap,
and over-budget entries table

**Forecast** — April 2024 spending forecast per category using linear regression,
trend indicators, and budget comparison

**Insights** — Automated insights (savings rate health, over-budget categories,
side income trend) plus 5 actionable financial recommendations

---

## How to Run

### Step 1 — Install dependencies
```bash
pip install pandas plotly dash scikit-learn openpyxl jupyter statsmodels
```

### Step 2 — Run the notebooks (recommended first)
```bash
cd notebooks
jupyter notebook
```
Run notebooks 01 through 05 in order. Notebook 01 generates `data/cleaned.csv`.

### Step 3 — Run the dashboard
```bash
cd dashboard
python app.py
```
Open `http://127.0.0.1:8050` in your browser.

---

## Key Findings

- **February** was the worst month — savings rate dropped to its lowest due to Valentine's Day
  spending and a R 2,800 clothing overspend
- **Food** is the largest expense category and was over budget in 2 of 3 months
- **Side income** contributed approximately 13% of total income — a meaningful supplement
- **March** showed recovery with the highest savings contribution of R 3,500
- **Forecast:** April spending is projected to be within budget if current March trends hold

---

## Skills Demonstrated

- End-to-end data pipeline — raw CSV to cleaned dataset
- Multi-source data merging (transactions + budgets)
- Pandas groupby aggregations across time dimensions
- Budget variance analysis with heatmap visualisation
- Linear regression with scikit-learn for time-series forecasting
- Rule-based insight generation from aggregated data
- 5-page Dash web application with routing
- Jupyter notebook documentation with full markdown commentary
- Translating financial data into actionable business recommendations

---

*Built with Python · pandas · scikit-learn · Plotly · Dash · Jupyter*
