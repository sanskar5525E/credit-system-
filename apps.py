import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import io

st.set_page_config(page_title="Wholesale Credit Risk Dashboard", layout="wide")

st.title("📊 Wholesale Credit Risk Dashboard")
st.caption("Identify risky customers, track overdue payments, and prioritize collections.")

# ---------------------------------------------------------
# Helper
# ---------------------------------------------------------

def format_inr(x):
    return f"₹{x:,.0f}"

# ---------------------------------------------------------
# Example data
# ---------------------------------------------------------

def generate_example_data():

    np.random.seed(42)

    customers = [
        "ABC Corp","XYZ Ltd","Mega Distributors",
        "Beta Stores","Gamma Inc","Delta Traders"
    ]

    data = []
    example_today = pd.Timestamp("2026-01-01")

    for cust in customers:

        n = np.random.randint(3,8)

        for i in range(n):

            invoice_date = example_today - pd.Timedelta(days=np.random.randint(30,200))
            due_date = invoice_date + pd.Timedelta(days=30)

            amount = np.random.randint(2000,40000)

            r = np.random.rand()

            if r < 0.3:
                paid_amount = amount
                payment_date = due_date - pd.Timedelta(days=np.random.randint(1,5))

            elif r < 0.6:
                paid_amount = amount
                payment_date = due_date + pd.Timedelta(days=np.random.randint(5,40))

            elif r < 0.8:
                paid_amount = amount * np.random.uniform(0.2,0.8)
                payment_date = due_date + pd.Timedelta(days=np.random.randint(-5,60))

            else:
                paid_amount = 0
                payment_date = None

            data.append({
                "customer_name":cust,
                "invoice_no":f"INV-{cust[:3]}-{i}",
                "invoice_date":invoice_date,
                "due_date":due_date,
                "amount":amount,
                "paid_amount":paid_amount,
                "payment_date":payment_date
            })

    return pd.DataFrame(data)

# ---------------------------------------------------------
# Cleaning
# ---------------------------------------------------------

def clean_data(df):

    df.columns = df.columns.str.lower().str.strip().str.replace(" ","_")

    required = [
        "customer_name",
        "invoice_no",
        "invoice_date",
        "due_date",
        "amount",
        "paid_amount"
    ]

    for col in required:
        if col not in df.columns:
            st.error(f"Missing column: {col}")
            st.stop()

    for c in ["invoice_date","due_date","payment_date"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c],errors="coerce")

    df["amount"] = pd.to_numeric(df["amount"],errors="coerce").fillna(0)
    df["paid_amount"] = pd.to_numeric(df["paid_amount"],errors="coerce").fillna(0)

    if "payment_date" not in df.columns:
        df["payment_date"] = pd.NaT

    df = df[df["amount"]>0]

    return df

# ---------------------------------------------------------
# Invoice metrics
# ---------------------------------------------------------

def calculate_invoice_metrics(df,today):

    df = df.copy()

    df["outstanding"] = (df["amount"] - df["paid_amount"]).clip(lower=0)

    df["fully_paid"] = df["paid_amount"] >= df["amount"]

    df["overdue_days"] = 0
    df["paid_late"] = False

    mask_unpaid = (df["outstanding"] > 0) & (df["due_date"] < today)

    df.loc[mask_unpaid,"overdue_days"] = (
        today - df.loc[mask_unpaid,"due_date"]
    ).dt.days

    mask_paid_late = (
        df["fully_paid"] &
        (df["payment_date"] > df["due_date"])
    )

    df.loc[mask_paid_late,"overdue_days"] = (
        df.loc[mask_paid_late,"payment_date"] -
        df.loc[mask_paid_late,"due_date"]
    ).dt.days

    df.loc[mask_paid_late,"paid_late"] = True

    df["overdue_days"] = df["overdue_days"].clip(lower=0,upper=180)

    return df

# ---------------------------------------------------------
# Risk scoring
# ---------------------------------------------------------

def calculate_risk_score(row):

    overdue_score = min(row["max_overdue_days"]/90,1) * 40

    outstanding_ratio = (
        row["total_outstanding"]/row["total_amount"]
        if row["total_amount"]>0 else 0
    )

    outstanding_score = outstanding_ratio * 40

    payment_ratio = (
        row["total_paid"]/row["total_amount"]
        if row["total_amount"]>0 else 0
    )

    late_ratio = (
        row["late_paid_count"]/row["total_paid_invoices"]
        if row["total_paid_invoices"]>0 else 1
    )

    behaviour_score = (1-payment_ratio)*10 + late_ratio*10
    behaviour_score = min(behaviour_score,20)

    score = overdue_score + outstanding_score + behaviour_score

    return min(round(score),100)

def assign_risk_grade(score):

    if score <= 10:
        return "A"
    elif score <= 30:
        return "B"
    elif score <= 60:
        return "C"
    else:
        return "D"

