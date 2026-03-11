"""
dashboard/app.py
────────────────
Personal Finance Analysis Dashboard
Multi-page Dash app — orange and black theme

Pages:
  /            → Home
  /dashboard   → Full analytics overview
  /budget      → Budget vs Actual detail
  /forecast    → April 2024 spending forecast
  /insights    → Automated financial insights

Run: python app.py
Open: http://127.0.0.1:8050
"""

import os, sys
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output
from sklearn.linear_model import LinearRegression

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../data")

# ── LOAD & PREPARE DATA ───────────────────────────────────────────────────

def load_data():
    cleaned = os.path.join(DATA_DIR, "cleaned.csv")
    if not os.path.exists(cleaned):
        sys.path.append(os.path.join(BASE_DIR, "../analysis"))
        from cleaning import load_and_clean
        load_and_clean()
    tx  = pd.read_csv(cleaned, parse_dates=["date"])
    bud = pd.read_csv(os.path.join(DATA_DIR, "budgets.csv"))
    return tx, bud

tx, bud = load_data()
income   = tx[tx["type"] == "Income"].copy()
expenses = tx[tx["type"] == "Expense"].copy()

MONTH_ORDER  = ["January", "February", "March"]
MONTH_NAMES  = {1: "January", 2: "February", 3: "March"}

# ── AGGREGATIONS ──────────────────────────────────────────────────────────

monthly_income   = income.groupby(["month","month_name"])["amount"].sum().reset_index().rename(columns={"amount":"total_income"})
monthly_salary   = income[income["category"]=="Salary"].groupby(["month","month_name"])["amount"].sum().reset_index().rename(columns={"amount":"salary"})
monthly_side     = income[income["category"]=="Side Income"].groupby(["month","month_name"])["amount"].sum().reset_index().rename(columns={"amount":"side_income"})
monthly_expenses = expenses.groupby(["month","month_name"])["amount"].sum().reset_index().rename(columns={"amount":"total_expenses"})

monthly = monthly_income.merge(monthly_salary, on=["month","month_name"], how="left")
monthly = monthly.merge(monthly_side,          on=["month","month_name"], how="left")
monthly = monthly.merge(monthly_expenses,      on=["month","month_name"], how="left")
monthly["side_income"]  = monthly["side_income"].fillna(0)
monthly["net_savings"]  = monthly["total_income"] - monthly["total_expenses"]
monthly["savings_rate"] = (monthly["net_savings"] / monthly["total_income"] * 100).round(1)
monthly = monthly.sort_values("month")
monthly["month_name"] = pd.Categorical(monthly["month_name"], categories=MONTH_ORDER, ordered=True)

cat_monthly = expenses.groupby(["month","month_name","category"])["amount"].sum().reset_index().rename(columns={"amount":"actual"})
cat_monthly = cat_monthly.merge(bud, on="category", how="left")
cat_monthly["variance"]      = cat_monthly["actual"] - cat_monthly["monthly_budget"]
cat_monthly["over_budget"]   = cat_monthly["variance"] > 0
cat_monthly["pct_of_budget"] = (cat_monthly["actual"] / cat_monthly["monthly_budget"] * 100).round(1)
cat_monthly["month_name"]    = pd.Categorical(cat_monthly["month_name"], categories=MONTH_ORDER, ordered=True)

cat_totals = expenses.groupby("category")["amount"].sum().reset_index().rename(columns={"amount":"total"}).sort_values("total", ascending=False)

# ── KPI numbers ───────────────────────────────────────────────────────────

total_income    = income["amount"].sum()
total_expenses  = expenses["amount"].sum()
net_saved       = total_income - total_expenses
avg_savings_rate= monthly["savings_rate"].mean()
total_side      = income[income["category"]=="Side Income"]["amount"].sum()
side_pct        = total_side / total_income * 100
total_budget_3m = bud["monthly_budget"].sum() * 3
variance_3m     = total_expenses - total_budget_3m
compliance      = (cat_monthly[~cat_monthly["over_budget"]].shape[0] / cat_monthly.shape[0] * 100)

