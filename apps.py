import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import io

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CreditPulse — Wholesale Risk Intelligence",
    layout="wide",
    page_icon="⚡"
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@700;800&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp { background: #060E18; color: #F0F4F8; }

/* Hide default streamlit header */
header[data-testid="stHeader"] { background: transparent; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0D1B2A !important;
    border-right: 1px solid rgba(255,255,255,0.07);
}
section[data-testid="stSidebar"] * { color: #C8D8E8 !important; }

/* Metrics */
[data-testid="metric-container"] {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 16px 20px;
}
[data-testid="metric-container"] label { color: #8899AA !important; font-size: 11px !important; letter-spacing: 0.08em; text-transform: uppercase; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { color: #F0F4F8 !important; font-family: 'DM Mono', monospace !important; font-size: 22px !important; }

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #5B9EF4, #4A7EC4) !important;
    border: none !important;
    color: white !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 10px 24px !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }

/* Dataframe */
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.03);
    border-radius: 10px;
    padding: 4px;
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: #8899AA;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    background: rgba(91,158,244,0.15) !important;
    color: #5B9EF4 !important;
}

/* Selectbox / Inputs */
.stSelectbox > div > div, .stDateInput > div > div {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    color: #F0F4F8 !important;
}

/* Expander */
.streamlit-expanderHeader {
    background: rgba(255,255,255,0.04) !important;
    border-radius: 10px !important;
    color: #C8D8E8 !important;
}

/* File uploader */
[data-testid="stFileUploader"] {
    background: rgba(91,158,244,0.06);
    border: 1px dashed rgba(91,158,244,0.3);
    border-radius: 12px;
    padding: 12px;
}

/* Download button */
.stDownloadButton > button {
    background: rgba(0,229,160,0.1) !important;
    border: 1px solid rgba(0,229,160,0.3) !important;
    color: #00E5A0 !important;
    border-radius: 10px !important;
}

