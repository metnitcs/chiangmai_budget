# แดชบอร์ดจัดซื้อจัดจ้าง อบจ.เชียงใหม่ (2558–2568)

One-page dashboard (Streamlit) สำหรับไฟล์ Excel ชุด "รายการจัดซื้อจัดจ้างองค์การบริหารส่วนจังหวัดเชียงใหม่2558-2568.xlsx"

## ฟีเจอร์
- อัปไฟล์ .xlsx หรือใช้ไฟล์ตัวอย่าง
- แปลงวันที่ไทย (พ.ศ./ตัวย่อเดือน) → ค.ศ. อัตโนมัติ
- ตัวกรอง: ช่วงวัน, หน่วยงาน, ประเภทงาน
- KPI: จำนวน, มูลค่ารวม, มูลค่าเฉลี่ย
- กราฟ: เส้นรายเดือน, แท่งตามหน่วยงาน (Top-N), วงกลมสัดส่วนตามประเภทงาน/ผู้รับจ้าง
- ตารางสรุปพร้อม % ส่วนแบ่ง

## รันบนเครื่อง
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy ทางลัด
### Streamlit Community Cloud
1) อัปโปรเจกต์ขึ้น GitHub  
2) ไปที่ https://share.streamlit.io/ → New app → ชี้ไปที่ `app.py`  
3) กด Deploy

### Hugging Face Spaces
1) สร้าง Space ใหม่ชนิด Streamlit  
2) อัป `app.py`, `requirements.txt`  
3) ระบบจะ build และรันให้อัตโนมัติ

## หมายเหตุคอลัมน์ (ปรับได้ในหน้าเว็บ)
- วันที่: `announce_date`
- หน่วยงาน: `dept_name`
- ประเภทงาน: `project_type_name`
- มูลค่า: `contract_price_agree`
- ผู้รับจ้าง: `winner_name`