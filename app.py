import os
import io
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
from datetime import datetime, date

st.set_page_config(page_title="แดชบอร์ดจัดซื้อจัดจ้าง อบจ.เชียงใหม่", layout="wide")

st.title("📊 แดชบอร์ดจัดซื้อจัดจ้าง อบจ.เชียงใหม่ (2558–2568)")
st.caption("อัปไฟล์ Excel หรือใช้ไฟล์ตัวอย่างที่เตรียมไว้ (ดึงคอลัมน์: วันที่ประกาศ, หน่วยงาน, ประเภทงาน, มูลค่า, ผู้รับจ้าง)")

# -------------------- Helpers --------------------
TH_MONTHS = {
    "ม.ค.": 1, "ก.พ.": 2, "มี.ค.": 3, "เม.ย.": 4, "พ.ค.": 5, "มิ.ย.": 6,
    "ก.ค.": 7, "ส.ค.": 8, "ก.ย.": 9, "ต.ค.": 10, "พ.ย.": 11, "ธ.ค.": 12,
    # เผื่อรูปแบบเต็ม
    "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3, "เมษายน": 4, "พฤษภาคม": 5, "มิถุนายน": 6,
    "กรกฎาคม": 7, "สิงหาคม": 8, "กันยายน": 9, "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12,
}

def parse_thai_date(s):
    """รับสตริงวันที่ไทย เช่น '13 พ.ย. 57' หรือ '2568-08-01 00:00:00' → datetime.date
       กติกา: ปีไทยมักย่อ (57→2557). ถ้าเจอปี < 2500 จะ +2500 แล้วลบ 543 ไปเป็น ค.ศ."""
    if pd.isna(s):
        return pd.NaT
    if isinstance(s, (pd.Timestamp, datetime, date)):
        # ถ้าเป็นวันที่อยู่แล้ว แปลงเป็น date
        return pd.to_datetime(s, errors='coerce').date()
    ss = str(s).strip()
    # ลอง parse เป็น iso-like ก่อน
    try:
        dt = pd.to_datetime(ss, errors='raise')
        return dt.date()
    except Exception:
        pass
    parts = ss.replace(",", " ").split()
    # คาดรูปแบบ: DD <th_month> YY/YYY[Y]
    try:
        if len(parts) >= 3:
            d = int(parts[0])
            mname = parts[1]
            y_text = parts[2]
            m = TH_MONTHS.get(mname, None)
            if m is None:
                return pd.NaT
            y = int(y_text)
            if y < 2500:  # ปีไทยแบบย่อ
                y = y + 2500
            # แปลงเป็น ค.ศ.
            y_g = y - 543
            return date(y_g, m, d)
    except Exception:
        return pd.NaT
    return pd.NaT

def clean_numeric(x):
    """แปลงมูลค่าเป็นตัวเลข"""
    if pd.isna(x):
        return np.nan
    if isinstance(x, (int, float, np.number)):
        return float(x)
    s = str(x).replace(",", "").replace(" ", "")
    try:
        return float(s)
    except Exception:
        return np.nan

# -------------------- Sidebar --------------------
with st.sidebar:
    st.header("⚙️ ตั้งค่า/อัปโหลด")
    uploaded = st.file_uploader("อัป Excel (.xlsx)", type=["xlsx"])
    use_sample = st.checkbox("ใช้ไฟล์ตัวอย่างที่เตรียมไว้", value=not bool(uploaded), help="ใช้ไฟล์บนเซิร์ฟเวอร์นี้ หากยังไม่อัปไฟล์ของคุณ")
    st.markdown("---")
    st.caption("เคล็ดลับ: ถ้าข้อมูลเยอะมาก ให้กรองคอลัมน์สำคัญก่อน เพื่อความเร็ว")

# -------------------- Load Data --------------------
df = None
source_note = ""

if use_sample and not uploaded:
    sample_path = "/mnt/data/รายการจัดซื้อจัดจ้างองค์การบริหารส่วนจังหวัดเชียงใหม่2558-2568.xlsx"
    try:
        xls = pd.ExcelFile(sample_path)
        df = pd.read_excel(xls, sheet_name=xls.sheet_names[0])
        source_note = "ใช้ไฟล์ตัวอย่างบนเซิร์ฟเวอร์"
    except Exception as e:
        st.error(f"ไม่พบไฟล์ตัวอย่าง: {e}")
        st.stop()