/* Success / Info */
.stSuccess { background: rgba(0,229,160,0.1) !important; border: 1px solid rgba(0,229,160,0.3) !important; border-radius: 10px !important; }
.stInfo    { background: rgba(91,158,244,0.1) !important; border: 1px solid rgba(91,158,244,0.3) !important; border-radius: 10px !important; }
.stWarning { background: rgba(255,140,66,0.1)  !important; border: 1px solid rgba(255,140,66,0.3)  !important; border-radius: 10px !important; }
.stError   { background: rgba(255,56,96,0.1)   !important; border: 1px solid rgba(255,56,96,0.3)   !important; border-radius: 10px !important; }
</style>
""", unsafe_allow_html=True)

# ─── Constants ────────────────────────────────────────────────────────────────
GRADE_META = {
    "A": {"color": "#00E5A0", "label": "Low Risk",      "action": "Increase Limit",    "call": "Thank & Reward Call",      "limit_mult": 1.2},
    "B": {"color": "#FFD166", "label": "Moderate Risk", "action": "Monitor Monthly",   "call": "Check-In Call",            "limit_mult": 0.8},
    "C": {"color": "#FF8C42", "label": "High Risk",     "action": "Reduce Limit 50%",  "call": "Payment Follow-Up Call",   "limit_mult": 0.5},
    "D": {"color": "#FF3860", "label": "Critical Risk", "action": "Suspend Credit",    "call": "Urgent Collection Call",   "limit_mult": 0.0},
}

CALL_SCRIPTS = {
    "A": "Hello {name}, we're calling to thank you for your outstanding payment record. As a valued customer, we're pleased to offer you an increased credit facility.",
    "B": "Hello {name}, this is a friendly check-in call. We noticed a few minor payment delays and want to ensure everything is running smoothly on your end.",
    "C": "Hello {name}, we're following up on overdue invoices totalling {amount}. We need to discuss an immediate payment arrangement to keep your account active.",
    "D": "Hello {name}, this is an urgent notice regarding your account. Outstanding dues of {amount} have been flagged for suspension. Immediate payment is required to avoid legal escalation.",
}

# ─── Helpers ──────────────────────────────────────────────────────────────────
def fmt(x): return f"₹{x:,.0f}"
def pct(a, b): return round((a / b) * 100) if b > 0 else 0

GRADE_RGBA = {"A": "0,229,160", "B": "255,209,102", "C": "255,140,66", "D": "255,56,96"}

def grade_badge(grade):
    m = GRADE_META[grade]
    rgba = GRADE_RGBA[grade]
    return f'<span style="background:rgba({rgba},0.15);color:{m["color"]};border:1px solid {m["color"]}40;padding:3px 12px;border-radius:20px;font-size:12px;font-weight:700">{grade} · {m["label"]}</span>'

# ─── Data Generation ──────────────────────────────────────────────────────────
def generate_example_data():
    np.random.seed(42)
    customers = ["Apex Retail Ltd","BlueStar Merchants","Cosmo Distributors",
                 "Delta Traders","Echo Enterprises","Frontier Goods","Global Mart","Horizon Shops"]
    data = []
    today = pd.Timestamp("2026-01-01")
    for cust in customers:
        n = np.random.randint(3, 8)
        for i in range(n):
            inv_date = today - pd.Timedelta(days=np.random.randint(30, 200))
            due_date = inv_date + pd.Timedelta(days=30)
            amount   = np.random.randint(2000, 40000)
            r = np.random.rand()
            if r < 0.3:
                paid = amount;       pay_date = due_date - pd.Timedelta(days=np.random.randint(1,5))
            elif r < 0.6:
                paid = amount;       pay_date = due_date + pd.Timedelta(days=np.random.randint(5,40))
            elif r < 0.8:
                paid = amount * np.random.uniform(0.2, 0.8)
                pay_date = due_date + pd.Timedelta(days=np.random.randint(-5, 60))
            else:
                paid = 0;            pay_date = pd.NaT
            data.append({"customer_name": cust, "invoice_no": f"INV-{cust[:3].upper()}-{i}",
                          "invoice_date": inv_date, "due_date": due_date,
                          "amount": round(amount), "paid_amount": round(paid), "payment_date": pay_date})
    return pd.DataFrame(data)

# ─── Cleaning ─────────────────────────────────────────────────────────────────
def clean_data(df):
    df.columns = df.columns.str.lower().str.strip().str.replace(" ", "_")
    required = ["customer_name","invoice_no","invoice_date","due_date","amount","paid_amount"]
    for col in required:
        if col not in df.columns:
            st.error(f"❌ Missing column: **{col}**"); st.stop()
    for c in ["invoice_date","due_date","payment_date"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    df["amount"]      = pd.to_numeric(df["amount"],      errors="coerce").fillna(0)
    df["paid_amount"] = pd.to_numeric(df["paid_amount"], errors="coerce").fillna(0)
    if "payment_date" not in df.columns:
        df["payment_date"] = pd.NaT
    return df[df["amount"] > 0].copy()

# ─── Invoice Metrics ──────────────────────────────────────────────────────────
def calculate_invoice_metrics(df, today):
    df = df.copy()
    df["outstanding"] = (df["amount"] - df["paid_amount"]).clip(lower=0)
    df["fully_paid"]  = df["paid_amount"] >= df["amount"]
    df["overdue_days"] = 0
    df["paid_late"]    = False

    mask_unpaid = (df["outstanding"] > 0) & (df["due_date"] < today)
    df.loc[mask_unpaid, "overdue_days"] = (today - df.loc[mask_unpaid, "due_date"]).dt.days

    mask_late = df["fully_paid"] & (df["payment_date"] > df["due_date"])
    df.loc[mask_late, "overdue_days"] = (df.loc[mask_late,"payment_date"] - df.loc[mask_late,"due_date"]).dt.days
    df.loc[mask_late, "paid_late"] = True

    df["overdue_days"] = df["overdue_days"].clip(lower=0, upper=180)
    return df

# ─── Risk Scoring ─────────────────────────────────────────────────────────────
def score_customer(row):
    overdue_score  = min(row["max_overdue"] / 90, 1) * 40
    out_ratio      = row["total_outstanding"] / row["total_amount"] if row["total_amount"] > 0 else 0
    out_score      = out_ratio * 40
    pay_ratio      = row["total_paid"] / row["total_amount"] if row["total_amount"] > 0 else 0
    late_ratio     = row["late_count"] / row["paid_count"] if row["paid_count"] > 0 else 1
    behav_score    = min((1 - pay_ratio) * 10 + late_ratio * 10, 20)
    return min(round(overdue_score + out_score + behav_score), 100)

def grade(score):
    return "A" if score <= 10 else "B" if score <= 30 else "C" if score <= 60 else "D"

# ─── Aggregation ──────────────────────────────────────────────────────────────
def aggregate(df):
    g = df.groupby("customer_name").agg(
        total_invoices   = ("invoice_no",    "count"),
        total_amount     = ("amount",        "sum"),
        total_paid       = ("paid_amount",   "sum"),
        max_overdue      = ("overdue_days",  "max"),
        late_count       = ("paid_late",     "sum"),
        paid_count       = ("fully_paid",    "sum"),
    ).reset_index()
    g["total_outstanding"] = (g["total_amount"] - g["total_paid"]).clip(lower=0)
    late_avg = df[df["paid_late"]].groupby("customer_name")["overdue_days"].mean()
    g["avg_delay"] = g["customer_name"].map(late_avg).fillna(0).round(1)

    rows = []
    for _, r in g.iterrows():
        sc = score_customer(r)
        gr = grade(sc)
        m  = GRADE_META[gr]
        rows.append({
            "Customer":        r["customer_name"],
            "Invoices":        int(r["total_invoices"]),
            "Total Credit":    r["total_amount"],
            "Total Paid":      r["total_paid"],
            "Outstanding":     r["total_outstanding"],
            "Max Overdue(d)":  int(r["max_overdue"]),
            "Avg Delay(d)":    r["avg_delay"],
            "Risk Score":      sc,
            "Risk Grade":      gr,
            "Grade Label":     m["label"],
            "Suggested Limit": r["total_amount"] * m["limit_mult"],
            "Credit Action":   m["action"],
            "Call Type":       m["call"],
            "Call Script":     CALL_SCRIPTS[gr].format(
                name=r["customer_name"],
                amount=fmt(r["total_outstanding"])
            ),
        })
    return pd.DataFrame(rows).sort_values("Risk Score", ascending=False)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚡ CreditPulse")
    st.markdown("---")
    today_input = st.date_input("📅 Calculation Date", value=datetime.now().date())
    today = pd.Timestamp(today_input)
    st.markdown("---")
    st.markdown("**Risk Grade Legend**")
    for g_key, m in GRADE_META.items():
        st.markdown(f'<span style="color:{m["color"]}">■</span> **Grade {g_key}** — {m["label"]}', unsafe_allow_html=True)
    st.markdown("---")
    template = pd.DataFrame({
        "customer_name":["ABC Stores"], "invoice_no":["INV001"],
        "invoice_date":["2026-01-01"], "due_date":["2026-01-31"],
        "amount":[10000], "paid_amount":[5000], "payment_date":["2026-02-10"]
    })
    st.download_button("📄 Download Template", template.to_csv(index=False), "template.csv", use_container_width=True)

# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style="padding:8px 0 24px">
  <div style="font-family:'Syne',sans-serif;font-size:30px;font-weight:800;letter-spacing:-0.03em;line-height:1.1">
    ⚡ CreditPulse
    <span style="font-size:14px;font-weight:400;color:#8899AA;letter-spacing:0;margin-left:10px">Wholesale Risk Intelligence</span>
  </div>
  <div style="color:#8899AA;font-size:13px;margin-top:6px">Identify risky customers · Score payment behaviour · Prioritize collections calls</div>
</div>
""", unsafe_allow_html=True)