# ── FORECAST ──────────────────────────────────────────────────────────────

cat_m_simple = expenses.groupby(["month","category"])["amount"].sum().reset_index().rename(columns={"amount":"actual"})
forecasts = []
for cat, group in cat_m_simple.groupby("category"):
    group = group.sort_values("month")
    X = group["month"].values.reshape(-1,1)
    y = group["actual"].values
    model = LinearRegression()
    model.fit(X, y)
    pred  = max(0, model.predict([[4]])[0])
    slope = model.coef_[0]
    trend = "↑" if slope > 50 else ("↓" if slope < -50 else "→")
    forecasts.append({
        "category": cat,
        "jan": y[0] if len(y)>0 else 0,
        "feb": y[1] if len(y)>1 else 0,
        "mar": y[2] if len(y)>2 else 0,
        "apr_forecast": round(pred, 2),
        "trend": trend,
    })

fdf = pd.DataFrame(forecasts).merge(bud, on="category", how="left")
fdf["vs_budget"]  = fdf["apr_forecast"] - fdf["monthly_budget"]
fdf["over"]       = fdf["vs_budget"] > 0

# ── INSIGHTS ──────────────────────────────────────────────────────────────

insights = []
if avg_savings_rate >= 20:
    insights.append(("✅", "Savings Rate", f"Average savings rate of {avg_savings_rate:.1f}% is healthy. Keep it up!"))
elif avg_savings_rate >= 10:
    insights.append(("⚠️", "Savings Rate", f"Savings rate of {avg_savings_rate:.1f}% is below the 20% target. Reduce Food and Entertainment spending."))
else:
    insights.append(("🔴", "Savings Rate", f"Savings rate of {avg_savings_rate:.1f}% is critically low. Review all discretionary categories."))

over_summary = cat_monthly[cat_monthly["over_budget"]].groupby("category").agg(
    months_over=("over_budget","count"), total_over=("variance","sum")
).reset_index().sort_values("total_over", ascending=False)

for _, row in over_summary.iterrows():
    icon = "🔴" if row["months_over"] >= 2 else "⚠️"
    insights.append((icon, f"{row['category']} Overspend",
        f"Over budget in {int(row['months_over'])}/3 months. Total overspend R {row['total_over']:,.0f}."))

side_by_month = income[income["category"]=="Side Income"].groupby("month")["amount"].sum()
if len(side_by_month) >= 2:
    trend_val = side_by_month.iloc[-1] - side_by_month.iloc[0]
    if trend_val > 0:
        insights.append(("✅","Side Income", f"Freelance income grew from R {side_by_month.iloc[0]:,.0f} to R {side_by_month.iloc[-1]:,.0f}. Keep growing this stream."))
    else:
        insights.append(("⚠️","Side Income", f"Freelance income dropped from R {side_by_month.iloc[0]:,.0f} to R {side_by_month.iloc[-1]:,.0f}. Find more projects."))

best_m  = monthly.loc[monthly["savings_rate"].idxmax(), "month_name"]
worst_m = monthly.loc[monthly["savings_rate"].idxmin(), "month_name"]
best_r  = monthly["savings_rate"].max()
worst_r = monthly["savings_rate"].min()
insights.append(("📅","Best Month",  f"{best_m} had the highest savings rate at {best_r:.1f}%."))
insights.append(("📅","Worst Month", f"{worst_m} had the lowest savings rate at {worst_r:.1f}%. Review spending that month."))

# ── CHARTS ────────────────────────────────────────────────────────────────

ACCENT = "#ff6b00"
ORANGE_SCALE = "Oranges"

# Income vs Expenses bar
fig_inc_exp = px.bar(monthly, x="month_name", y=["total_income","total_expenses"],
    barmode="group", title="Monthly Income vs Expenses",
    labels={"value":"Amount (R)","variable":"","month_name":"Month"},
    color_discrete_sequence=["#2ecc71","#e74c3c"], template="plotly_dark")

