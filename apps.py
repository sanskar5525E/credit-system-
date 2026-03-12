import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import io, os, re, json, hashlib

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="CreditPulse — Wholesale Risk Intelligence",
    layout="wide", page_icon="⚡"
)

# ══════════════════════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@700;800&family=Inter:wght@400;500;600&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.stApp{background:#060E18;color:#F0F4F8;}
header[data-testid="stHeader"]{background:transparent;}
section[data-testid="stSidebar"]{background:#0D1B2A !important;border-right:1px solid rgba(255,255,255,0.07);}
section[data-testid="stSidebar"] *{color:#C8D8E8 !important;}
[data-testid="metric-container"]{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:16px 20px;}
[data-testid="metric-container"] label{color:#8899AA !important;font-size:11px !important;letter-spacing:0.08em;text-transform:uppercase;}
[data-testid="metric-container"] [data-testid="stMetricValue"]{color:#F0F4F8 !important;font-family:'DM Mono',monospace !important;font-size:20px !important;}
.stButton>button{background:linear-gradient(135deg,#5B9EF4,#4A7EC4) !important;border:none !important;color:white !important;border-radius:10px !important;font-weight:600 !important;padding:10px 24px !important;}
[data-testid="stDataFrame"]{border-radius:12px;overflow:hidden;}
.stTabs [data-baseweb="tab-list"]{background:rgba(255,255,255,0.03);border-radius:10px;padding:4px;gap:4px;}
.stTabs [data-baseweb="tab"]{background:transparent;color:#8899AA;border-radius:8px;font-size:13px;font-weight:500;}
.stTabs [aria-selected="true"]{background:rgba(91,158,244,0.15) !important;color:#5B9EF4 !important;}
.stSelectbox>div>div,.stDateInput>div>div{background:rgba(255,255,255,0.05) !important;border:1px solid rgba(255,255,255,0.1) !important;border-radius:10px !important;color:#F0F4F8 !important;}
.streamlit-expanderHeader{background:rgba(255,255,255,0.04) !important;border-radius:10px !important;color:#C8D8E8 !important;}
[data-testid="stFileUploader"]{background:rgba(91,158,244,0.06);border:1px dashed rgba(91,158,244,0.3);border-radius:12px;padding:12px;}
.stDownloadButton>button{background:rgba(0,229,160,0.1) !important;border:1px solid rgba(0,229,160,0.3) !important;color:#00E5A0 !important;border-radius:10px !important;}
.stSuccess{background:rgba(0,229,160,0.1) !important;border:1px solid rgba(0,229,160,0.3) !important;border-radius:10px !important;}
.stInfo{background:rgba(91,158,244,0.1) !important;border:1px solid rgba(91,158,244,0.3) !important;border-radius:10px !important;}
.stWarning{background:rgba(255,140,66,0.1) !important;border:1px solid rgba(255,140,66,0.3) !important;border-radius:10px !important;}
.stError{background:rgba(255,56,96,0.1) !important;border:1px solid rgba(255,56,96,0.3) !important;border-radius:10px !important;}
input[type="password"],input[type="text"]{background:rgba(255,255,255,0.05) !important;border:1px solid rgba(255,255,255,0.1) !important;border-radius:10px !important;color:#F0F4F8 !important;}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
GRADE_META = {
    "A":{"color":"#00E5A0","rgba":"0,229,160",  "label":"Low Risk",      "action":"Increase Limit",   "call":"Thank & Reward Call",    "limit_mult":1.2},
    "B":{"color":"#FFD166","rgba":"255,209,102", "label":"Moderate Risk", "action":"Monitor Monthly",  "call":"Check-In Call",          "limit_mult":0.8},
    "C":{"color":"#FF8C42","rgba":"255,140,66",  "label":"High Risk",     "action":"Reduce Limit 50%", "call":"Payment Follow-Up Call", "limit_mult":0.5},
    "D":{"color":"#FF3860","rgba":"255,56,96",   "label":"Critical Risk", "action":"Suspend Credit",   "call":"Urgent Collection Call", "limit_mult":0.0},
}
CALL_SCRIPTS = {
    "A":"Hello {name}, we are calling to thank you for your outstanding payment record. As a valued customer, we are pleased to offer you an increased credit facility.",
    "B":"Hello {name}, this is a friendly check-in call. We noticed a few minor payment delays and want to ensure everything is running smoothly on your end.",
    "C":"Hello {name}, we are following up on overdue invoices totalling {amount}. We need to discuss an immediate payment arrangement to keep your account active.",
    "D":"Hello {name}, this is an urgent notice. Outstanding dues of {amount} have been flagged for suspension. Immediate payment is required to avoid legal escalation.",
}
OVERDUE_CAP  = 45
HISTORY_DIR  = "creditpulse_history"
CLIENTS_FILE = "creditpulse_clients.json"
# ── Change this to your own secret developer password ──
DEV_PASSWORD = "sanskar45"

os.makedirs(HISTORY_DIR, exist_ok=True)

# ══════════════════════════════════════════════════════════════════════════════
#  AUTH HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def hash_pw(pw):
    return hashlib.sha256(pw.strip().encode()).hexdigest()

def load_clients():
    if os.path.exists(CLIENTS_FILE):
        with open(CLIENTS_FILE,"r") as f:
            return json.load(f)
    # Default: empty client list
    return {}

def save_clients(clients):
    with open(CLIENTS_FILE,"w") as f:
        json.dump(clients, f, indent=2)

def client_login(business_id, password):
    """Returns (success, message)"""
    clients = load_clients()
    bid_upper = business_id.strip().upper()
    if bid_upper not in clients:
        return False, "Business ID not found. Contact your service provider."
    c = clients[bid_upper]
    if not c.get("active", False):
        return False, "Your account is deactivated. Contact your service provider."
    if hash_pw(password) != c["password_hash"]:
        return False, "Incorrect password."
    return True, "OK"

# ══════════════════════════════════════════════════════════════════════════════
#  HISTORY HELPERS  (BUG FIXED: keep="last" so updated payments win)
# ══════════════════════════════════════════════════════════════════════════════
def safe_bid(bid):
    return re.sub(r"[^a-zA-Z0-9_]","_", bid.strip().upper())

def history_path(bid):
    return os.path.join(HISTORY_DIR,"history_{}.csv".format(safe_bid(bid)))

def load_history(bid):
    path = history_path(bid)
    if os.path.exists(path):
        df = pd.read_csv(path)
        for c in ["invoice_date","due_date","payment_date"]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce")
        return df
    return pd.DataFrame()

def save_history(bid, df_new):
    """
    Append + deduplicate.
    BUG FIX: keep='last' so if paid_amount updated in new upload, it wins.
    Returns (final_df, new_rows, duplicates_updated)
    """
    path   = history_path(bid)
    df_new = df_new.copy()
    df_new["uploaded_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    if os.path.exists(path):
        df_old   = pd.read_csv(path)
        combined = pd.concat([df_old, df_new], ignore_index=True)
        before   = len(combined)
        # keep='last' → new upload overwrites old record for same invoice
        combined.drop_duplicates(subset=["customer_name","invoice_no"], keep="last", inplace=True)
        dupes    = before - len(combined)
        new_rows = len(df_new) - dupes
    else:
        combined = df_new.copy()
        dupes, new_rows = 0, len(df_new)

    combined.to_csv(path, index=False)
    return combined, new_rows, dupes

# ══════════════════════════════════════════════════════════════════════════════
#  UI HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def fmt(x):
    try:    return "Rs.{:,.0f}".format(float(x))
    except: return "Rs.0"

def card_html(gk, cnt):
    m = GRADE_META[gk]
    return (
        '<div style="background:rgba('+m["rgba"]+',0.08);border:1px solid '
        +m["color"]+'40;border-radius:14px;padding:16px;">'
        '<div style="color:'+m["color"]+';font-weight:700;font-size:15px;margin-bottom:6px">'
        'Grade '+gk+' &middot; '+str(cnt)+' customers</div>'
        '<div style="color:#C8D8E8;font-size:12px;margin-bottom:4px">&#128203; '+m["action"]+'</div>'
        '<div style="color:#C8D8E8;font-size:12px">&#128222; '+m["call"]+'</div></div>'
    )

def script_html(gk, script, out_str, overdue, action):
    m = GRADE_META[gk]
    return (
        '<div style="background:rgba('+m["rgba"]+',0.08);border:1px solid '
        +m["color"]+'40;border-radius:12px;padding:16px;margin-bottom:12px;">'
        '<div style="font-size:11px;color:'+m["color"]+';letter-spacing:0.1em;margin-bottom:8px">SUGGESTED SCRIPT</div>'
        '<div style="color:#C8D8E8;font-size:14px;line-height:1.7">'+str(script)+'</div></div>'
        '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;">'
        '<div style="background:rgba(255,255,255,0.04);border-radius:10px;padding:12px">'
        '<div style="font-size:10px;color:#8899AA">Outstanding</div>'
        '<div style="font-size:14px;font-weight:700;color:'+m["color"]+'">'+out_str+'</div></div>'
        '<div style="background:rgba(255,255,255,0.04);border-radius:10px;padding:12px">'
        '<div style="font-size:10px;color:#8899AA">Max Overdue</div>'
        '<div style="font-size:14px;font-weight:700;color:#C8D8E8">'+str(int(overdue))+' days</div></div>'
        '<div style="background:rgba(255,255,255,0.04);border-radius:10px;padding:12px">'
        '<div style="font-size:10px;color:#8899AA">Credit Action</div>'
        '<div style="font-size:13px;font-weight:600;color:#C8D8E8">'+str(action)+'</div></div></div>'
    )

def trend_badge(trend):
    cfg = {
        "Improving":("#00E5A0","0,229,160","&#8593; Improving"),
        "Worsening":("#FF3860","255,56,96","&#8595; Worsening"),
        "Stable":   ("#FFD166","255,209,102","&#8594; Stable"),
        "New":      ("#8899AA","136,153,170","&#8212; New / Low Data"),
    }
    c,rgba,label = cfg.get(trend, cfg["New"])
    return '<span style="background:rgba('+rgba+',0.15);color:'+c+';padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600">'+label+'</span>'

# ══════════════════════════════════════════════════════════════════════════════
#  DATA
# ══════════════════════════════════════════════════════════════════════════════
def generate_example_data():
    np.random.seed(42)
    customers = ["Apex Retail Ltd","BlueStar Merchants","Cosmo Distributors",
                 "Delta Traders","Echo Enterprises","Frontier Goods","Global Mart","Horizon Shops"]
    data, today = [], pd.Timestamp("2026-01-01")
    for cust in customers:
        for i in range(int(np.random.randint(5,12))):
            inv_date = today - pd.Timedelta(days=int(np.random.randint(10,300)))
            due_date = inv_date + pd.Timedelta(days=21)
            amount   = int(np.random.randint(2000,40000))
            r        = float(np.random.rand())
            if r<0.3:   paid=amount; pay_date=due_date-pd.Timedelta(days=int(np.random.randint(1,5)))
            elif r<0.6: paid=amount; pay_date=due_date+pd.Timedelta(days=int(np.random.randint(5,40)))
            elif r<0.8: paid=round(amount*float(np.random.uniform(0.2,0.8))); pay_date=due_date+pd.Timedelta(days=int(np.random.randint(0,60)))
            else:       paid=0; pay_date=pd.NaT
            data.append({"customer_name":cust,"invoice_no":"INV-{}-{}".format(cust[:3].upper(),i),
                          "invoice_date":inv_date,"due_date":due_date,
                          "amount":amount,"paid_amount":round(paid),"payment_date":pay_date})
    return pd.DataFrame(data)

def clean_data(df):
    df = df.copy()
    # Drop computed/meta columns before cleaning
    drop_cols = ["outstanding","fully_paid","overdue_days","paid_late","uploaded_at"]
    df.drop(columns=[c for c in drop_cols if c in df.columns], inplace=True)
    df.columns = df.columns.str.lower().str.strip().str.replace(" ","_")
    for col in ["customer_name","invoice_no","invoice_date","due_date","amount","paid_amount"]:
        if col not in df.columns:
            st.error("Missing column: {}".format(col)); st.stop()
    for c in ["invoice_date","due_date","payment_date"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    df["amount"]      = pd.to_numeric(df["amount"],      errors="coerce").fillna(0)
    df["paid_amount"] = pd.to_numeric(df["paid_amount"], errors="coerce").fillna(0)
    if "payment_date" not in df.columns:
        df["payment_date"] = pd.NaT
    return df[df["amount"]>0].copy()

def calc_metrics(df, today):
    df = df.copy()
    df["outstanding"]  = (df["amount"]-df["paid_amount"]).clip(lower=0)
    df["fully_paid"]   = df["paid_amount"]>=df["amount"]
    df["overdue_days"] = 0
    df["paid_late"]    = False
    mask_unpaid = (df["outstanding"]>0)&(df["due_date"]<today)
    df.loc[mask_unpaid,"overdue_days"] = (today-df.loc[mask_unpaid,"due_date"]).dt.days.astype(int)
    mask_late = df["fully_paid"]&df["payment_date"].notna()&(df["payment_date"]>df["due_date"])
    df.loc[mask_late,"overdue_days"] = (df.loc[mask_late,"payment_date"]-df.loc[mask_late,"due_date"]).dt.days.astype(int)
    df.loc[mask_late,"paid_late"] = True
    df["overdue_days"] = df["overdue_days"].clip(lower=0,upper=180)
    return df

def predict_behaviour(inv_df):
    paid = inv_df[inv_df["fully_paid"]==True].copy().sort_values("invoice_date")
    if len(paid)<3:
        return "New",0,"Not enough history to predict payment behaviour."
    mid     = len(paid)//2
    delta   = paid.iloc[mid:]["overdue_days"].mean() - paid.iloc[:mid]["overdue_days"].mean()
    last3   = paid.tail(3)["overdue_days"].mean()
    overall = paid["overdue_days"].mean()
    if delta>5 or last3>overall*1.3:
        return "Worsening",round(last3,1),"Likely to delay next payment by {:.0f}+ days. Reduce credit limit proactively.".format(max(last3,paid.iloc[mid:]["overdue_days"].mean()))
    elif delta<-5 or last3<overall*0.7:
        return "Improving",round(last3,1),"Payment behaviour improving. Average delay reduced to {:.0f} days recently.".format(last3)
    else:
        return "Stable",round(last3,1),"Consistent payment pattern. Average delay is {:.0f} days.".format(overall)

def calc_ageing(df):
    df = df[df["outstanding"]>0].copy()
    def bucket(d):
        if d<=0:    return "Current"
        elif d<=15: return "1-15 days"
        elif d<=30: return "16-30 days"
        elif d<=45: return "31-45 days"
        else:       return "45+ days"
    df["bucket"] = df["overdue_days"].apply(bucket)
    order = ["Current","1-15 days","16-30 days","31-45 days","45+ days"]
    ag    = df.groupby(["customer_name","bucket"])["outstanding"].sum().reset_index()
    pivot = ag.pivot(index="customer_name",columns="bucket",values="outstanding").fillna(0)
    for col in order:
        if col not in pivot.columns: pivot[col]=0
    pivot = pivot[order].reset_index()
    pivot["Total Outstanding"] = pivot[order].sum(axis=1)
    return pivot

def score_customer(row):
    od  = min(row["max_overdue"]/OVERDUE_CAP,1)*40
    ou  = (row["total_outstanding"]/row["total_amount"])*40 if row["total_amount"]>0 else 0
    pr  = row["total_paid"]/row["total_amount"] if row["total_amount"]>0 else 0
    lr  = row["late_count"]/row["paid_count"]   if row["paid_count"]>0   else 1
    return min(round(od+ou+min((1-pr)*10+lr*10,20)),100)

def get_grade(s):
    return "A" if s<=10 else "B" if s<=30 else "C" if s<=55 else "D"

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
    """BUG FIX: always process from raw, never from df_inv"""
    clean = clean_data(raw_df)
    inv   = calc_metrics(clean, today)
    summ  = aggregate(inv)
    age   = calc_ageing(inv)
    return inv, summ, age

def stepper(active):
    stages = ["① INPUT","② PROCESS","③ OUTPUT","④ ACTION"]
    cols   = st.columns(4)
    for i,(col,s) in enumerate(zip(cols,stages)):
        if i<active:    c,bg="#00E5A0","rgba(0,229,160,0.08)"
        elif i==active: c,bg="#5B9EF4","rgba(91,158,244,0.1)"
        else:           c,bg="#2D3F52","transparent"
        col.markdown('<div style="text-align:center;padding:10px;background:'+bg+';border-radius:10px;border:1px solid '+c+'40;color:'+c+';font-size:12px;font-weight:600">'+s+'</div>',unsafe_allow_html=True)
    st.markdown("<div style='height:16px'/>",unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
defaults = {
    "authenticated":False, "is_dev":False,
    "business_id":None,    "df_raw":None,
    "df_inv":None,         "summary":None,
    "ageing":None,         "today_cached":None,
}
for k,v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════════════════
#  HEADER (always visible)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="padding:12px 0 24px;position:relative;">
  <div style="position:absolute;top:0;left:0;right:0;height:3px;
    background:linear-gradient(90deg,#5B9EF4,#00E5A0,#FFD166,#FF3860);
    border-radius:2px;opacity:0.7;"></div>
  <div style="padding-top:16px;display:inline-flex;align-items:center;gap:12px;
    background:linear-gradient(135deg,rgba(91,158,244,0.1),rgba(0,229,160,0.06));
    border:1px solid rgba(91,158,244,0.2);border-radius:16px;padding:10px 20px;">
    <span style="font-size:24px;">&#9889;</span>
    <span style="font-family:'Syne',sans-serif;font-size:26px;font-weight:800;letter-spacing:-0.03em;
      background:linear-gradient(135deg,#5B9EF4 0%,#00E5A0 60%,#FFD166 100%);
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">CreditPulse</span>
    <span style="width:1px;height:20px;background:rgba(255,255,255,0.15);"></span>
    <span style="font-size:12px;color:#8899AA;letter-spacing:0.06em;">WHOLESALE RISK INTELLIGENCE</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  LOGIN SCREEN  (shown when not authenticated)
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state["authenticated"]:

    st.markdown("<div style='height:20px'/>",unsafe_allow_html=True)
    lcol, _, rcol = st.columns([1,0.1,1])

    # ── Client Login ──────────────────────────────────────────────────────────
    with lcol:
        st.markdown("""
        <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);
          border-radius:16px;padding:28px;">
          <div style="font-size:18px;font-weight:700;color:#F0F4F8;margin-bottom:4px">&#128100; Client Login</div>
          <div style="font-size:12px;color:#8899AA;margin-bottom:20px">Enter your Business ID and password provided by your service provider.</div>
        </div>
        """, unsafe_allow_html=True)
        c_bid = st.text_input("Business ID", placeholder="e.g. RAJ_TRADERS", key="login_bid")
        c_pw  = st.text_input("Password",    type="password", key="login_pw")
        if st.button("Login", use_container_width=True, key="client_login_btn"):
            if c_bid.strip() and c_pw.strip():
                ok, msg = client_login(c_bid, c_pw)
                if ok:
                    st.session_state["authenticated"] = True
                    st.session_state["is_dev"]        = False
                    st.session_state["business_id"]   = c_bid.strip().upper()
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("Please enter both Business ID and password.")

    # ── Developer Login ───────────────────────────────────────────────────────
    with rcol:
        st.markdown("""
        <div style="background:rgba(91,158,244,0.05);border:1px solid rgba(91,158,244,0.15);
          border-radius:16px;padding:28px;">
          <div style="font-size:18px;font-weight:700;color:#5B9EF4;margin-bottom:4px">&#9881; Developer Panel</div>
          <div style="font-size:12px;color:#8899AA;margin-bottom:20px">Admin access to manage clients and view all accounts.</div>
        </div>
        """, unsafe_allow_html=True)
        d_pw = st.text_input("Developer Password", type="password", key="dev_pw")
        if st.button("Enter Dev Panel", use_container_width=True, key="dev_login_btn"):
            if hash_pw(d_pw) == hash_pw(DEV_PASSWORD):
                st.session_state["authenticated"] = True
                st.session_state["is_dev"]        = True
                st.session_state["business_id"]   = "__DEV__"
                st.rerun()
            else:
                st.error("Wrong developer password.")

    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
#  DEVELOPER PANEL
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state["is_dev"]:

    st.markdown("### ⚙️ Developer Panel")
    st.caption("Manage client accounts, passwords, and access.")

    if st.button("Logout", key="dev_logout"):
        for k,v in defaults.items(): st.session_state[k]=v
        st.rerun()

    clients = load_clients()

    dev_tab1, dev_tab2, dev_tab3 = st.tabs(["👥 All Clients","➕ Add Client","📊 Storage Overview"])

    # ── All Clients ───────────────────────────────────────────────────────────
    with dev_tab1:
        if not clients:
            st.info("No clients added yet. Use Add Client tab.")
        else:
            st.markdown("**{} registered clients**".format(len(clients)))
            for bid, info in clients.items():
                hist   = load_history(bid)
                active = info.get("active", False)
                status_color  = "#00E5A0" if active else "#FF3860"
                status_label  = "Active" if active else "Deactivated"
                c1,c2,c3,c4 = st.columns([3,2,2,2])
                with c1:
                    st.markdown(
                        '<div style="padding:12px;background:rgba(255,255,255,0.03);border-radius:10px;border:1px solid rgba(255,255,255,0.07);">'
                        '<div style="font-weight:700;color:#C8D8E8;">'+bid+'</div>'
                        '<div style="font-size:11px;color:#8899AA;">Added: '+info.get("added","—")+'</div>'
                        '</div>', unsafe_allow_html=True)
                with c2:
                    st.markdown('<div style="padding:12px;"><span style="color:'+status_color+';font-size:12px;font-weight:600;">&#9679; '+status_label+'</span></div>',unsafe_allow_html=True)
                with c3:
                    st.markdown('<div style="padding:12px;font-size:12px;color:#8899AA;">{:,} invoice rows</div>'.format(len(hist)),unsafe_allow_html=True)
                with c4:
                    tog_label = "Deactivate" if active else "Activate"
                    if st.button(tog_label, key="tog_{}".format(bid)):
                        clients[bid]["active"] = not active
                        save_clients(clients)
                        st.rerun()
                    if st.button("Reset PW", key="rpw_{}".format(bid)):
                        st.session_state["reset_pw_target"] = bid

            # Password reset inline
            if st.session_state.get("reset_pw_target"):
                target = st.session_state["reset_pw_target"]
                st.markdown("---")
                st.markdown("**Reset password for: {}**".format(target))
                new_pw = st.text_input("New Password", type="password", key="new_pw_input")
                if st.button("Confirm Reset"):
                    if new_pw.strip():
                        clients[target]["password_hash"] = hash_pw(new_pw)
                        save_clients(clients)
                        st.session_state["reset_pw_target"] = None
                        st.success("Password reset for {}.".format(target))
                        st.rerun()
                    else:
                        st.error("Password cannot be empty.")

    # ── Add Client ────────────────────────────────────────────────────────────
    with dev_tab2:
        st.markdown("**Add a new client**")
        st.caption("The client will use this Business ID and password to log in.")
        n_bid  = st.text_input("Business ID", placeholder="e.g. RAJ_TRADERS", key="new_bid")
        n_name = st.text_input("Business Name (display)", placeholder="Rajan Traders, Nagpur", key="new_name")
        n_pw   = st.text_input("Password", type="password", key="new_pw")
        if st.button("Add Client", use_container_width=True):
            if n_bid.strip() and n_pw.strip():
                bid_clean = n_bid.strip().upper()
                if bid_clean in clients:
                    st.error("Business ID already exists.")
                else:
                    clients[bid_clean] = {
                        "display_name":  n_name.strip() or bid_clean,
                        "password_hash": hash_pw(n_pw),
                        "active":        True,
                        "added":         datetime.now().strftime("%Y-%m-%d"),
                    }
                    save_clients(clients)
                    st.success("Client **{}** added successfully. Share the Business ID and password with them.".format(bid_clean))
                    st.rerun()
            else:
                st.error("Business ID and Password are required.")

    # ── Storage Overview ──────────────────────────────────────────────────────
    with dev_tab3:
        st.markdown("**All history files on server**")
        files = [f for f in os.listdir(HISTORY_DIR) if f.endswith(".csv")]
        if not files:
            st.info("No history files yet.")
        else:
            total_rows = 0
            for f in sorted(files):
                fpath = os.path.join(HISTORY_DIR,f)
                df_tmp = pd.read_csv(fpath)
                total_rows += len(df_tmp)
                bid_name = f.replace("history_","").replace(".csv","")
                st.markdown(
                    '<div style="display:flex;justify-content:space-between;padding:10px 14px;'
                    'background:rgba(255,255,255,0.03);border-radius:8px;margin-bottom:6px;">'
                    '<span style="color:#C8D8E8;font-size:13px;">'+bid_name+'</span>'
                    '<span style="color:#8899AA;font-size:12px;">{:,} rows &nbsp;·&nbsp; {:.1f} KB</span>'.format(len(df_tmp), os.path.getsize(fpath)/1024)+
                    '</div>', unsafe_allow_html=True)
            st.markdown("---")
            st.metric("Total rows across all clients", "{:,}".format(total_rows))

    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR  (client view)
# ══════════════════════════════════════════════════════════════════════════════
bid = st.session_state["business_id"]
clients = load_clients()
display_name = clients.get(bid,{}).get("display_name", bid)

with st.sidebar:
    st.markdown("### ⚡ CreditPulse")
    st.markdown("---")
    st.markdown('<span style="color:#00E5A0;font-size:12px;">&#9679; Logged in</span>', unsafe_allow_html=True)
    st.markdown("**{}**".format(display_name))
    st.caption("ID: {}".format(bid))
    if st.button("Logout", use_container_width=True):
        for k,v in defaults.items(): st.session_state[k]=v
        st.rerun()
    st.markdown("---")

    today_input = st.date_input("📅 Calculation Date", value=datetime.now().date())
    today = pd.Timestamp(today_input)

    # BUG FIX: reprocess from df_raw, not from df_inv
    if st.session_state["today_cached"] != str(today) and st.session_state["df_raw"] is not None:
        inv, summ, age = process_all(st.session_state["df_raw"], today)
        st.session_state["df_inv"]       = inv
        st.session_state["summary"]      = summ
        st.session_state["ageing"]       = age
        st.session_state["today_cached"] = str(today)

    st.markdown("---")
    st.markdown("**Risk Grade Legend**")
    for gk,m in GRADE_META.items():
        st.markdown('<span style="color:'+m["color"]+'">&#9632;</span> **Grade '+gk+'** — '+m["label"],unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("**Scoring — FMCG India**")
    st.caption("Overdue cap: 45 days\nOverdue: 40 pts · Outstanding: 40 pts · Behaviour: 20 pts")
    st.markdown("---")
    hist_rows = len(load_history(bid))
    if hist_rows>0:
        st.caption("Saved history: {:,} invoice rows".format(hist_rows))
    if st.button("🔄 Reset / Load New Data", use_container_width=True):
        for k in ["df_raw","df_inv","summary","ageing","today_cached"]:
            st.session_state[k]=None
        st.rerun()
    template = pd.DataFrame({
        "customer_name":["ABC Stores"],"invoice_no":["INV001"],
        "invoice_date":["2026-01-01"],"due_date":["2026-01-21"],
        "amount":[10000],"paid_amount":[5000],"payment_date":["2026-02-05"]
    })
    st.download_button("📄 Download Template",template.to_csv(index=False),"template.csv",use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
#  INPUT
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state["summary"] is None:
    stepper(0)
    existing = load_history(bid)

    if len(existing)>0:
        st.info("**History found** — {:,} invoice rows saved. Upload new data to update, or use saved history.".format(len(existing)))
        if st.button("📂 Use Saved History"):
            inv,summ,age = process_all(existing, today)
            st.session_state.update({"df_raw":existing,"df_inv":inv,"summary":summ,
                                      "ageing":age,"today_cached":str(today)})
            st.rerun()

    c1,c2 = st.columns([2,1])
    with c1:
        uploaded = st.file_uploader("Upload Invoice File (CSV or Excel)", type=["csv","xlsx"])
    with c2:
        st.markdown("<div style='height:28px'/>",unsafe_allow_html=True)
        use_example = st.button("🧪 Use Example Data", use_container_width=True)

    if uploaded:
        raw = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
        with st.spinner("Saving and processing..."):
            cleaned      = clean_data(raw)
            full,new,dup = save_history(bid, cleaned)
            st.success("{} new rows added · {} updated · {:,} total history rows.".format(new,dup,len(full)))
            inv,summ,age = process_all(full, today)
            st.session_state.update({"df_raw":full,"df_inv":inv,"summary":summ,
                                      "ageing":age,"today_cached":str(today)})
        st.rerun()

    elif use_example:
        raw = generate_example_data()
        with st.spinner("Processing example data..."):
            inv,summ,age = process_all(raw, today)
            st.session_state.update({"df_raw":raw,"df_inv":inv,"summary":summ,
                                      "ageing":age,"today_cached":str(today)})
        st.rerun()

    elif len(existing)==0:
        st.markdown(
            '<div style="text-align:center;padding:60px 20px;">'
            '<div style="font-size:52px;margin-bottom:16px">&#128194;</div>'
            '<div style="font-size:20px;font-weight:600;color:#8899AA;margin-bottom:8px">No data yet</div>'
            '<div style="font-size:13px;color:#4A5568">Upload a CSV / Excel or click Use Example Data.</div>'
            '</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
else:
    summary = st.session_state["summary"]
    df_inv  = st.session_state["df_inv"]
    ageing  = st.session_state["ageing"]

    stepper(3)

    # KPIs
    k1,k2,k3,k4,k5 = st.columns(5)
    k1.metric("Customers",    str(len(summary)))
    k2.metric("Total Credit", fmt(summary["Total Credit"].sum()))
    k3.metric("Total Paid",   fmt(summary["Total Paid"].sum()))
    k4.metric("Outstanding",  fmt(summary["Outstanding"].sum()))
    k5.metric("Critical (D)", str(int((summary["Risk Grade"]=="D").sum())), delta="Immediate action needed", delta_color="inverse")
    st.markdown("<div style='height:16px'/>",unsafe_allow_html=True)

    # Charts
    ch1,ch2 = st.columns([1,2])
    with ch1:
        st.markdown("**Risk Grade Breakdown**")
        gc = summary["Risk Grade"].value_counts().reindex(["A","B","C","D"],fill_value=0)
        for gk,cnt in gc.items():
            m  = GRADE_META[gk]
            pv = round((cnt/len(summary))*100) if len(summary)>0 else 0
            st.markdown(
                '<div style="margin-bottom:12px;">'
                '<div style="display:flex;justify-content:space-between;margin-bottom:4px;">'
                '<span style="color:'+m["color"]+';font-weight:600;font-size:13px">Grade '+gk+' — '+m["label"]+'</span>'
                '<span style="color:#8899AA;font-size:12px">'+str(cnt)+' ('+str(pv)+'%)</span></div>'
                '<div style="background:rgba(255,255,255,0.06);border-radius:6px;height:10px;">'
                '<div style="width:'+str(max(pv,2))+'%;background:'+m["color"]+';height:10px;border-radius:6px;"></div>'
                '</div></div>', unsafe_allow_html=True)

    with ch2:
        st.markdown("**Outstanding Amount by Customer**")
        bar_df = summary[["Customer","Outstanding","Risk Grade"]].copy().sort_values("Outstanding",ascending=True)
        fig    = go.Figure()
        for gk in ["A","B","C","D"]:
            sub = bar_df[bar_df["Risk Grade"]==gk]
            if len(sub)==0: continue
            fig.add_trace(go.Bar(x=sub["Outstanding"],y=sub["Customer"],orientation="h",
                name="Grade "+gk, marker_color=GRADE_META[gk]["color"],
                text=sub["Outstanding"].apply(lambda v:"Rs.{:,.0f}".format(v)),
                textposition="outside",textfont=dict(size=10,color="#C8D8E8")))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
            font_color="#C8D8E8",barmode="overlay",
            legend=dict(font=dict(color="#C8D8E8"),orientation="h",y=-0.08),
            margin=dict(t=10,b=50,l=10,r=110),
            height=max(300,len(bar_df)*28+60),
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)",tickformat=",.0f",title=""),
            yaxis=dict(gridcolor="rgba(0,0,0,0)",title="",automargin=True,tickfont=dict(size=11)))
        st.plotly_chart(fig,use_container_width=True)

    st.markdown("---")
    rc = st.columns(4)
    for col,(gk,m) in zip(rc,GRADE_META.items()):
        col.markdown(card_html(gk,int((summary["Risk Grade"]==gk).sum())),unsafe_allow_html=True)
    st.markdown("<div style='height:20px'/>",unsafe_allow_html=True)

    grade_filter = st.selectbox("Filter by Risk Grade",["ALL","A","B","C","D"])
    filtered = summary.copy() if grade_filter=="ALL" else summary[summary["Risk Grade"]==grade_filter].copy()
    st.caption("Showing {} of {} customers".format(len(filtered),len(summary)))

    tab_risk,tab_beh,tab_call,tab_age,tab_inv,tab_hist = st.tabs([
        "📊 Risk Analysis","🔮 Behaviour Predictor",
        "📞 Call Table","📅 Ageing Report",
        "🧾 Invoice Detail","📁 History",
    ])

    # ── Risk Analysis ──────────────────────────────────────────────────────────
    with tab_risk:
        disp = filtered[["Customer","Invoices","Risk Score","Risk Grade","Grade Label",
                          "Total Credit","Total Paid","Outstanding","Max Overdue(d)",
                          "Avg Delay(d)","Suggested Limit","Credit Action","Behaviour Trend"]].copy()
        for c in ["Total Credit","Total Paid","Outstanding","Suggested Limit"]:
            disp[c] = disp[c].apply(fmt)
        st.dataframe(disp,use_container_width=True,hide_index=True,
            column_config={
                "Risk Score":      st.column_config.ProgressColumn("Score",min_value=0,max_value=100,format="%d"),
                "Risk Grade":      st.column_config.TextColumn("Grade",width="small"),
                "Max Overdue(d)":  st.column_config.NumberColumn("Max Overdue",format="%d days"),
                "Avg Delay(d)":    st.column_config.NumberColumn("Avg Delay",format="%.1f days"),
                "Invoices":        st.column_config.NumberColumn("Invoices",format="%d"),
                "Behaviour Trend": st.column_config.TextColumn("Trend"),
            })
        out = io.BytesIO()
        with pd.ExcelWriter(out,engine="openpyxl") as w:
            summary.to_excel(w,sheet_name="Customer Risk",index=False)
            df_inv.to_excel(w, sheet_name="Invoice Data", index=False)
            ageing.to_excel(w, sheet_name="Ageing Report",index=False)
        st.download_button("⬇ Download Full Excel Report",out.getvalue(),"credit_risk_report.xlsx")

    # ── Behaviour Predictor ────────────────────────────────────────────────────
    with tab_beh:
        st.markdown("### 🔮 Payment Behaviour Predictor")
        st.caption("Analyses full invoice history per customer. More history = more accurate predictions.")
        tc1,tc2,tc3,tc4 = st.columns(4)
        tc = filtered["Behaviour Trend"].value_counts()
        tc1.metric("Improving",      str(tc.get("Improving",0)), delta="Good trend")
        tc2.metric("Stable",         str(tc.get("Stable",0)))
        tc3.metric("Worsening",      str(tc.get("Worsening",0)), delta="Watch these", delta_color="inverse")
        tc4.metric("New / Low Data", str(tc.get("New",0)))
        st.markdown("<div style='height:12px'/>",unsafe_allow_html=True)
        for _,row in filtered.iterrows():
            m      = GRADE_META[row["Risk Grade"]]
            tc_clr = "#00E5A0" if row["Behaviour Trend"]=="Improving" else "#FF3860" if row["Behaviour Trend"]=="Worsening" else "#FFD166" if row["Behaviour Trend"]=="Stable" else "#8899AA"
            st.markdown(
                '<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:16px;margin-bottom:10px;">'
                '<div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">'
                '<div style="font-weight:700;color:#C8D8E8;font-size:14px;">'+str(row["Customer"])+'</div>'
                +trend_badge(row["Behaviour Trend"])+
                '<div style="margin-left:auto;font-size:12px;color:'+m["color"]+'">Grade '+row["Risk Grade"]+'</div></div>'
                '<div style="font-size:13px;color:#C8D8E8;margin-bottom:10px;">'+row["Behaviour Insight"]+'</div>'
                '<div style="display:flex;gap:20px;">'
                '<span style="font-size:11px;color:#8899AA">Overall avg delay: <b style="color:#C8D8E8">'+str(row["Avg Delay(d)"])+'d</b></span>'
                '<span style="font-size:11px;color:#8899AA">Recent avg delay: <b style="color:'+tc_clr+'">'+str(row["Recent Avg Delay"])+'d</b></span>'
                '<span style="font-size:11px;color:#8899AA">Outstanding: <b style="color:'+m["color"]+'">'+fmt(row["Outstanding"])+'</b></span>'
                '</div></div>', unsafe_allow_html=True)

    # ── Call Table ─────────────────────────────────────────────────────────────
    with tab_call:
        cd = filtered[["Customer","Risk Grade","Outstanding","Max Overdue(d)","Call Type","Credit Action","Call Script"]].copy()
        cd.insert(0,"Priority",range(1,len(cd)+1))
        cd["Outstanding"]    = cd["Outstanding"].apply(fmt)
        cd["Max Overdue(d)"] = cd["Max Overdue(d)"].apply(lambda x:"{} days".format(int(x)) if x>0 else "On time")
        st.dataframe(cd,use_container_width=True,hide_index=True,
            column_config={
                "Priority":   st.column_config.NumberColumn("#",width="small"),
                "Risk Grade": st.column_config.TextColumn("Grade",width="small"),
                "Call Script":st.column_config.TextColumn("Script",width="large"),
            })
        st.markdown("---")
        st.markdown("### Call Scripts & Outcome Logger")
        for _,row in filtered.iterrows():
            gk = row["Risk Grade"]
            with st.expander("{} | {} | {} | {}".format(gk,row["Customer"],row["Call Type"],fmt(row["Outstanding"]))):
                st.markdown(script_html(gk,row["Call Script"],fmt(row["Outstanding"]),row["Max Overdue(d)"],row["Credit Action"]),unsafe_allow_html=True)
                outcome = st.selectbox("Call Outcome",["Select outcome","Contacted","No Answer","Promise to Pay","Disputed","Paid in Full"],key="out_{}".format(row["Customer"]))
                st.text_area("Call Notes",placeholder="Notes...",key="note_{}".format(row["Customer"]),height=70)
                if st.button("Save Call Log",key="log_{}".format(row["Customer"])):
                    st.success("Logged for {} — {}".format(row["Customer"],outcome))
        ce = filtered[["Customer","Risk Grade","Outstanding","Max Overdue(d)","Call Type","Credit Action"]].copy()
        ce["Outstanding"] = ce["Outstanding"].apply(fmt)
        st.download_button("⬇ Export Call List",ce.to_csv(index=False),"call_list.csv")

    # ── Ageing ─────────────────────────────────────────────────────────────────
    with tab_age:
        st.markdown("### Ageing Report")
        st.caption("FMCG India buckets: Current / 1-15 / 16-30 / 31-45 / 45+ days")
        ad = ageing.copy()
        for c in ["Current","1-15 days","16-30 days","31-45 days","45+ days","Total Outstanding"]:
            if c in ad.columns: ad[c]=ad[c].apply(fmt)
        ad.rename(columns={"customer_name":"Customer"},inplace=True)
        st.dataframe(ad,use_container_width=True,hide_index=True)
        buckets = ["Current","1-15 days","16-30 days","31-45 days","45+ days"]
        melt    = ageing.melt(id_vars="customer_name",value_vars=buckets,var_name="Bucket",value_name="Amount")
        colors  = {"Current":"#8899AA","1-15 days":"#FFD166","16-30 days":"#FF8C42","31-45 days":"#FF5733","45+ days":"#FF3860"}
        fig_age = go.Figure()
        for b in buckets:
            sub = melt[melt["Bucket"]==b]
            fig_age.add_trace(go.Bar(x=sub["customer_name"],y=sub["Amount"],name=b,marker_color=colors[b]))
        fig_age.update_layout(barmode="stack",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
            font_color="#C8D8E8",legend=dict(font=dict(color="#C8D8E8"),orientation="h",y=-0.2),
            xaxis=dict(tickangle=-20,gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            margin=dict(t=10,b=60,l=0,r=0),height=max(320,len(ageing)*28+80))
        st.plotly_chart(fig_age,use_container_width=True)
        st.download_button("⬇ Export Ageing Report",ageing.to_csv(index=False),"ageing_report.csv")

    # ── Invoice Detail ─────────────────────────────────────────────────────────
    with tab_inv:
        st.markdown("### Customer Invoice Detail")
        sel      = st.selectbox("Select Customer",summary["Customer"].tolist(),key="inv_cust")
        cust_inv = df_inv[df_inv["customer_name"]==sel].copy()
        cust_row = summary[summary["Customer"]==sel].iloc[0]
        m        = GRADE_META[cust_row["Risk Grade"]]
        ic1,ic2,ic3,ic4,ic5 = st.columns(5)
        ic1.metric("Risk Grade",     "{} — {}".format(cust_row["Risk Grade"],cust_row["Grade Label"]))
        ic2.metric("Risk Score",     str(cust_row["Risk Score"]))
        ic3.metric("Total Invoices", str(cust_row["Invoices"]))
        ic4.metric("Outstanding",    fmt(cust_row["Outstanding"]))
        ic5.metric("Suggested Limit",fmt(cust_row["Suggested Limit"]))
        paid_pct = round((float(cust_row["Total Paid"])/float(cust_row["Total Credit"]))*100) if cust_row["Total Credit"]>0 else 0
        st.markdown(
            '<div style="margin:12px 0 16px;"><div style="display:flex;justify-content:space-between;margin-bottom:4px;">'
            '<span style="color:#8899AA;font-size:12px">Payment Progress</span>'
            '<span style="color:#C8D8E8;font-size:12px">'+str(paid_pct)+'% paid</span></div>'
            '<div style="background:rgba(255,56,96,0.25);border-radius:6px;height:8px;">'
            '<div style="width:'+str(paid_pct)+'%;background:#00E5A0;height:8px;border-radius:6px;"></div>'
            '</div></div>', unsafe_allow_html=True)
        trend  = cust_row["Behaviour Trend"]
        tc_clr = "#00E5A0" if trend=="Improving" else "#FF3860" if trend=="Worsening" else "#FFD166" if trend=="Stable" else "#8899AA"
        st.markdown(
            '<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);'
            'border-radius:10px;padding:14px;margin-bottom:16px;display:flex;align-items:center;gap:12px;">'
            +trend_badge(trend)+
            '<div style="font-size:13px;color:#C8D8E8;">'+cust_row["Behaviour Insight"]+'</div></div>',
            unsafe_allow_html=True)
        id_ = cust_inv[["invoice_no","invoice_date","due_date","amount","paid_amount","outstanding","overdue_days","paid_late","fully_paid"]].copy()
        id_.columns = ["Invoice","Invoice Date","Due Date","Amount","Paid","Outstanding","Overdue(d)","Paid Late","Fully Paid"]
        for c in ["Amount","Paid","Outstanding"]: id_[c]=id_[c].apply(fmt)
        st.dataframe(id_,use_container_width=True,hide_index=True,
            column_config={
                "Overdue(d)": st.column_config.NumberColumn("Overdue",format="%d days"),
                "Paid Late":  st.column_config.CheckboxColumn("Paid Late"),
                "Fully Paid": st.column_config.CheckboxColumn("Fully Paid"),
            })
        st.download_button("⬇ Export {}'s Invoices".format(sel),cust_inv.to_csv(index=False),"{}_invoices.csv".format(sel.replace(" ","_")))

    # ── History ────────────────────────────────────────────────────────────────
    with tab_hist:
        st.markdown("### 📁 My Invoice History")
        hist_df = load_history(bid)
        if len(hist_df)==0:
            st.info("No history saved yet.")
        else:
            h1,h2,h3 = st.columns(3)
            h1.metric("Total Invoice Rows", "{:,}".format(len(hist_df)))
            h2.metric("Unique Customers",   str(hist_df["customer_name"].nunique()))
            earliest = pd.to_datetime(hist_df["invoice_date"],errors="coerce").min()
            h3.metric("Earliest Invoice",   str(earliest.date()) if pd.notna(earliest) else "—")
            with st.expander("Preview first 50 rows"):
                st.dataframe(hist_df.head(50),use_container_width=True,hide_index=True)
            st.download_button("⬇ Download Full History",hist_df.to_csv(index=False),"history_{}.csv".format(safe_bid(bid)))
            st.markdown("---")
            st.caption("To delete your history, contact your service provider.")
