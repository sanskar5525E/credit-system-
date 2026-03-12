import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import io

st.set_page_config(page_title="Wholesale Credit Risk Dashboard", layout="wide")
st.title("📊 Wholesale Customer Risk Dashboard")

# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------
def format_inr(x):
    return f"₹{x:,.2f}"

def generate_example_data():
    np.random.seed(42)
    customers = [
        "ABC Corp","XYZ Ltd","Mega Distributors",
        "Beta Stores","Gamma Inc","Delta Traders"
    ]

    data = []
    example_today = pd.Timestamp("2025-03-01")

    for cust in customers:
        n_invoices = np.random.randint(3, 10)

        for i in range(n_invoices):

            invoice_date = example_today - pd.Timedelta(days=np.random.randint(1,180))
            due_date = invoice_date + pd.Timedelta(days=30)
            amount = np.random.randint(1000,50000)

            r = np.random.rand()

            # payment patterns
            if r < 0.3:
                paid_amount = amount
                payment_date = due_date - pd.Timedelta(days=np.random.randint(0,5))

            elif r < 0.6:
                paid_amount = amount
                payment_date = due_date + pd.Timedelta(days=np.random.randint(1,60))

            elif r < 0.8:
                paid_amount = amount * np.random.uniform(0.1,0.9)
                payment_date = due_date + pd.Timedelta(days=np.random.randint(-5,90))

            else:
                paid_amount = 0
                payment_date = None

            data.append({
                "customer_name":cust,
                "invoice_no":f"INV-{cust[:3]}-{i:03d}",
                "invoice_date":invoice_date,
                "due_date":due_date,
                "amount":amount,
                "paid_amount":paid_amount,
                "payment_date":payment_date
            })

    return pd.DataFrame(data)


