import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import io, re, hashlib
from supabase import create_client

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
[data-testid="metric-container"] [data-testid="stMetricValue"]{color:#F0F4F8 !important;font-family:'DM Mono',monospace !important;font-size:clamp(13px,1.4vw,18px) !important;white-space:normal !important;word-break:break-all !important;overflow:visible !important;}
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
# ── Developer password loaded from Streamlit secrets ──
# Add DEV_PASSWORD = "yourpassword" in Streamlit Cloud → Settings → Secrets
DEV_PASSWORD = st.secrets.get("DEV_PASSWORD", "creditpulse_dev_2026")

# ══════════════════════════════════════════════════════════════════════════════
#  SUPABASE CONNECTION  (replaces all file operations)
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def get_supabase():
    """Single connection reused across all reruns."""
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )

sb = get_supabase()

# ══════════════════════════════════════════════════════════════════════════════
#  AUTH  — now reads/writes Supabase clients table
# ══════════════════════════════════════════════════════════════════════════════
def hash_pw(pw):
    return hashlib.sha256(pw.strip().encode()).hexdigest()

def client_login(business_id, password):
    """Check credentials against Supabase clients table."""
    try:
        res = sb.table("clients")\
                .select("*")\
                .eq("business_id", business_id.strip().upper())\
                .execute()
        if not res.data:
            return False, "Business ID not found. Contact your service provider."
        c = res.data[0]
        if not c.get("active", False):
            return False, "Your account is deactivated. Contact your service provider."
        if hash_pw(password) != c["password_hash"]:
            return False, "Incorrect password."
        return True, c.get("display_name", business_id)
    except Exception as e:
        return False, "Connection error. Please try again."

def load_all_clients():
    """Load all clients for developer panel."""
    try:
        res = sb.table("clients").select("*").order("added", desc=True).execute()
        return res.data or []
    except:
        return []

def add_client(business_id, display_name, password):
    """Add new client to Supabase."""
    try:
        sb.table("clients").insert({
            "business_id":   business_id.strip().upper(),
            "display_name":  display_name.strip() or business_id.strip().upper(),
            "password_hash": hash_pw(password),
            "active":        True,
            "added":         datetime.now().strftime("%Y-%m-%d"),
        }).execute()
        return True, "OK"
    except Exception as e:
        err = str(e)
        if "duplicate" in err.lower() or "unique" in err.lower():
            return False, "Business ID already exists."
        return False, "Error: " + err

def toggle_client(business_id, current_active):
    """Activate or deactivate a client."""
    sb.table("clients")\
      .update({"active": not current_active})\
      .eq("business_id", business_id)\
      .execute()

def reset_client_password(business_id, new_password):
    """Reset a client's password."""
    sb.table("clients")\
      .update({"password_hash": hash_pw(new_password)})\
      .eq("business_id", business_id)\
      .execute()

# ══════════════════════════════════════════════════════════════════════════════
#  CALL LOGS  — saved to Supabase call_logs table
# ══════════════════════════════════════════════════════════════════════════════
def save_call_log(bid, customer_name, risk_grade, outcome):
    """Save a call outcome to Supabase."""
    try:
        sb.table("call_logs").insert({
            "business_id":   bid.upper(),
            "customer_name": customer_name,
            "risk_grade":    risk_grade,
            "outcome":       outcome,
        }).execute()
        return True
    except:
        return False

def load_call_logs(bid):
    """Load call logs for a specific business. Returns DataFrame."""
    try:
        res = sb.table("call_logs")\
                .select("*")\
                .eq("business_id", bid.upper())\
                .order("logged_at", desc=True)\
                .execute()
        if not res.data:
            return pd.DataFrame()
        df = pd.DataFrame(res.data)
        df["logged_at"] = pd.to_datetime(df["logged_at"], errors="coerce")
        return df[["business_id","customer_name","risk_grade","outcome","logged_at"]]
    except:
        return pd.DataFrame()