# ---------------------------------------------------------
# Customer aggregation
# ---------------------------------------------------------

def aggregate_customer(df):

    grouped = df.groupby("customer_name").agg(
        total_invoices=("invoice_no","count"),
        total_amount=("amount","sum"),
        total_paid=("paid_amount","sum"),
        max_overdue_days=("overdue_days","max"),
        late_paid_count=("paid_late","sum"),
        fully_paid_count=("fully_paid","sum")
    ).reset_index()

    grouped["total_outstanding"] = (
        grouped["total_amount"] - grouped["total_paid"]
    ).clip(lower=0)

    late_delay = df[df["paid_late"]].groupby("customer_name")["overdue_days"].mean()

    grouped["avg_payment_delay"] = grouped["customer_name"].map(late_delay).fillna(0)

    grouped["total_paid_invoices"] = grouped["fully_paid_count"]

    rows = []

    for _,r in grouped.iterrows():

        score = calculate_risk_score(r)
        grade = assign_risk_grade(score)

        if grade=="A":
            limit = r["total_amount"]*1.2
        elif grade=="B":
            limit = r["total_amount"]*0.8
        elif grade=="C":
            limit = r["total_amount"]*0.5
        else:
            limit = 0

        rows.append({
            "Customer":r["customer_name"],
            "Total Credit":r["total_amount"],
            "Total Paid":r["total_paid"],
            "Outstanding":r["total_outstanding"],
            "Max Delay":r["max_overdue_days"],
            "Avg Delay":round(r["avg_payment_delay"],1),
            "Risk Score":score,
            "Risk Grade":grade,
            "Suggested Limit":limit
        })

    return pd.DataFrame(rows)

# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------

st.sidebar.header("⚙️ Settings")

today_input = st.sidebar.date_input(
    "Calculation Date",
    value=datetime.now().date()
)

today = pd.Timestamp(today_input)

st.caption(f"📅 Calculated as of: {today.strftime('%d %B %Y')}")

# ---------------------------------------------------------
# Template
# ---------------------------------------------------------

template = pd.DataFrame({
"customer_name":["ABC Stores"],
"invoice_no":["INV001"],
"invoice_date":["2026-01-01"],
"due_date":["2026-01-31"],
"amount":[10000],
"paid_amount":[5000],
"payment_date":["2026-02-10"]
})

st.download_button(
"📄 Download Upload Template",
template.to_csv(index=False),
"invoice_template.csv"
)

# ---------------------------------------------------------
# Upload
# ---------------------------------------------------------

uploaded = st.file_uploader(
"Upload invoice file",
type=["csv","xlsx"]
)

if uploaded:

    if uploaded.name.endswith(".csv"):
        df_raw = pd.read_csv(uploaded)
    else:
        df_raw = pd.read_excel(uploaded)

else:

    if st.button("Load Example Data"):
        df_raw = generate_example_data()
    else:
        df_raw = None

# ---------------------------------------------------------
# Run
# ---------------------------------------------------------

if df_raw is not None:

    df_clean = clean_data(df_raw)

    df_inv = calculate_invoice_metrics(df_clean,today)

    customer_summary = aggregate_customer(df_inv)

    st.success("Data processed successfully")

    # KPIs
    col1,col2,col3,col4 = st.columns(4)

    col1.metric("Customers",customer_summary.shape[0])
    col2.metric("Total Credit",format_inr(df_inv["amount"].sum()))
    col3.metric("Total Paid",format_inr(customer_summary["Total Paid"].sum()))
    col4.metric("Outstanding",format_inr(customer_summary["Outstanding"].sum()))

    overdue_amt = df_inv[df_inv["overdue_days"]>0]["outstanding"].sum()

    st.metric("Total Overdue Amount",format_inr(overdue_amt))

    # Filter
    risk_filter = st.selectbox(
        "Filter Risk Level",
        ["All","A","B","C","D"]
    )

    if risk_filter!="All":
        customer_summary = customer_summary[
            customer_summary["Risk Grade"]==risk_filter
        ]

    # Table
    st.subheader("Customer Risk Analysis")

    st.dataframe(customer_summary,use_container_width=True)

    # Chart
    st.subheader("Risk Distribution")

    risk_counts = customer_summary["Risk Grade"].value_counts()

    fig = px.bar(
        x=risk_counts.index,
        y=risk_counts.values,
        labels={"x":"Risk Grade","y":"Customers"},
        color=risk_counts.index
    )

    st.plotly_chart(fig,use_container_width=True)

    # Export
    st.subheader("Export Report")

    output = io.BytesIO()

    with pd.ExcelWriter(output,engine="openpyxl") as writer:

        customer_summary.to_excel(writer,sheet_name="Customer Risk",index=False)
        df_inv.to_excel(writer,sheet_name="Invoice Data",index=False)

    st.download_button(
        "⬇ Download Excel Report",
        output.getvalue(),
        "credit_risk_report.xlsx"
    )