else:
    if not uploaded:
        st.stop()
    try:
        xls = pd.ExcelFile(uploaded)
        df = pd.read_excel(xls, sheet_name=xls.sheet_names[0])
        source_note = "ใช้ไฟล์ที่อัปโหลด"
    except Exception as e:
        st.error(f"อ่านไฟล์ไม่สำเร็จ: {e}")
        st.stop()

st.success(f"📄 โหลดข้อมูลสำเร็จ ({source_note}) • แถว: {len(df):,} • คอลัมน์: {len(df.columns)}")

# -------------------- Column Mapping --------------------
# คาดคอลัมน์หลักตามไฟล์ตัวอย่าง
# ปรับชื่อให้ตรง ถ้ายังไม่มีให้เลือกจาก selectbox
default_cols = {
    "date": "announce_date",
    "dept": "dept_name",
    "type": "project_type_name",
    "value": "contract_price_agree",  # ใช้มูลค่าตามสัญญา
    "vendor": "winner_name",
}
st.markdown("### 🔧 เลือกคอลัมน์ที่ใช้วิเคราะห์")
c1, c2, c3, c4, c5 = st.columns(5)
date_col = c1.selectbox("วันที่ประกาศ", df.columns.tolist(), index=df.columns.get_loc(default_cols["date"]) if default_cols["date"] in df.columns else 0)
dept_col = c2.selectbox("หน่วยงาน", df.columns.tolist(), index=df.columns.get_loc(default_cols["dept"]) if default_cols["dept"] in df.columns else 0)
type_col = c3.selectbox("ประเภทงาน", df.columns.tolist(), index=df.columns.get_loc(default_cols["type"]) if default_cols["type"] in df.columns else 0)
value_col = c4.selectbox("มูลค่า (บาท)", df.columns.tolist(), index=df.columns.get_loc(default_cols["value"]) if default_cols["value"] in df.columns else 0)
vendor_col = c5.selectbox("ผู้รับจ้าง/บริษัท", df.columns.tolist(), index=df.columns.get_loc(default_cols["vendor"]) if default_cols["vendor"] in df.columns else 0)

# แปลงวันที่ไทย → ค.ศ.
dt_series = df[date_col].apply(parse_thai_date)
df["_date"] = pd.to_datetime(dt_series, errors="coerce")
# ทำคอลัมน์เวลา
df["_year"] = df["_date"].dt.year
df["_month"] = df["_date"].dt.to_period("M").dt.to_timestamp()
df["_day"] = df["_date"].dt.date

# แปลงมูลค่าเป็นตัวเลข
df["_value"] = df[value_col].apply(clean_numeric)

# -------------------- Filters --------------------
st.markdown("### 🔎 ตัวกรอง (Filters)")
fc1, fc2, fc3 = st.columns(3)
# ช่วงวัน
min_d = df["_date"].min(); max_d = df["_date"].max()
if pd.isna(min_d) or pd.isna(max_d):
    st.warning("ยังไม่มีวันที่ที่ parse ได้ในข้อมูล (กรุณาตรวจสอบรูปแบบวันที่)")
    st.stop()
date_range = fc1.date_input("ช่วงวันที่", value=(min_d.date(), max_d.date()))
if isinstance(date_range, tuple):
    d_from, d_to = date_range
else:
    d_from, d_to = min_d.date(), max_d.date()

# เลือกหน่วยงาน/ประเภท
dept_vals = sorted([x for x in df[dept_col].dropna().unique().tolist() if str(x).strip() != ""])
type_vals = sorted([x for x in df[type_col].dropna().unique().tolist() if str(x).strip() != ""])
dept_sel = fc2.multiselect("หน่วยงาน", dept_vals, default=dept_vals[: min(20, len(dept_vals))])
type_sel = fc3.multiselect("ประเภทงาน", type_vals, default=type_vals or [])

# Apply filters
f = df.copy()
f = f[(f["_date"].dt.date >= d_from) & (f["_date"].dt.date <= d_to)]
if dept_sel:
    f = f[f[dept_col].isin(dept_sel)]
