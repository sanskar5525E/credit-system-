import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import io

# ------------------------------
# Page configuration
# ------------------------------
st.set_page_config(page_title="Wholesale Risk Dashboard (₹)", layout="wide")

st.title("📊 Wholesale Customer Risk Dashboard (₹)")
st.markdown("Upload your invoices file (CSV or Excel) to analyze customer credit risk.")

# ------------------------------
# Helper functions
# ------------------------------

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
        "paid_amount",
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

    mask = (df["outstanding"] > 0) & (df["due_date"] < today)

    df.loc[mask, "overdue_days"] = (today - df.loc[mask, "due_date"]).dt.days

    df["paid_late"] = False

    mask_paid = (
        (df["paid_amount"] >= df["amount"])
        & df["payment_date"].notna()
        & (df["payment_date"] > df["due_date"])
    )

    df.loc[mask_paid, "paid_late"] = True

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

        overdue = group[(group["outstanding"] > 0) & (group["due_date"] < today)]

        max_overdue_days = overdue["overdue_days"].max() if not overdue.empty else 0
        total_overdue_amount = overdue["outstanding"].sum()

        late_paid_count = group["paid_late"].sum()
        total_paid_invoices = group[group["paid_amount"] >= group["amount"]].shape[0]

        row = {
            "max_overdue_days": max_overdue_days,
            "total_outstanding": total_outstanding,
            "total_amount": total_amount,
            "late_paid_count": late_paid_count,
            "total_paid_invoices": total_paid_invoices,
        }

        risk_score = calculate_risk_score(row)

        grade = assign_risk_grade(risk_score)

        customers.append(
            {
                "customer_name": name,
                "total_invoices": group.shape[0],
                "total_amount": total_amount,
                "total_paid": total_paid,
                "total_outstanding": total_outstanding,
                "max_overdue_days": max_overdue_days,
                "risk_score": risk_score,
                "risk_grade": grade,
            }
        )

    customer_df = pd.DataFrame(customers)

    rec_map = {
        "A": "✅ Safe customer. Continue credit.",
        "B": "⚠️ Monitor occasionally.",
        "C": "🟠 Reduce credit and follow up.",
        "D": "🔴 High risk. Collect urgently.",
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
        df["total_outstanding"] * 0.5
        + df["max_overdue_days"] * 50
        + df["risk_score"] * 20
    )

    return df.sort_values("priority_score", ascending=False)


# ------------------------------
# Upload File
# ------------------------------

uploaded_file = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])

