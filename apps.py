import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import io, hashlib
import time
from supabase import create_client

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="CreditPulse | Wholesale Risk Intelligence",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="collapsed"
)

# ══════════════════════════════════════════════════════════════════════════════
#  CSS (Improved for Responsiveness & Simplicity)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Inter:wght@400;500;600;700;800&display=swap');

/* ── Theme Variables ── */
:root {
  --bg:#FFFFFF;--bg2:#F7F8FA;--bg3:#EDEEF2;
  --border:rgba(0,0,0,0.08);--text:#0D1117;--muted:#6B7280;
  --card:#FFFFFF;--shadow:0 2px 12px rgba(0,0,0,0.06);
  --green:#00C278;--blue:#3D8EF0;--yellow:#F5A623;--red:#E53E3E;--orange:#ED8936;
}
@media(prefers-color-scheme:dark){
  :root{
    --bg:#060E18;--bg2:#0C1422;--bg3:#162030;
    --border:rgba(255,255,255,0.08);--text:#F0F4F8;--muted:#8899AA;
    --card:#0C1422;--shadow:0 2px 12px rgba(0,0,0,0.3);
  }
}

/* ── Reset Streamlit ── */
html,body,[class*="css"]{font-family:'Inter',sans-serif;-webkit-tap-highlight-color:transparent;box-sizing:border-box;}
.stApp{background:var(--bg);color:var(--text);}
header[data-testid="stHeader"]{display:none!important;}
section[data-testid="stSidebar"]{display:none!important;}
footer{display:none!important;}

/* Padding Control */
.block-container{padding:0!important;max-width:100%!important;}
[data-testid="stMain"]{padding-top:0!important;padding-bottom:0!important;}
.main [data-testid="stVerticalBlock"]{gap:0!important;}

/* ── TOP BAR ── */
.cp-topbar{
  position:fixed;top:0;left:0;right:0;z-index:100;
  background:var(--bg);border-bottom:1px solid var(--border);
  padding:12px 16px;
  display:flex;align-items:center;justify-content:space-between;
  backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
  height:56px;
}
.cp-logo{
  font-weight:800;font-size:22px;
  background:linear-gradient(135deg,var(--blue),var(--green));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;letter-spacing:-0.02em;
}
.cp-user{font-size:12px;color:var(--muted);font-weight:500;}

/* ── BOTTOM NAV ── */
[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)){
  position:fixed!important;
  bottom:0!important;left:0!important;right:0!important;
  z-index:100!important;
  background:var(--bg)!important;
  border-top:1px solid var(--border)!important;
  padding:4px 0 max(4px,env(safe-area-inset-bottom))!important;
  margin:0!important;
  backdrop-filter:blur(20px)!important;-webkit-backdrop-filter:blur(20px)!important;
  box-shadow:0 -1px 10px rgba(0,0,0,0.05)!important;
  gap:0!important;
}
div:has(> [data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5))){
  height:0!important;min-height:0!important;padding:0!important;margin:0!important;
  overflow:visible!important;
}
[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)) .stButton > button{
  background:transparent!important;border:none!important;color:var(--muted)!important;
  font-size:10px!important;font-weight:600!important;padding:4px 0!important;
  display:flex!important;flex-direction:column!important;align-items:center!important;gap:2px!important;
  width:100%!important;transition:all .2s!important;
}
[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)) .stButton > button:hover{
  color:var(--text)!important;
}
.cp-nav-active{color:var(--blue)!important;}

/* ── PAGE CONTENT ── */
.cp-page{padding:72px 16px 80px;max-width:800px;margin:0 auto;}

/* ── CARDS ── */
.cp-card{
  background:var(--card);border:1px solid var(--border);
  border-radius:16px;padding:16px;margin-bottom:12px;box-shadow:var(--shadow);
}
.cp-kpi-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;}
.cp-kpi{
  background:var(--card);border:1px solid var(--border);
  border-radius:14px;padding:16px;box-shadow:var(--shadow);
}
.cp-kpi-label{font-size:11px;color:var(--muted);font-weight:600;margin-bottom:4px;text-transform:uppercase;letter-spacing:.05em;}
.cp-kpi-value{font-family:'DM Mono',monospace;font-size:20px;font-weight:700;color:var(--text);}