def load_all_call_logs():
    """Load ALL call logs across all clients — for developer Excel."""
    try:
        res = sb.table("call_logs")\
                .select("*")\
                .order("logged_at", desc=True)\
                .execute()
        if not res.data:
            return pd.DataFrame()
        df = pd.DataFrame(res.data)
        df["logged_at"] = pd.to_datetime(df["logged_at"], errors="coerce")
        return df[["business_id","customer_name","risk_grade","outcome","logged_at"]]
    except:
        return pd.DataFrame()

# ══════════════════════════════════════════════════════════════════════════════
#  INVOICE HISTORY  — now reads/writes Supabase invoices table
# ══════════════════════════════════════════════════════════════════════════════
def load_history(bid):
    """
    Load all invoices for this business from Supabase.
    Returns DataFrame — same shape as before so nothing else changes.
    """
    try:
        res = sb.table("invoices")\
                .select("*")\
                .eq("business_id", bid.upper())\
                .execute()
        if not res.data:
            return pd.DataFrame()
        df = pd.DataFrame(res.data)
        for c in ["invoice_date","due_date","payment_date"]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce")
        return df
    except:
        return pd.DataFrame()

def save_history(bid, df_new):
    """
    Upsert invoices into Supabase.
    UPSERT = insert if new, update if (business_id + invoice_no) already exists.
    This replaces the entire CSV dedup logic in one Supabase call.
    Returns (full_df, new_rows_approx, updated_rows_approx)
    """
    df_new = df_new.copy()

    # Prepare rows — convert dates to strings for JSON
    rows = []
    for _, r in df_new.iterrows():
        row = {
            "business_id":   bid.upper(),
            "customer_name": str(r["customer_name"]),
            "invoice_no":    str(r["invoice_no"]).upper(),
            "invoice_date":  str(r["invoice_date"].date()) if pd.notna(r.get("invoice_date")) else None,
            "due_date":      str(r["due_date"].date())     if pd.notna(r.get("due_date"))     else None,
            "amount":        float(r["amount"]),
            "paid_amount":   float(r.get("paid_amount", 0)),
            "payment_date":  str(r["payment_date"].date()) if pd.notna(r.get("payment_date")) else None,
        }
        rows.append(row)

    # Batch upsert — Supabase handles dedup via UNIQUE(business_id, invoice_no)
    # Send in chunks of 500 to avoid payload limits
    chunk_size = 500
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i+chunk_size]
        sb.table("invoices")\
          .upsert(chunk, on_conflict="business_id,invoice_no")\
          .execute()

    # Reload full history from DB to get accurate count
    full_df = load_history(bid)
    return full_df, len(df_new), 0

# ══════════════════════════════════════════════════════════════════════════════
#  UI HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def fmt(x):
    """Format in Indian number system — lakhs for large numbers."""
    try:
        v = float(x)
        if v >= 10_000_000:  return "Rs.{:.1f}Cr".format(v/10_000_000)
        elif v >= 100_000:   return "Rs.{:.1f}L".format(v/100_000)
        elif v >= 1_000:     return "Rs.{:.0f}K".format(v/1_000)
        else:                return "Rs.{:.0f}".format(v)
    except: return "Rs.0"

def fmt_full(x):
    """Full format with commas — for tables."""
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
#  DATA PROCESSING
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
    drop_cols = ["outstanding","fully_paid","overdue_days","paid_late","uploaded_at","id","business_id"]
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
    df["overdue_days"] = df["overdue_days"].clip(lower=0,upper=60)
    return df