# Savings rate bar
fig_savings = px.bar(monthly, x="month_name", y="savings_rate",
    title="Monthly Savings Rate (%)",
    labels={"savings_rate":"Savings Rate (%)","month_name":"Month"},
    color="savings_rate", color_continuous_scale="RdYlGn",
    text="savings_rate", template="plotly_dark")
fig_savings.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
fig_savings.add_hline(y=20, line_dash="dash", line_color="white", annotation_text="Target 20%")

# Category pie
fig_pie = px.pie(cat_totals, values="total", names="category",
    title="Total Spending by Category (Jan–Mar)",
    template="plotly_dark",
    color_discrete_sequence=px.colors.qualitative.Set2)

# Category bar
fig_cat_bar = px.bar(cat_totals, x="category", y="total",
    title="Total Spending per Category",
    labels={"total":"Total (R)","category":""},
    color="total", color_continuous_scale=ORANGE_SCALE,
    template="plotly_dark")
fig_cat_bar.update_layout(xaxis_tickangle=-30)

# Income breakdown stacked bar
inc_breakdown = monthly_salary.merge(monthly_side, on=["month","month_name"], how="left").fillna(0)
inc_breakdown["month_name"] = pd.Categorical(inc_breakdown["month_name"], categories=MONTH_ORDER, ordered=True)
inc_breakdown = inc_breakdown.sort_values("month_name")
fig_inc_stack = px.bar(inc_breakdown, x="month_name", y=["salary","side_income"],
    barmode="stack", title="Income: Salary vs Side Income",
    labels={"value":"Amount (R)","variable":"","month_name":"Month"},
    color_discrete_sequence=["#3498db","#ff6b00"], template="plotly_dark")

# Budget vs actual heatmap
pivot = cat_monthly.pivot_table(index="category", columns="month_name", values="variance", aggfunc="sum")
pivot = pivot.reindex(columns=MONTH_ORDER)
fig_heatmap = px.imshow(pivot, title="Budget Variance Heatmap (Red=Over, Green=Under)",
    color_continuous_scale="RdYlGn_r",
    labels={"color":"Variance (R)"}, template="plotly_dark",
    text_auto=True)
fig_heatmap.update_traces(texttemplate="R %{z:,.0f}")

# Forecast vs budget
fig_forecast = go.Figure()
fig_forecast.add_trace(go.Bar(name="Budget", x=fdf["category"], y=fdf["monthly_budget"], marker_color="#555555"))
fig_forecast.add_trace(go.Bar(name="Apr Forecast", x=fdf["category"], y=fdf["apr_forecast"], marker_color=ACCENT))
fig_forecast.update_layout(barmode="group", title="April 2024 Forecast vs Budget",
    xaxis_title="Category", yaxis_title="Amount (R)",
    template="plotly_dark", xaxis_tickangle=-30)

# Daily expense scatter
fig_daily = px.scatter(expenses, x="date", y="amount",
    color="category", size="amount", size_max=18,
    title="Daily Expense Transactions",
    labels={"amount":"Amount (R)","date":"Date"},
    template="plotly_dark")

# ── THEME ─────────────────────────────────────────────────────────────────

BG      = "#0a0a0a"
BG_CARD = "#111111"
BG_CHART= "#1a1a1a"
TEXT    = "#ffffff"
MUTED   = "#888888"

CARD = {
    "background": BG_CARD, "borderRadius": "12px",
    "padding": "18px 22px", "textAlign": "center",
    "flex": "1", "margin": "6px", "minWidth": "130px",
    "border": "1px solid #222",
    "boxShadow": "0 4px 12px rgba(0,0,0,0.5)"
}
CHART_CARD = {
    "background": BG_CHART, "borderRadius": "12px",
    "padding": "10px", "flex": "1", "minWidth": "320px", "margin": "8px"
}
NAV_LINK = {
    "color": MUTED, "textDecoration": "none",
    "padding": "8px 16px", "borderRadius": "8px",
    "fontSize": "13px", "fontWeight": "500"
}
NAV_ACTIVE = {**NAV_LINK, "color": TEXT, "background": ACCENT}