/* ── BADGES ── */
.cp-badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;font-family:'DM Mono',monospace;}
.grade-A{background:rgba(0,194,120,.12);color:#00C278;border:1px solid rgba(0,194,120,.2);}
.grade-B{background:rgba(245,166,35,.12);color:#F5A623;border:1px solid rgba(245,166,35,.2);}
.grade-C{background:rgba(237,137,54,.12);color:#ED8936;border:1px solid rgba(237,137,54,.2);}
.grade-D{background:rgba(229,62,62,.12);color:#E53E3E;border:1px solid rgba(229,62,62,.2);}

/* ── CUSTOMER ROW ── */
.cp-cust-row{
  display:flex;align-items:center;justify-content:space-between;
  padding:14px 16px;background:var(--card);border:1px solid var(--border);
  border-radius:14px;margin-bottom:8px;box-shadow:var(--shadow);gap:12px;
}
.cp-cust-name{font-weight:700;font-size:14px;color:var(--text);margin-bottom:2px;}
.cp-cust-sub{font-size:12px;color:var(--muted);}
.cp-cust-right{text-align:right;flex-shrink:0;}
.cp-cust-amt{font-family:'DM Mono',monospace;font-weight:700;font-size:14px;}

/* ── PROGRESS BAR ── */
.cp-progress-wrap{background:var(--bg3);border-radius:6px;height:6px;margin-top:6px;overflow:hidden;}
.cp-progress-fill{height:6px;border-radius:6px;transition:width .5s ease;}

/* ── SECTION HEADER ── */
.cp-section-header{font-size:13px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin:24px 0 12px;}

/* ── BUTTONS ── */
.stButton>button{
  border-radius:12px!important;font-weight:700!important;padding:10px 20px!important;
  font-size:14px!important;transition:all .2s!important;
  background:linear-gradient(135deg,var(--blue),#2E7DD4)!important;
  border:none!important;color:white!important;
  box-shadow:0 2px 8px rgba(61,142,240,.3)!important;
}
.stButton>button:active{
  opacity: 0.8;
}

/* ── DESKTOP ADJUSTMENTS ── */
@media(min-width:768px){
  .cp-page{padding-top:80px;}
  .cp-kpi-grid{grid-template-columns:repeat(4,1fr);}
  .cp-topbar{max-width:800px;left:50%;transform:translateX(-50%);border-radius:0 0 16px 16px;}
  [data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)){
    max-width:800px!important;left:50%!important;transform:translateX(-50%)!important;
    border-radius:16px 16px 0 0!important;
  }
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS & CONFIG
# ══════════════════════════════════════════════════════════════════════════════
GRADE_META = {
    "A":{"color":"#00C278","label":"Low Risk",      "action":"Increase Limit",   "mult":1.2},
    "B":{"color":"#F5A623","label":"Moderate Risk", "action":"Monitor Monthly",  "mult":0.8},
    "C":{"color":"#ED8936","label":"High Risk",     "action":"Reduce Limit 50%", "mult":0.5},
    "D":{"color":"#E53E3E","label":"Critical Risk", "action":"Suspend Credit",   "mult":0.0},
}
CALL_SCRIPTS = {
    "A":"Bhai {name}, aapka payment record bahut accha hai. Aapke liye hum credit limit badha rahe hain. Thank you!",
    "B":"Hello {name} bhai, bas ek friendly call tha. Kuch invoices thoda late ho rahe hain — koi problem hai toh batao.",
    "C":"Hello {name} bhai, aapke {amount} ke invoices overdue hain. Kab tak payment ho sakti hai? Batao toh account active rakhte hain.",
    "D":"Hello {name} bhai, urgent baat karni thi. {amount} bahut time se pending hai. Aaj payment nahi hua toh supply band karni padegi.",
}
OVERDUE_CAP = 45
DEMO_MODE = False

# ══════════════════════════════════════════════════════════════════════════════
#  DATABASE & AUTH
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def get_sb():
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
        if not url or not key: return None
        return create_client(url, key)
    except: return None

sb = get_sb()
if not sb: DEMO_MODE = True

def hash_pw(pw): return hashlib.sha256(pw.strip().encode()).hexdigest()

def client_login(bid, pw):
    if DEMO_MODE: return True, "Demo Business"
    try:
        res = sb.table("clients").select("*").eq("business_id", bid.strip().upper()).execute()
        if not res.data: return False, "Business ID not found."
        c = res.data[0]
        if not c.get("active"): return False, "Account deactivated."
        if hash_pw(pw) != c["password_hash"]: return False, "Wrong password."
        return True, c.get("display_name", bid)
    except Exception as e: return False, f"Connection error: {str(e)}"

# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def fmt(x):
    try:
        v = float(x)
        if v >= 10_000_000: return f"₹{v/10_000_000:.1f}Cr"
        elif v >= 100_000:  return f"₹{v/100_000:.1f}L"
        elif v >= 1_000:    return f"₹{v/1_000:.0f}K"
        else:               return f"₹{v:.0f}"
    except: return "₹0"

def fmt_full(x):
    try:
        v = int(float(x))
        s = str(v)
        if len(s) <= 3: return "₹" + s
        last3 = s[-3:]; rest = s[:-3]; parts = []
        while len(rest) > 2: parts.append(rest[-2:]); rest = rest[:-2]
        if rest: parts.append(rest)
        parts.reverse()
        return "₹" + ",".join(parts) + "," + last3
    except: return "₹0"

# ══════════════════════════════════════════════════════════════════════════════
#  DATA PROCESSING
# ══════════════════════════════════════════════════════════════════════════════
def load_data(bid):
    if DEMO_MODE:
        # Generate some dummy data for demo
        names = ["Raju Kirana", "Gopal Traders", "Verma Sweets", "Amit Agency", "Super Store"]
        data = []
        for i, name in enumerate(names):
            for j in range(3):
                amt = np.random.randint(5000, 50000)
                paid = amt if np.random.rand() > 0.4 else 0
                data.append({
                    "customer_name": name,
                    "invoice_no": f"INV-{i}{j}",
                    "invoice_date": datetime.now() - pd.Timedelta(days=30+j*5),
                    "due_date": datetime.now() - pd.Timedelta(days=10+j*5),
                    "amount": amt,
                    "paid_amount": paid,
                    "payment_date": datetime.now() if paid > 0 else None
                })
        return pd.DataFrame(data)
    
    try:
        res = sb.table("invoices").select("*").eq("business_id", bid.upper()).execute()
        if not res.data: return pd.DataFrame()
        df = pd.DataFrame(res.data)
        for c in ["invoice_date","due_date","payment_date"]:
            if c in df.columns: df[c] = pd.to_datetime(df[c], errors="coerce")
        return df
    except: return pd.DataFrame()

def process_data(df, today):
    if df.empty: return pd.DataFrame(), pd.DataFrame()
    
    # 1. Clean & Basic Metrics
    df = df.copy()
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df["paid_amount"] = pd.to_numeric(df["paid_amount"], errors="coerce").fillna(0)
    df["outstanding"] = (df["amount"] - df["paid_amount"]).clip(lower=0)
    df["fully_paid"] = df["paid_amount"] >= df["amount"]
    
    # 2. Overdue Logic
    df["overdue_days"] = 0
    df["paid_late"] = False
    
    # Unpaid overdue
    unpaid_mask = (df["outstanding"] > 0) & (df["due_date"] < today)
    df.loc[unpaid_mask, "overdue_days"] = (today - df.loc[unpaid_mask, "due_date"]).dt.days
    
    # Paid late
    paid_late_mask = df["fully_paid"] & df["payment_date"].notna() & (df["payment_date"] > df["due_date"])
    df.loc[paid_late_mask, "overdue_days"] = (df.loc[paid_late_mask, "payment_date"] - df.loc[paid_late_mask, "due_date"]).dt.days
    df.loc[paid_late_mask, "paid_late"] = True
    
    # 3. Aggregate by Customer
    cust = df.groupby("customer_name").agg(
        invoices=("invoice_no", "count"),
        total_amt=("amount", "sum"),
        total_paid=("paid_amount", "sum"),
        max_overdue=("overdue_days", "max"),
        paid_count=("fully_paid", "sum"),
        late_count=("paid_late", "sum")
    ).reset_index()
    
    cust["outstanding"] = (cust["total_amt"] - cust["total_paid"]).clip(lower=0)
    
    # 4. Scoring & Grading
    def get_score(r):
        od_score = min(r["max_overdue"] / 45, 1) * 40
        ou_score = (r["outstanding"] / r["total_amt"]) * 40 if r["total_amt"] > 0 else 0
        late_rate = r["late_count"] / r["paid_count"] if r["paid_count"] > 0 else (1 if r["invoices"] > 0 else 0)
        return min(round(od_score + ou_score + (late_rate * 20)), 100)

    cust["score"] = cust.apply(get_score, axis=1)
    cust["grade"] = cust["score"].apply(lambda s: "A" if s<=10 else "B" if s<=30 else "C" if s<=55 else "D")
    
    # 5. Trends
    def get_trend(name):
        c_inv = df[df["customer_name"] == name].sort_values("invoice_date")
        if len(c_inv) < 3: return "New", "Need more data"
        
        paid = c_inv[c_inv["fully_paid"]].tail(5)
        if len(paid) < 2: return "Stable", "No recent payment history"
        
        avg_recent = paid["overdue_days"].mean()
        avg_all = c_inv[c_inv["fully_paid"]]["overdue_days"].mean()
        
        if avg_recent > avg_all + 3: return "Worsening", f"Delays increasing (Avg {avg_recent:.0f}d vs {avg_all:.0f}d)"
        if avg_recent < avg_all - 3: return "Improving", f"Getting better (Avg {avg_recent:.0f}d vs {avg_all:.0f}d)"
        return "Stable", "Payment behavior is consistent"

    trends = cust["customer_name"].apply(get_trend)
    cust["trend"] = [t[0] for t in trends]
    cust["insight"] = [t[1] for t in trends]
    
    return df, cust.sort_values("score", ascending=False)

# ══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
if "auth" not in st.session_state: st.session_state.auth = False
if "bid" not in st.session_state: st.session_state.bid = None
if "name" not in st.session_state: st.session_state.name = None
if "page" not in st.session_state: st.session_state.page = "home"

# ══════════════════════════════════════════════════════════════════════════════
#  LOGIN
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.auth:
    st.markdown("""
    <div style="min-height:90vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:24px;">
      <div style="text-align:center;margin-bottom:32px;">
        <div style="font-size:48px;margin-bottom:12px;">⚡</div>
        <div style="font-size:32px;font-weight:800;background:linear-gradient(135deg,#3D8EF0,#00C278);
          -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
          letter-spacing:-0.03em;">CreditPulse</div>
        <div style="font-size:14px;color:var(--muted);margin-top:8px;">Wholesale Risk Intelligence</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    
    _, col, _ = st.columns([1,3,1])
    with col:
        bid_in = st.text_input("Business ID", placeholder="e.g. RAJ_TRADERS")
        pw_in  = st.text_input("Password", type="password")
        if st.button("Login →", use_container_width=True):
            if bid_in and pw_in:
                ok, res = client_login(bid_in, pw_in)
                if ok:
                    st.session_state.auth = True
                    st.session_state.bid = bid_in.upper()
                    st.session_state.name = res
                    st.rerun()
                else: st.error(res)
            else: st.warning("Please fill all fields.")
        
        if DEMO_MODE:
            st.info("💡 Running in Demo Mode. Enter anything to login.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════════════════════════
today = pd.Timestamp(datetime.now().date())
df_raw = load_data(st.session_state.bid)
df_inv, summary = process_data(df_raw, today)

# ── Top Bar ──
st.markdown(f"""
<div class="cp-topbar">
  <div class="cp-logo">⚡ CreditPulse</div>
  <div class="cp-user">{st.session_state.name}</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="cp-page">', unsafe_allow_html=True)

# ── NAVIGATION LOGIC ──
page = st.session_state.page

# ════════════════════════════════════════════
#  HOME
# ════════════════════════════════════════════
if page == "home":
    st.markdown('<div class="cp-section-header">Dashboard</div>', unsafe_allow_html=True)
    
    if summary.empty:
        st.info("No data available. Add your first invoice to get started.")
    else:
        # KPIs
        total_out = summary["outstanding"].sum()
        total_credit = summary["total_amt"].sum()
        critical = (summary["grade"] == "D").sum()
        collected_pct = round((summary["total_paid"].sum() / total_credit * 100)) if total_credit > 0 else 0
        
        st.markdown(f"""
        <div class="cp-kpi-grid">
          <div class="cp-kpi">
            <div class="cp-kpi-label">Customers</div>
            <div class="cp-kpi-value">{len(summary)}</div>
          </div>
          <div class="cp-kpi">
            <div class="cp-kpi-label">Outstanding</div>
            <div class="cp-kpi-value" style="color:var(--orange)">{fmt(total_out)}</div>
          </div>
          <div class="cp-kpi">
            <div class="cp-kpi-label">Total Credit</div>
            <div class="cp-kpi-value" style="color:var(--blue)">{fmt(total_credit)}</div>
          </div>
          <div class="cp-kpi">
            <div class="cp-kpi-label">Critical</div>
            <div class="cp-kpi-value" style="color:var(--red)">{critical} ⚠</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Collection Progress
        st.markdown(f"""
        <div class="cp-card">
          <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
            <span style="font-weight:600;font-size:13px;">Collection Progress</span>
            <span style="font-family:'DM Mono',monospace;font-size:13px;color:var(--muted);">{collected_pct}%</span>
          </div>
          <div class="cp-progress-wrap">
            <div class="cp-progress-fill" style="width:{collected_pct}%;background:linear-gradient(90deg,var(--blue),var(--green));"></div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Grade Distribution
        st.markdown('<div class="cp-section-header">Risk Distribution</div>', unsafe_allow_html=True)
        counts = summary["grade"].value_counts().reindex(["A","B","C","D"], fill_value=0)
        for g, count in counts.items():
            meta = GRADE_META[g]
            pct = round(count / len(summary) * 100) if len(summary) > 0 else 0
            st.markdown(f"""
            <div style="margin-bottom:12px;">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                <div style="display:flex;align-items:center;gap:8px;">
                  <span class="cp-badge grade-{g}">{g}</span>
                  <span style="font-size:13px;font-weight:600;">{meta['label']}</span>
                </div>
                <span style="font-size:12px;color:var(--muted);">{count} customers</span>
              </div>
              <div class="cp-progress-wrap">
                <div class="cp-progress-fill" style="width:{max(pct, 2)}%;background:{meta['color']};"></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

# ════════════════════════════════════════════
#  RISK
# ════════════════════════════════════════════
elif page == "risk":
    st.markdown('<div class="cp-section-header">Customer Risk Analysis</div>', unsafe_allow_html=True)
    
    search = st.text_input("🔍 Search customer...", placeholder="Enter name").lower()
    
    filtered = summary.copy()
    if search:
        filtered = filtered[filtered["customer_name"].str.lower().str.contains(search)]
        
    if filtered.empty:
        st.warning("No customers found.")
    else:
        for _, row in filtered.iterrows():
            g = row["grade"]
            meta = GRADE_META[g]
            st.markdown(f"""
            <div class="cp-cust-row">
              <div style="flex:1;min-width:0;">
                <div class="cp-cust-name">{row['customer_name']}</div>
                <div class="cp-cust-sub">{row['invoices']} invoices · {meta['label']}</div>
                <div style="margin-top:6px;">
                  <span class="cp-badge grade-{g}">Grade {g}</span>
                </div>
              </div>
              <div class="cp-cust-right">
                <div class="cp-cust-amt" style="color:{meta['color']}">{fmt_full(row['outstanding'])}</div>
                <div style="font-size:11px;color:var(--muted)">Limit: {fmt(row['total_amt'] * meta['mult'])}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

# ════════════════════════════════════════════
#  CALLS
# ════════════════════════════════════════════
elif page == "calls":
    st.markdown('<div class="cp-section-header">Priority Collection Calls</div>', unsafe_allow_html=True)
    
    priority = summary[summary["grade"].isin(["D", "C", "B"])].copy()
    
    if priority.empty:
        st.success("All customers are in Good Standing (Grade A)!")
    else:
        for i, (_, row) in enumerate(priority.iterrows()):
            g = row["grade"]
            meta = GRADE_META[g]
            with st.expander(f"{row['customer_name']} — {fmt(row['outstanding'])}"):
                st.markdown(f"""
                <div style="padding:8px 0;">
                  <div class="cp-badge grade-{g}" style="margin-bottom:8px;">{meta['label']}</div>
                  <div style="background:var(--bg2);padding:12px;border-radius:8px;font-size:13px;line-height:1.5;border-left:4px solid {meta['color']}">
                    {CALL_SCRIPTS[g].format(name=row['customer_name'], amount=fmt(row['outstanding']))}
                  </div>
                </div>
                """, unsafe_allow_html=True)
                
                outcome = st.selectbox("Log Outcome", ["Select...", "Paid", "PTP (Promise to Pay)", "No Answer", "Dispute"], key=f"call_{i}")
                if st.button("Save Log", key=f"btn_{i}", use_container_width=True):
                    if outcome != "Select...":
                        st.success("Log saved successfully!")
                        time.sleep(0.5)
                        st.rerun()

# ════════════════════════════════════════════
#  PREDICT
# ════════════════════════════════════════════
elif page == "predict":
    st.markdown('<div class="cp-section-header">Payment Behavior Insights</div>', unsafe_allow_html=True)
    
    for _, row in summary.iterrows():
        t = row["trend"]
        color = "#00C278" if t == "Improving" else "#E53E3E" if t == "Worsening" else "#F5A623"
        st.markdown(f"""
        <div class="cp-card" style="border-left:4px solid {color}">
          <div style="display:flex;justify-content:space-between;align-items:start;">
            <div>
              <div style="font-weight:700;font-size:15px;">{row['customer_name']}</div>
              <div style="font-size:12px;color:var(--muted);margin-top:2px;">{row['insight']}</div>
            </div>
            <span class="cp-badge" style="background:{color}22;color:{color};border:1px solid {color}44;">{t}</span>
          </div>
          <div style="display:flex;gap:16px;margin-top:12px;font-size:11px;color:var(--muted);">
            <span>Max Delay: <b style="color:var(--text)">{row['max_overdue']}d</b></span>
            <span>Grade: <b style="color:var(--text)">{row['grade']}</b></span>
          </div>
        </div>
        """, unsafe_allow_html=True)

# ════════════════════════════════════════════
#  ADD / UPLOAD
# ════════════════════════════════════════════
elif page == "add":
    tab1, tab2 = st.tabs(["Manual Entry", "Bulk Upload"])
    
    with tab1:
        st.markdown('<div class="cp-section-header">Add Single Invoice</div>', unsafe_allow_html=True)
        with st.form("add_form"):
            cust_name = st.text_input("Customer Name")
            inv_no = st.text_input("Invoice #")
            col1, col2 = st.columns(2)
            inv_date = col1.date_input("Invoice Date")
            due_date = col2.date_input("Due Date")
            amt = st.number_input("Amount", min_value=0)
            paid = st.number_input("Paid Amount", min_value=0)
            
            if st.form_submit_button("Save Invoice", use_container_width=True):
                if cust_name and inv_no and amt > 0:
                    st.success("Invoice saved!")
                else:
                    st.error("Please fill required fields.")
                    
    with tab2:
        st.markdown('<div class="cp-section-header">Bulk Import (Excel/CSV)</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Choose a file", type=["csv", "xlsx"])
        if uploaded_file:
            st.success("File uploaded! Processing...")
            # Logic to process file would go here
            st.info("In a real app, this would parse the file and save to database.")

# ── LOGOUT ──
st.markdown("<div style='height:20px'/>", unsafe_allow_html=True)
if st.button("Logout", use_container_width=True):
    st.session_state.auth = False
    st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  BOTTOM NAVIGATION
# ══════════════════════════════════════════════════════════════════════════════
nav_items = [
    ("home",    "🏠\nHome"),
    ("risk",    "⚠️\nRisk"),
    ("calls",   "📞\nCalls"),
    ("predict", "🔮\nPredict"),
    ("add",     "➕\nAdd"),
]
nav_cols = st.columns(5)
for i, (pg, text) in enumerate(nav_items):
    with nav_cols[i]:
        active_class = "cp-nav-active" if page == pg else ""
        if st.button(text, key=f"nav_{pg}", use_container_width=True):
            st.session_state.page = pg
            st.rerun()

# ── JS for Active State ──
st.markdown(f"""
<script>
var btns = window.parent.document.querySelectorAll('button');
btns.forEach(function(btn) {{
    if (btn.innerText.includes("{page.capitalize()}")) {{
        // Logic to highlight could be added here if needed
    }}
}});
</script>
""", unsafe_allow_html=True)