if uploaded_file is not None:

    if uploaded_file.name.endswith(".csv"):
        df_raw = pd.read_csv(uploaded_file)
    else:
        df_raw = pd.read_excel(uploaded_file)

    today = pd.Timestamp.now().normalize()

    df_clean = clean_data(df_raw)

    df_inv = calculate_invoice_metrics(df_clean, today)

    customer_summary = aggregate_customer(df_inv, today)

    st.success("Data processed successfully")

    # ------------------------------
    # Metrics
    # ------------------------------

    total_outstanding = customer_summary["total_outstanding"].sum()
    total_paid = customer_summary["total_paid"].sum()
    total_amount = customer_summary["total_amount"].sum()

    overdue_total = df_inv[df_inv["overdue_days"] > 0]["outstanding"].sum()

    num_customers = customer_summary.shape[0]

    st.header("📈 Key Metrics")

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Outstanding", format_inr(total_outstanding))
    col2.metric("Overdue", format_inr(overdue_total))
    col3.metric("Total Paid", format_inr(total_paid))
    col4.metric("Total Invoiced", format_inr(total_amount))
    col5.metric("Customers", num_customers)

    # ------------------------------
    # Customer Table
    # ------------------------------

    st.header("👥 Customer Risk Summary")

    display_df = customer_summary.copy()

    for col in ["total_amount", "total_paid", "total_outstanding"]:
        display_df[col] = display_df[col].apply(format_inr)

    styled = display_df.style.applymap(color_grade, subset=["risk_grade"]).set_properties(
        subset=["risk_grade"], **{"text-align": "center", "font-weight": "bold"}
    )

    st.dataframe(styled, use_container_width=True)

    # ------------------------------
    # Risk Distribution
    # ------------------------------

    st.header("📊 Risk Distribution")

    grade_counts = customer_summary["risk_grade"].value_counts().reindex(
        ["A", "B", "C", "D"], fill_value=0
    )

    fig = px.bar(
        x=grade_counts.index,
        y=grade_counts.values,
        color=grade_counts.index,
        color_discrete_map={
            "A": "green",
            "B": "gold",
            "C": "orange",
            "D": "red",
        },
    )

    st.plotly_chart(fig, use_container_width=True)

    # ------------------------------
    # Collection Priority
    # ------------------------------

    st.header("📞 Customers To Collect")

    priority_df = collection_priority(customer_summary)

    top_collect = priority_df[priority_df["total_outstanding"] > 0].head(10)

    st.dataframe(
        top_collect[
            [
                "customer_name",
                "total_outstanding",
                "max_overdue_days",
                "risk_grade",
                "recommendation",
            ]
        ],
        use_container_width=True,
    )

    # ------------------------------
    # Download Report
    # ------------------------------

    st.header("📥 Download Excel Report")

    detailed = df_inv.merge(
        customer_summary[["customer_name", "risk_grade", "recommendation"]],
        on="customer_name",
        how="left",
    )

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:

        customer_summary.to_excel(writer, sheet_name="Customer Summary", index=False)

        detailed.to_excel(writer, sheet_name="Invoice Details", index=False)

    st.download_button(
        "Download Report",
        data=output.getvalue(),
        file_name=f"risk_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

else:

    st.info("Upload a CSV or Excel file to start analysis.")import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import io

# ------------------------------
# Page configuration
# ------------------------------
st.set_page_config(page_title="Wholesale Risk Dashboard (₹)", layout="wide")
st.title("📊 Wholesale Customer Risk Dashboard (₹)")
st.markdown("Upload your invoices file (CSV or Excel) to analyze outstanding amounts, overdue days, and customer risk grades.")

# ------------------------------
# Helper functions
# ------------------------------

def format_inr(x):
    return f"₹{x:,.2f}"

def clean_data(df):
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

    required = ['customer_name','invoice_no','invoice_date','due_date','amount','paid_amount']
    for col in required:
        if col not in df.columns:
            st.error(f"Missing required column: {col}")
            st.stop()

    date_cols = ['invoice_date','due_date','payment_date']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    df['amount'] = pd.to_numeric(df['amount'], errors="coerce").fillna(0)
    df['paid_amount'] = pd.to_numeric(df['paid_amount'], errors="coerce").fillna(0)

    if "payment_date" not in df.columns:
        df["payment_date"] = pd.NaT

    df.dropna(subset=['customer_name','invoice_no','invoice_date','due_date'], inplace=True)

    df = df[df['amount'] > 0]

    return df


def calculate_invoice_metrics(df, today):

    df = df.copy()

    df["outstanding"] = df["amount"] - df["paid_amount"]
    df["outstanding"] = df["outstanding"].clip(lower=0)

    df["overdue_days"] = 0

    mask = (df["outstanding"] > 0) & (df["due_date"] < today)
    df.loc[mask,"overdue_days"] = (today - df.loc[mask,"due_date"]).dt.days

    df["paid_late"] = False

    mask_paid = (
        (df["paid_amount"] >= df["amount"]) &
        df["payment_date"].notna() &
        (df["payment_date"] > df["due_date"])
    )

    df.loc[mask_paid,"paid_late"] = True

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


def aggregate_customer(df,today):

    customers = []

    for name,group in df.groupby("customer_name"):

        total_amount = group["amount"].sum()
        total_paid = group["paid_amount"].sum()
        total_outstanding = total_amount - total_paid

        overdue = group[(group["outstanding"]>0) & (group["due_date"]<today)]

        max_overdue_days = overdue["overdue_days"].max() if not overdue.empty else 0
        total_overdue_amount = overdue["outstanding"].sum()

        late_paid_count = group["paid_late"].sum()
        total_paid_invoices = group[group["paid_amount"]>=group["amount"]].shape[0]

        row = {
            "max_overdue_days":max_overdue_days,
            "total_outstanding":total_outstanding,
            "total_amount":total_amount,
            "late_paid_count":late_paid_count,
            "total_paid_invoices":total_paid_invoices
        }

        risk_score = calculate_risk_score(row)
        grade = assign_risk_grade(risk_score)

        customers.append({
            "customer_name":name,
            "total_invoices":group.shape[0],
            "total_amount":total_amount,
            "total_paid":total_paid,
            "total_outstanding":total_outstanding,
            "max_overdue_days":max_overdue_days,
            "total_overdue_amount":total_overdue_amount,
            "late_paid_count":late_paid_count,
            "total_paid_invoices":total_paid_invoices,
            "risk_score":risk_score,
            "risk_grade":grade
        })

    customer_df = pd.DataFrame(customers)

    rec_map = {
        "A":"✅ Safe customer. Normal credit allowed",
        "B":"⚠️ Monitor occasionally",
        "C":"🔶 Reduce credit. Follow up regularly",
        "D":"🔴 High risk. Collect urgently / cash only"
    }

    customer_df["recommendation"] = customer_df["risk_grade"].map(rec_map)

    return customer_df


def collection_priority(df):

    df = df.copy()

    df["priority_score"] = (
        df["total_outstanding"]*0.5 +
        df["max_overdue_days"]*50 +
        df["risk_score"]*20
    )

    df = df.sort_values("priority_score",ascending=False)

    return df


def color_grade(val):

    if val=="A":
        return "background-color:#d4edda"
    elif val=="B":
        return "background-color:#fff3cd"
    elif val=="C":
        return "background-color:#ffe5b4"
    elif val=="D":
        return "background-color:#f8d7da"
    return ""


# ------------------------------
# File Upload
# ------------------------------

uploaded_file = st.file_uploader("Upload CSV or Excel",type=["csv","xlsx"])

if "sample_uploaded" in st.session_state:
    uploaded_file = st.session_state["sample_uploaded"]


if uploaded_file is not None:

    try:

        if isinstance(uploaded_file,io.BytesIO):
            df_raw = pd.read_csv(uploaded_file)

        elif uploaded_file.name.endswith(".csv"):
            df_raw = pd.read_csv(uploaded_file)

        else:
            df_raw = pd.read_excel(uploaded_file)

    except Exception as e:
        st.error(f"Error reading file: {e}")
        st.stop()


    with st.spinner("Processing data..."):

        df_clean = clean_data(df_raw)

        today = pd.Timestamp.now().normalize()

        df_inv = calculate_invoice_metrics(df_clean,today)

        customer_summary = aggregate_customer(df_inv,today)


    st.success("Data processed successfully")


    # ------------------------------
    # Metrics
    # ------------------------------

    total_outstanding = customer_summary["total_outstanding"].sum()
    total_paid = customer_summary["total_paid"].sum()
    total_amount = customer_summary["total_amount"].sum()
    num_customers = customer_summary.shape[0]

    overdue_total = df_inv[df_inv["overdue_days"]>0]["outstanding"].sum()

    st.header("📈 Key Metrics")

    col1,col2,col3,col4,col5 = st.columns(5)

    col1.metric("Outstanding",format_inr(total_outstanding))
    col2.metric("Overdue",format_inr(overdue_total))
    col3.metric("Total Paid",format_inr(total_paid))
    col4.metric("Total Invoiced",format_inr(total_amount))
    col5.metric("Customers",num_customers)


    # ------------------------------
    # Customer Table
    # ------------------------------

    st.header("👥 Customer Risk Summary")

    display_cols = [
        "customer_name",
        "total_invoices",
        "total_amount",
        "total_paid",
        "total_outstanding",
        "max_overdue_days",
        "risk_score",
        "risk_grade",
        "recommendation"
    ]

    display_df = customer_summary[display_cols].copy()

    for col in ["total_amount","total_paid","total_outstanding"]:
        display_df[col] = display_df[col].apply(format_inr)

    styled = display_df.style.applymap(color_grade,subset=["risk_grade"])

    st.dataframe(styled,use_container_width=True)


    # ------------------------------
    # Risk Chart
    # ------------------------------

    st.header("📊 Risk Distribution")

    grade_counts = customer_summary["risk_grade"].value_counts().reindex(["A","B","C","D"],fill_value=0)

    fig = px.bar(
        x=grade_counts.index,
        y=grade_counts.values,
        labels={"x":"Risk Grade","y":"Customers"},
        color=grade_counts.index,
        color_discrete_map={"A":"green","B":"gold","C":"orange","D":"red"}
    )

    st.plotly_chart(fig,use_container_width=True)


    # ------------------------------
    # Collection Priority
    # ------------------------------

    st.header("📞 Customers To Collect From")

    priority_df = collection_priority(customer_summary)

    top_collect = priority_df[
        priority_df["total_outstanding"]>0
    ].head(10)

    st.dataframe(
        top_collect[
            [
                "customer_name",
                "total_outstanding",
                "max_overdue_days",
                "risk_grade",
                "recommendation"
            ]
        ],
        use_container_width=True
    )


    # ------------------------------
    # Download Report
    # ------------------------------

    st.header("📥 Download Report")

    detailed = df_inv.merge(
        customer_summary[["customer_name","risk_grade","recommendation"]],
        on="customer_name",
        how="left"
    )

    output = io.BytesIO()

    with pd.ExcelWriter(output,engine="openpyxl") as writer:

        customer_summary.to_excel(writer,sheet_name="Customer Summary",index=False)
        detailed.to_excel(writer,sheet_name="Invoice Details",index=False)

    st.download_button(
        "Download Excel Report",
        data=output.getvalue(),
        file_name=f"risk_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


else:

    st.info("Upload a file to begin")

    if st.button("Use Sample Data"):

        sample_data = pd.DataFrame({

            "customer_name":["Alpha","Alpha","Beta","Gamma","Delta"],

            "invoice_no":["INV1","INV2","INV3","INV4","INV5"],

            "invoice_date":["2025-01-10","2025-01-15","2025-02-01","2025-02-10","2025-02-15"],

            "due_date":["2025-02-10","2025-02-15","2025-03-01","2025-03-10","2025-03-15"],

            "amount":[5000,3000,7000,4000,6000],

            "paid_amount":[5000,1000,0,2000,0],

            "payment_date":["2025-02-05",None,None,"2025-03-05",None]

        })

        sample_bytes = io.BytesIO()

        sample_data.to_csv(sample_bytes,index=False)

        sample_bytes.seek(0)

        st.session_state["sample_uploaded"] = sample_bytes

        st.rerun()
