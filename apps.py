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
st.markdown("Upload your invoices file (CSV or Excel) to analyze outstanding amounts, overdue days, and customer risk grades.")

# ------------------------------
# Helper functions
# ------------------------------
def clean_data(df):
    """Standardize column names, parse dates, and ensure numeric amounts."""
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
    
    # Map expected column names
    col_map = {
        'customer_name': 'customer_name',
        'invoice_no': 'invoice_no',
        'invoice_date': 'invoice_date',
        'due_date': 'due_date',
        'amount': 'amount',
        'paid_amount': 'paid_amount',
        'payment_date': 'payment_date'
    }
    
    # Fuzzy rename if exact match not found
    for std_name in col_map.values():
        if std_name not in df.columns:
            for col in df.columns:
                if std_name.replace('_', '') in col.replace('_', ''):
                    df.rename(columns={col: std_name}, inplace=True)
                    break
    
    # Ensure required columns exist
    required = ['customer_name', 'invoice_no', 'invoice_date', 'due_date', 'amount', 'paid_amount']
    for col in required:
        if col not in df.columns:
            st.error(f"Missing required column: {col}")
            st.stop()
    
    # Parse dates
    date_cols = ['invoice_date', 'due_date', 'payment_date']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Convert amounts to numeric
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
    df['paid_amount'] = pd.to_numeric(df['paid_amount'], errors='coerce').fillna(0)
    
    # Fill missing payment_date with NaT
    if 'payment_date' not in df.columns:
        df['payment_date'] = pd.NaT
    else:
        df['payment_date'] = pd.to_datetime(df['payment_date'], errors='coerce')
    
    # Drop rows with critical missing data
    df.dropna(subset=['customer_name', 'invoice_no', 'invoice_date', 'due_date'], inplace=True)
    
    # Ensure positive amounts
    df = df[df['amount'] > 0]
    
    return df

def calculate_invoice_metrics(df, today):
    """Add outstanding, overdue days, and payment status per invoice."""
    df = df.copy()
    df['outstanding'] = df['amount'] - df['paid_amount']
    df['outstanding'] = df['outstanding'].clip(lower=0)
    
    # Overdue days for unpaid invoices
    df['overdue_days'] = 0
    mask = (df['outstanding'] > 0) & (df['due_date'] < today)
    df.loc[mask, 'overdue_days'] = (today - df.loc[mask, 'due_date']).dt.days
    
    # Flag for late payment (fully paid but after due date)
    df['paid_late'] = False
    mask_paid = (df['paid_amount'] >= df['amount']) & df['payment_date'].notna() & (df['payment_date'] > df['due_date'])
    df.loc[mask_paid, 'paid_late'] = True
    
    return df

def calculate_risk_score(row):
    """
    Compute a risk score (0-100) based on:
    - Max overdue days (0-40 points)
    - Overdue amount ratio (0-50 points)
    - Late payment ratio (0-10 points)
    """
    score = 0
    
    # Overdue days factor
    max_days = row['max_overdue_days']
    if max_days > 0:
        if max_days <= 30:
            score += 10
        elif max_days <= 60:
            score += 20
        elif max_days <= 90:
            score += 30
        else:
            score += 40
    
    # Overdue amount ratio (outstanding / total amount)
    if row['total_amount'] > 0:
        overdue_ratio = row['total_outstanding'] / row['total_amount']
        score += overdue_ratio * 50  # max 50 points
    
    # Late payment ratio (late_paid / total_paid_invoices)
    if row['total_paid_invoices'] > 0:
        late_ratio = row['late_paid_count'] / row['total_paid_invoices']
        score += late_ratio * 10  # max 10 points
    
    return min(round(score), 100)  # cap at 100

def assign_risk_grade(score):
    """Map score to A-D grades."""
    if score <= 10:
        return 'A'
    elif score <= 30:
        return 'B'
    elif score <= 60:
        return 'C'
    else:
        return 'D'

def aggregate_customer(df, today):
    """Compute per‑customer metrics and assign risk grade."""
    customers = []
    for name, group in df.groupby('customer_name'):
        total_amount = group['amount'].sum()
        total_paid = group['paid_amount'].sum()
        total_outstanding = total_amount - total_paid
        
        # Overdue details
        overdue_invoices = group[(group['outstanding'] > 0) & (group['due_date'] < today)]
        max_overdue_days = overdue_invoices['overdue_days'].max() if not overdue_invoices.empty else 0
        total_overdue_amount = overdue_invoices['outstanding'].sum()
        
        # Late payments (fully paid after due date)
        late_paid_count = group['paid_late'].sum()
        total_paid_invoices = group[group['paid_amount'] >= group['amount']].shape[0]
        
        # Risk score
        row = {
            'max_overdue_days': max_overdue_days,
            'total_outstanding': total_outstanding,
            'total_amount': total_amount,
            'late_paid_count': late_paid_count,
            'total_paid_invoices': total_paid_invoices
        }
        risk_score = calculate_risk_score(row)
        grade = assign_risk_grade(risk_score)
        
        customers.append({
            'customer_name': name,
            'total_invoices': group.shape[0],
            'total_amount': total_amount,
            'total_paid': total_paid,
            'total_outstanding': total_outstanding,
            'max_overdue_days': max_overdue_days,
            'total_overdue_amount': total_overdue_amount,
            'late_paid_count': late_paid_count,
            'total_paid_invoices': total_paid_invoices,
            'risk_score': risk_score,
            'risk_grade': grade
        })
    
    customer_df = pd.DataFrame(customers)
    # Add recommendation based on grade
    rec_map = {
        'A': '✅ Customer pays on time. Safe to continue normal credit.',
        'B': '⚠️ Moderate risk. Monitor occasionally; consider slight credit limit.',
        'C': '🔶 High risk. Reduce credit exposure, follow up regularly, ask for advances.',
        'D': '🔴 Very high risk. Stop new credit, collect urgently, cash only.'
    }
    customer_df['recommendation'] = customer_df['risk_grade'].map(rec_map)
    return customer_df