# ── COMPONENTS ────────────────────────────────────────────────────────────

def kpi(label, value, color=TEXT):
    return html.Div([
        html.P(label, style={"color": MUTED, "margin": "0 0 4px 0",
               "fontSize": "10px", "textTransform": "uppercase", "letterSpacing": "1px"}),
        html.H3(value, style={"color": color, "margin": "0", "fontSize": "19px", "fontWeight": "700"}),
    ], style=CARD)


def navbar(current):
    pages = [
        ("/",          "🏠 Home"),
        ("/dashboard", "📊 Dashboard"),
        ("/budget",    "🎯 Budget"),
        ("/forecast",  "🔮 Forecast"),
        ("/insights",  "💡 Insights"),
    ]
    links = [html.A(label, href=path, style=NAV_ACTIVE if current==path else NAV_LINK)
             for path, label in pages]
    return html.Div(style={
        "background": BG_CARD, "padding": "0 28px",
        "display": "flex", "alignItems": "center",
        "justifyContent": "space-between", "height": "58px",
        "boxShadow": "0 2px 12px rgba(0,0,0,0.6)",
        "position": "sticky", "top": "0", "zIndex": "1000"
    }, children=[
        html.Div([
            html.Span("💰", style={"fontSize": "22px", "marginRight": "10px"}),
            html.Span("Personal Finance Analysis",
                      style={"color": TEXT, "fontWeight": "700", "fontSize": "16px"}),
        ], style={"display": "flex", "alignItems": "center"}),
        html.Div(links, style={"display": "flex", "gap": "4px", "alignItems": "center"}),
    ])


def feature_card(icon, title, desc):
    return html.Div([
        html.Div(icon, style={"fontSize": "26px", "marginBottom": "8px"}),
        html.H3(title, style={"color": TEXT, "margin": "0 0 6px 0", "fontSize": "14px"}),
        html.P(desc,   style={"color": MUTED, "margin": "0", "fontSize": "12px", "lineHeight": "1.6"}),
    ], style={**CHART_CARD, "minWidth": "180px", "padding": "16px"})


# ── PAGES ─────────────────────────────────────────────────────────────────

def page_home():
    return html.Div([
        navbar("/"),
        html.Div(style={"maxWidth": "860px", "margin": "60px auto", "padding": "0 24px"}, children=[
            html.Div(style={"textAlign": "center", "marginBottom": "48px"}, children=[
                html.Div("💰", style={"fontSize": "64px"}),
                html.H1("Personal Finance Analysis",
                    style={"color": TEXT, "fontSize": "30px", "margin": "12px 0", "fontWeight": "800"}),
                html.P("Tracking income, expenses, budget performance, and savings for a "
                       "single professional in Johannesburg — salary plus freelance side income — "
                       "across January, February, and March 2024.",
                    style={"color": MUTED, "fontSize": "15px", "lineHeight": "1.7",
                           "maxWidth": "580px", "margin": "0 auto"}),
                html.Div(style={"marginTop": "20px", "display": "flex", "gap": "10px", "justifyContent": "center"}, children=[
                    html.A("View Dashboard →", href="/dashboard",
                           style={**NAV_ACTIVE, "fontSize": "14px", "padding": "10px 24px"}),
                    html.A("View Insights →",  href="/insights",
                           style={**NAV_LINK,   "fontSize": "14px", "padding": "10px 24px",
                                  "border": f"1px solid {ACCENT}"}),
                ]),
            ]),
            html.H2("What This Project Covers",
                    style={"color": TEXT, "fontSize": "18px", "marginBottom": "14px"}),
            html.Div(style={"display": "flex", "flexWrap": "wrap", "gap": "12px", "marginBottom": "44px"}, children=[
                feature_card("📊","Income vs Expenses","Monthly comparison of total income, salary, and freelance income against total spending."),
                feature_card("🎯","Budget vs Actual","Compares spending per category against monthly budget with variance heatmap."),
                feature_card("🔮","Forecasting","Linear regression model predicting April 2024 spending per category."),
                feature_card("🚨","Anomaly Detection","Flags categories that consistently went over budget."),
                feature_card("💡","Insights","Automated financial insights and actionable recommendations."),
                feature_card("📈","Savings Rate","Tracks monthly savings rate against the 20% benchmark."),
            ]),
            html.H2("Tech Stack", style={"color": TEXT, "fontSize": "18px", "marginBottom": "12px"}),
            html.Div(style={"display": "flex", "flexWrap": "wrap", "gap": "10px", "marginBottom": "40px"}, children=[
                html.Span(t, style={"background": ACCENT, "color": TEXT, "padding": "6px 14px",
                                    "borderRadius": "20px", "fontSize": "12px", "fontWeight": "600"})
                for t in ["Python", "pandas", "scikit-learn", "Plotly", "Dash", "Jupyter Notebooks", "openpyxl"]
            ]),
        ])
    ])


