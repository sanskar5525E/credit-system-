import streamlit as st
import pandas as import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import io, hashlib
from supabase import create_client

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="CreditPulse",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="collapsed"
)

# ══════════════════════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Inter:wght@400;500;600;700;800&display=swap');

/* ── Theme Variables ── */
:root {
  --bg:#FFFFFF;--bg2:#F7F8FA;--bg3:#EDEEF2;
  --border:rgba(0,0,0,0.08);--text:#0D1117;--muted:#6B7280;
  --card:#FFFFFF;--shadow:0 2px 12px rgba(0,0,0,0.08);
  --green:#00C278;--blue:#3D8EF0;--yellow:#F5A623;--red:#E53E3E;--orange:#ED8936;
}
@media(prefers-color-scheme:dark){
  :root{
    --bg:#060E18;--bg2:#0C1422;--bg3:#162030;
    --border:rgba(255,255,255,0.08);--text:#F0F4F8;--muted:#8899AA;
    --card:#0C1422;--shadow:0 2px 12px rgba(0,0,0,0.4);
  }
}

/* ── Reset Streamlit ── */
html,body,[class*="css"]{font-family:'Inter',sans-serif;-webkit-tap-highlight-color:transparent;box-sizing:border-box;}
.stApp{background:var(--bg);color:var(--text);}
header[data-testid="stHeader"]{display:none!important;}
section[data-testid="stSidebar"]{display:none!important;}
footer{display:none!important;}

/* Kill ALL Streamlit padding so we control everything */
.block-container{padding:0!important;max-width:100%!important;}
[data-testid="stMain"]{padding-top:0!important;padding-bottom:0!important;}
.main [data-testid="stVerticalBlock"]{gap:0!important;}

/* ════════════════════════════════════════════════════════════════════════════
   TOP BAR
   ════════════════════════════════════════════════════════════════════════════ */
.cp-topbar{
  position:fixed;top:0;left:0;right:0;z-index:100;
  background:var(--bg);border-bottom:1px solid var(--border);
  padding:12px 16px;
  display:flex;align-items:center;justify-content:space-between;
  backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
  height:48px;
}
.cp-logo{
  font-weight:800;font-size:20px;
  background:linear-gradient(135deg,var(--blue),var(--green));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;
}
.cp-user{font-size:12px;color:var(--muted);font-weight:500;}

/* ════════════════════════════════════════════════════════════════════════════
   BOTTOM NAV — CSS :has() targets the 5-column st.columns layout
   Streamlit buttons inside it work normally (session state preserved).
   ════════════════════════════════════════════════════════════════════════════ */

/* --- Make the 5-column horizontal block FIXED at the bottom --- */
[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)){
  position:fixed!important;
  bottom:0!important;left:0!important;right:0!important;
  z-index:100!important;
  background:var(--bg)!important;
  border-top:1px solid var(--border)!important;
  padding:2px 0 max(2px,env(safe-area-inset-bottom))!important;
  margin:0!important;
  backdrop-filter:blur(20px)!important;-webkit-backdrop-filter:blur(20px)!important;
  box-shadow:0 -1px 10px rgba(0,0,0,0.05)!important;
  gap:0!important;
}

/* --- Collapse the wrapper that Streamlit places around the 5-col block --- */
div:has(> [data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5))){
  height:0!important;min-height:0!important;padding:0!important;margin:0!important;
  overflow:visible!important;
}

/* --- Style nav buttons: transparent, icon + label column layout --- */
[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)) .stButton > button,
[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)) button{
  background:transparent!important;
  border:none!important;
  color:var(--muted)!important;
  font-size:10px!important;font-weight:600!important;
  padding:6px 2px 4px!important;
  border-radius:0!important;
  box-shadow:none!important;
  display:flex!important;flex-direction:column!important;
  align-items:center!important;gap:1px!important;
  white-space:pre-line!important;line-height:1.35!important;
  cursor:pointer!important;width:100%!important;
  transition:color .15s!important;
}
[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)) .stButton > button:hover{
  color:var(--text)!important;background:transparent!important;
}
/* Active nav item (applied via JS) */
.cp-nav-active{
  color:var(--blue)!important;
  background:transparent!important;
}

/* ════════════════════════════════════════════════════════════════════════════
   PAGE CONTENT
   ════════════════════════════════════════════════════════════════════════════ */
.cp-page{padding:60px 16px 70px;}

/* ════════════════════════════════════════════════════════════════════════════
   CARDS
   ════════════════════════════════════════════════════════════════════════════ */
.cp-card{
  background:var(--card);border:1px solid var(--border);
  border-radius:16px;padding:16px;margin-bottom:12px;box-shadow:var(--shadow);
}
.cp-card-sm{
  background:var(--bg2);border:1px solid var(--border);
  border-radius:12px;padding:12px 14px;margin-bottom:8px;
}

/* ════════════════════════════════════════════════════════════════════════════
   KPI GRID
   ════════════════════════════════════════════════════════════════════════════ */
.cp-kpi-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px;}
.cp-kpi{
  background:var(--card);border:1px solid var(--border);
  border-radius:14px;padding:14px;box-shadow:var(--shadow);min-width:0;
}
.cp-kpi-label{font-size:11px;color:var(--muted);font-weight:500;margin-bottom:4px;text-transform:uppercase;letter-spacing:.05em;}
.cp-kpi-value{font-family:'DM Mono',monospace;font-size:clamp(16px,4vw,22px);font-weight:700;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}

/* ════════════════════════════════════════════════════════════════════════════
   GRADE BADGES
   ════════════════════════════════════════════════════════════════════════════ */