def color_grade(val):
    """Return CSS background color for risk grade."""
    if val == 'A':
        return 'background-color: #d4edda'  # light green
    elif val == 'B':
        return 'background-color: #fff3cd'  # light yellow
    elif val == 'C':
        return 'background-color: #ffe5b4'  # light orange
    elif val == 'D':
        return 'background-color: #f8d7da'  # light red
    return ''

# ------------------------------
# Main app
# ------------------------------
uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=['csv', 'xlsx'])

if uploaded_file is not None:
    # Read file
    try:
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file)
        else:
            df_raw = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Error reading file: {e}")
        st.stop()
    
    # Clean data
    with st.spinner("Cleaning data..."):
        df_clean = clean_data(df_raw)
        today = pd.Timestamp.now().normalize()
        df_inv = calculate_invoice_metrics(df_clean, today)
        customer_summary = aggregate_customer(df_inv, today)
    
    st.success("Data processed successfully!")
    
    # ------------------------------
    # Dashboard
    # ------------------------------
    st.header("📋 Data Overview")
    with st.expander("Show cleaned data preview"):
        st.dataframe(df_inv.head(10))
    
    # Key metrics (in ₹)
    st.header("📈 Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    total_outstanding = customer_summary['total_outstanding'].sum()
    total_paid = customer_summary['total_paid'].sum()
    total_amount = customer_summary['total_amount'].sum()
    num_customers = customer_summary.shape[0]
    
    col1.metric("Total Outstanding", f"₹{total_outstanding:,.2f}")
    col2.metric("Total Paid", f"₹{total_paid:,.2f}")
    col3.metric("Total Invoiced", f"₹{total_amount:,.2f}")
    col4.metric("Number of Customers", num_customers)
    
    # Customer table with risk grades
    st.header("👥 Customer Risk Summary")
    display_cols = ['customer_name', 'total_invoices', 'total_amount', 'total_paid', 
                    'total_outstanding', 'max_overdue_days', 'risk_score', 'risk_grade', 'recommendation']
    display_df = customer_summary[display_cols].copy()
    
    # Format currency in ₹
    for col in ['total_amount', 'total_paid', 'total_outstanding']:
        display_df[col] = display_df[col].apply(lambda x: f"₹{x:,.2f}")
    
    # Apply color to risk grade column
    styled = display_df.style.applymap(color_grade, subset=['risk_grade'])
    st.dataframe(styled, use_container_width=True)
    
    # Risk distribution chart
    st.header("📊 Risk Category Distribution")
    grade_counts = customer_summary['risk_grade'].value_counts().reindex(['A','B','C','D'], fill_value=0)
    fig = px.bar(x=grade_counts.index, y=grade_counts.values, 
                 title="Customers by Risk Grade",
                 labels={'x':'Risk Grade', 'y':'Number of Customers'},
                 color=grade_counts.index,
                 color_discrete_map={'A':'green','B':'gold','C':'orange','D':'red'})
    st.plotly_chart(fig, use_container_width=True)
    
    # Download report
    st.header("📥 Download Full Report")
    
    # Prepare detailed invoice-level data with risk grade per customer
    detailed_report = df_inv.merge(customer_summary[['customer_name', 'risk_grade', 'recommendation']], on='customer_name', how='left')
    
    # Create Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        customer_summary.to_excel(writer, sheet_name='Customer Summary', index=False)
        detailed_report.to_excel(writer, sheet_name='Invoice Details', index=False)
    
    st.download_button(
        label="Download Excel Report",
        data=output.getvalue(),
        file_name=f"risk_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
else:
    st.info("👆 Please upload a file to begin.")
    if st.button("Use sample data"):
        sample_data = pd.DataFrame({
            'Customer_name': ['Alpha Ltd', 'Alpha Ltd', 'Beta Inc', 'Beta Inc', 'Gamma LLC', 'Delta Corp'],
            'Invoice_No': ['INV001', 'INV002', 'INV003', 'INV004', 'INV005', 'INV006'],
            'Invoice_date': ['2025-01-10', '2025-01-15', '2025-01-20', '2025-02-01', '2025-02-10', '2025-02-15'],
            'Due_date': ['2025-02-09', '2025-02-14', '2025-02-19', '2025-03-03', '2025-03-12', '2025-03-17'],
            'Amount': [5000, 3000, 7000, 2000, 4000, 6000],
            'paid_Amount': [5000, 3000, 0, 2000, 1000, 0],
            'Payment_date': ['2025-02-05', '2025-02-20', None, '2025-03-01', '2025-03-15', None]
        })
        sample_bytes = io.BytesIO()
        sample_data.to_csv(sample_bytes, index=False)
        sample_bytes.seek(0)
        st.session_state['sample_uploaded'] = sample_bytes
        st.rerun()

if 'sample_uploaded' in st.session_state:
    uploaded_file = st.session_state['sample_uploaded']