def page_dashboard():
    return html.Div([
        navbar("/dashboard"),
        html.Div(style={"padding": "24px 28px", "background": BG, "minHeight": "100vh"}, children=[
            html.H2("📊 Overview Dashboard", style={"color": TEXT, "margin": "0 0 4px 0"}),
            html.P("Jan–Mar 2024  •  Single professional  •  Johannesburg  •  All values in ZAR",
                   style={"color": MUTED, "margin": "0 0 20px 0", "fontSize": "12px"}),

            # KPI row
            html.Div(style={"display": "flex", "flexWrap": "wrap", "marginBottom": "20px"}, children=[
                kpi("Total Income (3 months)",   f"R {total_income:,.0f}",    "#2ecc71"),
                kpi("Total Expenses",            f"R {total_expenses:,.0f}",  "#e74c3c"),
                kpi("Net Saved",                 f"R {net_saved:,.0f}",       "#3498db"),
                kpi("Avg Savings Rate",          f"{avg_savings_rate:.1f}%",
                    "#2ecc71" if avg_savings_rate >= 20 else "#e67e22"),
                kpi("Freelance Earned",          f"R {total_side:,.0f}",      ACCENT),
                kpi("Side Income %",             f"{side_pct:.1f}%",          ACCENT),
                kpi("Budget Compliance",         f"{compliance:.1f}%",
                    "#2ecc71" if compliance >= 70 else "#e74c3c"),
            ]),

            # Row 1
            html.Div(style={"display": "flex", "flexWrap": "wrap"}, children=[
                html.Div(dcc.Graph(figure=fig_inc_exp,   config={"displayModeBar": False}), style={**CHART_CARD,"flex":"1"}),
                html.Div(dcc.Graph(figure=fig_savings,   config={"displayModeBar": False}), style={**CHART_CARD,"flex":"1"}),
            ]),
            # Row 2
            html.Div(style={"display": "flex", "flexWrap": "wrap"}, children=[
                html.Div(dcc.Graph(figure=fig_inc_stack, config={"displayModeBar": False}), style={**CHART_CARD,"flex":"1"}),
                html.Div(dcc.Graph(figure=fig_pie,       config={"displayModeBar": False}), style={**CHART_CARD,"flex":"1"}),
            ]),
            # Row 3
            html.Div(dcc.Graph(figure=fig_cat_bar,   config={"displayModeBar": False}), style={**CHART_CARD}),
            html.Div(dcc.Graph(figure=fig_daily,     config={"displayModeBar": False}), style={**CHART_CARD}),
        ])
    ])


