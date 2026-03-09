
import streamlit as st
import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import plotly.express as px
import io

st.set_page_config(page_title="Wholesale Credit Risk Dashboard", layout="wide")
st.title("📊 Wholesale Customer Risk Dashboard")

def format_inr(x):
    return f"₹{x:,.2f}"

def generate_example_data():
    np.random.seed(42)
    random.seed(42)
    customers = ['ABC Corp', 'XYZ Ltd', 'Mega Distributors', 'Beta Stores', 'Gamma Inc', 'Delta Traders']
    data = []
    today = pd.Timestamp.now().normalize()
    for cust in customers:
        n_invoices = np.random.randint(3, 10)
        for i in range(n_invoices):
            invoice_date = today - pd.Timedelta(days=np.random.randint(1, 180))
            due_date = invoice_date + pd.Timedelta(days=30)
            amount = np.random.randint(1000, 50000)
            if np.random.rand() > 0.3:
                paid_amount = amount
                payment_date = due_date + pd.Timedelta(days=np.random.randint(-5, 60))
            else:
                paid_amount = amount * np.random.uniform(0, 0.9)
                payment_date = pd.NaT
            data.append({
                'customer_name': cust,
                'invoice_no': f'INV-{cust[:3]}-{i:03d}',
                'invoice_date': invoice_date,
                'due_date': due_date,
                'amount': amount,
                'paid_amount': paid_amount,
                'payment_date': payment_date if not pd.isna(payment_date) else None
            })
    return pd.DataFrame(data)

