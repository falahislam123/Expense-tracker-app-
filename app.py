%%writefile app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

import database as db
from ai_helper import get_ai_tips

st.set_page_config(page_title="AI Expense Tracker", page_icon="💰", layout="wide")
db.init_db()

st.title("💰 AI Expense Tracker")

# ----- SIDEBAR: add a transaction -----
st.sidebar.header("➕ Add Transaction")
t_type = st.sidebar.selectbox("Type", ["Expense", "Income"])

if t_type == "Expense":
    categories = ["Food", "Transport", "Rent", "Bills", "Shopping",
                  "Health", "Entertainment", "Education", "Other"]
else:
    categories = ["Salary", "Business", "Gift", "Other"]

category = st.sidebar.selectbox("Category", categories)
amount = st.sidebar.number_input("Amount", min_value=0.0, step=100.0)
t_date = st.sidebar.date_input("Date", date.today())
note = st.sidebar.text_input("Note (optional)")

if st.sidebar.button("Add Transaction"):
    if amount > 0:
        db.add_transaction(t_type, category, amount, str(t_date), note)
        st.sidebar.success("Saved!")
    else:
        st.sidebar.error("Please enter an amount greater than 0.")

# ----- SIDEBAR: monthly budget -----
st.sidebar.header("📅 Monthly Budget")
month_options = [
    (pd.Timestamp.today() - pd.DateOffset(months=i)).strftime("%Y-%m")
    for i in range(12)
]
month = st.sidebar.selectbox("Month", month_options)

saved_budget = db.get_budget(month)
budget = st.sidebar.number_input(
    "Budget amount", min_value=0.0, value=float(saved_budget),
    step=1000.0, key=f"budget_{month}",
)
if st.sidebar.button("Save Budget"):
    db.set_budget(month, budget)
    st.sidebar.success("Budget saved!")

# ----- LOAD DATA -----
df = db.get_transactions()
if df.empty:
    st.info("No data yet. Add your first transaction from the sidebar 👈")
    st.stop()

df["month"] = df["date"].str[:7]          # '2026-10-25' -> '2026-10'
month_df = df[df["month"] == month]

if month_df.empty:
    st.info(f"No transactions found for {month}.")
    st.stop()

# ----- TOTALS -----
income_total = month_df[month_df["type"] == "Income"]["amount"].sum()
expense_df = month_df[month_df["type"] == "Expense"]
expense_total = expense_df["amount"].sum()
balance = income_total - expense_total

c1, c2, c3 = st.columns(3)
c1.metric("Total Income", f"{income_total:,.0f}")
c2.metric("Total Expenses", f"{expense_total:,.0f}")
c3.metric("Remaining Balance", f"{balance:,.0f}")

# ----- BUDGET STATUS -----
if budget > 0:
    used = expense_total / budget
    st.progress(min(used, 1.0), text=f"Budget used: {used * 100:.0f}%")
    if expense_total > budget:
        st.error(f"⚠️ You are over budget by {expense_total - budget:,.0f}")
    else:
        st.success(f"You can still spend {budget - expense_total:,.0f} this month.")
else:
    st.info("Set a monthly budget in the sidebar to track it.")

# ----- CHARTS -----
st.subheader("📊 Charts")
category_totals = expense_df.groupby("category")["amount"].sum().sort_values(ascending=False)

if expense_df.empty:
    st.info("No expenses yet, so there is nothing to chart.")
else:
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("**Spending by category**")
        fig = px.pie(values=category_totals.values, names=category_totals.index)
        st.plotly_chart(fig)
    with col_b:
        st.write("**Spending by day**")
        daily = expense_df.groupby("date")["amount"].sum()
        st.bar_chart(daily)

# ----- TABLE + DELETE -----
st.subheader("🧾 Transactions")
st.dataframe(month_df[["id", "date", "type", "category", "amount", "note"]])

del_id = st.number_input("Transaction ID to delete", min_value=0, step=1)
if st.button("Delete"):
    db.delete_transaction(int(del_id))
    st.rerun()

# ----- AI ADVICE -----
st.subheader("🤖 AI Spending Advice")
if st.button("Analyze my spending"):
    breakdown = category_totals.to_string() if not expense_df.empty else "No expenses"
    summary = f"""Month: {month}
Total income: {income_total:,.0f}
Total expenses: {expense_total:,.0f}
Monthly budget: {budget:,.0f}
Remaining balance: {balance:,.0f}
Spending by category:
{breakdown}"""
    with st.spinner("AI is thinking..."):
        advice = get_ai_tips(summary)
    st.markdown(advice)