def clean_data(df):

    df.columns = df.columns.str.strip().str.lower().str.replace(" ","_")

    required = [
        "customer_name","invoice_no",
        "invoice_date","due_date",
        "amount","paid_amount"
    ]

    for col in required:
        if col not in df.columns:
            st.error(f"Missing column: {col}")
            st.stop()

    for col in ["invoice_date","due_date","payment_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col],errors="coerce")

    df["amount"] = pd.to_numeric(df["amount"],errors="coerce").fillna(0)
    df["paid_amount"] = pd.to_numeric(df["paid_amount"],errors="coerce").fillna(0)

    if "payment_date" not in df.columns:
        df["payment_date"] = pd.NaT

    df = df[df["amount"] > 0]

    return df


def calculate_invoice_metrics(df,today):

    df = df.copy()

    df["outstanding"] = (df["amount"] - df["paid_amount"]).clip(lower=0)

    df["fully_paid"] = df["paid_amount"] >= df["amount"]

    df["overdue_days"] = 0
    df["paid_late"] = False

    # unpaid / partial
    mask_unpaid = (df["outstanding"] > 0) & (df["due_date"] < today)

    df.loc[mask_unpaid,"overdue_days"] = (
        today - df.loc[mask_unpaid,"due_date"]
    ).dt.days

    # paid late
    mask_paid_late = (
        df["fully_paid"] &
        (df["payment_date"] > df["due_date"])
    )

    df.loc[mask_paid_late,"overdue_days"] = (
        df.loc[mask_paid_late,"payment_date"]
        - df.loc[mask_paid_late,"due_date"]
    ).dt.days

    df.loc[mask_paid_late,"paid_late"] = True

    df["overdue_days"] = df["overdue_days"].clip(lower=0, upper=180)

    return df


# ---------------------------------------------------------
# Risk Scoring
# ---------------------------------------------------------
def calculate_risk_score(row):

    overdue_score = min(row["max_overdue_days"]/90,1) * 40

    outstanding_ratio = (
        row["total_outstanding"]/row["total_amount"]
        if row["total_amount"] > 0 else 0
    )

    outstanding_score = outstanding_ratio * 40

    payment_ratio = (
        row["total_paid"]/row["total_amount"]
        if row["total_amount"] > 0 else 0
    )

    late_ratio = (
        row["late_paid_count"]/row["total_paid_invoices"]
        if row["total_paid_invoices"] > 0 else 1
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
# Customer Aggregation
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

    late_delays = df[df["paid_late"]].groupby("customer_name")["overdue_days"].mean()

    grouped["avg_payment_delay"] = (
        grouped["customer_name"].map(late_delays).fillna(0)
    )

    grouped["total_paid_invoices"] = grouped["fully_paid_count"]

    risk_rows = []

    for _,row in grouped.iterrows():

        score = calculate_risk_score(row)
        grade = assign_risk_grade(score)

        if grade == "A":
            limit = row["total_amount"] * 1.2
        elif grade == "B":
            limit = row["total_amount"] * 0.8
        elif grade == "C":
            limit = row["total_amount"] * 0.5
        else:
            limit = 0

        risk_rows.append({
            "customer_name":row["customer_name"],
            "total_invoices":row["total_invoices"],
            "total_amount":row["total_amount"],
            "total_paid":row["total_paid"],
            "total_outstanding":row["total_outstanding"],
            "max_overdue_days":row["max_overdue_days"],
            "avg_payment_delay":round(row["avg_payment_delay"],1),
            "late_paid_count":row["late_paid_count"],
            "total_paid_invoices":row["total_paid_invoices"],
            "risk_score":score,
            "risk_grade":grade,
            "suggested_credit_limit":limit,
            "payment_ratio":(
                row["total_paid"]/row["total_amount"]
                if row["total_amount"]>0 else 0
            )
        })

    customer_df = pd.DataFrame(risk_rows)

    status_map = {
        "A":"🟢 Low Risk",
        "B":"🟡 Medium Risk",
        "C":"🟠 High Risk",
        "D":"🔴 Critical"
    }

    action_map = {
        "A":"✅ Extend credit limit",
        "B":"👀 Monitor payments",
        "C":"⚠️ Reduce exposure",
        "D":"🚨 Immediate collection"
    }

    customer_df["status"] = customer_df["risk_grade"].map(status_map)
    customer_df["recommendation"] = customer_df["risk_grade"].map(action_map)

    return customer_df


# ---------------------------------------------------------
# Priority
# ---------------------------------------------------------
def collection_priority(df):

    df = df.copy()

    def norm(series):
        if series.max() == series.min():
            return pd.Series(0,index=series.index)
        return (series-series.min())/(series.max()-series.min())

    df["out_norm"] = norm(df["total_outstanding"])
    df["delay_norm"] = norm(df["max_overdue_days"])
    df["risk_norm"] = norm(df["risk_score"])

    df["priority_score"] = df["out_norm"] + df["delay_norm"] + df["risk_norm"]

    return df.sort_values("priority_score",ascending=False)


# ---------------------------------------------------------
# UI
# ---------------------------------------------------------
st.sidebar.header("Settings")

today_input = st.sidebar.date_input(
    "As of date",
    value=datetime.now().date()
)

today = pd.Timestamp(today_input)

uploaded = st.file_uploader(
    "Upload CSV or Excel",
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
# Run pipeline
# ---------------------------------------------------------
if df_raw is not None:

    df_clean = clean_data(df_raw)

    df_inv = calculate_invoice_metrics(df_clean,today)

    customer_summary = aggregate_customer(df_inv)

    st.success("Data processed")

    # KPIs
    total_customers = customer_summary.shape[0]
    total_credits = df_inv["amount"].sum()
    total_paid = customer_summary["total_paid"].sum()
    total_outstanding = customer_summary["total_outstanding"].sum()

    col1,col2,col3,col4 = st.columns(4)

    col1.metric("Customers",total_customers)
    col2.metric("Total Credit",format_inr(total_credits))
    col3.metric("Paid",format_inr(total_paid))
    col4.metric("Outstanding",format_inr(total_outstanding))

    # Table
    st.subheader("Customer Risk")

    st.dataframe(customer_summary,use_container_width=True)

    # Risk distribution
    st.subheader("Risk Distribution")

    grade_counts = (
        customer_summary["risk_grade"]
        .value_counts()
        .reindex(["A","B","C","D"],fill_value=0)
    )

    fig = px.bar(
        x=grade_counts.index,
        y=grade_counts.values,
        color=grade_counts.index
    )

    st.plotly_chart(fig,use_container_width=True)

    # Priority
    st.subheader("Customers to Call")

    priority = collection_priority(customer_summary)

    st.dataframe(
        priority.head(10),
        use_container_width=True
    )

    # Export
    st.subheader("Download Report")

    output = io.BytesIO()

    with pd.ExcelWriter(output,engine="openpyxl") as writer:
        customer_summary.to_excel(writer,sheet_name="Customers",index=False)
        df_inv.to_excel(writer,sheet_name="Invoices",index=False)

    st.download_button(
        "Download Excel",
        data=output.getvalue(),
        file_name="credit_risk_report.xlsx"
    )