def clean_data(df):
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    required = ["customer_name", "invoice_no", "invoice_date", "due_date", "amount", "paid_amount"]
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
    df.loc[mask_unpaid, "overdue_days"] = (today - df.loc[mask_unpaid, "due_date"]).dt.days
    mask_paid_late = (
        (df["paid_amount"] >= df["amount"]) &
        df["payment_date"].notna() &
        (df["payment_date"] > df["due_date"])
    )
    df.loc[mask_paid_late, "overdue_days"] = (df.loc[mask_paid_late, "payment_date"] - df.loc[mask_paid_late, "due_date"]).dt.days
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
        avg_delay = 0 if pd.isna(avg_delay) else avg_delay
        row = {
            "customer_name": name,
            "total_invoices": group.shape[0],
            "total_amount": total_amount,
            "total_paid": total_paid,
            "total_outstanding": total_outstanding,
            "max_overdue_days": max_overdue_days,
            "avg_payment_delay": round(avg_delay, 1),
            "late_paid_count": late_paid_count,
            "total_paid_invoices": total_paid_invoices
        }
        score = calculate_risk_score(row)
        grade = assign_risk_grade(score)
        if grade == "A":
            credit_limit = total_amount * 1.2
        elif grade == "B":
            credit_limit = total_amount * 0.8
        elif grade == "C":
            credit_limit = total_amount * 0.5
        else:
            credit_limit = 0
        customers.append({
            **row,
            "risk_score": score,
            "risk_grade": grade,
            "suggested_credit_limit": credit_limit
        })
    customer_df = pd.DataFrame(customers)
    rec_map = {
        "A": "Safe",
        "B": "Monitor",
        "C": "Reduce credit",
        "D": "Collect payment"
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
if 'use_example' not in st.session_state:
    st.session_state['use_example'] = False

col1, col2 = st.columns([3, 1])
with col1:
    uploaded_file = st.file_uploader("Upload your own CSV or Excel", type=["csv", "xlsx"])
with col2:
    if st.button("📁 Load Example Data"):
        st.session_state['use_example'] = True
        st.rerun()

if uploaded_file is not None:
    st.session_state['use_example'] = False
    if uploaded_file.name.endswith(".csv"):
        df_raw = pd.read_csv(uploaded_file)
    else:
        df_raw = pd.read_excel(uploaded_file)
elif st.session_state['use_example']:
    df_raw = generate_example_data()
    st.info("📌 Showing example data. Upload a file to use your own.")
else:
    df_raw = None

if df_raw is not None:
    today = pd.Timestamp.now().normalize()
    df_clean = clean_data(df_raw)
    df_inv = calculate_invoice_metrics(df_clean, today)
    customer_summary = aggregate_customer(df_inv, today)

    st.success("Data processed successfully")

    # --- MODERN FINANCIAL SUMMARY ---
    total_customers = customer_summary.shape[0]
    total_credits = df_inv["amount"].sum()
    total_paid = customer_summary["total_paid"].sum()
    total_outstanding = customer_summary["total_outstanding"].sum()
    overdue_amt = df_inv[df_inv["overdue_days"] > 0]["outstanding"].sum()
    high_risk = customer_summary[customer_summary["risk_grade"].isin(["C","D"])].shape[0]

    st.markdown("""
    <style>
        .metric-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            border: 1px solid #eaeaea;
            transition: transform 0.2s;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.1);
        }
        .metric-label {
            font-size: 0.9rem;
            color: #5f6b7a;
            margin-bottom: 8px;
            letter-spacing: 0.5px;
        }
        .metric-value {
            font-size: 2rem;
            font-weight: 600;
            color: #1e293b;
            line-height: 1.2;
        }
        .metric-icon {
            font-size: 1.8rem;
            margin-right: 10px;
            vertical-align: middle;
        }
        .sub-metric {
            margin-top: 10px;
            font-size: 0.85rem;
            color: #64748b;
            border-top: 1px dashed #e2e8f0;
            padding-top: 8px;
        }
    </style>
    """, unsafe_allow_html=True)

    st.header("📊 Financial Summary")

    # Row 1: four main metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div><span class="metric-icon">👥</span> <span class="metric-label">Total Customers</span></div>
            <div class="metric-value">{total_customers}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div><span class="metric-icon">💰</span> <span class="metric-label">Total Credits</span></div>
            <div class="metric-value">{format_inr(total_credits)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div><span class="metric-icon">💳</span> <span class="metric-label">Total Paid</span></div>
            <div class="metric-value">{format_inr(total_paid)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div><span class="metric-icon">📉</span> <span class="metric-label">Outstanding</span></div>
            <div class="metric-value">{format_inr(total_outstanding)}</div>
        </div>
        """, unsafe_allow_html=True)

    # Row 2: additional metrics (overdue and high risk)
    col5, col6 = st.columns(2)
    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <div><span class="metric-icon">⏰</span> <span class="metric-label">Overdue Amount</span></div>
            <div class="metric-value">{format_inr(overdue_amt)}</div>
            <div class="sub-metric">Outstanding past due date</div>
        </div>
        """, unsafe_allow_html=True)
    with col6:
        st.markdown(f"""
        <div class="metric-card">
            <div><span class="metric-icon">⚠️</span> <span class="metric-label">High Risk Customers</span></div>
            <div class="metric-value">{high_risk}</div>
            <div class="sub-metric">Grades C & D</div>
        </div>
        """, unsafe_allow_html=True)
    # --- END MODERN SUMMARY ---

    # Customer Risk Summary table
    st.header("👥 Customer Risk Summary")
    display_df = customer_summary.copy()
    display_df.rename(columns={
        "customer_name": "Customer",
        "total_invoices": "Invoices",
        "total_amount": "Total Amount",
        "total_paid": "Paid",
        "total_outstanding": "Due",
        "max_overdue_days": "Overdue Days",
        "avg_payment_delay": "Avg Delay",
        "risk_score": "Risk Score",
        "risk_grade": "Risk",
        "suggested_credit_limit": "Credit Limit",
        "recommendation": "Action"
    }, inplace=True)
    for col in ["Total Amount", "Paid", "Due", "Credit Limit"]:
        display_df[col] = display_df[col].apply(format_inr)
    styled = display_df.style.applymap(color_grade, subset=["Risk"])
    st.dataframe(styled, use_container_width=True)

    # Risk Distribution chart
    st.header("📊 Risk Distribution")
    grade_counts = customer_summary["risk_grade"].value_counts().reindex(["A", "B", "C", "D"], fill_value=0)
    fig = px.bar(
        x=["Low", "Medium", "High", "Very High"],
        y=grade_counts.values,
        color=["Low", "Medium", "High", "Very High"],
        color_discrete_map={"Low": "green", "Medium": "gold", "High": "orange", "Very High": "red"},
        labels={"x": "Risk Level", "y": "Number of Customers"}
    )
    st.plotly_chart(fig, use_container_width=True)

    # Top Risky Customers
    st.header("🚩 Top Risky Customers")
    risky_df = customer_summary[customer_summary["risk_grade"].isin(["C","D"])].copy()
    if not risky_df.empty:
        risky_display = risky_df[["customer_name", "total_outstanding", "max_overdue_days", "risk_grade", "recommendation"]].copy()
        risky_display.rename(columns={
            "customer_name": "Customer",
            "total_outstanding": "Due",
            "max_overdue_days": "Overdue Days",
            "risk_grade": "Risk",
            "recommendation": "Action"
        }, inplace=True)
        risky_display["Due"] = risky_display["Due"].apply(format_inr)
        styled_risky = risky_display.style.applymap(color_grade, subset=["Risk"])
        st.dataframe(styled_risky, use_container_width=True)
    else:
        st.write("No high-risk customers found.")

    # Customers to Call
    st.header("📞 Customers to Call")
    priority_df = collection_priority(customer_summary)
    priority_display = priority_df[["customer_name", "total_outstanding", "max_overdue_days", "risk_grade", "recommendation"]].head(10).copy()
    priority_display.rename(columns={
        "customer_name": "Customer",
        "total_outstanding": "Due",
        "max_overdue_days": "Overdue Days",
        "risk_grade": "Risk",
        "recommendation": "Action"
    }, inplace=True)
    priority_display["Due"] = priority_display["Due"].apply(format_inr)
    styled_priority = priority_display.style.applymap(color_grade, subset=["Risk"])
    st.dataframe(styled_priority, use_container_width=True)

    # Download report
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