def page_budget():
    # Build per-month budget vs actual charts
    month_charts = []
    for month in MONTH_ORDER:
        data = cat_monthly[cat_monthly["month_name"] == month].copy()
        fig = px.bar(data, x="category", y=["monthly_budget","actual"],
            barmode="group",
            title=f"Budget vs Actual — {month}",
            labels={"value":"Amount (R)","variable":"","category":"Category"},
            color_discrete_map={"monthly_budget":"#555555","actual":ACCENT},
            template="plotly_dark")
        fig.update_layout(xaxis_tickangle=-30)
        month_charts.append(
            html.Div(dcc.Graph(figure=fig, config={"displayModeBar": False}),
                     style={**CHART_CARD, "flex": "1"})
        )

    # Over budget table
    over = over_summary = cat_monthly[cat_monthly["over_budget"]].copy()
    over = over.sort_values("variance", ascending=False)
    TH   = {"padding":"10px 14px","color":MUTED,"fontSize":"11px",
             "textTransform":"uppercase","borderBottom":f"2px solid {ACCENT}"}
    rows = [html.Tr([
        html.Td(r["month_name"], style={"padding":"10px 14px","color":TEXT}),
        html.Td(r["category"],   style={"padding":"10px 14px","color":TEXT}),
        html.Td(f"R {r['monthly_budget']:,.0f}", style={"padding":"10px 14px","color":MUTED}),
        html.Td(f"R {r['actual']:,.0f}",         style={"padding":"10px 14px","color":"#e74c3c","fontWeight":"700"}),
        html.Td(f"+R {r['variance']:,.0f}",       style={"padding":"10px 14px","color":"#e74c3c"}),
        html.Td(f"{r['pct_of_budget']:.1f}%",    style={"padding":"10px 14px","color":MUTED}),
    ], style={"borderBottom":"1px solid #222"})
    for _, r in over.iterrows()]

    return html.Div([
        navbar("/budget"),
        html.Div(style={"padding": "24px 28px", "background": BG, "minHeight": "100vh"}, children=[
            html.H2("🎯 Budget vs Actual", style={"color": TEXT, "margin": "0 0 4px 0"}),
            html.P("Monthly budget compliance per spending category",
                   style={"color": MUTED, "margin": "0 0 20px 0", "fontSize": "12px"}),

            html.Div(style={"display": "flex", "flexWrap": "wrap", "marginBottom": "20px"}, children=[
                kpi("Total Budget (3m)", f"R {total_budget_3m:,.0f}", TEXT),
                kpi("Total Actual (3m)", f"R {total_expenses:,.0f}",  "#e74c3c" if variance_3m > 0 else "#2ecc71"),
                kpi("Overall Variance",  f"R {variance_3m:+,.0f}",    "#e74c3c" if variance_3m > 0 else "#2ecc71"),
                kpi("Compliance Rate",   f"{compliance:.1f}%",         "#2ecc71" if compliance >= 70 else "#e74c3c"),
            ]),

            # Per-month charts
            html.Div(style={"display": "flex", "flexWrap": "wrap"}, children=month_charts),

            # Heatmap
            html.Div(dcc.Graph(figure=fig_heatmap, config={"displayModeBar": False}),
                     style={**CHART_CARD}),

            # Over-budget table
            html.Div(style={**CHART_CARD, "marginTop": "8px"}, children=[
                html.H3("Over-Budget Entries", style={"color": TEXT, "margin": "8px 8px 16px 8px", "fontSize": "14px"}),
                html.Table(style={"width":"100%","borderCollapse":"collapse"}, children=[
                    html.Thead(html.Tr([
                        html.Th("Month",    style=TH),
                        html.Th("Category", style=TH),
                        html.Th("Budget",   style=TH),
                        html.Th("Actual",   style=TH),
                        html.Th("Overspend",style=TH),
                        html.Th("% of Budget",style=TH),
                    ])),
                    html.Tbody(rows),
                ]),
            ]),
        ])
    ])