# ─── Pipeline Stepper ─────────────────────────────────────────────────────────
def stepper(active):
    stages = ["① INPUT", "② PROCESS", "③ OUTPUT", "④ ACTION"]
    cols = st.columns(len(stages))
    for i, (col, s) in enumerate(zip(cols, stages)):
        color = "#5B9EF4" if i == active else ("#00E5A0" if i < active else "#2D3F52")
        col.markdown(f'<div style="text-align:center;padding:10px;background:rgba(255,255,255,0.03);border-radius:10px;border:1px solid {color}40;color:{color};font-size:12px;font-weight:600">{s}</div>', unsafe_allow_html=True)

# ─── INPUT STAGE ──────────────────────────────────────────────────────────────
stepper(0)
st.markdown("<div style='height:20px'/>", unsafe_allow_html=True)

col_upload, col_example = st.columns([2, 1])

with col_upload:
    uploaded = st.file_uploader("Upload Invoice File (CSV or Excel)", type=["csv","xlsx"])

with col_example:
    st.markdown("<div style='height:28px'/>", unsafe_allow_html=True)
    use_example = st.button("🧪 Use Example Data", use_container_width=True)

df_raw = None
if uploaded:
    df_raw = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
    st.success(f"✅ Loaded **{len(df_raw)}** rows from `{uploaded.name}`")
