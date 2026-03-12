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
header[data-testid="stHeader"] { background: transparent; }
section[data-testid="stSidebar"] { background: #0D1B2A !important; border-right: 1px solid rgba(255,255,255,0.07); }
section[data-testid="stSidebar"] * { color: #C8D8E8 !important; }
[data-testid="metric-container"] { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; padding: 16px 20px; }
[data-testid="metric-container"] label { color: #8899AA !important; font-size: 11px !important; letter-spacing: 0.08em; text-transform: uppercase; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { color: #F0F4F8 !important; font-family: 'DM Mono', monospace !important; font-size: 20px !important; }
.stButton > button { background: linear-gradient(135deg, #5B9EF4, #4A7EC4) !important; border: none !important; color: white !important; border-radius: 10px !important; font-weight: 600 !important; padding: 10px 24px !important; }
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }
.stTabs [data-baseweb="tab-list"] { background: rgba(255,255,255,0.03); border-radius: 10px; padding: 4px; gap: 4px; }
.stTabs [data-baseweb="tab"] { background: transparent; color: #8899AA; border-radius: 8px; font-size: 13px; font-weight: 500; }
.stTabs [aria-selected="true"] { background: rgba(91,158,244,0.15) !important; color: #5B9EF4 !important; }
.stSelectbox > div > div, .stDateInput > div > div { background: rgba(255,255,255,0.05) !important; border: 1px solid rgba(255,255,255,0.1) !important; border-radius: 10px !important; color: #F0F4F8 !important; }
.streamlit-expanderHeader { background: rgba(255,255,255,0.04) !important; border-radius: 10px !important; color: #C8D8E8 !important; }
[data-testid="stFileUploader"] { background: rgba(91,158,244,0.06); border: 1px dashed rgba(91,158,244,0.3); border-radius: 12px; padding: 12px; }
.stDownloadButton > button { background: rgba(0,229,160,0.1) !important; border: 1px solid rgba(0,229,160,0.3) !important; color: #00E5A0 !important; border-radius: 10px !important; }
</style>
""", unsafe_allow_html=True)

# ─── Constants ────────────────────────────────────────────────────────────────
GRADE_META = {
    "A": {"color": "#00E5A0", "rgba": "0,229,160",   "label": "Low Risk",      "action": "Increase Limit",   "call": "Thank & Reward Call",    "limit_mult": 1.2},
    "B": {"color": "#FFD166", "rgba": "255,209,102",  "label": "Moderate Risk", "action": "Monitor Monthly",  "call": "Check-In Call",          "limit_mult": 0.8},
    "C": {"color": "#FF8C42", "rgba": "255,140,66",   "label": "High Risk",     "action": "Reduce Limit 50%", "call": "Payment Follow-Up Call", "limit_mult": 0.5},
    "D": {"color": "#FF3860", "rgba": "255,56,96",    "label": "Critical Risk", "action": "Suspend Credit",   "call": "Urgent Collection Call", "limit_mult": 0.0},
}

CALL_SCRIPTS = {
    "A": "Hello {name}, we are calling to thank you for your outstanding payment record. As a valued customer, we are pleased to offer you an increased credit facility.",
    "B": "Hello {name}, this is a friendly check-in call. We noticed a few minor payment delays and want to ensure everything is running smoothly on your end.",
    "C": "Hello {name}, we are following up on overdue invoices totalling {amount}. We need to discuss an immediate payment arrangement to keep your account active.",
    "D": "Hello {name}, this is an urgent notice. Outstanding dues of {amount} have been flagged for suspension. Immediate payment is required to avoid legal escalation.",
}

# ─── Helpers ──────────────────────────────────────────────────────────────────
def fmt(x):
    try:
        return "Rs.{:,.0f}".format(float(x))
    except Exception:
        return "Rs.0"

def action_card_html(gk, cnt):
    m = GRADE_META[gk]
    return (
        '<div style="background:rgba(' + m["rgba"] + ',0.08);border:1px solid ' + m["color"] + '40;'
        'border-radius:14px;padding:16px;">'
        '<div style="color:' + m["color"] + ';font-weight:700;font-size:16px;margin-bottom:4px">'
        'Grade ' + gk + ' &middot; ' + str(cnt) + ' customers</div>'
        '<div style="color:#C8D8E8;font-size:12px;margin-bottom:6px">&#128203; ' + m["action"] + '</div>'
        '<div style="color:#C8D8E8;font-size:12px">&#128222; ' + m["call"] + '</div>'
        '</div>'
    )

def script_card_html(gk, script, outstanding_str, overdue_days, action):
    m = GRADE_META[gk]
    return (
        '<div style="background:rgba(' + m["rgba"] + ',0.08);border:1px solid ' + m["color"] + '40;'
        'border-radius:12px;padding:16px;margin-bottom:12px;">'
        '<div style="font-size:11px;color:' + m["color"] + ';letter-spacing:0.1em;margin-bottom:8px">SUGGESTED SCRIPT</div>'
        '<div style="color:#C8D8E8;font-size:14px;line-height:1.7">' + str(script) + '</div>'
        '</div>'
        '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:8px;">'
        '<div style="background:rgba(255,255,255,0.04);border-radius:10px;padding:12px">'
        '<div style="font-size:10px;color:#8899AA">Outstanding</div>'
        '<div style="font-size:15px;font-weight:700;color:' + m["color"] + '">' + outstanding_str + '</div></div>'
        '<div style="background:rgba(255,255,255,0.04);border-radius:10px;padding:12px">'
        '<div style="font-size:10px;color:#8899AA">Max Overdue</div>'
        '<div style="font-size:15px;font-weight:700;color:#C8D8E8">' + str(overdue_days) + ' days</div></div>'
        '<div style="background:rgba(255,255,255,0.04);border-radius:10px;padding:12px">'
        '<div style="font-size:10px;color:#8899AA">Credit Action</div>'
        '<div style="font-size:13px;font-weight:600;color:#C8D8E8">' + str(action) + '</div></div>'
        '</div>'
    )

# ─── Data Generation ──────────────────────────────────────────────────────────
def generate_example_data():
    np.random.seed(42)
    customers = [
        "Apex Retail Ltd", "BlueStar Merchants", "Cosmo Distributors",
        "Delta Traders", "Echo Enterprises", "Frontier Goods",
        "Global Mart", "Horizon Shops"
    ]
    data = []
    today = pd.Timestamp("2026-01-01")
    for cust in customers:
        n = int(np.random.randint(3, 8))
        for i in range(n):
            inv_date = today - pd.Timedelta(days=int(np.random.randint(30, 200)))
            due_date = inv_date + pd.Timedelta(days=30)
            amount   = int(np.random.randint(2000, 40000))
            r = np.random.rand()
            if r < 0.3:
                paid     = amount
                pay_date = due_date - pd.Timedelta(days=int(np.random.randint(1, 5)))
            elif r < 0.6:
                paid     = amount
                pay_date = due_date + pd.Timedelta(days=int(np.random.randint(5, 40)))
            elif r < 0.8:
                paid     = round(amount * float(np.random.uniform(0.2, 0.8)))
                pay_date = due_date + pd.Timedelta(days=int(np.random.randint(0, 60)))
            else:
                paid     = 0
                pay_date = pd.NaT
            data.append({
                "customer_name": cust,
                "invoice_no":    "INV-{}-{}".format(cust[:3].upper(), i),
                "invoice_date":  inv_date,
                "due_date":      due_date,
                "amount":        amount,
                "paid_amount":   round(paid),
                "payment_date":  pay_date,
            })
    return pd.DataFrame(data)

# ─── Cleaning ─────────────────────────────────────────────────────────────────
def clean_data(df):
    df = df.copy()
    df.columns = df.columns.str.lower().str.strip().str.replace(" ", "_")
    required = ["customer_name", "invoice_no", "invoice_date", "due_date", "amount", "paid_amount"]
    for col in required:
        if col not in df.columns:
            st.error("Missing column: {}".format(col))
            st.stop()
    for c in ["invoice_date", "due_date", "payment_date"]:
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
    df.loc[mask_unpaid, "overdue_days"] = (
        today - df.loc[mask_unpaid, "due_date"]
    ).dt.days.astype(int)

    mask_late = (
        df["fully_paid"] &
        df["payment_date"].notna() &
        (df["payment_date"] > df["due_date"])
    )
    df.loc[mask_late, "overdue_days"] = (
        df.loc[mask_late, "payment_date"] - df.loc[mask_late, "due_date"]
    ).dt.days.astype(int)
    df.loc[mask_late, "paid_late"] = True
    df["overdue_days"] = df["overdue_days"].clip(lower=0, upper=180)
    return df

# ─── Ageing ───────────────────────────────────────────────────────────────────
def calculate_ageing(df):
    df = df[df["outstanding"] > 0].copy()

    def bucket(d):
        if d <= 0:    return "Current"
        elif d <= 30: return "1-30 days"
        elif d <= 60: return "31-60 days"
        elif d <= 90: return "61-90 days"
        else:         return "90+ days"

    df["bucket"] = df["overdue_days"].apply(bucket)
    order  = ["Current", "1-30 days", "31-60 days", "61-90 days", "90+ days"]
    ag     = df.groupby(["customer_name", "bucket"])["outstanding"].sum().reset_index()
    pivot  = ag.pivot(index="customer_name", columns="bucket", values="outstanding").fillna(0)
    for col in order:
        if col not in pivot.columns:
            pivot[col] = 0
    pivot = pivot[order].reset_index()
    pivot["Total Outstanding"] = pivot[order].sum(axis=1)
    return pivot

# ─── Scoring ──────────────────────────────────────────────────────────────────
def score_customer(row):
    overdue_score = min(row["max_overdue"] / 90, 1) * 40
    out_ratio     = row["total_outstanding"] / row["total_amount"] if row["total_amount"] > 0 else 0
    out_score     = out_ratio * 40
    pay_ratio     = row["total_paid"] / row["total_amount"] if row["total_amount"] > 0 else 0
    late_ratio    = row["late_count"] / row["paid_count"] if row["paid_count"] > 0 else 1
    behav_score   = min((1 - pay_ratio) * 10 + late_ratio * 10, 20)
    return min(round(overdue_score + out_score + behav_score), 100)

def get_grade(score):
    if score <= 10:   return "A"
    elif score <= 30: return "B"
    elif score <= 60: return "C"
    else:             return "D"

# ─── Aggregation ──────────────────────────────────────────────────────────────
def aggregate(df):
    g = df.groupby("customer_name").agg(
        total_invoices=("invoice_no",   "count"),
        total_amount  =("amount",       "sum"),
        total_paid    =("paid_amount",  "sum"),
        max_overdue   =("overdue_days", "max"),
        late_count    =("paid_late",    "sum"),
        paid_count    =("fully_paid",   "sum"),
    ).reset_index()

    g["total_outstanding"] = (g["total_amount"] - g["total_paid"]).clip(lower=0)
    late_avg = df[df["paid_late"]].groupby("customer_name")["overdue_days"].mean()
    g["avg_delay"] = g["customer_name"].map(late_avg).fillna(0).round(1)

    rows = []
    for _, r in g.iterrows():
        sc = score_customer(r)
        gr = get_grade(sc)
        m  = GRADE_META[gr]
        rows.append({
            "Customer":        r["customer_name"],
            "Invoices":        int(r["total_invoices"]),
            "Total Credit":    round(float(r["total_amount"]), 2),
            "Total Paid":      round(float(r["total_paid"]), 2),
            "Outstanding":     round(float(r["total_outstanding"]), 2),
            "Max Overdue(d)":  int(r["max_overdue"]),
            "Avg Delay(d)":    float(r["avg_delay"]),
            "Risk Score":      sc,
            "Risk Grade":      gr,
            "Grade Label":     m["label"],
            "Suggested Limit": round(float(r["total_amount"]) * m["limit_mult"], 2),
            "Credit Action":   m["action"],
            "Call Type":       m["call"],
            "Call Script":     CALL_SCRIPTS[gr].format(
                name=r["customer_name"],
                amount=fmt(r["total_outstanding"])
            ),
        })

    return pd.DataFrame(rows).sort_values("Risk Score", ascending=False).reset_index(drop=True)

# ─── Stepper ──────────────────────────────────────────────────────────────────
def stepper(active):
    stages = ["① INPUT", "② PROCESS", "③ OUTPUT", "④ ACTION"]
    cols   = st.columns(len(stages))
    for i, (col, s) in enumerate(zip(cols, stages)):
        if i < active:
            color, bg = "#00E5A0", "rgba(0,229,160,0.08)"
        elif i == active:
            color, bg = "#5B9EF4", "rgba(91,158,244,0.1)"
        else:
            color, bg = "#2D3F52", "transparent"
        col.markdown(
            '<div style="text-align:center;padding:10px;background:' + bg + ';'
            'border-radius:10px;border:1px solid ' + color + '40;'
            'color:' + color + ';font-size:12px;font-weight:600">' + s + '</div>',
            unsafe_allow_html=True
        )
    st.markdown("<div style='height:20px'/>", unsafe_allow_html=True)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚡ CreditPulse")
    st.markdown("---")
    today_input = st.date_input("📅 Calculation Date", value=datetime.now().date())
    today = pd.Timestamp(today_input)
    st.markdown("---")
    st.markdown("**Risk Grade Legend**")
    for gk, m in GRADE_META.items():
        st.markdown(
            '<span style="color:' + m["color"] + '">&#9632;</span> **Grade ' + gk + '** — ' + m["label"],
            unsafe_allow_html=True
        )
    st.markdown("---")
    template = pd.DataFrame({
        "customer_name": ["ABC Stores"],
        "invoice_no":    ["INV001"],
        "invoice_date":  ["2026-01-01"],
        "due_date":      ["2026-01-31"],
        "amount":        [10000],
        "paid_amount":   [5000],
        "payment_date":  ["2026-02-10"],
    })
    st.download_button("📄 Download Template", template.to_csv(index=False), "template.csv", use_container_width=True)

# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="padding:8px 0 24px">'
    '<div style="font-family:Syne,sans-serif;font-size:30px;font-weight:800;letter-spacing:-0.03em;line-height:1.1">'
    '&#9889; CreditPulse '
    '<span style="font-size:14px;font-weight:400;color:#8899AA;margin-left:10px">Wholesale Risk Intelligence</span>'
    '</div>'
    '<div style="color:#8899AA;font-size:13px;margin-top:6px">'
    'Identify risky customers &middot; Score payment behaviour &middot; Prioritize collections calls'
    '</div></div>',
    unsafe_allow_html=True
)

# ─── INPUT ────────────────────────────────────────────────────────────────────
stepper(0)

col_upload, col_example = st.columns([2, 1])
with col_upload:
    uploaded = st.file_uploader("Upload Invoice File (CSV or Excel)", type=["csv", "xlsx"])
with col_example:
    st.markdown("<div style='height:28px'/>", unsafe_allow_html=True)
    use_example = st.button("🧪 Use Example Data", use_container_width=True)

df_raw = None
if uploaded:
    if uploaded.name.endswith(".csv"):
        df_raw = pd.read_csv(uploaded)
    else:
        df_raw = pd.read_excel(uploaded)
    st.success("Loaded {} rows from {}".format(len(df_raw), uploaded.name))
elif use_example:
    df_raw = generate_example_data()
    st.info("Example data loaded — {} invoices across 8 customers".format(len(df_raw)))

# ─── MAIN ─────────────────────────────────────────────────────────────────────
if df_raw is not None:

    stepper(1)
    with st.spinner("Calculating overdue metrics and risk scores..."):
        df_clean = clean_data(df_raw)
        df_inv   = calculate_invoice_metrics(df_clean, today)
        summary  = aggregate(df_inv)
        ageing   = calculate_ageing(df_inv)
    st.success("Data processed — {} customers analysed".format(len(summary)))

    # KPIs
    stepper(2)
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Customers",    str(len(summary)))
    k2.metric("Total Credit", fmt(summary["Total Credit"].sum()))
    k3.metric("Total Paid",   fmt(summary["Total Paid"].sum()))
    k4.metric("Outstanding",  fmt(summary["Outstanding"].sum()))
    k5.metric("Critical (D)", str(int((summary["Risk Grade"] == "D").sum())),
              delta="Immediate action needed", delta_color="inverse")

    st.markdown("<div style='height:16px'/>", unsafe_allow_html=True)

    # Charts
    ch1, ch2 = st.columns([1, 2])
    with ch1:
        grade_counts = summary["Risk Grade"].value_counts().reindex(["A","B","C","D"], fill_value=0)
        fig_pie = go.Figure(go.Pie(
            labels=["Grade " + g for g in grade_counts.index],
            values=grade_counts.values,
            hole=0.6,
            marker_colors=[GRADE_META[g]["color"] for g in grade_counts.index],
            textfont=dict(color="white"),
        ))
        fig_pie.update_layout(
            title="Risk Distribution",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#C8D8E8", legend=dict(font=dict(color="#C8D8E8")),
            margin=dict(t=40, b=0, l=0, r=0), height=280
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with ch2:
        fig_bar = px.bar(
            summary.sort_values("Outstanding", ascending=False),
            x="Customer", y="Outstanding", color="Risk Grade",
            color_discrete_map={g: GRADE_META[g]["color"] for g in GRADE_META},
            title="Outstanding Amount by Customer",
            labels={"Outstanding": "Outstanding (INR)", "Customer": ""}
        )
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#C8D8E8", legend_title_text="Grade",
            margin=dict(t=40, b=0, l=0, r=0), height=280,
            xaxis=dict(tickangle=-20, gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)")
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # Action Recommendations
    stepper(3)
    rec_cols = st.columns(4)
    for col, (gk, m) in zip(rec_cols, GRADE_META.items()):
        cnt = int((summary["Risk Grade"] == gk).sum())
        col.markdown(action_card_html(gk, cnt), unsafe_allow_html=True)

    st.markdown("<div style='height:24px'/>", unsafe_allow_html=True)

    # Grade Filter
    grade_filter = st.selectbox("Filter by Risk Grade", ["ALL", "A", "B", "C", "D"])
    filtered = summary.copy() if grade_filter == "ALL" else summary[summary["Risk Grade"] == grade_filter].copy()
    st.caption("Showing {} of {} customers".format(len(filtered), len(summary)))

    # Tabs
    tab_risk, tab_call, tab_ageing, tab_invoice = st.tabs([
        "📊 Risk Analysis",
        "📞 Call Table",
        "📅 Ageing Report",
        "🧾 Invoice Detail"
    ])

    # ── Tab 1: Risk Analysis ──────────────────────────────────────────────────
    with tab_risk:
        display = filtered[[
            "Customer", "Invoices", "Risk Score", "Risk Grade", "Grade Label",
            "Total Credit", "Total Paid", "Outstanding",
            "Max Overdue(d)", "Avg Delay(d)", "Suggested Limit", "Credit Action"
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
                "Avg Delay(d)":   st.column_config.NumberColumn("Avg Delay", format="%.1f days"),
                "Invoices":       st.column_config.NumberColumn("Invoices", format="%d"),
            }
        )

        out = io.BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as w:
            summary.to_excel(w, sheet_name="Customer Risk", index=False)
            df_inv.to_excel(w,  sheet_name="Invoice Data",  index=False)
            ageing.to_excel(w,  sheet_name="Ageing Report", index=False)
        st.download_button("⬇ Download Full Excel Report", out.getvalue(), "credit_risk_report.xlsx")

    # ── Tab 2: Call Table ─────────────────────────────────────────────────────
    with tab_call:
        st.markdown("{} customers · Sorted by urgency (Grade D first)".format(len(filtered)))

        call_display = filtered[[
            "Customer", "Risk Grade", "Outstanding",
            "Max Overdue(d)", "Call Type", "Credit Action", "Call Script"
        ]].copy()
        call_display.insert(0, "Priority", range(1, len(call_display) + 1))
        call_display["Outstanding"]    = call_display["Outstanding"].apply(fmt)
        call_display["Max Overdue(d)"] = call_display["Max Overdue(d)"].apply(
            lambda x: "{} days".format(int(x)) if x > 0 else "On time"
        )

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

        st.markdown("---")
        st.markdown("### Call Scripts & Outcome Logger")

        for _, row in filtered.iterrows():
            gk    = row["Risk Grade"]
            label = "{} | {} | {} | {}".format(gk, row["Customer"], row["Call Type"], fmt(row["Outstanding"]))
            with st.expander(label):
                st.markdown(
                    script_card_html(
                        gk,
                        row["Call Script"],
                        fmt(row["Outstanding"]),
                        int(row["Max Overdue(d)"]),
                        row["Credit Action"]
                    ),
                    unsafe_allow_html=True
                )
                outcome = st.selectbox(
                    "Call Outcome",
                    ["Select outcome", "Contacted", "No Answer", "Promise to Pay", "Disputed", "Paid in Full"],
                    key="outcome_{}".format(row["Customer"])
                )
                st.text_area("Call Notes", placeholder="Add notes here...", key="notes_{}".format(row["Customer"]), height=80)
                if st.button("Save Call Log", key="log_{}".format(row["Customer"])):
                    st.success("Call logged for {} — {}".format(row["Customer"], outcome))

        call_export = filtered[[
            "Customer", "Risk Grade", "Outstanding",
            "Max Overdue(d)", "Call Type", "Credit Action", "Call Script"
        ]].copy()
        call_export["Outstanding"] = call_export["Outstanding"].apply(fmt)
        st.download_button("⬇ Export Call List CSV", call_export.to_csv(index=False), "call_list.csv")

    # ── Tab 3: Ageing Report ──────────────────────────────────────────────────
    with tab_ageing:
        st.markdown("### Ageing Report")
        st.caption("Shows how long outstanding amounts have been unpaid per customer.")

        age_display = ageing.copy()
        money_cols  = ["Current", "1-30 days", "31-60 days", "61-90 days", "90+ days", "Total Outstanding"]
        for c in money_cols:
            if c in age_display.columns:
                age_display[c] = age_display[c].apply(fmt)
        age_display.rename(columns={"customer_name": "Customer"}, inplace=True)
        st.dataframe(age_display, use_container_width=True, hide_index=True)

        buckets  = ["Current", "1-30 days", "31-60 days", "61-90 days", "90+ days"]
        age_melt = ageing.melt(id_vars="customer_name", value_vars=buckets, var_name="Bucket", value_name="Amount")
        fig_age  = px.bar(
            age_melt, x="customer_name", y="Amount", color="Bucket",
            title="Ageing Breakdown by Customer",
            labels={"customer_name": "", "Amount": "Outstanding (INR)"},
            color_discrete_map={
                "Current":     "#8899AA",
                "1-30 days":   "#FFD166",
                "31-60 days":  "#FF8C42",
                "61-90 days":  "#FF5733",
                "90+ days":    "#FF3860",
            }
        )
        fig_age.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#C8D8E8", barmode="stack",
            xaxis=dict(tickangle=-20, gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            margin=dict(t=40, b=0, l=0, r=0), height=320
        )
        st.plotly_chart(fig_age, use_container_width=True)
        st.download_button("⬇ Export Ageing Report", ageing.to_csv(index=False), "ageing_report.csv")

    # ── Tab 4: Invoice Detail ─────────────────────────────────────────────────
    with tab_invoice:
        st.markdown("### Customer Invoice Detail")

        selected_customer = st.selectbox("Select Customer", summary["Customer"].tolist(), key="inv_sel")
        cust_inv = df_inv[df_inv["customer_name"] == selected_customer].copy()
        cust_row = summary[summary["Customer"] == selected_customer].iloc[0]

        ic1, ic2, ic3, ic4, ic5 = st.columns(5)
        ic1.metric("Risk Grade",      "{} — {}".format(cust_row["Risk Grade"], cust_row["Grade Label"]))
        ic2.metric("Risk Score",      str(cust_row["Risk Score"]))
        ic3.metric("Total Invoices",  str(cust_row["Invoices"]))
        ic4.metric("Outstanding",     fmt(cust_row["Outstanding"]))
        ic5.metric("Suggested Limit", fmt(cust_row["Suggested Limit"]))

        inv_display = cust_inv[[
            "invoice_no", "invoice_date", "due_date",
            "amount", "paid_amount", "outstanding",
            "overdue_days", "paid_late", "fully_paid"
        ]].copy()
        inv_display.columns = [
            "Invoice", "Invoice Date", "Due Date",
            "Amount", "Paid", "Outstanding",
            "Overdue(d)", "Paid Late", "Fully Paid"
        ]
        inv_display["Amount"]      = inv_display["Amount"].apply(fmt)
        inv_display["Paid"]        = inv_display["Paid"].apply(fmt)
        inv_display["Outstanding"] = inv_display["Outstanding"].apply(fmt)

        st.dataframe(
            inv_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Overdue(d)": st.column_config.NumberColumn("Overdue", format="%d days"),
                "Paid Late":  st.column_config.CheckboxColumn("Paid Late"),
                "Fully Paid": st.column_config.CheckboxColumn("Fully Paid"),
            }
        )
        st.download_button(
            "⬇ Export Invoices",
            cust_inv.to_csv(index=False),
            "{}_invoices.csv".format(selected_customer.replace(" ", "_"))
        )

else:
    st.markdown(
        '<div style="text-align:center;padding:80px 20px;">'
        '<div style="font-size:52px;margin-bottom:16px">📂</div>'
        '<div style="font-size:20px;font-weight:600;color:#8899AA;margin-bottom:10px">No data loaded yet</div>'
        '<div style="font-size:13px;color:#4A5568">Upload a CSV / Excel file or click Use Example Data above to begin</div>'
        '</div>',
        unsafe_allow_html=True
    )