def page_forecast():
    TH = {"padding":"10px 14px","color":MUTED,"fontSize":"11px",
          "textTransform":"uppercase","borderBottom":f"2px solid {ACCENT}"}

    rows = [html.Tr([
        html.Td(r["category"],           style={"padding":"10px 14px","color":TEXT}),
        html.Td(f"R {r['jan']:,.0f}",    style={"padding":"10px 14px","color":MUTED}),
        html.Td(f"R {r['feb']:,.0f}",    style={"padding":"10px 14px","color":MUTED}),
        html.Td(f"R {r['mar']:,.0f}",    style={"padding":"10px 14px","color":MUTED}),
        html.Td(f"R {r['apr_forecast']:,.0f}",style={"padding":"10px 14px","color":ACCENT,"fontWeight":"700"}),
        html.Td(r["trend"],              style={"padding":"10px 14px","color":"#2ecc71" if r["trend"]=="↓" else "#e74c3c" if r["trend"]=="↑" else TEXT}),
        html.Td("⚠️ Over" if r["over"] else "✅ OK",
                style={"padding":"10px 14px","color":"#e74c3c" if r["over"] else "#2ecc71","fontWeight":"600"}),
    ], style={"borderBottom":"1px solid #222"})
    for _, r in fdf.iterrows()]

    total_f = fdf["apr_forecast"].sum()
    total_b = fdf["monthly_budget"].sum()

    return html.Div([
        navbar("/forecast"),
        html.Div(style={"padding": "24px 28px", "background": BG, "minHeight": "100vh"}, children=[
            html.H2("🔮 April 2024 Forecast", style={"color": TEXT, "margin": "0 0 4px 0"}),
            html.P("Linear regression trained on Jan–Mar 2024 spending data",
                   style={"color": MUTED, "margin": "0 0 20px 0", "fontSize": "12px"}),

            html.Div(style={"display": "flex", "flexWrap": "wrap", "marginBottom": "20px"}, children=[
                kpi("Total Forecast Spend", f"R {total_f:,.0f}", "#e74c3c" if total_f > total_b else "#2ecc71"),
                kpi("Monthly Budget",       f"R {total_b:,.0f}", TEXT),
                kpi("Forecast Variance",    f"R {total_f - total_b:+,.0f}", "#e74c3c" if total_f > total_b else "#2ecc71"),
                kpi("Categories Over Budget",str(fdf["over"].sum()), "#e74c3c" if fdf["over"].sum() > 0 else "#2ecc71"),
            ]),

            html.Div(dcc.Graph(figure=fig_forecast, config={"displayModeBar": False}),
                     style={**CHART_CARD}),

            html.Div(style={**CHART_CARD, "marginTop": "8px"}, children=[
                html.H3("Category Forecasts", style={"color": TEXT, "margin": "8px 8px 16px 8px", "fontSize": "14px"}),
                html.Table(style={"width":"100%","borderCollapse":"collapse"}, children=[
                    html.Thead(html.Tr([
                        html.Th("Category", style=TH), html.Th("Jan", style=TH),
                        html.Th("Feb", style=TH),      html.Th("Mar", style=TH),
                        html.Th("Apr Forecast", style=TH), html.Th("Trend", style=TH),
                        html.Th("vs Budget", style=TH),
                    ])),
                    html.Tbody(rows),
                ]),
            ]),
        ])
    ])


