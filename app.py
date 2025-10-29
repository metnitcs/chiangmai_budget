import os
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
from datetime import datetime, date
from pathlib import Path

st.set_page_config(page_title="ระบบติดตามงบประมาณ ", layout="wide")

# BRIGHT THEME
BASE_CSS = """
<style>
:root { --primary: #ff6b35; --secondary: #f7931e; --accent: #00d4aa; --purple: #8b5cf6; }

/* Force light background */
.stApp, .main .block-container, [data-testid="stAppViewContainer"] {
  background-color: #ffffff !important;
  color: #1f2937 !important;
}

.block-container { padding-top: 0.5rem; }
.hero {
  background: linear-gradient(135deg, var(--primary), var(--secondary), var(--accent));
  color: white; padding: 24px; border-radius: 20px; box-shadow: 0 12px 32px rgba(255,107,53,.2);
}
.hero h1 { margin: 0; font-size: 1.8rem; font-weight: 800; }
.hero p { margin: 8px 0 0; opacity: .95; font-size: 1.05rem; }

.kpi { 
  background: linear-gradient(145deg, #ffffff, #f8fafc); 
  border-radius: 20px; padding: 20px; 
  border: 2px solid #e0f2fe; 
  box-shadow: 0 8px 25px rgba(0,212,170,.1);
  transition: transform 0.2s ease;
}
.kpi:hover { transform: translateY(-2px); }
.kpi .label { color: #475569; font-size: .95rem; font-weight: 600; }
.kpi .value { color: var(--primary); font-weight: 800; font-size: 1.4rem; }

/* Override Streamlit components */
.stSelectbox > div > div, .stDateInput > div > div {
  background-color: #ffffff !important;
  color: #1f2937 !important;
}

.stTabs [data-baseweb="tab-list"] { gap: .5rem; }
.stTabs [data-baseweb="tab"] { 
  border-radius: 25px; 
  background: linear-gradient(145deg, #f1f5f9, #e2e8f0) !important;
  border: 2px solid transparent;
  font-weight: 600;
  color: #1f2937 !important;
}
.stTabs [data-baseweb="tab"]:hover { 
  background: linear-gradient(145deg, var(--accent), var(--purple)) !important;
  color: white !important;
}
</style>
"""
st.markdown(BASE_CSS, unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>ระบบติดตามงบประมาณ</h1>
  <p>แดชบอร์ดสรุปการจัดซื้อจัดจ้าง · เลือกปีงบประมาณ/ปฏิทิน → เลือกช่วงวัน</p>
</div>
""", unsafe_allow_html=True)

# HELPERS
DATA_PATH = Path(__file__).with_name("data.xlsx")
TH_MONTHS = {
    "ม.ค.":1,"ก.พ.":2,"มี.ค.":3,"เม.ย.":4,"พ.ค.":5,"มิ.ย.":6,
    "ก.ค.":7,"ส.ค.":8,"ก.ย.":9,"ต.ค.":10,"พ.ย.":11,"ธ.ค.":12,
    "มกราคม":1,"กุมภาพันธ์":2,"มีนาคม":3,"เมษายน":4,"พฤษภาคม":5,"มิถุนายน":6,
    "กรกฎาคม":7,"สิงหาคม":8,"กันยายน":9,"ตุลาคม":10,"พฤศจิกายน":11,"ธันวาคม":12
}
def parse_thai_date(s):
    if pd.isna(s): return pd.NaT
    if isinstance(s, (pd.Timestamp, datetime, date)): return pd.to_datetime(s, errors="coerce")
    ss = str(s).strip()
    dt = pd.to_datetime(ss, errors="coerce")
    if pd.notna(dt): return dt
    parts = ss.replace(",", " ").split()
    try:
        if len(parts) >= 3:
            d = int(parts[0]); m = TH_MONTHS.get(parts[1], None); y = int(parts[2])
            if m is None: return pd.NaT
            if y < 2500: y = y + 2500
            y_ce = y - 543
            return pd.to_datetime(f"{y_ce:04d}-{m:02d}-{d:02d}", errors="coerce")
    except Exception:
        return pd.NaT
    return pd.NaT

def clean_num(x):
    if pd.isna(x): return np.nan
    if isinstance(x, (int, float, np.number)): return float(x)
    try: return float(str(x).replace(",", "").replace(" ", ""))
    except: return np.nan

def to_be(ce): return ce + 543

# LOAD FIXED FILE
try:
    xls = pd.ExcelFile(DATA_PATH)
    df = pd.read_excel(xls, sheet_name=xls.sheet_names[0])
    st.success(f"📄 โหลดข้อมูลจากไฟล์บนเซิร์ฟเวอร์ • แถว {len(df):,} • คอลัมน์ {len(df.columns)}")
except Exception as e:
    st.error(f"อ่านไฟล์ไม่สำเร็จ: {e}")
    st.stop()

default_cols = {
    "date": "transaction_date",
    "type": "project_type_name",
    "value": "contract_price_agree",
    "vendor": "winner_name",
    "money": "project_money",
}
c1, c2, c3, c4, c5 = st.columns(5)
date_col = c1.selectbox("วันที่ประกาศ (ใช้กรอง)", df.columns.tolist(),
                        index=df.columns.get_loc(default_cols["date"]) if default_cols["date"] in df.columns else 0)
type_col = c2.selectbox("ประเภทงาน", df.columns.tolist(),
                        index=df.columns.get_loc(default_cols["type"]) if default_cols["type"] in df.columns else 0)
value_col = c3.selectbox("มูลค่าตามสัญญา", df.columns.tolist(),
                         index=df.columns.get_loc(default_cols["value"]) if default_cols["value"] in df.columns else 0)
vendor_col = c4.selectbox("ผู้รับจ้าง", df.columns.tolist(),
                          index=df.columns.get_loc(default_cols["vendor"]) if default_cols["vendor"] in df.columns else 0)
money_col = c5.selectbox("งบ/วงเงินโครงการ (ใช้สรุปต่อปี)", df.columns.tolist(),
                         index=df.columns.get_loc(default_cols["money"]) if default_cols["money"] in df.columns else 0)

df["_date"] = pd.to_datetime(df[date_col].apply(parse_thai_date), errors="coerce")
df["_value"] = df[value_col].apply(clean_num)
df["_money"] = df[money_col].apply(clean_num)
df["_year_ce"] = df["_date"].dt.year
df["_month"] = df["_date"].dt.month
if df["_date"].notna().sum() == 0:
    st.error("ไม่พบวันที่ที่ parse ได้จากคอลัมน์ที่เลือก")
    st.stop()

# YEAR FIRST → DATE FILTER
st.markdown("### 📅 เลือกปีงบประมาณ/ปฏิทิน ก่อน แล้วค่อยกรองช่วงวัน")
fy_toggle = st.toggle("ใช้ปีงบประมาณไทย (ต.ค. ปีก่อน → ก.ย. ปีที่เลือก)", value=True)

if fy_toggle:
    df["_year_be"] = np.where(df["_month"] >= 10, to_be(df["_year_ce"] + 1), to_be(df["_year_ce"]))
else:
    df["_year_be"] = to_be(df["_year_ce"])

years = sorted(df["_year_be"].dropna().unique().tolist())
sel_year = st.selectbox("เลือกปี (พ.ศ.)", years, index=len(years)-1)

today = pd.Timestamp.today().date()
if fy_toggle:
    y_ce = sel_year - 543
    start = date(y_ce-1, 10, 1)
    end = date(y_ce, 9, 30)
else:
    y_ce = sel_year - 543
    start = date(y_ce, 1, 1)
    end = min(today, date(y_ce, 12, 31))

cda, cdb = st.columns(2)
date_from = cda.date_input("วันเริ่ม", value=start)
date_to = cdb.date_input("วันจบ", value=end)

f = df[(df["_year_be"] == sel_year)]
f = f[(f["_date"].dt.date >= date_from) & (f["_date"].dt.date <= date_to)]

# KPI
k1, k2, k3, k4 = st.columns(4)
k1.markdown(f'<div class="kpi"><div class="label">จำนวนรายการ</div><div class="value">{len(f):,}</div></div>', unsafe_allow_html=True)
k2.markdown(f'<div class="kpi"><div class="label">มูลค่ารวม (บ.)</div><div class="value">{f["_value"].sum():,.2f}</div></div>', unsafe_allow_html=True)
k3.markdown(f'<div class="kpi"><div class="label">ผู้รับจ้าง (ไม่ซ้ำ)</div><div class="value">{f[vendor_col].nunique():,}</div></div>', unsafe_allow_html=True)
monthly_sum = f.groupby(f["_date"].dt.to_period("M"))["_value"].sum()
k4.markdown(f'<div class="kpi"><div class="label">เฉลี่ยต่อเดือน (บ.)</div><div class="value">{(monthly_sum.mean() if len(monthly_sum)>0 else 0):,.2f}</div></div>', unsafe_allow_html=True)

st.markdown("---")

# TABS
tab1, tab2, tab3, tab4, tab5 = st.tabs(["ภาพรวม", "ผู้รับจ้าง", "ประเภทงาน", "สรุปต่อปี", "ข้อมูลดิบ"])

with tab1:
    c1, c2 = st.columns(2)
    m = f.copy()
    m["ym"] = m["_date"].dt.to_period("M").dt.to_timestamp()
    m = m.groupby("ym")["_value"].sum().reset_index()
    fig_line = px.line(m, x="ym", y="_value", markers=True, title="มูลค่ารวมรายเดือน")
    c1.plotly_chart(fig_line, use_container_width=True)

    type_agg = f.groupby(type_col)["_value"].sum().reset_index()
    if len(type_agg) > 0:
        fig_pie = px.pie(type_agg, names=type_col, values="_value", hole=0.5, title="% มูลค่าตามประเภทงาน")
        c2.plotly_chart(fig_pie, use_container_width=True)

with tab2:
    topn = st.slider("จำนวนบริษัทที่แสดง (Top-N)", 5, 30, 10, 1, key="topn_vendor")
    vendor_agg = f.groupby(vendor_col)["_value"].sum().reset_index().sort_values("_value", ascending=False).head(topn)
    fig_bar = px.bar(vendor_agg, x=vendor_col, y="_value", title=f"มูลค่ารวมตามผู้รับจ้าง (Top {topn})")
    st.plotly_chart(fig_bar, use_container_width=True)

with tab3:
    # Count by project_id if available, else by row index
    count_col = "project_id" if "project_id" in f.columns else None
    if count_col is None:
        f = f.reset_index()
        count_col = "index"
    type_tbl = f.groupby(type_col).agg(จำนวน=(count_col,"count"), มูลค่ารวม=("_value","sum")).reset_index().sort_values("มูลค่ารวม", ascending=False)
    tot = type_tbl["มูลค่ารวม"].sum() or 1.0
    type_tbl["% ส่วนแบ่ง"] = (type_tbl["มูลค่ารวม"]/tot*100).round(2)
    st.dataframe(type_tbl, use_container_width=True)

with tab4:
    money_year = f.groupby(df["_year_be"])["_money"].sum().reset_index()
    money_year.columns = ["ปี (พ.ศ.)", "รวม project_money"]
    st.dataframe(money_year.sort_values("ปี (พ.ศ.)"), use_container_width=True)

with tab5:
    st.dataframe(f.head(1000), use_container_width=True)
    csv = f.to_csv(index=False).encode("utf-8-sig")
    st.download_button("ดาวน์โหลด CSV", data=csv, file_name="filtered.csv", mime="text/csv")