.grade-A{background:rgba(0,194,120,.12);color:#00C278;border:1px solid rgba(0,194,120,.25);}
.grade-B{background:rgba(245,166,35,.12);color:#F5A623;border:1px solid rgba(245,166,35,.25);}
.grade-C{background:rgba(237,137,54,.12);color:#ED8936;border:1px solid rgba(237,137,54,.25);}
.grade-D{background:rgba(229,62,62,.12);color:#E53E3E;border:1px solid rgba(229,62,62,.25);}
.cp-badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;font-family:'DM Mono',monospace;}

/* ════════════════════════════════════════════════════════════════════════════
   CUSTOMER ROW
   ════════════════════════════════════════════════════════════════════════════ */
.cp-cust-row{
  display:flex;align-items:center;justify-content:space-between;
  padding:14px 16px;background:var(--card);border:1px solid var(--border);
  border-radius:14px;margin-bottom:8px;box-shadow:var(--shadow);gap:12px;
}
.cp-cust-name{font-weight:700;font-size:14px;color:var(--text);margin-bottom:2px;word-break:break-word;}
.cp-cust-sub{font-size:12px;color:var(--muted);}
.cp-cust-right{text-align:right;flex-shrink:0;}
.cp-cust-amt{font-family:'DM Mono',monospace;font-weight:700;font-size:14px;}

/* ════════════════════════════════════════════════════════════════════════════
   CALL CARD
   ════════════════════════════════════════════════════════════════════════════ */
.cp-call-script{
  background:var(--bg2);border-radius:10px;padding:12px;
  font-size:13px;color:var(--text);line-height:1.7;margin:10px 0;word-break:break-word;
}

/* ════════════════════════════════════════════════════════════════════════════
   PROGRESS BAR
   ════════════════════════════════════════════════════════════════════════════ */
.cp-progress-wrap{background:var(--bg3);border-radius:6px;height:6px;margin-top:6px;}
.cp-progress-fill{height:6px;border-radius:6px;transition:width .5s ease;}

/* ════════════════════════════════════════════════════════════════════════════
   SECTION HEADER
   ════════════════════════════════════════════════════════════════════════════ */
.cp-section-header{font-size:13px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin:20px 0 10px;}

/* ════════════════════════════════════════════════════════════════════════════
   ACTION BUTTONS — blue gradient (excludes nav via CSS specificity)
   ════════════════════════════════════════════════════════════════════════════ */
.stButton>button{
  background:linear-gradient(135deg,var(--blue),#2E7DD4)!important;
  border:none!important;color:white!important;
  border-radius:12px!important;font-weight:700!important;
  padding:12px 20px!important;width:100%!important;
  font-size:14px!important;letter-spacing:-.01em!important;
  cursor:pointer!important;transition:opacity .15s!important;
  box-shadow:0 2px 8px rgba(61,142,240,.3)!important;
}
.stButton>button:hover{opacity:.9!important;}
.stButton>button:active{opacity:.8!important;}

/* Download buttons */
.stDownloadButton>button{
  background:var(--bg2)!important;border:1px solid var(--border)!important;
  color:var(--text)!important;border-radius:12px!important;font-weight:600!important;
  padding:10px 16px!important;width:100%!important;font-size:13px!important;cursor:pointer!important;
  box-shadow:none!important;
}

/* ════════════════════════════════════════════════════════════════════════════
   INPUTS
   ════════════════════════════════════════════════════════════════════════════ */
.stTextInput>div>div>input,
.stSelectbox>div>div{
  background:var(--bg2)!important;border:1px solid var(--border)!important;
  border-radius:10px!important;color:var(--text)!important;font-size:14px!important;
}
.stNumberInput>div>div>input,
.stDateInput>div>div>input{
  background:var(--bg2)!important;border:1px solid var(--border)!important;
  border-radius:10px!important;color:var(--text)!important;
}
.stRadio>label{color:var(--text)!important;}

/* ════════════════════════════════════════════════════════════════════════════
   ALERTS
   ════════════════════════════════════════════════════════════════════════════ */
.stSuccess{background:rgba(0,194,120,.08)!important;border:1px solid rgba(0,194,120,.25)!important;border-radius:12px!important;}
.stError{background:rgba(229,62,62,.08)!important;border:1px solid rgba(229,62,62,.25)!important;border-radius:12px!important;}
.stInfo{background:rgba(61,142,240,.08)!important;border:1px solid rgba(61,142,240,.25)!important;border-radius:12px!important;}
.stWarning{background:rgba(245,166,35,.08)!important;border:1px solid rgba(245,166,35,.25)!important;border-radius:12px!important;}

/* ════════════════════════════════════════════════════════════════════════════
   DATAFRAME & EXPANDER
   ════════════════════════════════════════════════════════════════════════════ */
[data-testid="stDataFrame"]{border-radius:12px!important;overflow:hidden!important;}
.streamlit-expanderHeader{
  background:var(--bg2)!important;border-radius:12px!important;
  font-weight:600!important;font-size:13px!important;
}

/* ════════════════════════════════════════════════════════════════════════════
   DEV PANEL TABS
   ════════════════════════════════════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"]{
  gap:4px;background:var(--bg2);border-radius:12px;padding:4px;margin-bottom:16px;
}
.stTabs [data-baseweb="tab"]{
  border-radius:10px!important;background:transparent!important;
  color:var(--muted)!important;font-weight:600!important;font-size:13px!important;padding:8px 16px!important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"]{
  background:var(--card)!important;color:var(--text)!important;
  box-shadow:0 1px 4px rgba(0,0,0,.08)!important;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"]{display:none!important;}

/* ════════════════════════════════════════════════════════════════════════════
   DESKTOP (≥768px)
   ════════════════════════════════════════════════════════════════════════════ */
@media(min-width:768px){
  .block-container{max-width:900px!important;margin:0 auto!important;padding:0!important;}
  .cp-page{padding:68px 0 70px;}
  .cp-topbar{
    max-width:900px;left:50%;right:auto;transform:translateX(-50%);
    border-radius:0 0 16px 16px;padding:12px 24px;
  }
  .cp-kpi-grid{grid-template-columns:repeat(4,1fr);}
  /* Nav bar: center + rounded top corners */
  [data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)){
    max-width:900px!important;left:50%!important;right:auto!important;
    transform:translateX(-50%)!important;
    border-radius:16px 16px 0 0!important;
  }
}

</style>

<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#060E18" media="(prefers-color-scheme:dark)">
<meta name="theme-color" content="#FFFFFF" media="(prefers-color-scheme:light)">
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
GRADE_META = {
    "A":{"color":"#00C278","rgba":"0,194,120",  "label":"Low Risk",      "action":"Increase Limit",   "call":"Thank & Reward",         "limit_mult":1.2},
    "B":{"color":"#F5A623","rgba":"245,166,35",  "label":"Moderate Risk", "action":"Monitor Monthly",  "call":"Check-In Call",          "limit_mult":0.8},
    "C":{"color":"#ED8936","rgba":"237,137,54",  "label":"High Risk",     "action":"Reduce Limit 50%", "call":"Follow-Up Call",         "limit_mult":0.5},
    "D":{"color":"#E53E3E","rgba":"229,62,62",   "label":"Critical Risk", "action":"Suspend Credit",   "call":"Urgent Collection",      "limit_mult":0.0},
}
CALL_SCRIPTS = {
    "A":"Bhai {name}, aapka payment record bahut accha hai. Aapke liye hum credit limit badha rahe hain. Thank you!",
    "B":"Hello {name} bhai, bas ek friendly call tha. Kuch invoices thoda late ho rahe hain — koi problem hai toh batao.",
    "C":"Hello {name} bhai, aapke {amount} ke invoices overdue hain. Kab tak payment ho sakti hai? Batao toh account active rakhte hain.",
    "D":"Hello {name} bhai, urgent baat karni thi. {amount} bahut time se pending hai. Aaj payment nahi hua toh supply band karni padegi.",
}
OVERDUE_CAP  = 45
DEV_PASSWORD = st.secrets.get("DEV_PASSWORD", "creditpulse_dev_2026")

# ══════════════════════════════════════════════════════════════════════════════
#  SUPABASE
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def get_sb():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
sb = get_sb()

# ══════════════════════════════════════════════════════════════════════════════
#  FORMAT HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def fmt(x):
    try:
        v = float(x)
        if v >= 10_000_000: return "₹{:.1f}Cr".format(v/10_000_000)
        elif v >= 100_000:  return "₹{:.1f}L".format(v/100_000)
        elif v >= 1_000:    return "₹{:.0f}K".format(v/1_000)
        else:               return "₹{:.0f}".format(v)
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

def hash_pw(pw): return hashlib.sha256(pw.strip().encode()).hexdigest()

# ══════════════════════════════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════════════════════════════
def client_login(bid, pw):
    try:
        res = sb.table("clients").select("*").eq("business_id", bid.strip().upper()).execute()
        if not res.data: return False, "Business ID not found. Contact your provider."
        c = res.data[0]
        if not c.get("active"): return False, "Account deactivated. Contact your provider."
        if hash_pw(pw) != c["password_hash"]: return False, "Wrong password."
        return True, c.get("display_name", bid)
    except: return False, "Connection error. Try again."

def load_history(bid):
    try:
        res = sb.table("invoices").select("*").eq("business_id", bid.upper()).execute()
        if not res.data: return pd.DataFrame()
        df = pd.DataFrame(res.data)
        for c in ["invoice_date","due_date","payment_date"]:
            if c in df.columns: df[c] = pd.to_datetime(df[c], errors="coerce")
        return df
    except: return pd.DataFrame()

def save_invoice(bid, row_dict):
    try:
        sb.table("invoices").upsert(row_dict, on_conflict="business_id,invoice_no").execute()
        return True
    except: return False

def save_call_log(bid, cust, grade, outcome):
    try:
        sb.table("call_logs").insert({"business_id":bid,"customer_name":cust,"risk_grade":grade,"outcome":outcome}).execute()
        return True
    except: return False

def load_all_clients():
    try:
        res = sb.table("clients").select("*").order("added", desc=True).execute()
        return res.data or []
    except: return []

def add_client(bid, name, pw):
    try:
        sb.table("clients").insert({
            "business_id": bid.strip().upper(),
            "display_name": name.strip() or bid.strip().upper(),
            "password_hash": hash_pw(pw),
            "active": True,
            "added": datetime.now().strftime("%Y-%m-%d"),
        }).execute()
        return True, "OK"
    except Exception as e:
        err = str(e)
        if "duplicate" in err.lower() or "unique" in err.lower():
            return False, "Business ID already exists."
        return False, "Error: " + err

def toggle_client(bid, active):
    sb.table("clients").update({"active": not active}).eq("business_id", bid).execute()

def reset_pw(bid, new_pw):
    sb.table("clients").update({"password_hash": hash_pw(new_pw)}).eq("business_id", bid).execute()

# ══════════════════════════════════════════════════════════════════════════════
#  DATA PROCESSING
# ══════════════════════════════════════════════════════════════════════════════
def clean_data(df):
    df = df.copy()
    drop = ["outstanding","fully_paid","overdue_days","paid_late","uploaded_at","id","business_id"]
    df.drop(columns=[c for c in drop if c in df.columns], inplace=True)
    df.columns = df.columns.str.lower().str.strip().str.replace(" ","_")
    for c in ["invoice_date","due_date","payment_date"]:
        if c in df.columns: df[c] = pd.to_datetime(df[c], errors="coerce")
    df["amount"]      = pd.to_numeric(df["amount"],      errors="coerce").fillna(0)
    df["paid_amount"] = pd.to_numeric(df["paid_amount"], errors="coerce").fillna(0)
    if "payment_date" not in df.columns: df["payment_date"] = pd.NaT
    return df[df["amount"]>0].copy()

def calc_metrics(df, today):
    df = df.copy()
    df["outstanding"]  = (df["amount"]-df["paid_amount"]).clip(lower=0)
    df["fully_paid"]   = df["paid_amount"] >= df["amount"]
    df["overdue_days"] = 0; df["paid_late"] = False
    mu = (df["outstanding"]>0)&(df["due_date"]<today)
    df.loc[mu,"overdue_days"] = (today-df.loc[mu,"due_date"]).dt.days.astype(int)
    ml = df["fully_paid"]&df["payment_date"].notna()&(df["payment_date"]>df["due_date"])
    df.loc[ml,"overdue_days"] = (df.loc[ml,"payment_date"]-df.loc[ml,"due_date"]).dt.days.astype(int)
    df.loc[ml,"paid_late"] = True
    df["overdue_days"] = df["overdue_days"].clip(lower=0,upper=60)
    return df

def predict_behaviour(inv_df):
    paid = inv_df[inv_df["fully_paid"]==True].copy().sort_values("invoice_date")
    total = len(inv_df); pc = len(paid)
    if pc < 3:
        pct = round(((total-pc)/total)*100) if total>0 else 0
        return "New", 0, "Only {} paid invoice(s). {}% unpaid.".format(pc, pct)
    mid = len(paid)//2
    delta = paid.iloc[mid:]["overdue_days"].mean() - paid.iloc[:mid]["overdue_days"].mean()
    last3 = paid.tail(3)["overdue_days"].mean()
    overall = paid["overdue_days"].mean()
    pay_rate = pc/total if total>0 else 0
    if (delta>5 and last3>overall) or last3>overall*1.3:
        msg = "Delays increasing. Last 3 avg {:.0f}d vs {:.0f}d overall.".format(last3,overall)
        if pay_rate<0.6: msg += " Only {:.0f}% fully paid.".format(pay_rate*100)
        return "Worsening", round(last3,1), msg
    elif (delta<-5 and last3<overall) or last3<overall*0.7:
        return "Improving", round(last3,1), "Getting better. Last 3 avg {:.0f}d vs {:.0f}d overall.".format(last3,overall)
    else:
        return "Stable", round(last3,1), "Consistent. Avg delay {:.0f}d. Pay rate {:.0f}%.".format(overall,pay_rate*100)

def score_customer(row):
    od = min(row["max_overdue"]/OVERDUE_CAP,1)*40
    ou = (row["total_outstanding"]/row["total_amount"])*40 if row["total_amount"]>0 else 0
    pr = row["total_paid"]/row["total_amount"] if row["total_amount"]>0 else 0
    lr = row["late_count"]/row["paid_count"] if row["paid_count"]>0 else 1
    return min(round(od+ou+min((1-pr)*10+lr*10,20)),100)

def get_grade(s): return "A" if s<=10 else "B" if s<=30 else "C" if s<=55 else "D"

def aggregate(df):
    g = df.groupby("customer_name").agg(
        total_invoices=("invoice_no","count"), total_amount=("amount","sum"),
        total_paid=("paid_amount","sum"),      max_overdue=("overdue_days","max"),
        late_count=("paid_late","sum"),        paid_count=("fully_paid","sum"),
    ).reset_index()
    g["total_outstanding"] = (g["total_amount"]-g["total_paid"]).clip(lower=0)
    g["avg_delay"] = g["customer_name"].map(
        df[df["paid_late"]].groupby("customer_name")["overdue_days"].mean()).fillna(0).round(1)
    rows = []
    for _,r in g.iterrows():
        sc=score_customer(r); gr=get_grade(sc); m=GRADE_META[gr]
        trend,last3,pred = predict_behaviour(df[df["customer_name"]==r["customer_name"]])
        rows.append({
            "Customer":r["customer_name"],"Invoices":int(r["total_invoices"]),
            "Total Credit":round(float(r["total_amount"]),2),
            "Total Paid":round(float(r["total_paid"]),2),
            "Outstanding":round(float(r["total_outstanding"]),2),
            "Max Overdue(d)":int(r["max_overdue"]),"Avg Delay(d)":float(r["avg_delay"]),
            "Risk Score":sc,"Risk Grade":gr,"Grade Label":m["label"],
            "Suggested Limit":round(float(r["total_amount"])*m["limit_mult"],2),
            "Credit Action":m["action"],"Call Type":m["call"],
            "Call Script":CALL_SCRIPTS[gr].format(name=r["customer_name"],amount=fmt(r["total_outstanding"])),
            "Behaviour Trend":trend,"Recent Avg Delay":last3,"Behaviour Insight":pred,
        })
    return pd.DataFrame(rows).sort_values("Risk Score",ascending=False).reset_index(drop=True)

def process_all(raw_df, today):
    c = clean_data(raw_df); i = calc_metrics(c,today)
    return i, aggregate(i)

# ══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
defaults = {
    "auth":False,"is_dev":False,"bid":None,"display_name":None,
    "df_inv":None,"summary":None,"page":"home","form_success":None,
}
for k,v in defaults.items():
    if k not in st.session_state: st.session_state[k]=v

# ══════════════════════════════════════════════════════════════════════════════
#  LOGIN PAGE
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state["auth"]:
    st.markdown("""
    <div style="min-height:100vh;display:flex;flex-direction:column;align-items:center;
      justify-content:center;padding:24px;background:var(--bg);">
      <div style="width:100%;max-width:380px;">
        <div style="text-align:center;margin-bottom:32px;">
          <div style="font-size:40px;margin-bottom:8px;">⚡</div>
          <div style="font-size:28px;font-weight:800;background:linear-gradient(135deg,#3D8EF0,#00C278);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
            letter-spacing:-0.03em;">CreditPulse</div>
          <div style="font-size:13px;color:var(--muted);margin-top:4px;">Wholesale Risk Intelligence</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1,3,1])
    with col:
        login_type = st.radio("Login as", ["Client","Developer"], horizontal=True, label_visibility="collapsed")
        st.markdown("<div style='height:8px'/>", unsafe_allow_html=True)

        if login_type == "Client":
            bid_in = st.text_input("Business ID", placeholder="e.g. RAJ_TRADERS")
            pw_in  = st.text_input("Password", type="password", placeholder="Your password")
            if st.button("Login →", use_container_width=True):
                if bid_in.strip() and pw_in.strip():
                    ok, result = client_login(bid_in, pw_in)
                    if ok:
                        st.session_state.update({"auth":True,"is_dev":False,
                            "bid":bid_in.strip().upper(),"display_name":result})
                        st.rerun()
                    else: st.error(result)
                else: st.warning("Enter both fields.")
        else:
            dev_pw = st.text_input("Developer Password", type="password")
            if st.button("Enter Dev Panel →", use_container_width=True):
                if hash_pw(dev_pw) == hash_pw(DEV_PASSWORD):
                    st.session_state.update({"auth":True,"is_dev":True,"bid":"__DEV__"})
                    st.rerun()
                else: st.error("Wrong password.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
#  DEVELOPER PANEL
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state["is_dev"]:
    st.markdown('<div class="cp-page">', unsafe_allow_html=True)
    st.markdown("### ⚙️ Developer Panel")
    if st.button("Logout"):
        for k,v in defaults.items(): st.session_state[k]=v
        st.rerun()

    dev_t1, dev_t2, dev_t3 = st.tabs(["👥 Clients","➕ Add","📊 Overview"])

    with dev_t1:
        clients = load_all_clients()
        if not clients:
            st.info("No clients yet.")
        else:
            for c in clients:
                bid = c["business_id"]; active = c.get("active",False)
                with st.expander("{} — {} — {}".format(bid, c.get("display_name",""), "✅ Active" if active else "❌ Off")):
                    c1,c2 = st.columns(2)
                    with c1:
                        if st.button("Toggle Active", key="tog_"+bid):
                            toggle_client(bid, active); st.rerun()
                    with c2:
                        new_p = st.text_input("New Password", type="password", key="np_"+bid)
                        if st.button("Reset PW", key="rp_"+bid):
                            if new_p.strip(): reset_pw(bid, new_p); st.success("Done")
                            else: st.error("Enter password")

    with dev_t2:
        n_bid  = st.text_input("Business ID", placeholder="RAJ_TRADERS")
        n_name = st.text_input("Display Name", placeholder="Rajan Traders, Nagpur")
        n_pw   = st.text_input("Password", type="password")
        if st.button("Add Client", use_container_width=True):
            if n_bid.strip() and n_pw.strip():
                ok, msg = add_client(n_bid, n_name, n_pw)
                if ok: st.success("Added: {}".format(n_bid.strip().upper())); st.rerun()
                else: st.error(msg)
            else: st.error("ID and password required.")

    with dev_t3:
        try:
            res = sb.table("invoices").select("business_id").execute()
            if res.data:
                df_c = pd.DataFrame(res.data)["business_id"].value_counts().reset_index()
                df_c.columns = ["Business ID","Rows"]
                st.dataframe(df_c, use_container_width=True, hide_index=True)
                st.metric("Total rows", "{:,}".format(len(res.data)))
            else: st.info("No data yet.")

            logs = sb.table("call_logs").select("*").order("logged_at",desc=True).execute()
            if logs.data:
                st.markdown("---")
                st.markdown("**Call Logs**")
                ldf = pd.DataFrame(logs.data)
                st.dataframe(ldf[["business_id","customer_name","risk_grade","outcome","logged_at"]],
                    use_container_width=True, hide_index=True)
                out = io.BytesIO()
                with pd.ExcelWriter(out,engine="openpyxl") as w:
                    ldf.to_excel(w,sheet_name="All Call Logs",index=False)
                st.download_button("⬇ Download All Call Logs", out.getvalue(), "all_call_logs.xlsx")
        except Exception as e: st.error(str(e))

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
#  CLIENT APP
# ══════════════════════════════════════════════════════════════════════════════
bid          = st.session_state["bid"]
display_name = st.session_state["display_name"] or bid
today        = pd.Timestamp(datetime.now().date())
page         = st.session_state["page"]

# Load data
@st.cache_data(ttl=300, show_spinner=False)
def get_data(bid, today_str):
    raw = load_history(bid)
    if len(raw) == 0: return pd.DataFrame(), pd.DataFrame()
    return process_all(raw, pd.Timestamp(today_str))

df_inv, summary = get_data(bid, str(today))

# ── Top Bar ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="cp-topbar">
  <div class="cp-logo">⚡ CreditPulse</div>
  <div class="cp-user">{}</div>
</div>
""".format(display_name), unsafe_allow_html=True)

# ── Page Content ──────────────────────────────────────────────────────────────
st.markdown('<div class="cp-page">', unsafe_allow_html=True)

# ════════════════════════════════════════════
#  PAGE 1 — HOME (Summary Report)
# ════════════════════════════════════════════
if page == "home":
    st.markdown('<div class="cp-section-header">Summary Report</div>', unsafe_allow_html=True)

    if len(summary) == 0:
        st.markdown("""
        <div class="cp-card" style="text-align:center;padding:40px 20px;">
          <div style="font-size:40px;margin-bottom:12px;">📂</div>
          <div style="font-weight:700;font-size:16px;margin-bottom:8px;">No data yet</div>
          <div style="color:var(--muted);font-size:13px;">Tap ➕ below to add your first invoice</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        total_credit  = summary["Total Credit"].sum()
        total_paid    = summary["Total Paid"].sum()
        total_out     = summary["Outstanding"].sum()
        critical_cnt  = int((summary["Risk Grade"]=="D").sum())
        pay_pct       = round((total_paid/total_credit)*100) if total_credit>0 else 0

        st.markdown("""
        <div class="cp-kpi-grid">
          <div class="cp-kpi">
            <div class="cp-kpi-label">Customers</div>
            <div class="cp-kpi-value">{}</div>
          </div>
          <div class="cp-kpi">
            <div class="cp-kpi-label">Outstanding</div>
            <div class="cp-kpi-value" style="color:#F5A623">{}</div>
          </div>
          <div class="cp-kpi">
            <div class="cp-kpi-label">Total Credit</div>
            <div class="cp-kpi-value" style="color:#3D8EF0">{}</div>
          </div>
          <div class="cp-kpi">
            <div class="cp-kpi-label">Critical</div>
            <div class="cp-kpi-value" style="color:#E53E3E">{} ⚠</div>
          </div>
        </div>
        """.format(len(summary), fmt_full(total_out), fmt_full(total_credit), critical_cnt),
        unsafe_allow_html=True)

        # Payment progress
        st.markdown("""
        <div class="cp-card">
          <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
            <span style="font-weight:600;font-size:13px;">Collection Progress</span>
            <span style="font-family:'DM Mono',monospace;font-size:13px;color:var(--muted);">{}% collected</span>
          </div>
          <div class="cp-progress-wrap">
            <div class="cp-progress-fill" style="width:{}%;background:linear-gradient(90deg,#3D8EF0,#00C278);"></div>
          </div>
          <div style="display:flex;justify-content:space-between;margin-top:8px;font-size:12px;color:var(--muted);">
            <span>Paid: {}</span>
            <span>Pending: {}</span>
          </div>
        </div>
        """.format(pay_pct, pay_pct, fmt_full(total_paid), fmt_full(total_out)),
        unsafe_allow_html=True)

        # Grade breakdown
        st.markdown('<div class="cp-section-header">Grade Breakdown</div>', unsafe_allow_html=True)
        gc = summary["Risk Grade"].value_counts().reindex(["A","B","C","D"],fill_value=0)
        for gk, cnt in gc.items():
            m  = GRADE_META[gk]
            pv = round((cnt/len(summary))*100) if len(summary)>0 else 0
            st.markdown("""
            <div style="margin-bottom:10px;">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;">
                <div style="display:flex;align-items:center;gap:8px;">
                  <span class="cp-badge grade-{}" style="min-width:28px;text-align:center;">{}</span>
                  <span style="font-size:13px;font-weight:600;color:var(--text);">{}</span>
                </div>
                <span style="font-family:'DM Mono',monospace;font-size:12px;color:var(--muted);">{} customers</span>
              </div>
              <div class="cp-progress-wrap">
                <div class="cp-progress-fill" style="width:{}%;background:{};"></div>
              </div>
            </div>
            """.format(gk,gk,m["label"],cnt,max(pv,2),m["color"]), unsafe_allow_html=True)

        st.markdown("<div style='height:12px'/>", unsafe_allow_html=True)
        if st.button("Logout", use_container_width=True):
            for k,v in defaults.items(): st.session_state[k]=v
            st.rerun()

# ════════════════════════════════════════════
#  PAGE 2 — RISK (Risky Customers)
# ════════════════════════════════════════════
elif page == "risk":
    st.markdown('<div class="cp-section-header">Risky Customers</div>', unsafe_allow_html=True)

    if len(summary) == 0:
        st.info("No data yet. Add invoices from the ➕ tab.")
    else:
        grade_filter = st.selectbox("Filter", ["All Grades","🔴 Critical (D)","🟠 High (C)","🟡 Moderate (B)","🟢 Low (A)"])
        grade_map = {"All Grades":None,"🔴 Critical (D)":"D","🟠 High (C)":"C","🟡 Moderate (B)":"B","🟢 Low (A)":"A"}
        gf = grade_map[grade_filter]
        filtered = summary.copy() if not gf else summary[summary["Risk Grade"]==gf].copy()

        for _, row in filtered.iterrows():
            gr = row["Risk Grade"]
            m  = GRADE_META[gr]
            outstanding = row["Outstanding"]
            status_color = "#00C278" if outstanding == 0 else m["color"]
            status_text  = "Fully Paid ✓" if outstanding == 0 else "{} overdue".format(row["Max Overdue(d)"])+" days"

            st.markdown("""
            <div class="cp-cust-row">
              <div style="flex:1;min-width:0;">
                <div class="cp-cust-name">{}</div>
                <div class="cp-cust-sub">{} invoices · {}</div>
                <div style="margin-top:6px;">
                  <span class="cp-badge grade-{}">Grade {}</span>
                  <span style="font-size:11px;color:var(--muted);margin-left:8px;">{}</span>
                </div>
              </div>
              <div class="cp-cust-right">
                <div class="cp-cust-amt" style="color:{};">{}</div>
                <div style="font-size:11px;color:{};">{}</div>
                <div style="font-size:11px;color:var(--muted);margin-top:2px;">{}</div>
              </div>
            </div>
            """.format(
                row["Customer"],
                row["Invoices"],
                row["Grade Label"],
                gr, gr,
                m["action"],
                status_color, fmt_full(outstanding),
                status_color, status_text,
                "Suggested: " + fmt(row["Suggested Limit"])
            ), unsafe_allow_html=True)

# ════════════════════════════════════════════
#  PAGE 3 — CALLS (Whom to Call)
# ════════════════════════════════════════════
elif page == "calls":
    st.markdown('<div class="cp-section-header">Whom to Call Today</div>', unsafe_allow_html=True)

    if len(summary) == 0:
        st.info("No data yet. Add invoices from the ➕ tab.")
    else:
        call_df = summary[summary["Risk Grade"].isin(["D","C","B"])].copy()
        call_df = call_df.sort_values("Risk Score", ascending=False).reset_index(drop=True)

        if len(call_df) == 0:
            st.markdown("""
            <div class="cp-card" style="text-align:center;padding:32px;">
              <div style="font-size:32px;margin-bottom:8px;">🎉</div>
              <div style="font-weight:700;">All customers are Grade A!</div>
              <div style="color:var(--muted);font-size:13px;margin-top:4px;">No urgent calls needed today.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            priority_label = {"D":"🔴 URGENT","C":"🟠 FOLLOW UP","B":"🟡 CHECK IN"}

            for i, (_, row) in enumerate(call_df.iterrows()):
                gr = row["Risk Grade"]
                m  = GRADE_META[gr]

                with st.expander("#{} {} — {} — {}".format(
                    i+1, row["Customer"], fmt_full(row["Outstanding"]), priority_label[gr])):

                    st.markdown("""
                    <div style="margin-bottom:8px;">
                      <span class="cp-badge grade-{}">{}</span>
                      <span style="font-size:12px;color:var(--muted);margin-left:8px;">{} overdue · {}</span>
                    </div>
                    <div class="cp-call-script">{}</div>
                    """.format(gr, gr,
                        str(row["Max Overdue(d)"])+" days",
                        m["action"],
                        row["Call Script"]
                    ), unsafe_allow_html=True)

                    outcome = st.selectbox("Call Outcome",
                        ["Select outcome","Contacted","No Answer","Promise to Pay","Disputed","Paid in Full"],
                        key="out_{}".format(row["Customer"]))

                    if st.button("💾 Save Log", key="save_{}".format(row["Customer"]), use_container_width=True):
                        if outcome == "Select outcome":
                            st.warning("Select an outcome first.")
                        else:
                            if save_call_log(bid, row["Customer"], gr, outcome):
                                st.success("✓ Logged — {}".format(outcome))
                            else:
                                st.error("Failed to save. Check connection.")

        st.markdown("<div style='height:8px'/>", unsafe_allow_html=True)
        try:
            logs = sb.table("call_logs").select("*").eq("business_id",bid).order("logged_at",desc=True).execute()
            if logs.data:
                ldf = pd.DataFrame(logs.data)
                ldf["logged_at"] = pd.to_datetime(ldf["logged_at"]).dt.strftime("%d %b %Y %H:%M")
                out = io.BytesIO()
                with pd.ExcelWriter(out,engine="openpyxl") as w:
                    ldf[["customer_name","risk_grade","outcome","logged_at"]].to_excel(w,index=False)
                st.download_button("⬇ Download Call Logs", out.getvalue(),
                    "call_logs_{}.xlsx".format(bid),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except: pass

# ════════════════════════════════════════════
#  PAGE 4 — PREDICT (Late Payment Predictor)
# ════════════════════════════════════════════
elif page == "predict":
    st.markdown('<div class="cp-section-header">Predict Late Payments</div>', unsafe_allow_html=True)

    if len(summary) == 0:
        st.info("No data yet. Add invoices from the ➕ tab.")
    else:
        tc = summary["Behaviour Trend"].value_counts()
        st.markdown("""
        <div class="cp-kpi-grid">
          <div class="cp-kpi">
            <div class="cp-kpi-label">Improving</div>
            <div class="cp-kpi-value" style="color:#00C278;">{}</div>
          </div>
          <div class="cp-kpi">
            <div class="cp-kpi-label">Stable</div>
            <div class="cp-kpi-value" style="color:#F5A623;">{}</div>
          </div>
          <div class="cp-kpi">
            <div class="cp-kpi-label">Worsening</div>
            <div class="cp-kpi-value" style="color:#E53E3E;">{}</div>
          </div>
          <div class="cp-kpi">
            <div class="cp-kpi-label">New</div>
            <div class="cp-kpi-value" style="color:var(--muted);">{}</div>
          </div>
        </div>
        """.format(
            tc.get("Improving",0), tc.get("Stable",0),
            tc.get("Worsening",0), tc.get("New",0)
        ), unsafe_allow_html=True)

        trend_cfg = {
            "Improving": ("#00C278","rgba(0,194,120,0.08)","rgba(0,194,120,0.2)","↑"),
            "Worsening": ("#E53E3E","rgba(229,62,62,0.08)","rgba(229,62,62,0.2)","↓"),
            "Stable":    ("#F5A623","rgba(245,166,35,0.08)","rgba(245,166,35,0.2)","→"),
            "New":       ("#8899AA","rgba(136,153,170,0.08)","rgba(136,153,170,0.2)","—"),
        }

        ordered = pd.concat([
            summary[summary["Behaviour Trend"]=="Worsening"],
            summary[summary["Behaviour Trend"]=="Stable"],
            summary[summary["Behaviour Trend"]=="Improving"],
            summary[summary["Behaviour Trend"]=="New"],
        ])

        for _, row in ordered.iterrows():
            trend = row["Behaviour Trend"]
            color, bg, border, arrow = trend_cfg.get(trend, trend_cfg["New"])
            gr = row["Risk Grade"]

            st.markdown("""
            <div style="background:{};border:1px solid {};border-radius:14px;padding:14px 16px;margin-bottom:10px;">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
                <div style="font-weight:700;font-size:14px;color:var(--text);">{}</div>
                <span style="color:{};font-weight:700;font-size:13px;">{} {}</span>
              </div>
              <div style="font-size:13px;color:var(--text);margin-bottom:10px;">{}</div>
              <div style="display:flex;gap:16px;flex-wrap:wrap;">
                <span style="font-size:11px;color:var(--muted);">Grade: <b style="color:{};">{}</b></span>
                <span style="font-size:11px;color:var(--muted);">Avg delay: <b style="color:var(--text);">{}d</b></span>
                <span style="font-size:11px;color:var(--muted);">Recent: <b style="color:{};">{}d</b></span>
                <span style="font-size:11px;color:var(--muted);">Outstanding: <b style="color:{};">{}</b></span>
              </div>
            </div>
            """.format(
                bg, border,
                row["Customer"],
                color, arrow, trend,
                row["Behaviour Insight"],
                GRADE_META[gr]["color"], gr,
                row["Avg Delay(d)"],
                color, row["Recent Avg Delay"],
                GRADE_META[gr]["color"], fmt_full(row["Outstanding"])
            ), unsafe_allow_html=True)

# ════════════════════════════════════════════
#  PAGE 5 — ADD INVOICE
# ════════════════════════════════════════════
elif page == "add":
    st.markdown('<div class="cp-section-header">Add Invoice</div>', unsafe_allow_html=True)

    if st.session_state["form_success"]:
        st.success("✓ {} saved! Dashboard updated.".format(st.session_state["form_success"]))
        if st.button("➕ Add Another", use_container_width=True):
            st.session_state["form_success"] = None
            st.rerun()
    else:
        if len(summary) > 0:
            existing = summary["Customer"].tolist()
            cust_opt = ["New customer..."] + existing
            cust_sel = st.selectbox("Customer", cust_opt)
            if cust_sel == "New customer...":
                f_cust = st.text_input("Customer Name", placeholder="e.g. Raju Kirana Stores")
            else:
                f_cust = cust_sel
        else:
            f_cust = st.text_input("Customer Name", placeholder="e.g. Raju Kirana Stores")

        f_inv  = st.text_input("Invoice Number", placeholder="e.g. INV-001")

        col1, col2 = st.columns(2)
        with col1:
            f_inv_date = st.date_input("Invoice Date", value=datetime.now().date())
        with col2:
            f_due_date = st.date_input("Due Date",
                value=(datetime.now() + pd.Timedelta(days=21)).date())

        f_amount = st.number_input("Invoice Amount (₹)", min_value=0.0, step=1000.0, format="%.0f")
        f_paid   = st.number_input("Paid Amount (₹)", min_value=0.0, step=1000.0, format="%.0f",
                                    help="Leave 0 if unpaid")

        f_paid_date = None
        if f_paid > 0:
            f_paid_date = st.date_input("Payment Date", value=datetime.now().date())

        if f_amount > 0 and f_paid > f_amount:
            st.error("Paid amount cannot exceed invoice amount.")
        if f_due_date < f_inv_date:
            st.error("Due date cannot be before invoice date.")

        if st.button("💾 Save Invoice", use_container_width=True):
            errors = []
            if not f_cust.strip():   errors.append("Customer name required.")
            if not f_inv.strip():    errors.append("Invoice number required.")
            if f_amount <= 0:        errors.append("Amount must be greater than 0.")
            if f_paid > f_amount:    errors.append("Paid cannot exceed amount.")
            if f_due_date < f_inv_date: errors.append("Due date before invoice date.")

            if errors:
                for e in errors: st.error(e)
            else:
                row = {
                    "business_id":   bid,
                    "customer_name": f_cust.strip(),
                    "invoice_no":    f_inv.strip().upper(),
                    "invoice_date":  str(f_inv_date),
                    "due_date":      str(f_due_date),
                    "amount":        float(f_amount),
                    "paid_amount":   float(f_paid),
                    "payment_date":  str(f_paid_date) if f_paid_date and f_paid > 0 else None,
                }
                if save_invoice(bid, row):
                    st.cache_data.clear()
                    st.session_state["form_success"] = f_inv.strip().upper()
                    st.rerun()
                else:
                    st.error("Failed to save. Check your connection.")

st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  BOTTOM NAVIGATION (st.columns + st.button → session state preserved)
#  CSS :has() makes the 5-column block fixed at the bottom.
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
        if st.button(text, key="nav_"+pg, use_container_width=True):
            st.session_state["page"] = pg
            st.rerun()

# ── JavaScript: highlight the active nav button ──────────────────────────────
st.markdown("""
<script>
(function(){
  function highlightNav(){
    var map = {'home':'🏠','risk':'⚠️','calls':'📞','predict':'🔮','add':'➕'};
    var cur = document.querySelector('.cp-page');
    if(!cur) return;
    var pg = cur.getAttribute('data-page') || '';
    if(!pg){
      // Fallback: find hidden data attribute
      var pd = document.getElementById('cp-cpage');
      if(pd) pg = pd.getAttribute('data-p') || '';
    }
    var hBlock = document.querySelector('[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5))');
    if(!hBlock) return;
    var btns = hBlock.querySelectorAll('button');
    btns.forEach(function(b){
      b.classList.remove('cp-nav-active');
      if(pg && b.textContent.indexOf(map[pg]) !== -1){
        b.classList.add('cp-nav-active');
      }
    });
  }
  var t = setInterval(highlightNav, 150);
  setTimeout(function(){ clearInterval(t); }, 3000);
})();
</script>
<div id="cp-cpage" data-p="{}" style="display:none"></div>
""".format(page), unsafe_allow_html=True)
pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import io, hashlib
from supabase import create_client

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="CreditPulse",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="collapsed"
)

# ══════════════════════════════════════════════════════════════════════════════
#  CSS — Mobile First + PWA + Auto Theme
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Inter:wght@400;500;600;700;800&display=swap');

/* ── Auto Theme Variables ── */
:root {
  --bg:       #FFFFFF;
  --bg2:      #F7F8FA;
  --bg3:      #EDEEF2;
  --border:   rgba(0,0,0,0.08);
  --text:     #0D1117;
  --muted:    #6B7280;
  --card:     #FFFFFF;
  --shadow:   0 2px 12px rgba(0,0,0,0.08);
  --green:    #00C278;
  --blue:     #3D8EF0;
  --yellow:   #F5A623;
  --red:      #E53E3E;
  --orange:   #ED8936;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg:     #060E18;
    --bg2:    #0C1422;
    --bg3:    #162030;
    --border: rgba(255,255,255,0.08);
    --text:   #F0F4F8;
    --muted:  #8899AA;
    --card:   #0C1422;
    --shadow: 0 2px 12px rgba(0,0,0,0.4);
  }
}

/* ── Base ── */
html,body,[class*="css"]{font-family:'Inter',sans-serif;-webkit-tap-highlight-color:transparent;}
.stApp{background:var(--bg);color:var(--text);}
header[data-testid="stHeader"]{display:none!important;}
section[data-testid="stSidebar"]{display:none!important;}
.block-container{padding:0 0 80px 0!important;max-width:100%!important;}
footer{display:none!important;}

/* ── PWA Meta ── */

/* ── Top Bar ── */
.cp-topbar{
  position:fixed;top:0;left:0;right:0;z-index:100;
  background:var(--bg);border-bottom:1px solid var(--border);
  padding:12px 16px;
  display:flex;align-items:center;justify-content:space-between;
  backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
}
.cp-logo{
  font-weight:800;font-size:20px;
  background:linear-gradient(135deg,var(--blue),var(--green));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;
}
.cp-user{font-size:12px;color:var(--muted);font-weight:500;}

/* ── Bottom Nav ── */
.cp-nav{
  position:fixed;bottom:0;left:0;right:0;z-index:100;
  background:var(--bg);border-top:1px solid var(--border);
  display:grid;grid-template-columns:repeat(5,1fr);
  padding:8px 0 env(safe-area-inset-bottom,8px);
  backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
}
.cp-nav-item{
  display:flex;flex-direction:column;align-items:center;
  gap:3px;padding:4px 0;cursor:pointer;
  font-size:10px;color:var(--muted);font-weight:500;
  border:none;background:none;
  transition:color 0.15s;
  -webkit-tap-highlight-color:transparent;
}
.cp-nav-item.active{color:var(--blue);}
.cp-nav-icon{font-size:20px;line-height:1;}

/* ── Page Content ── */
.cp-page{padding:72px 16px 16px;}

/* ── Cards ── */
.cp-card{
  background:var(--card);
  border:1px solid var(--border);
  border-radius:16px;
  padding:16px;
  margin-bottom:12px;
  box-shadow:var(--shadow);
}
.cp-card-sm{
  background:var(--bg2);
  border:1px solid var(--border);
  border-radius:12px;
  padding:12px 14px;
  margin-bottom:8px;
}

/* ── KPI Grid ── */
.cp-kpi-grid{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:10px;
  margin-bottom:16px;
}
.cp-kpi{
  background:var(--card);
  border:1px solid var(--border);
  border-radius:14px;
  padding:14px;
  box-shadow:var(--shadow);
}
.cp-kpi-label{font-size:11px;color:var(--muted);font-weight:500;margin-bottom:4px;text-transform:uppercase;letter-spacing:0.05em;}
.cp-kpi-value{font-family:'DM Mono',monospace;font-size:clamp(16px,4vw,22px);font-weight:700;color:var(--text);word-break:break-all;}

/* ── Grade Badges ── */
.grade-A{background:rgba(0,194,120,0.12);color:#00C278;border:1px solid rgba(0,194,120,0.25);}
.grade-B{background:rgba(245,166,35,0.12);color:#F5A623;border:1px solid rgba(245,166,35,0.25);}
.grade-C{background:rgba(237,137,54,0.12);color:#ED8936;border:1px solid rgba(237,137,54,0.25);}
.grade-D{background:rgba(229,62,62,0.12);color:#E53E3E;border:1px solid rgba(229,62,62,0.25);}
.cp-badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;font-family:'DM Mono',monospace;}

/* ── Customer Row ── */
.cp-cust-row{
  display:flex;align-items:center;justify-content:space-between;
  padding:14px 16px;
  background:var(--card);
  border:1px solid var(--border);
  border-radius:14px;
  margin-bottom:8px;
  box-shadow:var(--shadow);
}
.cp-cust-name{font-weight:700;font-size:14px;color:var(--text);margin-bottom:2px;}
.cp-cust-sub{font-size:12px;color:var(--muted);}
.cp-cust-right{text-align:right;}
.cp-cust-amt{font-family:'DM Mono',monospace;font-weight:700;font-size:14px;}

/* ── Call Card ── */
.cp-call-card{
  background:var(--card);
  border:1px solid var(--border);
  border-radius:16px;
  padding:16px;
  margin-bottom:12px;
  box-shadow:var(--shadow);
}
.cp-call-script{
  background:var(--bg2);
  border-radius:10px;
  padding:12px;
  font-size:13px;
  color:var(--text);
  line-height:1.7;
  margin:10px 0;
}
.cp-priority{
  display:inline-flex;align-items:center;gap:4px;
  font-size:11px;font-weight:700;padding:3px 10px;
  border-radius:20px;margin-bottom:8px;
}

/* ── Progress Bar ── */
.cp-progress-wrap{background:var(--bg3);border-radius:6px;height:6px;margin-top:6px;}
.cp-progress-fill{height:6px;border-radius:6px;transition:width 0.5s ease;}

/* ── Predict Card ── */
.cp-predict{
  border-radius:14px;
  padding:14px 16px;
  margin-bottom:10px;
  border:1px solid var(--border);
}

/* ── Section Header ── */
.cp-section-header{
  font-size:13px;font-weight:700;color:var(--muted);
  text-transform:uppercase;letter-spacing:0.08em;
  margin:20px 0 10px;
}

/* ── Action Button ── */
.stButton>button{
  background:linear-gradient(135deg,var(--blue),#2E7DD4)!important;
  border:none!important;color:white!important;
  border-radius:12px!important;font-weight:700!important;
  padding:12px 20px!important;width:100%!important;
  font-size:14px!important;letter-spacing:-0.01em!important;
}
.stDownloadButton>button{
  background:var(--bg2)!important;
  border:1px solid var(--border)!important;
  color:var(--text)!important;
  border-radius:12px!important;font-weight:600!important;
  padding:10px 16px!important;width:100%!important;
}

/* ── Inputs ── */
.stTextInput>div>div>input,.stSelectbox>div>div{
  background:var(--bg2)!important;
  border:1px solid var(--border)!important;
  border-radius:10px!important;color:var(--text)!important;
  font-size:14px!important;
}
.stNumberInput>div>div>input{
  background:var(--bg2)!important;
  border:1px solid var(--border)!important;
  border-radius:10px!important;color:var(--text)!important;
}

/* ── Alerts ── */
.stSuccess{background:rgba(0,194,120,0.08)!important;border:1px solid rgba(0,194,120,0.25)!important;border-radius:12px!important;}
.stError{background:rgba(229,62,62,0.08)!important;border:1px solid rgba(229,62,62,0.25)!important;border-radius:12px!important;}
.stInfo{background:rgba(61,142,240,0.08)!important;border:1px solid rgba(61,142,240,0.25)!important;border-radius:12px!important;}
.stWarning{background:rgba(245,166,35,0.08)!important;border:1px solid rgba(245,166,35,0.25)!important;border-radius:12px!important;}

/* ── Dataframe ── */
[data-testid="stDataFrame"]{border-radius:12px!important;overflow:hidden!important;}

/* ── Expander ── */
.streamlit-expanderHeader{
  background:var(--bg2)!important;border-radius:12px!important;
  font-weight:600!important;font-size:13px!important;
}

/* ── Desktop adjustments ── */
@media (min-width:768px){
  .block-container{padding:0 48px 80px!important;max-width:900px!important;margin:0 auto!important;}
  .cp-page{padding:80px 0 16px;}
  .cp-kpi-grid{grid-template-columns:repeat(4,1fr);}
  .cp-nav{max-width:900px;left:50%;transform:translateX(-50%);border-radius:20px 20px 0 0;}
  .cp-topbar{max-width:900px;left:50%;transform:translateX(-50%);border-radius:0 0 16px 16px;}
}

/* ── Tab workaround — hide Streamlit tabs, use custom nav ── */
.stTabs{display:none!important;}
</style>

<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#060E18" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#FFFFFF" media="(prefers-color-scheme: light)">
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
GRADE_META = {
    "A":{"color":"#00C278","rgba":"0,194,120",  "label":"Low Risk",      "action":"Increase Limit",   "call":"Thank & Reward",         "limit_mult":1.2},
    "B":{"color":"#F5A623","rgba":"245,166,35",  "label":"Moderate Risk", "action":"Monitor Monthly",  "call":"Check-In Call",          "limit_mult":0.8},
    "C":{"color":"#ED8936","rgba":"237,137,54",  "label":"High Risk",     "action":"Reduce Limit 50%", "call":"Follow-Up Call",         "limit_mult":0.5},
    "D":{"color":"#E53E3E","rgba":"229,62,62",   "label":"Critical Risk", "action":"Suspend Credit",   "call":"Urgent Collection",      "limit_mult":0.0},
}
CALL_SCRIPTS = {
    "A":"Bhai {name}, aapka payment record bahut accha hai. Aapke liye hum credit limit badha rahe hain. Thank you!",
    "B":"Hello {name} bhai, bas ek friendly call tha. Kuch invoices thoda late ho rahe hain — koi problem hai toh batao.",
    "C":"Hello {name} bhai, aapke {amount} ke invoices overdue hain. Kab tak payment ho sakti hai? Batao toh account active rakhte hain.",
    "D":"Hello {name} bhai, urgent baat karni thi. {amount} bahut time se pending hai. Aaj payment nahi hua toh supply band karni padegi.",
}
OVERDUE_CAP  = 45
DEV_PASSWORD = st.secrets.get("DEV_PASSWORD", "creditpulse_dev_2026")

# ══════════════════════════════════════════════════════════════════════════════
#  SUPABASE
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def get_sb():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
sb = get_sb()

# ══════════════════════════════════════════════════════════════════════════════
#  FORMAT HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def fmt(x):
    try:
        v = float(x)
        if v >= 10_000_000: return "₹{:.1f}Cr".format(v/10_000_000)
        elif v >= 100_000:  return "₹{:.1f}L".format(v/100_000)
        elif v >= 1_000:    return "₹{:.0f}K".format(v/1_000)
        else:               return "₹{:.0f}".format(v)
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

def hash_pw(pw): return hashlib.sha256(pw.strip().encode()).hexdigest()

# ══════════════════════════════════════════════════════════════════════════════
#  AUTH — Simple login
# ══════════════════════════════════════════════════════════════════════════════
def client_login(bid, pw):
    try:
        res = sb.table("clients").select("*").eq("business_id", bid.strip().upper()).execute()
        if not res.data: return False, "Business ID not found. Contact your provider."
        c = res.data[0]
        if not c.get("active"): return False, "Account deactivated. Contact your provider."
        if hash_pw(pw) != c["password_hash"]: return False, "Wrong password."
        return True, c.get("display_name", bid)
    except: return False, "Connection error. Try again."

def load_history(bid):
    try:
        res = sb.table("invoices").select("*").eq("business_id", bid.upper()).execute()
        if not res.data: return pd.DataFrame()
        df = pd.DataFrame(res.data)
        for c in ["invoice_date","due_date","payment_date"]:
            if c in df.columns: df[c] = pd.to_datetime(df[c], errors="coerce")
        return df
    except: return pd.DataFrame()

def save_invoice(bid, row_dict):
    try:
        sb.table("invoices").upsert(row_dict, on_conflict="business_id,invoice_no").execute()
        return True
    except: return False

def save_call_log(bid, cust, grade, outcome):
    try:
        sb.table("call_logs").insert({"business_id":bid,"customer_name":cust,"risk_grade":grade,"outcome":outcome}).execute()
        return True
    except: return False

# Dev panel helpers
def load_all_clients():
    try:
        res = sb.table("clients").select("*").order("added", desc=True).execute()
        return res.data or []
    except: return []

def add_client(bid, name, pw):
    try:
        sb.table("clients").insert({
            "business_id": bid.strip().upper(),
            "display_name": name.strip() or bid.strip().upper(),
            "password_hash": hash_pw(pw),
            "active": True,
            "added": datetime.now().strftime("%Y-%m-%d"),
        }).execute()
        return True, "OK"
    except Exception as e:
        err = str(e)
        if "duplicate" in err.lower() or "unique" in err.lower():
            return False, "Business ID already exists."
        return False, "Error: " + err

def toggle_client(bid, active):
    sb.table("clients").update({"active": not active}).eq("business_id", bid).execute()

def reset_pw(bid, new_pw):
    sb.table("clients").update({"password_hash": hash_pw(new_pw)}).eq("business_id", bid).execute()

# ══════════════════════════════════════════════════════════════════════════════
#  DATA PROCESSING
# ══════════════════════════════════════════════════════════════════════════════
def clean_data(df):
    df = df.copy()
    drop = ["outstanding","fully_paid","overdue_days","paid_late","uploaded_at","id","business_id"]
    df.drop(columns=[c for c in drop if c in df.columns], inplace=True)
    df.columns = df.columns.str.lower().str.strip().str.replace(" ","_")
    for c in ["invoice_date","due_date","payment_date"]:
        if c in df.columns: df[c] = pd.to_datetime(df[c], errors="coerce")
    df["amount"]      = pd.to_numeric(df["amount"],      errors="coerce").fillna(0)
    df["paid_amount"] = pd.to_numeric(df["paid_amount"], errors="coerce").fillna(0)
    if "payment_date" not in df.columns: df["payment_date"] = pd.NaT
    return df[df["amount"]>0].copy()

def calc_metrics(df, today):
    df = df.copy()
    df["outstanding"]  = (df["amount"]-df["paid_amount"]).clip(lower=0)
    df["fully_paid"]   = df["paid_amount"] >= df["amount"]
    df["overdue_days"] = 0; df["paid_late"] = False
    mu = (df["outstanding"]>0)&(df["due_date"]<today)
    df.loc[mu,"overdue_days"] = (today-df.loc[mu,"due_date"]).dt.days.astype(int)
    ml = df["fully_paid"]&df["payment_date"].notna()&(df["payment_date"]>df["due_date"])
    df.loc[ml,"overdue_days"] = (df.loc[ml,"payment_date"]-df.loc[ml,"due_date"]).dt.days.astype(int)
    df.loc[ml,"paid_late"] = True
    df["overdue_days"] = df["overdue_days"].clip(lower=0,upper=60)
    return df

def predict_behaviour(inv_df):
    paid = inv_df[inv_df["fully_paid"]==True].copy().sort_values("invoice_date")
    total = len(inv_df); pc = len(paid)
    if pc < 3:
        pct = round(((total-pc)/total)*100) if total>0 else 0
        return "New", 0, "Only {} paid invoice(s). {}% unpaid.".format(pc, pct)
    mid = len(paid)//2
    delta = paid.iloc[mid:]["overdue_days"].mean() - paid.iloc[:mid]["overdue_days"].mean()
    last3 = paid.tail(3)["overdue_days"].mean()
    overall = paid["overdue_days"].mean()
    pay_rate = pc/total if total>0 else 0
    if (delta>5 and last3>overall) or last3>overall*1.3:
        msg = "Delays increasing. Last 3 avg {:.0f}d vs {:.0f}d overall.".format(last3,overall)
        if pay_rate<0.6: msg += " Only {:.0f}% fully paid.".format(pay_rate*100)
        return "Worsening", round(last3,1), msg
    elif (delta<-5 and last3<overall) or last3<overall*0.7:
        return "Improving", round(last3,1), "Getting better. Last 3 avg {:.0f}d vs {:.0f}d overall.".format(last3,overall)
    else:
        return "Stable", round(last3,1), "Consistent. Avg delay {:.0f}d. Pay rate {:.0f}%.".format(overall,pay_rate*100)

def score_customer(row):
    od = min(row["max_overdue"]/OVERDUE_CAP,1)*40
    ou = (row["total_outstanding"]/row["total_amount"])*40 if row["total_amount"]>0 else 0
    pr = row["total_paid"]/row["total_amount"] if row["total_amount"]>0 else 0
    lr = row["late_count"]/row["paid_count"] if row["paid_count"]>0 else 1
    return min(round(od+ou+min((1-pr)*10+lr*10,20)),100)

def get_grade(s): return "A" if s<=10 else "B" if s<=30 else "C" if s<=55 else "D"

def aggregate(df):
    g = df.groupby("customer_name").agg(
        total_invoices=("invoice_no","count"), total_amount=("amount","sum"),
        total_paid=("paid_amount","sum"),      max_overdue=("overdue_days","max"),
        late_count=("paid_late","sum"),        paid_count=("fully_paid","sum"),
    ).reset_index()
    g["total_outstanding"] = (g["total_amount"]-g["total_paid"]).clip(lower=0)
    g["avg_delay"] = g["customer_name"].map(
        df[df["paid_late"]].groupby("customer_name")["overdue_days"].mean()).fillna(0).round(1)
    rows = []
    for _,r in g.iterrows():
        sc=score_customer(r); gr=get_grade(sc); m=GRADE_META[gr]
        trend,last3,pred = predict_behaviour(df[df["customer_name"]==r["customer_name"]])
        rows.append({
            "Customer":r["customer_name"],"Invoices":int(r["total_invoices"]),
            "Total Credit":round(float(r["total_amount"]),2),
            "Total Paid":round(float(r["total_paid"]),2),
            "Outstanding":round(float(r["total_outstanding"]),2),
            "Max Overdue(d)":int(r["max_overdue"]),"Avg Delay(d)":float(r["avg_delay"]),
            "Risk Score":sc,"Risk Grade":gr,"Grade Label":m["label"],
            "Suggested Limit":round(float(r["total_amount"])*m["limit_mult"],2),
            "Credit Action":m["action"],"Call Type":m["call"],
            "Call Script":CALL_SCRIPTS[gr].format(name=r["customer_name"],amount=fmt(r["total_outstanding"])),
            "Behaviour Trend":trend,"Recent Avg Delay":last3,"Behaviour Insight":pred,
        })
    return pd.DataFrame(rows).sort_values("Risk Score",ascending=False).reset_index(drop=True)

def process_all(raw_df, today):
    c = clean_data(raw_df); i = calc_metrics(c,today)
    return i, aggregate(i)

# ══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
defaults = {
    "auth":False,"is_dev":False,"bid":None,"display_name":None,
    "df_inv":None,"summary":None,"page":"home","form_success":None,
}
for k,v in defaults.items():
    if k not in st.session_state: st.session_state[k]=v

# ══════════════════════════════════════════════════════════════════════════════
#  LOGIN PAGE
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state["auth"]:
    st.markdown("""
    <div style="min-height:100vh;display:flex;flex-direction:column;align-items:center;
      justify-content:center;padding:24px;background:var(--bg);">
      <div style="width:100%;max-width:380px;">
        <div style="text-align:center;margin-bottom:32px;">
          <div style="font-size:40px;margin-bottom:8px;">⚡</div>
          <div style="font-size:28px;font-weight:800;background:linear-gradient(135deg,#3D8EF0,#00C278);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
            letter-spacing:-0.03em;">CreditPulse</div>
          <div style="font-size:13px;color:var(--muted);margin-top:4px;">Wholesale Risk Intelligence</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Center the form
    _, col, _ = st.columns([1,3,1])
    with col:
        login_type = st.radio("Login as", ["Client","Developer"], horizontal=True, label_visibility="collapsed")
        st.markdown("<div style='height:8px'/>", unsafe_allow_html=True)

        if login_type == "Client":
            bid_in = st.text_input("Business ID", placeholder="e.g. RAJ_TRADERS")
            pw_in  = st.text_input("Password", type="password", placeholder="Your password")
            if st.button("Login →", use_container_width=True):
                if bid_in.strip() and pw_in.strip():
                    ok, result = client_login(bid_in, pw_in)
                    if ok:
                        st.session_state.update({"auth":True,"is_dev":False,
                            "bid":bid_in.strip().upper(),"display_name":result})
                        st.rerun()
                    else: st.error(result)
                else: st.warning("Enter both fields.")
        else:
            dev_pw = st.text_input("Developer Password", type="password")
            if st.button("Enter Dev Panel →", use_container_width=True):
                if hash_pw(dev_pw) == hash_pw(DEV_PASSWORD):
                    st.session_state.update({"auth":True,"is_dev":True,"bid":"__DEV__"})
                    st.rerun()
                else: st.error("Wrong password.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
#  DEVELOPER PANEL
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state["is_dev"]:
    st.markdown('<div class="cp-page">', unsafe_allow_html=True)
    st.markdown("### ⚙️ Developer Panel")
    if st.button("Logout"):
        for k,v in defaults.items(): st.session_state[k]=v
        st.rerun()

    dev_t1, dev_t2, dev_t3 = st.tabs(["👥 Clients","➕ Add","📊 Overview"])

    with dev_t1:
        clients = load_all_clients()
        if not clients:
            st.info("No clients yet.")
        else:
            for c in clients:
                bid = c["business_id"]; active = c.get("active",False)
                with st.expander("{} — {} — {}".format(bid, c.get("display_name",""), "✅ Active" if active else "❌ Off")):
                    c1,c2 = st.columns(2)
                    with c1:
                        if st.button("Toggle Active", key="tog_"+bid):
                            toggle_client(bid, active); st.rerun()
                    with c2:
                        new_p = st.text_input("New Password", type="password", key="np_"+bid)
                        if st.button("Reset PW", key="rp_"+bid):
                            if new_p.strip(): reset_pw(bid, new_p); st.success("Done")
                            else: st.error("Enter password")

    with dev_t2:
        n_bid  = st.text_input("Business ID", placeholder="RAJ_TRADERS")
        n_name = st.text_input("Display Name", placeholder="Rajan Traders, Nagpur")
        n_pw   = st.text_input("Password", type="password")
        if st.button("Add Client", use_container_width=True):
            if n_bid.strip() and n_pw.strip():
                ok, msg = add_client(n_bid, n_name, n_pw)
                if ok: st.success("Added: {}".format(n_bid.strip().upper())); st.rerun()
                else: st.error(msg)
            else: st.error("ID and password required.")

    with dev_t3:
        try:
            res = sb.table("invoices").select("business_id").execute()
            if res.data:
                df_c = pd.DataFrame(res.data)["business_id"].value_counts().reset_index()
                df_c.columns = ["Business ID","Rows"]
                st.dataframe(df_c, use_container_width=True, hide_index=True)
                st.metric("Total rows", "{:,}".format(len(res.data)))
            else: st.info("No data yet.")

            logs = sb.table("call_logs").select("*").order("logged_at",desc=True).execute()
            if logs.data:
                st.markdown("---")
                st.markdown("**Call Logs**")
                ldf = pd.DataFrame(logs.data)
                st.dataframe(ldf[["business_id","customer_name","risk_grade","outcome","logged_at"]],
                    use_container_width=True, hide_index=True)
                out = io.BytesIO()
                with pd.ExcelWriter(out,engine="openpyxl") as w:
                    ldf.to_excel(w,sheet_name="All Call Logs",index=False)
                st.download_button("⬇ Download All Call Logs", out.getvalue(), "all_call_logs.xlsx")
        except Exception as e: st.error(str(e))

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
#  CLIENT APP
# ══════════════════════════════════════════════════════════════════════════════
bid          = st.session_state["bid"]
display_name = st.session_state["display_name"] or bid
today        = pd.Timestamp(datetime.now().date())

# Load data
@st.cache_data(ttl=300, show_spinner=False)
def get_data(bid, today_str):
    raw = load_history(bid)
    if len(raw) == 0: return pd.DataFrame(), pd.DataFrame()
    return process_all(raw, pd.Timestamp(today_str))

df_inv, summary = get_data(bid, str(today))

# ── Top Bar ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="cp-topbar">
  <div class="cp-logo">⚡ CreditPulse</div>
  <div class="cp-user">{}</div>
</div>
""".format(display_name), unsafe_allow_html=True)

# ── Bottom Nav ────────────────────────────────────────────────────────────────
page = st.session_state["page"]

nav_items = [
    ("home",    "🏠", "Home"),
    ("risk",    "⚠️", "Risk"),
    ("calls",   "📞", "Calls"),
    ("predict", "🔮", "Predict"),
    ("add",     "➕", "Add"),
]

nav_cols = st.columns(5)
for i, (pg, icon, label) in enumerate(nav_items):
    with nav_cols[i]:
        active_class = "active" if page == pg else ""
        if st.button(icon + "\n" + label, key="nav_"+pg, use_container_width=True):
            st.session_state["page"] = pg
            st.rerun()

# ── Inject styled bottom nav ──────────────────────────────────────────────────
st.markdown("""
<style>
div[data-testid="column"] button {
  background: transparent !important;
  border: none !important;
  color: var(--muted) !important;
  font-size: 11px !important;
  font-weight: 500 !important;
  padding: 8px 4px !important;
  border-radius: 10px !important;
  box-shadow: none !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  white-space: pre-line !important;
  line-height: 1.4 !important;
  width: 100% !important;
}
</style>
""", unsafe_allow_html=True)

# ── Page Content ──────────────────────────────────────────────────────────────
st.markdown('<div class="cp-page">', unsafe_allow_html=True)

# ════════════════════════════════════════════
#  PAGE 1 — HOME (Summary Report)
# ════════════════════════════════════════════
if page == "home":
    st.markdown('<div class="cp-section-header">Summary Report</div>', unsafe_allow_html=True)

    if len(summary) == 0:
        st.markdown("""
        <div class="cp-card" style="text-align:center;padding:40px 20px;">
          <div style="font-size:40px;margin-bottom:12px;">📂</div>
          <div style="font-weight:700;font-size:16px;margin-bottom:8px;">No data yet</div>
          <div style="color:var(--muted);font-size:13px;">Tap ➕ below to add your first invoice</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        total_credit  = summary["Total Credit"].sum()
        total_paid    = summary["Total Paid"].sum()
        total_out     = summary["Outstanding"].sum()
        critical_cnt  = int((summary["Risk Grade"]=="D").sum())
        pay_pct       = round((total_paid/total_credit)*100) if total_credit>0 else 0

        st.markdown("""
        <div class="cp-kpi-grid">
          <div class="cp-kpi">
            <div class="cp-kpi-label">Customers</div>
            <div class="cp-kpi-value">{}</div>
          </div>
          <div class="cp-kpi">
            <div class="cp-kpi-label">Outstanding</div>
            <div class="cp-kpi-value" style="color:#F5A623">{}</div>
          </div>
          <div class="cp-kpi">
            <div class="cp-kpi-label">Total Credit</div>
            <div class="cp-kpi-value" style="color:#3D8EF0">{}</div>
          </div>
          <div class="cp-kpi">
            <div class="cp-kpi-label">Critical</div>
            <div class="cp-kpi-value" style="color:#E53E3E">{} ⚠</div>
          </div>
        </div>
        """.format(len(summary), fmt_full(total_out), fmt_full(total_credit), critical_cnt),
        unsafe_allow_html=True)

        # Payment progress
        st.markdown("""
        <div class="cp-card">
          <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
            <span style="font-weight:600;font-size:13px;">Collection Progress</span>
            <span style="font-family:'DM Mono',monospace;font-size:13px;color:var(--muted);">{}% collected</span>
          </div>
          <div class="cp-progress-wrap">
            <div class="cp-progress-fill" style="width:{}%;background:linear-gradient(90deg,#3D8EF0,#00C278);"></div>
          </div>
          <div style="display:flex;justify-content:space-between;margin-top:8px;font-size:12px;color:var(--muted);">
            <span>Paid: {}</span>
            <span>Pending: {}</span>
          </div>
        </div>
        """.format(pay_pct, pay_pct, fmt_full(total_paid), fmt_full(total_out)),
        unsafe_allow_html=True)

        # Grade breakdown
        st.markdown('<div class="cp-section-header">Grade Breakdown</div>', unsafe_allow_html=True)
        gc = summary["Risk Grade"].value_counts().reindex(["A","B","C","D"],fill_value=0)
        for gk, cnt in gc.items():
            m  = GRADE_META[gk]
            pv = round((cnt/len(summary))*100) if len(summary)>0 else 0
            st.markdown("""
            <div style="margin-bottom:10px;">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;">
                <div style="display:flex;align-items:center;gap:8px;">
                  <span class="cp-badge grade-{}" style="min-width:28px;text-align:center;">{}</span>
                  <span style="font-size:13px;font-weight:600;color:var(--text);">{}</span>
                </div>
                <span style="font-family:'DM Mono',monospace;font-size:12px;color:var(--muted);">{} customers</span>
              </div>
              <div class="cp-progress-wrap">
                <div class="cp-progress-fill" style="width:{}%;background:{};"></div>
              </div>
            </div>
            """.format(gk,gk,m["label"],cnt,max(pv,2),m["color"]), unsafe_allow_html=True)

        # Quick logout
        st.markdown("<div style='height:12px'/>", unsafe_allow_html=True)
        if st.button("Logout", use_container_width=True):
            for k,v in defaults.items(): st.session_state[k]=v
            st.rerun()

# ════════════════════════════════════════════
#  PAGE 2 — RISK (Risky Customers + Actions + Status)
# ════════════════════════════════════════════
elif page == "risk":
    st.markdown('<div class="cp-section-header">Risky Customers</div>', unsafe_allow_html=True)

    if len(summary) == 0:
        st.info("No data yet. Add invoices from the ➕ tab.")
    else:
        grade_filter = st.selectbox("Filter", ["All Grades","🔴 Critical (D)","🟠 High (C)","🟡 Moderate (B)","🟢 Low (A)"])
        grade_map = {"All Grades":None,"🔴 Critical (D)":"D","🟠 High (C)":"C","🟡 Moderate (B)":"B","🟢 Low (A)":"A"}
        gf = grade_map[grade_filter]
        filtered = summary.copy() if not gf else summary[summary["Risk Grade"]==gf].copy()

        for _, row in filtered.iterrows():
            gr = row["Risk Grade"]
            m  = GRADE_META[gr]
            outstanding = row["Outstanding"]
            status_color = "#00C278" if outstanding == 0 else m["color"]
            status_text  = "Fully Paid ✓" if outstanding == 0 else "{} overdue".format(row["Max Overdue(d)"])+" days"

            st.markdown("""
            <div class="cp-cust-row">
              <div style="flex:1;">
                <div class="cp-cust-name">{}</div>
                <div class="cp-cust-sub">{} invoices · {}</div>
                <div style="margin-top:6px;">
                  <span class="cp-badge grade-{}">Grade {}</span>
                  <span style="font-size:11px;color:var(--muted);margin-left:8px;">{}</span>
                </div>
              </div>
              <div class="cp-cust-right">
                <div class="cp-cust-amt" style="color:{};">{}</div>
                <div style="font-size:11px;color:{};">{}</div>
                <div style="font-size:11px;color:var(--muted);margin-top:2px;">{}</div>
              </div>
            </div>
            """.format(
                row["Customer"],
                row["Invoices"],
                row["Grade Label"],
                gr, gr,
                m["action"],
                status_color, fmt_full(outstanding),
                status_color, status_text,
                "Suggested: " + fmt(row["Suggested Limit"])
            ), unsafe_allow_html=True)

# ════════════════════════════════════════════
#  PAGE 3 — CALLS (Whom to Call)
# ════════════════════════════════════════════
elif page == "calls":
    st.markdown('<div class="cp-section-header">Whom to Call Today</div>', unsafe_allow_html=True)

    if len(summary) == 0:
        st.info("No data yet. Add invoices from the ➕ tab.")
    else:
        # Only show customers who need action (C and D first, then B)
        call_df = summary[summary["Risk Grade"].isin(["D","C","B"])].copy()
        call_df = call_df.sort_values("Risk Score", ascending=False).reset_index(drop=True)

        if len(call_df) == 0:
            st.markdown("""
            <div class="cp-card" style="text-align:center;padding:32px;">
              <div style="font-size:32px;margin-bottom:8px;">🎉</div>
              <div style="font-weight:700;">All customers are Grade A!</div>
              <div style="color:var(--muted);font-size:13px;margin-top:4px;">No urgent calls needed today.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            priority_color = {"D":"#E53E3E","C":"#ED8936","B":"#F5A623"}
            priority_label = {"D":"🔴 URGENT","C":"🟠 FOLLOW UP","B":"🟡 CHECK IN"}

            for i, (_, row) in enumerate(call_df.iterrows()):
                gr = row["Risk Grade"]
                m  = GRADE_META[gr]

                with st.expander("#{} {} — {} — {}".format(
                    i+1, row["Customer"], fmt_full(row["Outstanding"]), priority_label[gr])):

                    st.markdown("""
                    <div style="margin-bottom:8px;">
                      <span class="cp-badge grade-{}">{}</span>
                      <span style="font-size:12px;color:var(--muted);margin-left:8px;">{} overdue · {}</span>
                    </div>
                    <div class="cp-call-script">{}</div>
                    """.format(gr, gr,
                        str(row["Max Overdue(d)"])+" days",
                        m["action"],
                        row["Call Script"]
                    ), unsafe_allow_html=True)

                    outcome = st.selectbox("Call Outcome",
                        ["Select outcome","Contacted","No Answer","Promise to Pay","Disputed","Paid in Full"],
                        key="out_{}".format(row["Customer"]))

                    if st.button("💾 Save Log", key="save_{}".format(row["Customer"]), use_container_width=True):
                        if outcome == "Select outcome":
                            st.warning("Select an outcome first.")
                        else:
                            if save_call_log(bid, row["Customer"], gr, outcome):
                                st.success("✓ Logged — {}".format(outcome))
                            else:
                                st.error("Failed to save. Check connection.")

        # Download call logs
        st.markdown("<div style='height:8px'/>", unsafe_allow_html=True)
        try:
            logs = sb.table("call_logs").select("*").eq("business_id",bid).order("logged_at",desc=True).execute()
            if logs.data:
                ldf = pd.DataFrame(logs.data)
                ldf["logged_at"] = pd.to_datetime(ldf["logged_at"]).dt.strftime("%d %b %Y %H:%M")
                out = io.BytesIO()
                with pd.ExcelWriter(out,engine="openpyxl") as w:
                    ldf[["customer_name","risk_grade","outcome","logged_at"]].to_excel(w,index=False)
                st.download_button("⬇ Download Call Logs", out.getvalue(),
                    "call_logs_{}.xlsx".format(bid),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except: pass

# ════════════════════════════════════════════
#  PAGE 4 — PREDICT (Late Payment Predictor)
# ════════════════════════════════════════════
elif page == "predict":
    st.markdown('<div class="cp-section-header">Predict Late Payments</div>', unsafe_allow_html=True)

    if len(summary) == 0:
        st.info("No data yet. Add invoices from the ➕ tab.")
    else:
        tc = summary["Behaviour Trend"].value_counts()
        st.markdown("""
        <div class="cp-kpi-grid">
          <div class="cp-kpi">
            <div class="cp-kpi-label">Improving</div>
            <div class="cp-kpi-value" style="color:#00C278;">{}</div>
          </div>
          <div class="cp-kpi">
            <div class="cp-kpi-label">Stable</div>
            <div class="cp-kpi-value" style="color:#F5A623;">{}</div>
          </div>
          <div class="cp-kpi">
            <div class="cp-kpi-label">Worsening</div>
            <div class="cp-kpi-value" style="color:#E53E3E;">{}</div>
          </div>
          <div class="cp-kpi">
            <div class="cp-kpi-label">New</div>
            <div class="cp-kpi-value" style="color:var(--muted);">{}</div>
          </div>
        </div>
        """.format(
            tc.get("Improving",0), tc.get("Stable",0),
            tc.get("Worsening",0), tc.get("New",0)
        ), unsafe_allow_html=True)

        trend_cfg = {
            "Improving": ("#00C278","rgba(0,194,120,0.08)","rgba(0,194,120,0.2)","↑"),
            "Worsening": ("#E53E3E","rgba(229,62,62,0.08)","rgba(229,62,62,0.2)","↓"),
            "Stable":    ("#F5A623","rgba(245,166,35,0.08)","rgba(245,166,35,0.2)","→"),
            "New":       ("#8899AA","rgba(136,153,170,0.08)","rgba(136,153,170,0.2)","—"),
        }

        # Show worsening first
        ordered = pd.concat([
            summary[summary["Behaviour Trend"]=="Worsening"],
            summary[summary["Behaviour Trend"]=="Stable"],
            summary[summary["Behaviour Trend"]=="Improving"],
            summary[summary["Behaviour Trend"]=="New"],
        ])

        for _, row in ordered.iterrows():
            trend = row["Behaviour Trend"]
            color, bg, border, arrow = trend_cfg.get(trend, trend_cfg["New"])
            gr = row["Risk Grade"]

            st.markdown("""
            <div style="background:{};border:1px solid {};border-radius:14px;padding:14px 16px;margin-bottom:10px;">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
                <div style="font-weight:700;font-size:14px;color:var(--text);">{}</div>
                <span style="color:{};font-weight:700;font-size:13px;">{} {}</span>
              </div>
              <div style="font-size:13px;color:var(--text);margin-bottom:10px;">{}</div>
              <div style="display:flex;gap:16px;flex-wrap:wrap;">
                <span style="font-size:11px;color:var(--muted);">Grade: <b style="color:{};">{}</b></span>
                <span style="font-size:11px;color:var(--muted);">Avg delay: <b style="color:var(--text);">{}d</b></span>
                <span style="font-size:11px;color:var(--muted);">Recent: <b style="color:{};">{}d</b></span>
                <span style="font-size:11px;color:var(--muted);">Outstanding: <b style="color:{};">{}</b></span>
              </div>
            </div>
            """.format(
                bg, border,
                row["Customer"],
                color, arrow, trend,
                row["Behaviour Insight"],
                GRADE_META[gr]["color"], gr,
                row["Avg Delay(d)"],
                color, row["Recent Avg Delay"],
                GRADE_META[gr]["color"], fmt_full(row["Outstanding"])
            ), unsafe_allow_html=True)

# ════════════════════════════════════════════
#  PAGE 5 — ADD INVOICE
# ════════════════════════════════════════════
elif page == "add":
    st.markdown('<div class="cp-section-header">Add Invoice</div>', unsafe_allow_html=True)

    # Success message
    if st.session_state["form_success"]:
        st.success("✓ {} saved! Dashboard updated.".format(st.session_state["form_success"]))
        if st.button("➕ Add Another"):
            st.session_state["form_success"] = None
            st.rerun()
    else:
        # Customer name with hint
        if len(summary) > 0:
            existing = summary["Customer"].tolist()
            cust_opt = ["New customer..."] + existing
            cust_sel = st.selectbox("Customer", cust_opt)
            if cust_sel == "New customer...":
                f_cust = st.text_input("Customer Name", placeholder="e.g. Raju Kirana Stores")
            else:
                f_cust = cust_sel
        else:
            f_cust = st.text_input("Customer Name", placeholder="e.g. Raju Kirana Stores")

        f_inv  = st.text_input("Invoice Number", placeholder="e.g. INV-001")

        col1, col2 = st.columns(2)
        with col1:
            f_inv_date = st.date_input("Invoice Date", value=datetime.now().date())
        with col2:
            f_due_date = st.date_input("Due Date",
                value=(datetime.now() + pd.Timedelta(days=21)).date())

        f_amount = st.number_input("Invoice Amount (₹)", min_value=0.0, step=1000.0, format="%.0f")
        f_paid   = st.number_input("Paid Amount (₹)", min_value=0.0, step=1000.0, format="%.0f",
                                    help="Leave 0 if unpaid")

        f_paid_date = None
        if f_paid > 0:
            f_paid_date = st.date_input("Payment Date", value=datetime.now().date())

        # Live validation
        if f_amount > 0 and f_paid > f_amount:
            st.error("Paid amount cannot exceed invoice amount.")
        if f_due_date < f_inv_date:
            st.error("Due date cannot be before invoice date.")

        if st.button("💾 Save Invoice", use_container_width=True):
            errors = []
            if not f_cust.strip():   errors.append("Customer name required.")
            if not f_inv.strip():    errors.append("Invoice number required.")
            if f_amount <= 0:        errors.append("Amount must be greater than 0.")
            if f_paid > f_amount:    errors.append("Paid cannot exceed amount.")
            if f_due_date < f_inv_date: errors.append("Due date before invoice date.")

            if errors:
                for e in errors: st.error(e)
            else:
                row = {
                    "business_id":   bid,
                    "customer_name": f_cust.strip(),
                    "invoice_no":    f_inv.strip().upper(),
                    "invoice_date":  str(f_inv_date),
                    "due_date":      str(f_due_date),
                    "amount":        float(f_amount),
                    "paid_amount":   float(f_paid),
                    "payment_date":  str(f_paid_date) if f_paid_date and f_paid > 0 else None,
                }
                if save_invoice(bid, row):
                    st.cache_data.clear()
                    st.session_state["form_success"] = f_inv.strip().upper()
                    st.rerun()
                else:
                    st.error("Failed to save. Check your connection.")

st.markdown('</div>', unsafe_allow_html=True)