def predict_behaviour(inv_df):
    """
    Improved behaviour predictor.
    Uses 3 signals:
    1. Trend — are delays getting better or worse over time?
    2. Recent vs overall — last 3 invoices vs lifetime average
    3. Payment rate — what % of invoices are fully paid?
    Needs min 3 paid invoices for a prediction.
    """
    paid = inv_df[inv_df["fully_paid"]==True].copy().sort_values("invoice_date")
    total_inv = len(inv_df)
    paid_count = len(paid)

    # Not enough data
    if paid_count < 3:
        if total_inv == 0:
            return "New", 0, "No invoice history yet."
        unpaid_pct = round(((total_inv - paid_count) / total_inv) * 100)
        return "New", 0, "Only {} paid invoice(s). Need 3+ to predict. {}% invoices unpaid.".format(paid_count, unpaid_pct)

    mid     = len(paid) // 2
    first_half_avg = paid.iloc[:mid]["overdue_days"].mean()
    second_half_avg = paid.iloc[mid:]["overdue_days"].mean()
    delta   = second_half_avg - first_half_avg
    last3   = paid.tail(3)["overdue_days"].mean()
    overall = paid["overdue_days"].mean()

    # Payment rate signal
    pay_rate = paid_count / total_inv if total_inv > 0 else 0

    # Worsening: delays increasing AND/OR last 3 worse than average
    if (delta > 5 and last3 > overall) or last3 > overall * 1.3:
        msg = "Payment delays increasing. Last 3 invoices averaged {:.0f} days late vs {:.0f} days overall.".format(last3, overall)
        if pay_rate < 0.6:
            msg += " Only {:.0f}% invoices fully paid — high default risk.".format(pay_rate * 100)
        return "Worsening", round(last3, 1), msg

    # Improving: delays decreasing AND last 3 better than average
    elif (delta < -5 and last3 < overall) or last3 < overall * 0.7:
        msg = "Payment behaviour improving. Last 3 invoices averaged {:.0f} days late vs {:.0f} days overall.".format(last3, overall)
        return "Improving", round(last3, 1), msg

    # Stable
    else:
        msg = "Consistent payment pattern. Average delay {:.0f} days. Pay rate {:.0f}%.".format(overall, pay_rate * 100)
        return "Stable", round(last3, 1), msg

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
    "business_id":None,    "display_name":None,
    "df_raw":None,         "df_inv":None,
    "summary":None,        "ageing":None,
    "today_cached":None,
}
for k,v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════════════════
#  HEADER
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
#  LOGIN SCREEN
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state["authenticated"]:
    st.markdown("<div style='height:20px'/>",unsafe_allow_html=True)
    lcol, _, rcol = st.columns([1,0.1,1])

    with lcol:
        st.markdown("""
        <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);
          border-radius:16px;padding:28px;">
          <div style="font-size:18px;font-weight:700;color:#F0F4F8;margin-bottom:4px">&#128100; Client Login</div>
          <div style="font-size:12px;color:#8899AA;margin-bottom:20px">Enter your Business ID and password provided by your service provider.</div>
        </div>
        """, unsafe_allow_html=True)
        c_bid = st.text_input("Business ID", placeholder="e.g. RAJ_TRADERS", key="login_bid")
        c_pw  = st.text_input("Password", type="password", key="login_pw")
        if st.button("Login", use_container_width=True, key="client_login_btn"):
            if c_bid.strip() and c_pw.strip():
                ok, result = client_login(c_bid, c_pw)
                if ok:
                    st.session_state["authenticated"] = True
                    st.session_state["is_dev"]        = False
                    st.session_state["business_id"]   = c_bid.strip().upper()
                    st.session_state["display_name"]  = result
                    st.rerun()
                else:
                    st.error(result)
            else:
                st.warning("Please enter both Business ID and password.")

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
    st.caption("Manage client accounts and passwords. All data stored in Supabase.")
    if st.button("Logout", key="dev_logout"):
        for k,v in defaults.items(): st.session_state[k]=v
        st.rerun()

    dev_tab1, dev_tab2, dev_tab3 = st.tabs(["👥 All Clients","➕ Add Client","📊 Storage Overview"])

    with dev_tab1:
        clients = load_all_clients()
        if not clients:
            st.info("No clients yet. Use Add Client tab.")
        else:
            st.markdown("**{} registered clients**".format(len(clients)))
            for c in clients:
                bid    = c["business_id"]
                active = c.get("active", False)
                sc, sl = ("#00E5A0","Active") if active else ("#FF3860","Deactivated")
                col1,col2,col3,col4 = st.columns([3,2,2,2])
                with col1:
                    st.markdown(
                        '<div style="padding:12px;background:rgba(255,255,255,0.03);border-radius:10px;border:1px solid rgba(255,255,255,0.07);">'
                        '<div style="font-weight:700;color:#C8D8E8;">'+bid+'</div>'
                        '<div style="font-size:11px;color:#8899AA;">'+str(c.get("display_name",""))+'</div>'
                        '</div>', unsafe_allow_html=True)
                with col2:
                    st.markdown('<div style="padding:12px;"><span style="color:'+sc+';font-size:12px;font-weight:600;">&#9679; '+sl+'</span></div>',unsafe_allow_html=True)
                with col3:
                    st.markdown('<div style="padding:12px;font-size:12px;color:#8899AA;">Added: '+str(c.get("added","—"))+'</div>',unsafe_allow_html=True)
                with col4:
                    if st.button("Deactivate" if active else "Activate", key="tog_"+bid):
                        toggle_client(bid, active)
                        st.rerun()
                    if st.button("Reset PW", key="rpw_"+bid):
                        st.session_state["reset_pw_target"] = bid

            if st.session_state.get("reset_pw_target"):
                target = st.session_state["reset_pw_target"]
                st.markdown("---")
                st.markdown("**Reset password for: {}**".format(target))
                new_pw = st.text_input("New Password", type="password", key="new_pw_input")
                if st.button("Confirm Reset"):
                    if new_pw.strip():
                        reset_client_password(target, new_pw)
                        st.session_state["reset_pw_target"] = None
                        st.success("Password reset for {}.".format(target))
                        st.rerun()
                    else:
                        st.error("Password cannot be empty.")

    with dev_tab2:
        st.markdown("**Add a new client**")
        n_bid  = st.text_input("Business ID", placeholder="e.g. RAJ_TRADERS", key="new_bid")
        n_name = st.text_input("Business Name", placeholder="Rajan Traders, Nagpur", key="new_name")
        n_pw   = st.text_input("Password", type="password", key="new_pw")
        if st.button("Add Client", use_container_width=True):
            if n_bid.strip() and n_pw.strip():
                ok, msg = add_client(n_bid, n_name, n_pw)
                if ok:
                    st.success("Client **{}** added. Share credentials with them.".format(n_bid.strip().upper()))
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.error("Business ID and Password are required.")

    with dev_tab3:
        st.markdown("**Supabase invoices table overview**")
        try:
            res = sb.table("invoices").select("business_id").execute()
            if res.data:
                df_counts = pd.DataFrame(res.data)
                counts = df_counts["business_id"].value_counts().reset_index()
                counts.columns = ["Business ID","Invoice Rows"]
                st.dataframe(counts, use_container_width=True, hide_index=True)
                st.metric("Total invoice rows across all clients", "{:,}".format(len(res.data)))
            else:
                st.info("No invoice data yet.")
        except Exception as e:
            st.error("Error loading data: "+str(e))

        st.markdown("---")
        st.markdown("**📥 All Clients Call Logs**")
        all_logs = load_all_call_logs()
        if len(all_logs) == 0:
            st.info("No call logs saved yet across any client.")
        else:
            # Summary per client
            summary_logs = all_logs.groupby("business_id").agg(
                Total_Calls=("outcome","count"),
                Last_Call=("logged_at","max")
            ).reset_index()
            summary_logs.columns = ["Business ID","Total Calls","Last Call"]
            summary_logs["Last Call"] = pd.to_datetime(summary_logs["Last Call"]).dt.strftime("%d %b %Y %H:%M")
            st.dataframe(summary_logs, use_container_width=True, hide_index=True)
            st.metric("Total call logs across all clients", str(len(all_logs)))

            # Full Excel with all clients on one sheet
            all_out = io.BytesIO()
            export_df = all_logs.copy()
            export_df.columns = ["Business ID","Customer","Grade","Outcome","Date & Time"]
            export_df["Date & Time"] = pd.to_datetime(export_df["Date & Time"]).dt.strftime("%d %b %Y %H:%M")
            with pd.ExcelWriter(all_out, engine="openpyxl") as w:
                export_df.to_excel(w, sheet_name="All Call Logs", index=False)
                # Also one sheet per client
                for bid_name in export_df["Business ID"].unique():
                    client_df = export_df[export_df["Business ID"]==bid_name]
                    sheet_name = str(bid_name)[:31]  # Excel sheet name max 31 chars
                    client_df.to_excel(w, sheet_name=sheet_name, index=False)
            st.download_button(
                "⬇ Download All Clients Call Logs (Excel)",
                all_out.getvalue(),
                "all_call_logs.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
#  CLIENT SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
bid          = st.session_state["business_id"]
display_name = st.session_state.get("display_name") or bid

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

    # Reprocess when date changes
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

    # Show how many rows are saved in DB
    if st.session_state.get("df_raw") is not None:
        st.caption("Loaded: {:,} invoice rows".format(len(st.session_state["df_raw"])))

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

    # ── Manual Invoice Entry Form ─────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**➕ Add Invoice Manually**")
    st.caption("Fill one invoice at a time. Saved to database instantly.")

    if "show_form" not in st.session_state:
        st.session_state["show_form"] = True
    if "form_success" not in st.session_state:
        st.session_state["form_success"] = None

    if st.session_state["form_success"]:
        inv_no = st.session_state["form_success"]
        st.markdown(
            '<div style="background:rgba(0,229,160,0.1);border:1px solid rgba(0,229,160,0.3);'
            'border-radius:10px;padding:12px;margin-bottom:10px;">'
            '<div style="color:#00E5A0;font-weight:700;font-size:13px;">&#10003; Invoice saved!</div>'
            '<div style="color:#C8D8E8;font-size:12px;margin-top:4px;">'+str(inv_no)+' added to database.</div>'
            '</div>', unsafe_allow_html=True)
        if st.button("➕ Add Another Invoice", use_container_width=True):
            st.session_state["form_success"] = None
            st.rerun()
    else:
        f_cust = st.text_input("Customer Name", placeholder="e.g. Rajan Traders", key="f_cust")
        if st.session_state.get("summary") is not None:
            existing_customers = st.session_state["summary"]["Customer"].tolist()
            if existing_customers:
                st.caption("Existing: " + " · ".join(existing_customers[:4]) +
                           ("..." if len(existing_customers)>4 else ""))
        f_inv = st.text_input("Invoice No", placeholder="e.g. INV-001", key="f_inv")
        col_a,col_b = st.columns(2)
        with col_a:
            f_inv_date = st.date_input("Invoice Date", value=datetime.now().date(), key="f_inv_date")
        with col_b:
            f_due_date = st.date_input("Due Date",
                value=(datetime.now()+pd.Timedelta(days=21)).date(), key="f_due_date")
        f_amount = st.number_input("Amount (Rs.)", min_value=0.0, step=500.0, format="%.0f", key="f_amount")
        f_paid   = st.number_input("Paid Amount (Rs.)", min_value=0.0, step=500.0, format="%.0f", key="f_paid",
                                    help="Leave 0 if not paid yet")
        f_paid_date = None
        if f_paid > 0:
            f_paid_date = st.date_input("Payment Date", value=datetime.now().date(), key="f_paid_date")

        # Live validation
        if f_amount > 0 and f_paid > f_amount:
            st.markdown('<div style="color:#FF3860;font-size:11px;">&#9888; Paid cannot exceed invoice amount.</div>',unsafe_allow_html=True)
        if f_due_date < f_inv_date:
            st.markdown('<div style="color:#FF3860;font-size:11px;">&#9888; Due date before invoice date.</div>',unsafe_allow_html=True)

        if st.button("💾 Save Invoice", use_container_width=True, key="save_manual_invoice"):
            errs = []
            if not f_cust.strip():    errs.append("Customer name required.")
            if not f_inv.strip():     errs.append("Invoice number required.")
            if f_amount <= 0:         errs.append("Amount must be greater than 0.")
            if f_paid > f_amount:     errs.append("Paid cannot exceed amount.")
            if f_due_date < f_inv_date: errs.append("Due date before invoice date.")

            if errs:
                for e in errs: st.error(e)
            else:
                new_row = pd.DataFrame([{
                    "customer_name": f_cust.strip(),
                    "invoice_no":    f_inv.strip().upper(),
                    "invoice_date":  pd.Timestamp(f_inv_date),
                    "due_date":      pd.Timestamp(f_due_date),
                    "amount":        float(f_amount),
                    "paid_amount":   float(f_paid),
                    "payment_date":  pd.Timestamp(f_paid_date) if f_paid_date and f_paid>0 else pd.NaT,
                }])
                with st.spinner("Saving..."):
                    full, _, _ = save_history(bid, new_row)
                    if len(full) > 0:
                        inv, summ, age = process_all(full, today)
                        st.session_state["df_raw"]       = full
                        st.session_state["df_inv"]       = inv
                        st.session_state["summary"]      = summ
                        st.session_state["ageing"]       = age
                        st.session_state["today_cached"] = str(today)
                        st.session_state["form_success"] = f_inv.strip().upper()
                        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
#  INPUT
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state["summary"] is None:
    stepper(0)
    existing = load_history(bid)

    if len(existing)>0:
        st.info("**History found** — {:,} invoice rows in database. Load to analyse.".format(len(existing)))
        if st.button("📂 Load My Data"):
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
        with st.spinner("Saving to database and processing..."):
            cleaned      = clean_data(raw)
            full,new,dup = save_history(bid, cleaned)
            st.success("{} invoices saved to database. Total: {:,} rows.".format(new, len(full)))
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
            '<div style="font-size:13px;color:#4A5568">Upload a file, use example data, or add invoices manually from the sidebar.</div>'
            '</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
else:
    summary = st.session_state["summary"]
    df_inv  = st.session_state["df_inv"]
    ageing  = st.session_state["ageing"]

    stepper(3)

    k1,k2,k3,k4,k5 = st.columns(5)
    k1.metric("Customers",    str(len(summary)))
    k2.metric("Total Credit", fmt(summary["Total Credit"].sum()))
    k3.metric("Total Paid",   fmt(summary["Total Paid"].sum()))
    k4.metric("Outstanding",  fmt(summary["Outstanding"].sum()))
    k5.metric("Critical (D)", str(int((summary["Risk Grade"]=="D").sum())),
              delta="Immediate action needed", delta_color="inverse")
    st.markdown("<div style='height:16px'/>",unsafe_allow_html=True)

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

    with tab_risk:
        disp = filtered[["Customer","Invoices","Risk Score","Risk Grade","Grade Label",
                          "Total Credit","Total Paid","Outstanding","Max Overdue(d)",
                          "Avg Delay(d)","Suggested Limit","Credit Action","Behaviour Trend"]].copy()
        for c in ["Total Credit","Total Paid","Outstanding","Suggested Limit"]:
            disp[c] = disp[c].apply(fmt_full)
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

    with tab_beh:
        st.markdown("### 🔮 Payment Behaviour Predictor")
        st.caption("Analyses full invoice history. More history = more accurate predictions.")
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

    with tab_call:
        cd = filtered[["Customer","Risk Grade","Outstanding","Max Overdue(d)","Call Type","Credit Action","Call Script"]].copy()
        cd.insert(0,"Priority",range(1,len(cd)+1))
        cd["Outstanding"]    = cd["Outstanding"].apply(fmt_full)
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
                if st.button("Save Call Log",key="log_{}".format(row["Customer"])):
                    if outcome == "Select outcome":
                        st.warning("Please select an outcome before saving.")
                    else:
                        saved = save_call_log(bid, row["Customer"], row["Risk Grade"], outcome)
                        if saved:
                            st.success("✓ Logged — {} · {}".format(row["Customer"], outcome))
                        else:
                            st.error("Failed to save. Check your Supabase connection.")

        # ── Call Logs Excel Download ──────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📥 Download Call Logs")
        logs_df = load_call_logs(bid)
        if len(logs_df) == 0:
            st.info("No call logs saved yet. Use the outcome logger above.")
        else:
            st.caption("{} call logs saved for your account.".format(len(logs_df)))
            # Preview
            preview = logs_df.copy()
            preview.columns = ["Business ID","Customer","Grade","Outcome","Date & Time"]
            preview["Date & Time"] = preview["Date & Time"].dt.strftime("%d %b %Y %H:%M")
            st.dataframe(preview.drop(columns=["Business ID"]), use_container_width=True, hide_index=True)
            # Build Excel
            log_out = io.BytesIO()
            with pd.ExcelWriter(log_out, engine="openpyxl") as w:
                preview.to_excel(w, sheet_name="Call Logs", index=False)
            st.download_button(
                "⬇ Download My Call Logs (Excel)",
                log_out.getvalue(),
                "call_logs_{}.xlsx".format(bid),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        ce = filtered[["Customer","Risk Grade","Outstanding","Max Overdue(d)","Call Type","Credit Action"]].copy()
        ce["Outstanding"] = ce["Outstanding"].apply(fmt_full)
        st.download_button("⬇ Export Call List",ce.to_csv(index=False),"call_list.csv")

    with tab_age:
        st.markdown("### Ageing Report")
        st.caption("FMCG India buckets: Current / 1-15 / 16-30 / 31-45 / 45+ days")
        ad = ageing.copy()
        for c in ["Current","1-15 days","16-30 days","31-45 days","45+ days","Total Outstanding"]:
            if c in ad.columns: ad[c]=ad[c].apply(fmt_full)
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
        trend = cust_row["Behaviour Trend"]
        tc_clr = "#00E5A0" if trend=="Improving" else "#FF3860" if trend=="Worsening" else "#FFD166" if trend=="Stable" else "#8899AA"
        st.markdown(
            '<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);'
            'border-radius:10px;padding:14px;margin-bottom:16px;display:flex;align-items:center;gap:12px;">'
            +trend_badge(trend)+
            '<div style="font-size:13px;color:#C8D8E8;">'+cust_row["Behaviour Insight"]+'</div></div>',
            unsafe_allow_html=True)
        id_ = cust_inv[["invoice_no","invoice_date","due_date","amount","paid_amount","outstanding","overdue_days","paid_late","fully_paid"]].copy()
        id_.columns = ["Invoice","Invoice Date","Due Date","Amount","Paid","Outstanding","Overdue(d)","Paid Late","Fully Paid"]
        for c in ["Amount","Paid","Outstanding"]: id_[c]=id_[c].apply(fmt_full)
        st.dataframe(id_,use_container_width=True,hide_index=True,
            column_config={
                "Overdue(d)": st.column_config.NumberColumn("Overdue",format="%d days"),
                "Paid Late":  st.column_config.CheckboxColumn("Paid Late"),
                "Fully Paid": st.column_config.CheckboxColumn("Fully Paid"),
            })
        st.download_button("⬇ Export {}'s Invoices".format(sel),cust_inv.to_csv(index=False),"{}_invoices.csv".format(sel.replace(" ","_")))

    with tab_hist:
        st.markdown("### 📁 My Invoice History")
        st.caption("All your invoice data stored permanently in Supabase database.")
        hist_df = st.session_state.get("df_raw", pd.DataFrame())
        if len(hist_df)==0:
            st.info("No history yet. Upload invoices or add manually from the sidebar.")
        else:
            h1,h2,h3 = st.columns(3)
            h1.metric("Total Invoice Rows", "{:,}".format(len(hist_df)))
            h2.metric("Unique Customers",   str(hist_df["customer_name"].nunique()) if "customer_name" in hist_df.columns else "—")
            earliest = pd.to_datetime(hist_df["invoice_date"],errors="coerce").min() if "invoice_date" in hist_df.columns else None
            h3.metric("Earliest Invoice",   str(earliest.date()) if earliest and pd.notna(earliest) else "—")
            with st.expander("Preview first 50 rows"):
                st.dataframe(hist_df.head(50),use_container_width=True,hide_index=True)
            st.download_button("⬇ Download Full History",hist_df.to_csv(index=False),"history_{}.csv".format(bid))
            st.markdown("---")
            st.caption("To delete history, contact your service provider.")
