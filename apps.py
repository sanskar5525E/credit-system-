import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import io

st.set_page_config(page_title="Wholesale Credit Risk Dashboard", layout="wide")
st.title("📊 Wholesale Customer Risk Dashboard")

# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------
def format_inr(x):
    """Return currency string (for display only)."""
    return f"₹{x:,.2f}"

def generate_example_data():
    """Generate realistic wholesale payment patterns."""
    np.random.seed(42)
    customers = ['ABC Corp', 'XYZ Ltd', 'Mega Distributors', 'Beta Stores', 'Gamma Inc', 'Delta Traders']
    data = []
    # Use a fixed "today" for example data so overdue is consistent
    example_today = pd.Timestamp('2025-03-01')
    for cust in customers:
        n_invoices = np.random.randint(3, 10)
        for i in range(n_invoices):
            invoice_date = example_today - pd.Timedelta(days=np.random.randint(1, 180))
            due_date = invoice_date + pd.Timedelta(days=30)
            amount = np.random.randint(1000, 50000)
            # Payment patterns: 30% on time, 30% late, 20% partial, 20% unpaid
            r = np.random.rand()
            if r < 0.3:          # paid on time
                paid_amount = amount
                payment_date = due_date - pd.Timedelta(days=np.random.randint(0, 5))
            elif r < 0.6:         # paid late
                paid_amount = amount
                payment_date = due_date + pd.Timedelta(days=np.random.randint(1, 60))
            elif r < 0.8:         # partial payment
                paid_amount = amount * np.random.uniform(0.1, 0.9)
                payment_date = due_date + pd.Timedelta(days=np.random.randint(-5, 90))
            else:                  # unpaid
                paid_amount = 0
                payment_date = None

            data.append({
                'customer_name': cust,
                'invoice_no': f'INV-{cust[:3]}-{i:03d}',
                'invoice_date': invoice_date,
                'due_date': due_date,
                'amount': amount,
                'paid_amount': paid_amount,
                'payment_date': payment_date
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
    """Add overdue_days, paid_late, fully_paid columns."""
    df = df.copy()
    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    df["due_date"] = pd.to_datetime(df["due_date"])
    df["payment_date"] = pd.to_datetime(df["payment_date"])

    df["outstanding"] = (df["amount"] - df["paid_amount"]).clip(lower=0)
    df["overdue_days"] = 0
    df["paid_late"] = False
    df["fully_paid"] = df["paid_amount"] >= df["amount"]

    # Unpaid or partially paid and overdue
    mask_unpaid = (df["outstanding"] > 0) & (df["due_date"] < today)
    df.loc[mask_unpaid, "overdue_days"] = (today - df.loc[mask_unpaid, "due_date"]).dt.days

    # Fully paid but late
    mask_paid_late = df["fully_paid"] & df["payment_date"].notna() & (df["payment_date"] > df["due_date"])
    df.loc[mask_paid_late, "overdue_days"] = (df.loc[mask_paid_late, "payment_date"] - df.loc[mask_paid_late, "due_date"]).dt.days
    df.loc[mask_paid_late, "paid_late"] = True

    df["overdue_days"] = df["overdue_days"].clip(lower=0)
    return df

def calculate_risk_score(row):
    """Balanced risk score: 40% overdue, 40% outstanding, 20% payment behaviour."""
    # Overdue score (max 40) – linear up to 90 days
    overdue_score = min(row["max_overdue_days"] / 90, 1.0) * 40

    # Outstanding ratio score (max 40)
    outstanding_ratio = row["total_outstanding"] / row["total_amount"] if row["total_amount"] > 0 else 0
    outstanding_score = outstanding_ratio * 40

    # Payment behaviour score (max 20) – combines late ratio and payment ratio
    payment_ratio = row["total_paid"] / row["total_amount"] if row["total_amount"] > 0 else 0
    late_ratio = row["late_paid_count"] / row["total_paid_invoices"] if row["total_paid_invoices"] > 0 else 0
    behaviour_score = (1 - payment_ratio) * 10 + late_ratio * 10
    behaviour_score = min(behaviour_score, 20)

    return min(round(overdue_score + outstanding_score + behaviour_score), 100)

def assign_risk_grade(score):
    if score <= 10: return "A"
    elif score <= 30: return "B"
    elif score <= 60: return "C"
    else: return "D"

def aggregate_customer(df, today):
    """Vectorised customer aggregation."""
    # Add fully_paid flag if not already present
    if "fully_paid" not in df.columns:
        df["fully_paid"] = df["paid_amount"] >= df["amount"]

    # Group by customer
    grouped = df.groupby("customer_name").agg(
        total_invoices=("invoice_no", "count"),
        total_amount=("amount", "sum"),
        total_paid=("paid_amount", "sum"),
        max_overdue_days=("overdue_days", "max"),
        late_paid_count=("paid_late", "sum"),
        fully_paid_count=("fully_paid", "sum")
    ).reset_index()

    # Total outstanding (never negative)
    grouped["total_outstanding"] = (grouped["total_amount"] - grouped["total_paid"]).clip(lower=0)

    # Average delay among late payments
    late_delays = df[df["paid_late"]].groupby("customer_name")["overdue_days"].mean()
    grouped["avg_payment_delay"] = grouped["customer_name"].map(late_delays).fillna(0)

    # Total paid invoices (fully paid count)
    grouped["total_paid_invoices"] = grouped["fully_paid_count"]

    # Compute risk score and grade
    risk_data = []
    for _, row in grouped.iterrows():
        score = calculate_risk_score(row)
        grade = assign_risk_grade(score)
        if grade == "A":
            credit_limit = row["total_amount"] * 1.2
        elif grade == "B":
            credit_limit = row["total_amount"] * 0.8
        elif grade == "C":
            credit_limit = row["total_amount"] * 0.5
        else:
            credit_limit = 0
        risk_data.append({
            "customer_name": row["customer_name"],
            "total_invoices": row["total_invoices"],
            "total_amount": row["total_amount"],
            "total_paid": row["total_paid"],
            "total_outstanding": row["total_outstanding"],
            "max_overdue_days": row["max_overdue_days"],
            "avg_payment_delay": round(row["avg_payment_delay"], 1),
            "late_paid_count": row["late_paid_count"],
            "total_paid_invoices": row["total_paid_invoices"],
            "risk_score": score,
            "risk_grade": grade,
            "suggested_credit_limit": credit_limit,
            "payment_ratio": round(row["total_paid"] / row["total_amount"], 2) if row["total_amount"] > 0 else 0
        })

    customer_df = pd.DataFrame(risk_data)

    # Status & recommendation with emojis
    status_map = {"A": "🟢 Low Risk", "B": "🟡 Medium Risk", "C": "🟠 High Risk", "D": "🔴 Critical"}
    action_map = {"A": "✅ Extend credit limit", "B": "👀 Monitor payments closely",
                  "C": "⚠️ Reduce exposure", "D": "🚨 Immediate collection"}
    customer_df["status"] = customer_df["risk_grade"].map(status_map)
    customer_df["recommendation"] = customer_df["risk_grade"].map(action_map)
    return customer_df

def collection_priority(df):
    """Normalised priority score (higher = call sooner)."""
    df = df.copy()
    # Normalise each component to 0-1
    min_out, max_out = df["total_outstanding"].min(), df["total_outstanding"].max()
    min_od, max_od = df["max_overdue_days"].min(), df["max_overdue_days"].max()
    min_risk, max_risk = df["risk_score"].min(), df["risk_score"].max()

    def norm(series, min_val, max_val):
        if max_val > min_val:
            return (series - min_val) / (max_val - min_val)
        return 0

    df["outstanding_norm"] = norm(df["total_outstanding"], min_out, max_out)
    df["overdue_norm"] = norm(df["max_overdue_days"], min_od, max_od)
    df["risk_norm"] = norm(df["risk_score"], min_risk, max_risk)

    # Simple sum (equal weight) – you can adjust weights if desired
    df["priority_score"] = df["outstanding_norm"] + df["overdue_norm"] + df["risk_norm"]
    return df.sort_values("priority_score", ascending=False)

def color_grade(val):
    if val == "A": return "background-color:#1b5e20; color:white"
    elif val == "B": return "background-color:#f9a825; color:black"
    elif val == "C": return "background-color:#ef6c00; color:white"
    elif val == "D": return "background-color:#c62828; color:white"
    return ""

# -------------------------------------------------------------------
# Main app
# -------------------------------------------------------------------
if 'use_example' not in st.session_state:
    st.session_state['use_example'] = False

# Sidebar: set reference date
st.sidebar.header("⚙️ Settings")
today_input = st.sidebar.date_input("As of date (for overdue calculation)", value=datetime.now().date())
today = pd.Timestamp(today_input)

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
    df_clean = clean_data(df_raw)
    df_inv = calculate_invoice_metrics(df_clean, today)
    customer_summary = aggregate_customer(df_inv, today)

    st.success("Data processed successfully")

    # -------------------------------------------------------------------
    # Transparent financial summary cards (unchanged, just using today)
    # -------------------------------------------------------------------
    total_customers = customer_summary.shape[0]
    total_credits = df_inv["amount"].sum()
    total_paid = customer_summary["total_paid"].sum()
    total_outstanding = customer_summary["total_outstanding"].sum()
    overdue_amt = df_inv[df_inv["overdue_days"] > 0]["outstanding"].sum()
    high_risk = customer_summary[customer_summary["risk_grade"].isin(["C","D"])].shape[0]

    st.markdown("""
    <style>
        .metric-card {
            background: rgba(20, 20, 30, 0.7);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 8px 20px rgba(0,0,0,0.2);
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .metric-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 24px rgba(0,0,0,0.3);
            background: rgba(30, 30, 40, 0.8);
        }
        .metric-label {
            font-size: 0.9rem;
            color: #ccc;
            margin-bottom: 8px;
            letter-spacing: 0.5px;
        }
        .metric-value {
            font-size: 2rem;
            font-weight: 600;
            color: white;
            line-height: 1.2;
        }
        .metric-icon {
            font-size: 1.8rem;
            margin-right: 10px;
            vertical-align: middle;
            color: white;
        }
        .sub-metric {
            margin-top: 10px;
            font-size: 0.85rem;
            color: #aaa;
            border-top: 1px dashed rgba(255,255,255,0.2);
            padding-top: 8px;
        }
    </style>
    """, unsafe_allow_html=True)

    st.header("📊 Financial Summary")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class="metric-card"><div><span class="metric-icon">👥</span> <span class="metric-label">Total Customers</span></div><div class="metric-value">{total_customers}</div></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="metric-card"><div><span class="metric-icon">💰</span> <span class="metric-label">Total Credits</span></div><div class="metric-value">{format_inr(total_credits)}</div></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="metric-card"><div><span class="metric-icon">💳</span> <span class="metric-label">Total Paid</span></div><div class="metric-value">{format_inr(total_paid)}</div></div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class="metric-card"><div><span class="metric-icon">📉</span> <span class="metric-label">Outstanding</span></div><div class="metric-value">{format_inr(total_outstanding)}</div></div>""", unsafe_allow_html=True)

    col5, col6 = st.columns(2)
    with col5:
        st.markdown(f"""<div class="metric-card"><div><span class="metric-icon">⏰</span> <span class="metric-label">Overdue Amount</span></div><div class="metric-value">{format_inr(overdue_amt)}</div><div class="sub-metric">Outstanding past due date</div></div>""", unsafe_allow_html=True)
    with col6:
        st.markdown(f"""<div class="metric-card"><div><span class="metric-icon">⚠️</span> <span class="metric-label">High Risk Customers</span></div><div class="metric-value">{high_risk}</div><div class="sub-metric">Grades C & D</div></div>""", unsafe_allow_html=True)

    # -------------------------------------------------------------------
    # Customer Risk Summary (with proper numeric formatting)
    # -------------------------------------------------------------------
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
        "status": "Status",
        "recommendation": "Suggested Action",
        "payment_ratio": "Payment Ratio"
    }, inplace=True)

    # Keep numeric columns; format via Styler
    cols = ["Customer", "Invoices", "Total Amount", "Paid", "Due", "Overdue Days", "Avg Delay", "Payment Ratio", "Risk Score", "Risk", "Status", "Suggested Action", "Credit Limit"]
    display_df = display_df[cols]

    styled = (display_df.style
              .format({
                  "Total Amount": format_inr,
                  "Paid": format_inr,
                  "Due": format_inr,
                  "Credit Limit": format_inr,
                  "Payment Ratio": "{:.2%}"
              })
              .applymap(color_grade, subset=["Risk"]))
    st.dataframe(styled, use_container_width=True)

    # -------------------------------------------------------------------
    # Risk Distribution (now using grade letters)
    # -------------------------------------------------------------------
    st.header("📊 Risk Distribution")
    grade_counts = customer_summary["risk_grade"].value_counts().reindex(["A", "B", "C", "D"], fill_value=0)
    fig = px.bar(
        x=grade_counts.index,
        y=grade_counts.values,
        color=grade_counts.index,
        color_discrete_map={"A": "green", "B": "gold", "C": "orange", "D": "red"},
        labels={"x": "Risk Grade", "y": "Number of Customers"}
    )
    st.plotly_chart(fig, use_container_width=True)

    # -------------------------------------------------------------------
    # Top Risky Customers (C & D)
    # -------------------------------------------------------------------
    st.header("🚩 Top Risky Customers")
    risky_df = customer_summary[customer_summary["risk_grade"].isin(["C","D"])].copy()
    if not risky_df.empty:
        risky_display = risky_df[["customer_name", "total_outstanding", "max_overdue_days", "risk_grade", "status", "recommendation"]].copy()
        risky_display.rename(columns={
            "customer_name": "Customer",
            "total_outstanding": "Due",
            "max_overdue_days": "Overdue Days",
            "risk_grade": "Risk",
            "status": "Status",
            "recommendation": "Suggested Action"
        }, inplace=True)
        styled_risky = (risky_display.style
                        .format({"Due": format_inr})
                        .applymap(color_grade, subset=["Risk"]))
        st.dataframe(styled_risky, use_container_width=True)
    else:
        st.write("No high-risk customers found.")

    # -------------------------------------------------------------------
    # Customers to Call (priority)
    # -------------------------------------------------------------------
    st.header("📞 Customers to Call")
    priority_df = collection_priority(customer_summary)
    priority_display = priority_df[["customer_name", "total_outstanding", "max_overdue_days", "risk_grade", "status", "recommendation"]].head(10).copy()
    priority_display.rename(columns={
        "customer_name": "Customer",
        "total_outstanding": "Due",
        "max_overdue_days": "Overdue Days",
        "risk_grade": "Risk",
        "status": "Status",
        "recommendation": "Suggested Action"
    }, inplace=True)
    styled_priority = (priority_display.style
                       .format({"Due": format_inr})
                       .applymap(color_grade, subset=["Risk"]))
    st.dataframe(styled_priority, use_container_width=True)

    # -------------------------------------------------------------------
    # Download report
    # -------------------------------------------------------------------
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