if type_sel:
    f = f[f[type_col].isin(type_sel)]

# -------------------- KPIs --------------------
st.markdown("### 📌 ตัวชี้วัด (KPIs)")
k1, k2, k3, k4 = st.columns(4)
k1.metric("จำนวนรายการ", f"{len(f):,}")
k2.metric("มูลค่ารวม (บาท)", f"{f['_value'].sum():,.2f}")
k3.metric("มูลค่าเฉลี่ย/รายการ", f"{f['_value'].mean():,.2f}")
k4.metric("มูลค่าเฉลี่ย/วัน", f"{(f.groupby('_day')['_value'].sum().mean() if not f.empty else 0):,.2f}")

st.markdown("---")

# -------------------- Charts --------------------
co1, co2 = st.columns(2)

# 1) เส้นรายเดือน (มูลค่ารวม)
m = f.dropna(subset=["_month"]).groupby("_month")["_value"].sum().reset_index()
m["_month"] = pd.to_datetime(m["_month"])
fig_line = px.line(m, x="_month", y="_value", title="มูลค่ารวมรายเดือน")
co1.plotly_chart(fig_line, use_container_width=True)

# 2) แท่งตามหน่วยงาน (Top N)
dept_agg = f.groupby(dept_col)["_value"].sum().reset_index().sort_values("_value", ascending=False)
topn = st.slider("จำนวนหน่วยงานที่แสดง (Top-N)", 5, 30, 10, 1)
dept_top = dept_agg.head(topn)
fig_bar = px.bar(dept_top, x=dept_col, y="_value", title=f"มูลค่ารวมตามหน่วยงาน (Top {topn})")
co2.plotly_chart(fig_bar, use_container_width=True)

# 3) Pie: % ตามประเภทงาน
type_agg = f.groupby(type_col)["_value"].sum().reset_index()
if len(type_agg) > 0:
    fig_pie_type = px.pie(type_agg, names=type_col, values="_value", title="% มูลค่าตามประเภทงาน")
    st.plotly_chart(fig_pie_type, use_container_width=True)

# 4) Pie: % ตามผู้รับจ้าง (Top-N)
vendor_agg = f.groupby(vendor_col)["_value"].sum().reset_index().sort_values("_value", ascending=False)
vendor_top = vendor_agg.head(topn)
if len(vendor_top) > 0:
    fig_pie_vendor = px.pie(vendor_top, names=vendor_col, values="_value", title=f"% มูลค่าตามผู้รับจ้าง (Top {topn})")
    st.plotly_chart(fig_pie_vendor, use_container_width=True)

st.markdown("---")

# -------------------- Summary Tables with % Share --------------------
st.subheader("📊 ตารางสรุปพร้อมสัดส่วน (%)")

# หน่วยงาน
dept_tbl = f.groupby(dept_col).agg(
    จำนวน=("project_id", "count"),
    มูลค่ารวม=("_value", "sum")
).reset_index().sort_values("มูลค่ารวม", ascending=False)
total_val = dept_tbl["มูลค่ารวม"].sum() or 1.0
dept_tbl["% ส่วนแบ่งมูลค่า"] = (dept_tbl["มูลค่ารวม"] / total_val * 100).round(2)

# ประเภทงาน
type_tbl = f.groupby(type_col).agg(
    จำนวน=("project_id", "count"),
    มูลค่ารวม=("_value", "sum")
).reset_index().sort_values("มูลค่ารวม", ascending=False)
total_val_t = type_tbl["มูลค่ารวม"].sum() or 1.0
type_tbl["% ส่วนแบ่งมูลค่า"] = (type_tbl["มูลค่ารวม"] / total_val_t * 100).round(2)

t1, t2 = st.columns(2)
with t1:
    st.markdown("**หน่วยงาน**")
    st.dataframe(dept_tbl, use_container_width=True)
with t2:
    st.markdown("**ประเภทงาน**")
    st.dataframe(type_tbl, use_container_width=True)

with st.expander("🧾 ดูข้อมูลดิบ (ตัวอย่าง 1,000 แถว)"):
    st.dataframe(f.head(1000), use_container_width=True)

st.caption("สร้างด้วย Streamlit • Plotly • Pandas • รองรับวันที่ไทย → ค.ศ. อัตโนมัติ")