def page_insights():
    cards = []
    icon_colors = {"✅": "#2ecc71", "⚠️": "#f39c12", "🔴": "#e74c3c", "📅": "#3498db", "📊": ACCENT}
    for icon, title, msg in insights:
        border_color = icon_colors.get(icon, MUTED)
        cards.append(html.Div(style={
            **CHART_CARD, "borderLeft": f"4px solid {border_color}",
            "padding": "16px 20px", "minWidth": "280px"
        }, children=[
            html.Div(style={"display":"flex","alignItems":"center","marginBottom":"8px"}, children=[
                html.Span(icon,   style={"fontSize":"20px","marginRight":"10px"}),
                html.Span(title,  style={"color":TEXT,"fontWeight":"700","fontSize":"14px"}),
            ]),
            html.P(msg, style={"color":MUTED,"margin":"0","fontSize":"13px","lineHeight":"1.6"}),
        ]))

    recs = [
        ("Automate savings", "Set up a debit order on salary day. Pay yourself first before any other expense."),
        ("48-hour rule for clothing", "Wait 48 hours before any clothing purchase over R 500. February's R 2,800 overspend shows impulse buying."),
        ("Meal prep Sundays", f"Food at R {expenses[expenses['category']=='Food']['amount'].sum()/3:,.0f}/month is above budget. Preparing meals weekly reduces takeaway spend."),
        ("Reinvest side income", f"Put 100% of freelance income (avg R {total_side/3:,.0f}/month) into savings or an emergency fund — not lifestyle."),
        ("Entertainment envelope", "Set a monthly cash envelope for entertainment. Once it's gone, it's gone. Stops the pattern of two over-budget months."),
    ]

    rec_cards = [html.Div(style={
        **CHART_CARD, "borderLeft": f"4px solid {ACCENT}",
        "padding": "16px 20px", "minWidth": "260px"
    }, children=[
        html.H4(f"💡 {title}", style={"color":ACCENT,"margin":"0 0 8px 0","fontSize":"13px"}),
        html.P(msg, style={"color":MUTED,"margin":"0","fontSize":"13px","lineHeight":"1.6"}),
    ]) for title, msg in recs]

    return html.Div([
        navbar("/insights"),
        html.Div(style={"padding":"24px 28px","background":BG,"minHeight":"100vh"}, children=[
            html.H2("💡 Financial Insights", style={"color":TEXT,"margin":"0 0 4px 0"}),
            html.P("Automated insights generated from Jan–Mar 2024 spending data",
                   style={"color":MUTED,"margin":"0 0 20px 0","fontSize":"12px"}),

            html.Div(style={"display":"flex","flexWrap":"wrap","marginBottom":"20px"}, children=[
                kpi("Avg Savings Rate",  f"{avg_savings_rate:.1f}%",  "#2ecc71" if avg_savings_rate>=20 else "#e74c3c"),
                kpi("Budget Compliance", f"{compliance:.1f}%",         "#2ecc71" if compliance>=70 else "#e74c3c"),
                kpi("Total Freelance",   f"R {total_side:,.0f}",       ACCENT),
                kpi("Net Saved (3m)",    f"R {net_saved:,.0f}",        "#2ecc71" if net_saved>0 else "#e74c3c"),
            ]),

            html.H3("Insights", style={"color":TEXT,"fontSize":"16px","margin":"0 0 12px 8px"}),
            html.Div(style={"display":"flex","flexWrap":"wrap"}, children=cards),

            html.H3("Recommendations", style={"color":TEXT,"fontSize":"16px","margin":"20px 0 12px 8px"}),
            html.Div(style={"display":"flex","flexWrap":"wrap"}, children=rec_cards),
        ])
    ])


# ── APP ───────────────────────────────────────────────────────────────────

app = Dash(__name__, suppress_callback_exceptions=True)

app.layout = html.Div(
    style={"background": BG, "minHeight": "100vh",
           "fontFamily": "'Segoe UI', Arial, sans-serif"},
    children=[
        dcc.Location(id="url", refresh=False),
        html.Div(id="page-content"),
    ]
)


@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def display_page(pathname):
    if pathname == "/" or pathname is None:
        return page_home()
    elif pathname == "/dashboard":
        return page_dashboard()
    elif pathname == "/budget":
        return page_budget()
    elif pathname == "/forecast":
        return page_forecast()
    elif pathname == "/insights":
        return page_insights()
    else:
        return html.Div([
            navbar("/"),
            html.Div(style={"textAlign":"center","marginTop":"100px"}, children=[
                html.H1("404", style={"color":ACCENT,"fontSize":"64px","margin":"0"}),
                html.P("Page not found.", style={"color":MUTED,"fontSize":"16px"}),
                html.A("← Home", href="/", style={**NAV_ACTIVE,"display":"inline-block","marginTop":"14px"}),
            ])
        ])


if __name__ == "__main__":
    print("\n💰 Personal Finance Dashboard starting...")
    print("   Open http://127.0.0.1:8050 in your browser")
    print("   Press Ctrl+C to stop\n")
    app.run(debug=True)