elif use_example:
    df_raw = generate_example_data()
    st.info(f"🧪 Example data loaded — **{len(df_raw)}** invoices across **8** customers")

# ─── PROCESS + OUTPUT + ACTION ────────────────────────────────────────────────
if df_raw is not None:

    # PROCESS
    stepper(1)
    with st.spinner("⚙️ Calculating overdue metrics and risk scores..."):
        df_clean  = clean_data(df_raw)
        df_inv    = calculate_invoice_metrics(df_clean, today)
        summary   = aggregate(df_inv)
    st.success("✅ Data processed successfully")

    # ── KPIs ──────────────────────────────────────────────────────────────────
    stepper(2)
    st.markdown("<div style='height:16px'/>", unsafe_allow_html=True)

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Customers",      summary.shape[0])
    k2.metric("Total Credit",   fmt(summary["Total Credit"].sum()))
    k3.metric("Total Paid",     fmt(summary["Total Paid"].sum()))
    k4.metric("Outstanding",    fmt(summary["Outstanding"].sum()))
    k5.metric("Critical (D)",   int((summary["Risk Grade"] == "D").sum()), delta="Needs immediate action", delta_color="inverse")

    st.markdown("<div style='height:16px'/>", unsafe_allow_html=True)

    # ── Charts Row ────────────────────────────────────────────────────────────
    ch1, ch2 = st.columns([1, 2])

    with ch1:
        grade_counts = summary["Risk Grade"].value_counts().reindex(["A","B","C","D"], fill_value=0)
        fig_pie = go.Figure(go.Pie(
            labels=[f"Grade {g}" for g in grade_counts.index],
            values=grade_counts.values,
            hole=0.6,
            marker_colors=[GRADE_META[g]["color"] for g in grade_counts.index],
            textfont=dict(color="white"),
        ))
        fig_pie.update_layout(
            title="Risk Distribution", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#C8D8E8", legend=dict(font=dict(color="#C8D8E8")),
            margin=dict(t=40,b=0,l=0,r=0), height=260
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with ch2:
        fig_bar = px.bar(
            summary.sort_values("Outstanding", ascending=False),
            x="Customer", y="Outstanding", color="Risk Grade",
            color_discrete_map={g: GRADE_META[g]["color"] for g in GRADE_META},
            title="Outstanding by Customer",
            labels={"Outstanding": "Outstanding (₹)", "Customer": ""}
        )
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#C8D8E8", legend_title_text="Grade",
            margin=dict(t=40,b=0,l=0,r=0), height=260,
            xaxis=dict(tickangle=-20, gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)")
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ── Action Recommendations Panel ──────────────────────────────────────────
    stepper(3)
    st.markdown("<div style='height:12px'/>", unsafe_allow_html=True)

    rec_cols = st.columns(4)
    for col, (g_key, m) in zip(rec_cols, GRADE_META.items()):
        cnt = int((summary["Risk Grade"] == g_key).sum())
        rgba = GRADE_RGBA[g_key]
        col.markdown(f"""
        <div style="background:rgba({rgba},0.08);
                    border:1px solid {m["color"]}40;border-radius:14px;padding:16px;">
          <div style="color:{m["color"]};font-weight:700;font-size:16px;margin-bottom:4px">Grade {g_key} · {cnt} customers</div>
          <div style="color:#C8D8E8;font-size:12px;margin-bottom:6px">📋 {m["action"]}</div>
          <div style="color:#C8D8E8;font-size:12px">📞 {m["call"]}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:24px'/>", unsafe_allow_html=True)

    # ── Tabs: Risk Table | Call Table | Invoice Detail ─────────────────────────
    grade_filter = st.selectbox("🔍 Filter by Risk Grade", ["ALL","A","B","C","D"], horizontal=True if hasattr(st, 'radio') else False)
    filtered = summary if grade_filter == "ALL" else summary[summary["Risk Grade"] == grade_filter]

    tab_risk, tab_call, tab_invoice = st.tabs(["📊 Risk Analysis Table", "📞 Call Table", "🧾 Invoice Detail"])

    # ── Risk Table ──────────────────────────────────────────────────────────
    with tab_risk:
        display = filtered[[
            "Customer","Risk Score","Risk Grade","Grade Label",
            "Total Credit","Total Paid","Outstanding",
            "Max Overdue(d)","Avg Delay(d)","Suggested Limit","Credit Action"
        ]].copy()
        display["Total Credit"]    = display["Total Credit"].apply(fmt)
        display["Total Paid"]      = display["Total Paid"].apply(fmt)
        display["Outstanding"]     = display["Outstanding"].apply(fmt)
        display["Suggested Limit"] = display["Suggested Limit"].apply(fmt)

        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Risk Score":     st.column_config.ProgressColumn("Risk Score", min_value=0, max_value=100, format="%d"),
                "Risk Grade":     st.column_config.TextColumn("Grade", width="small"),
                "Max Overdue(d)": st.column_config.NumberColumn("Max Overdue", format="%d days"),
                "Avg Delay(d)":   st.column_config.NumberColumn("Avg Delay",   format="%.1f days"),
            }
        )

        # Export
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as w:
            summary.to_excel(w, sheet_name="Customer Risk", index=False)
            df_inv.to_excel(w,  sheet_name="Invoice Data",  index=False)
        st.download_button("⬇ Download Excel Report", out.getvalue(), "credit_risk_report.xlsx", use_container_width=False)

    # ── Call Table ──────────────────────────────────────────────────────────
    with tab_call:
        st.markdown(f"**{len(filtered)} customers** · Sorted by urgency (Grade D first)")
        st.markdown("<div style='height:8px'/>", unsafe_allow_html=True)

        call_display = filtered[[
            "Customer","Risk Grade","Outstanding","Max Overdue(d)","Call Type","Credit Action","Call Script"
        ]].copy()
        call_display.insert(0, "Priority", range(1, len(call_display)+1))
        call_display["Outstanding"]     = call_display["Outstanding"].apply(fmt)
        call_display["Max Overdue(d)"]  = call_display["Max Overdue(d)"].apply(lambda x: f"{x} days" if x > 0 else "✅ On time")

        st.dataframe(
            call_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Priority":    st.column_config.NumberColumn("#", width="small"),
                "Risk Grade":  st.column_config.TextColumn("Grade", width="small"),
                "Call Script": st.column_config.TextColumn("Call Script", width="large"),
            }
        )

        # Call script expanders
        st.markdown("### 📋 Call Scripts by Customer")
        for _, row in filtered.iterrows():
            m = GRADE_META[row["Risk Grade"]]
            rgba = GRADE_RGBA[row["Risk Grade"]]
            with st.expander(f"{row['Risk Grade']} · {row['Customer']} — {row['Call Type']} · Outstanding: {fmt(row['Outstanding'])}"):
                st.markdown(f"""
                <div style="background:rgba({rgba},0.08);
                            border:1px solid {m["color"]}40;border-radius:12px;padding:16px;margin-bottom:12px;">
                  <div style="font-size:11px;color:{m["color"]};letter-spacing:0.1em;margin-bottom:8px">SUGGESTED SCRIPT</div>
                  <div style="color:#C8D8E8;font-size:14px;line-height:1.7">{row["Call Script"]}</div>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;">
                  <div style="background:rgba(255,255,255,0.04);border-radius:10px;padding:12px">
                    <div style="font-size:10px;color:#8899AA">Outstanding</div>
                    <div style="font-size:15px;font-weight:700;color:{m["color"]}">{fmt(row["Outstanding"])}</div>
                  </div>
                  <div style="background:rgba(255,255,255,0.04);border-radius:10px;padding:12px">
                    <div style="font-size:10px;color:#8899AA">Max Overdue</div>
                    <div style="font-size:15px;font-weight:700;color:#C8D8E8">{row["Max Overdue(d)"]} days</div>
                  </div>
                  <div style="background:rgba(255,255,255,0.04);border-radius:10px;padding:12px">
                    <div style="font-size:10px;color:#8899AA">Credit Action</div>
                    <div style="font-size:14px;font-weight:600;color:#C8D8E8">{row["Credit Action"]}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                # Call outcome logger
                outcome = st.selectbox("Call Outcome", ["— Select —","Contacted","No Answer","Promise to Pay","Disputed","Paid in Full"], key=f"outcome_{row['Customer']}")
                notes   = st.text_area("Call Notes", placeholder="Add notes here...", key=f"notes_{row['Customer']}", height=80)
                if st.button("💾 Log Call", key=f"log_{row['Customer']}"):
                    st.success(f"✅ Call logged for **{row['Customer']}** — {outcome}")

        # Export call list
        call_export = filtered[["Customer","Risk Grade","Outstanding","Max Overdue(d)","Call Type","Credit Action","Call Script"]].copy()
        call_export["Outstanding"] = call_export["Outstanding"].apply(fmt)
        st.download_button("⬇ Export Call List", call_export.to_csv(index=False), "call_list.csv", use_container_width=False)

    # ── Invoice Detail ──────────────────────────────────────────────────────
    with tab_invoice:
        selected_customer = st.selectbox("Select Customer", summary["Customer"].tolist())
        cust_inv = df_inv[df_inv["customer_name"] == selected_customer].copy()

        cust_row = summary[summary["Customer"] == selected_customer].iloc[0]
        m = GRADE_META[cust_row["Risk Grade"]]

        ic1, ic2, ic3, ic4 = st.columns(4)
        ic1.metric("Risk Grade",   f"{cust_row['Risk Grade']} — {cust_row['Grade Label']}")
        ic2.metric("Risk Score",   cust_row["Risk Score"])
        ic3.metric("Outstanding",  fmt(cust_row["Outstanding"]))
        ic4.metric("Suggested Limit", fmt(cust_row["Suggested Limit"]))

        inv_display = cust_inv[["invoice_no","invoice_date","due_date","amount","paid_amount","outstanding","overdue_days","paid_late","fully_paid"]].copy()
        inv_display.columns = ["Invoice","Invoice Date","Due Date","Amount","Paid","Outstanding","Overdue(d)","Paid Late","Fully Paid"]
        inv_display["Amount"]      = inv_display["Amount"].apply(fmt)
        inv_display["Paid"]        = inv_display["Paid"].apply(fmt)
        inv_display["Outstanding"] = inv_display["Outstanding"].apply(fmt)

        st.dataframe(inv_display, use_container_width=True, hide_index=True,
            column_config={"Overdue(d)": st.column_config.NumberColumn(format="%d days"),
                           "Paid Late":  st.column_config.CheckboxColumn(),
                           "Fully Paid": st.column_config.CheckboxColumn()})

else:
    st.markdown("""
    <div style="text-align:center;padding:60px 20px;color:#4A5568">
      <div style="font-size:48px;margin-bottom:16px">📂</div>
      <div style="font-size:18px;font-weight:600;color:#8899AA;margin-bottom:8px">No data loaded yet</div>
      <div style="font-size:13px">Upload a CSV/Excel file or click <b>Use Example Data</b> above to begin</div>
    </div>
    """, unsafe_allow_html=True)
