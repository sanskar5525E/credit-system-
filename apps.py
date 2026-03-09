import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import io

st.set_page_config(page_title="Wholesale Credit Risk Dashboard", layout="wide")

st.title("📊 Wholesale Customer Risk Dashboard")

def format_inr(x):
    return f"₹{x:,.2f}"

def clean_data(df):
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

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

    date_cols = ["invoice_date", "due_date", "payment_date"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df["paid_amount"] = pd.to_numeric(df["paid_amount"], errors="coerce").fillna(0)

    if "payment_date" not in df.columns:
        df["payment_date"] = pd.NaT

    df = df[df["amount"] > 0]
    return df

def calculate_invoice_metrics(df, today):
    df = df.copy()
    df["outstanding"] = df["amount"] - df["paid_amount"]
    df["outstanding"] = df["outstanding"].clip(lower=0)

    df["overdue_days"] = 0
    mask_unpaid = (df["outstanding"] > 0) & (df["due_date"] < today)
    df.loc[mask_unpaid, "overdue_days"] = (
        today - df.loc[mask_unpaid, "due_date"]
    ).dt.days

    mask_paid_late = (
        (df["paid_amount"] >= df["amount"]) &
        df["payment_date"].notna() &
        (df["payment_date"] > df["due_date"])
    )
    df.loc[mask_paid_late, "overdue_days"] = (
        df.loc[mask_paid_late, "payment_date"] -
        df.loc[mask_paid_late, "due_date"]
    ).dt.days

    df["paid_late"] = False
    df.loc[mask_paid_late, "paid_late"] = True

    return df

def calculate_risk_score(row):
    score = 0
    max_days = row["max_overdue_days"]
    if max_days > 0:
        if max_days <= 30:
            score += 10
        elif max_days <= 60:
            score += 20
        elif max_days <= 90:
            score += 30
        else:
            score += 40

    if row["total_amount"] > 0:
        overdue_ratio = row["total_outstanding"] / row["total_amount"]
        score += overdue_ratio * 50

    if row["total_paid_invoices"] > 0:
        late_ratio = row["late_paid_count"] / row["total_paid_invoices"]
        score += late_ratio * 10

    return min(round(score), 100)

def assign_risk_grade(score):
    if score <= 10:
        return "A"
    elif score <= 30:
        return "B"
    elif score <= 60:
        return "C"
    else:
        return "D"

def aggregate_customer(df, today):
    customers = []
    for name, group in df.groupby("customer_name"):
        total_amount = group["amount"].sum()
        total_paid = group["paid_amount"].sum()
        total_outstanding = total_amount - total_paid

        overdue = group[group["overdue_days"] > 0]
        max_overdue_days = overdue["overdue_days"].max() if not overdue.empty else 0

        late_paid_count = group["paid_late"].sum()
        total_paid_invoices = group[group["paid_amount"] >= group["amount"]].shape[0]

        avg_delay = group[group["paid_late"]]["overdue_days"].mean()
        if pd.isna(avg_delay):
            avg_delay = 0

        row = {
            "max_overdue_days": max_overdue_days,
            "total_outstanding": total_outstanding,
            "total_amount": total_amount,
            "late_paid_count": late_paid_count,
            "total_paid_invoices": total_paid_invoices
        }

        risk_score = calculate_risk_score(row)
        grade = assign_risk_grade(risk_score)

        if grade == "A":
            credit_limit = total_amount * 1.2
        elif grade == "B":
            credit_limit = total_amount * 0.8
        elif grade == "C":
            credit_limit = total_amount * 0.5
        else:
            credit_limit = 0

        if grade == "D":
            dispatch = "⛔ Stop Sales"
        elif grade == "C":
            dispatch = "⚠️ Credit Risk"
        else:
            dispatch = "✅ Allowed"

        customers.append({
            "customer_name": name,
            "total_invoices": group.shape[0],
            "total_amount": total_amount,
            "total_paid": total_paid,
            "total_outstanding": total_outstanding,
            "max_overdue_days": max_overdue_days,
            "avg_payment_delay": round(avg_delay, 1),
            "risk_score": risk_score,
            "risk_grade": grade,
            "suggested_credit_limit": credit_limit,
            "sales_status": dispatch
        })

    customer_df = pd.DataFrame(customers)

    rec_map = {
        "A": "✅ Safe customer",
        "B": "⚠️ Monitor occasionally",
        "C": "🟠 Reduce credit",
        "D": "🔴 Collect urgently"
    }
    customer_df["recommendation"] = customer_df["risk_grade"].map(rec_map)

    return customer_df

def color_grade(val):
    if val == "A":
        return "background-color:#1b5e20; color:white"
    elif val == "B":
        return "background-color:#f9a825; color:black"
    elif val == "C":
        return "background-color:#ef6c00; color:white"
    elif val == "D":
        return "background-color:#c62828; color:white"
    return ""

def collection_priority(df):
    df = df.copy()
    df["priority_score"] = (
        df["total_outstanding"] * 0.5 +
        df["max_overdue_days"] * 50 +
        df["risk_score"] * 20
    )
    return df.sort_values("priority_score", ascending=False)

# Main app
uploaded_file = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])

if uploaded_file is not None:
    if uploaded_file.name.endswith(".csv"):
        df_raw = pd.read_csv(uploaded_file)
    else:
        df_raw = pd.read_excel(uploaded_file)
else:
    df_raw = None

if df_raw is not None:
    today = pd.Timestamp.now().normalize()

    df_clean = clean_data(df_raw)
    df_inv = calculate_invoice_metrics(df_clean, today)
    customer_summary = aggregate_customer(df_inv, today)

    st.success("Data processed successfully")

    st.header("👥 Customer Risk Summary")
    display_df = customer_summary.copy()
    for col in ["total_amount", "total_paid", "total_outstanding", "suggested_credit_limit"]:
        display_df[col] = display_df[col].apply(format_inr)

    # Use map instead of applymap for pandas >=2.0
    styled = display_df.style.map(color_grade, subset=["risk_grade"])
    st.dataframe(styled, use_container_width=True)

    st.header("📊 Risk Distribution")
    grade_counts = customer_summary["risk_grade"].value_counts().reindex(["A", "B", "C", "D"], fill_value=0)
    fig = px.bar(
        x=grade_counts.index,
        y=grade_counts.values,
        color=grade_counts.index,
        color_discrete_map={"A": "green", "B": "gold", "C": "orange", "D": "red"}
    )
    st.plotly_chart(fig, use_container_width=True)

    st.header("📞 Customers To Collect")
    priority_df = collection_priority(customer_summary)
    st.dataframe(priority_df.head(10), use_container_width=True)

    st.header("📥 Download Report")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        customer_summary.to_excel(writer, sheet_name="Customer Summary", index=False)
        df_inv.to_excel(writer, sheet_name="Invoice Details", index=False)

    st.download_button(
        "Download Excel",
        data=output.getvalue(),
        file_name=f"risk_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
