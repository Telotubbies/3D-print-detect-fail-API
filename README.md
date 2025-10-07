# 3D-print-detect-fail-API  
YOLOv8 + FastAPI สำหรับตรวจจับ “สปาเก็ตตี้/ความล้มเหลว” ของงานพิมพ์ 3D จากรูปภาพ พร้อมเดโม่หน้าเว็บ, เก็บประวัติใน SQLite, คีย์ API และเสิร์ฟไฟล์ผลลัพธ์ชั่วคราว

---

## สารบัญ
- [คุณสมบัติเด่น](#คุณสมบัติเด่น)
- [สถาปัตยกรรมโดยสรุป](#สถาปัตยกรรมโดยสรุป)
- [เริ่มต้นอย่างรวดเร็ว (Quick Start)](#เริ่มต้นอย่างรวดเร็ว-quick-start)
- [การตั้งค่า ENV ที่สำคัญ](#การตั้งค่า-env-ที่สำคัญ)
- [โครงสร้างโปรเจกต์](#โครงสร้างโปรเจกต์)
- [API Reference (มีตารางสรุป)](#api-reference-มีตารางสรุป)
- [ตัวอย่างการเรียกด้วย cURL](#ตัวอย่างการเรียกด้วย-curl)
- [Frontend เดโม่ (การแสดงผลภาพตรวจจับ)](#frontend-เดโม่-การแสดงผลภาพตรวจจับ)
- [การเทรนโมเดล YOLOv8](#การเทรนโมเดล-yolov8)
- [แนวปฏิบัติด้านความปลอดภัย](#แนวปฏิบัติด้านความปลอดภัย)
- [Troubleshooting](#troubleshooting)
- [การมีส่วนร่วมและไลเซนส์](#การมีส่วนร่วมและไลเซนส์)

---

## คุณสมบัติเด่น
- ตรวจจับความผิดปกติของงานพิมพ์ 3D ด้วย **YOLOv8** (รองรับไฟล์โมเดล `.pt`)
- **FastAPI** RESTful: อัปโหลด → รันโมเดล → ส่งคืน URL รูปผลลัพธ์
- ระบบ **API Key** ผ่านเฮดเดอร์ `x-api-key`
- เก็บบันทึกลง **SQLite**: ตาราง `clients`, `images`, `ai_tests`
- เสิร์ฟรูปผลลัพธ์แบบชั่วคราว (มี TTL) พร้อมกัน **path traversal**
- หน้าเว็บเดโม่ (HTML/JS) แสดงรูปผลลัพธ์จาก `detected_image_url`

---

## สถาปัตยกรรมโดยสรุป

```
Client (Web/CLI) ──► FastAPI (/cards, /replace, /genkey ...)
                      │
                      ├─ YOLOv8 Inference (backend/model.py)
                      │     └─ สร้างภาพผลตรวจ + บันทึกไฟล์ชั่วคราว
                      │
                      ├─ SQLite (images, ai_tests, clients)
                      │
                      └─ Static/Temp server
                            └─ GET /temp/results/{sid}/{filename}
```

---

## เริ่มต้นอย่างรวดเร็ว (Quick Start)

### 1) ติดตั้งไลบรารีหลัก (แนะนำ Python 3.10+)
```bash
pip install -U pip
pip install fastapi uvicorn[standard] "sqlalchemy<2.0" aiosqlite \
           python-multipart httpx opencv-python pillow ultralytics python-dotenv
```
> CPU ก็ใช้งานได้ หากต้องการ GPU ให้ติดตั้ง PyTorch ตามคำแนะนำทางการของ PyTorch

### 2) สร้างไฟล์ `.env` (ในรากโปรเจกต์)
```env
MODEL_PATH=./models/best.pt
TMP_ROOT=./.tmp
MAX_FILE_SIZE=10485760
ALLOWED_MIME=image/jpeg,image/png
KEY_TTL=86400
DB_URL=sqlite:///./app.db
CORS_ALLOW_ORIGINS=*
```

### 3) รันเซิร์ฟเวอร์
```bash
uvicorn backend.main:app --reload --port 8000
```
- หน้าเว็บเดโม่: `http://localhost:8000`
- เอกสาร API (Swagger): `http://localhost:8000/docs`

---

## การตั้งค่า ENV ที่สำคัญ

| Key | ค่าเริ่มต้น/ตัวอย่าง | อธิบาย |
|---|---|---|
| `MODEL_PATH` | `./models/best.pt` | ไฟล์โมเดล YOLOv8 |
| `TMP_ROOT` | `./.tmp` | โฟลเดอร์เก็บไฟล์ชั่วคราว/ผลลัพธ์ |
| `MAX_FILE_SIZE` | `10485760` | ขนาดอัปโหลดสูงสุด (ไบต์) |
| `ALLOWED_MIME` | `image/jpeg,image/png` | MIME ที่อนุญาต |
| `KEY_TTL` | `86400` | อายุ API key (วินาที) |
| `DB_URL` | `sqlite:///./app.db` | ที่อยู่ฐานข้อมูล SQLite |
| `CORS_ALLOW_ORIGINS` | `*` | กำหนด CORS (ถ้าต้องการ) |

---

## โครงสร้างโปรเจกต์

```
3D-print-detect-fail-API/
├─ backend/
│  ├─ main.py            # FastAPI app: mount static, init_db, routes
│  ├─ cards.py           # /cards, /cards/{id}/replace, /cards/replace, /cards/genkey
│  ├─ model.py           # detect(image, out_dir=Path, ...) เรียก YOLOv8
│  ├─ schemas.py         # Pydantic models
│  ├─ config.py          # ค่าคงที่/ENV
│  ├─ database.py        # SQLite (SQLAlchemy)
│  ├─ temp_store.py      # เก็บไฟล์ temp + schedule cleanup (TTL)
│  └─ ...
├─ frontend/
│  ├─ index.html
│  └─ static/
│     ├─ js/app.js
│     └─ css/style.css
├─ models/
│  └─ best.pt
├─ schema_sqlite.sql
└─ README.md
```

---

## API Reference (มีตารางสรุป)

### สรุป Endpoint

| Method | Path | Headers | Body (Form/Data) | คำอธิบาย | Response 200 (ตัวอย่าง) |
|---|---|---|---|---|---|
| `POST` | `/cards/genkey` | – | – | สร้าง API Key ใหม่ | `{ "key": "xxxxx", "ttl": 86400 }` |
| `POST` | `/cards` | `x-api-key: <KEY>` | `image=@<file>` | อัปโหลดรูปเพื่อสร้างการ์ดใหม่ + ตรวจจับ | `{ "card_id": "94eded13", "detected_image_url": "..." }` |
| `POST` | `/cards/{card_id}/replace` | `x-api-key: <KEY>` | `image=@<file>` | แทนที่รูปของการ์ดเดิม + ตรวจจับ | `{ "card_id": "94eded13", "detected_image_url": "..." }` |
| `POST` | `/cards/replace` | `x-api-key: <KEY>` | `image=@<file>` | แทนที่รูปโดย *ให้ backend map จากคีย์* | `{ "card_id": "auto-mapped", "detected_image_url": "..." }` |
| `GET` | `/temp/results/{sid}/{filename}` | – | – | ดาวน์โหลด/แสดงรูปผลลัพธ์ (Cache-Control: no-store) | (ไฟล์ภาพ) |

> รูปผลลัพธ์ถูกเก็บในโฟลเดอร์ชั่วคราว ภายใน TTL ที่กำหนด และมีการป้องกัน **path traversal**

---

## ตัวอย่างการเรียกด้วย cURL

> **Windows (CMD/PowerShell):** ถ้า path มีช่องว่าง ต้องใส่ `"` รอบ path และ escape ให้ถูก เช่น `"C:\My Pics\test.jpg"`

**1) ขอ API Key**
```bash
curl -X POST "http://localhost:8000/cards/genkey"
```

**2) อัปโหลดรูปสร้างการ์ดใหม่**
```bash
curl -X POST "http://localhost:8000/cards" -H "x-api-key: YOUR_KEY" -F "image=@\"C:\Users\You\Pictures\test.jpg\""
```

**3) แทนที่รูปโดยระบุ `card_id`**
```bash
curl -X POST "http://localhost:8000/cards/94eded13/replace" -H "x-api-key: YOUR_KEY" -F "image=@\"C:\Users\You\Pictures\test.jpg\""
```

**4) แทนที่รูป (ให้ backend map จากคีย์)**
```bash
curl -X POST "http://localhost:8000/cards/replace" -H "x-api-key: YOUR_KEY" -F "image=@\"C:\Users\You\Pictures\test.jpg\""
```

**5) ดาวน์โหลด/เปิดภาพผลลัพธ์**
```bash
curl -L "http://localhost:8000/temp/results/<sid>/<filename>"
```

---

## Frontend เดโม่ (การแสดงผลภาพตรวจจับ)

เมื่อเรียก API สำเร็จ จะได้ `detected_image_url` กลับมา จากนั้นใน `frontend/static/js/app.js` สามารถอัปเดตรูปบนหน้าเว็บได้เช่น:
```html
<img id="result" alt="Detection result" />
<script>
  // ตัวอย่างหลังรับ response จาก API
  const detected_image_url = data.detected_image_url; // มาจาก response JSON
  document.getElementById('result').src = detected_image_url; // แสดงผลทันที
</script>
```
> ฝั่งเซิร์ฟเวอร์กำหนด `Cache-Control: no-store` ให้รูปผลลัพธ์ เพื่อให้รีเฟรชแล้วเห็นภาพล่าสุด

---

## การเทรนโมเดล YOLOv8

1. เตรียมชุดข้อมูล (YOLO format/Roboflow ฯลฯ)  
2. เทรนด้วยโน้ตบุ๊ก/สคริปต์ (เช่น `notebooks/train_yolov8.ipynb`) ให้ได้ไฟล์ `.pt`  
3. วางไฟล์ไว้ตาม `MODEL_PATH` (ค่าเริ่มต้น `./models/best.pt`)  
4. ฟังก์ชัน `backend/model.py::detect(...)` จะอ่านโมเดล รัน inference และบันทึกภาพผลลัพธ์ไปยังโฟลเดอร์ชั่วคราว

---

## แนวปฏิบัติด้านความปลอดภัย
- ทุกการอัปโหลด/แก้ไขต้องส่ง `x-api-key`
- กำหนด `KEY_TTL` ให้เหมาะสม และ **rotate keys** เป็นระยะ
- ตรวจสอบ `ALLOWED_MIME`, `MAX_FILE_SIZE` ป้องกันไฟล์ไม่พึงประสงค์
- เส้นทาง `/temp/results/...` มีการป้องกัน **path traversal** แล้ว (ตรวจซ้ำก่อนขึ้นโปรดักชัน)

---

## Troubleshooting

| อาการ | สาเหตุที่เป็นไปได้ | วิธีแก้ |
|---|---|---|
| `{"detail":"API key expired/invalid"}` | คีย์หมดอายุ/ไม่ถูกต้อง | เรียก `/cards/genkey` ใหม่ และส่ง `x-api-key` ให้ถูกต้อง |
| รูปผลลัพธ์ไม่อัปเดต | แคชภาพเก่า | ใช้ header `Cache-Control: no-store` (ฝั่งเซิร์ฟเวอร์ตั้งไว้แล้ว) หรือเติม `?v=timestamp` ท้าย URL |
| โหลดโมเดลไม่ขึ้น | `MODEL_PATH` ผิด/ไฟล์ไม่อยู่ | ตรวจ path/สิทธิ์การอ่าน และรีสตาร์ตเซิร์ฟเวอร์ |
| อัปโหลดล้มเหลว | MIME/ขนาดไฟล์ไม่ผ่าน | ตรวจ `ALLOWED_MIME`, `MAX_FILE_SIZE` |

---

## การมีส่วนร่วมและไลเซนส์
- ยินดีรับ PR/Issue: Fork → Branch → Commit → PR (แนบตัวอย่างภาพและเวอร์ชันแพ็กเกจที่ใช้)
- โปรดระบุ **LICENSE** (เช่น MIT/Apache-2.0) ในไฟล์ `LICENSE` ของรีโป

---

> **หมายเหตุ**: ชื่อไฟล์/เส้นทางบางส่วนใน README อ้างอิงจากโครงของโปรเจกต์ปัจจุบัน หากคุณปรับโครงไฟล์หรือชื่อ endpoint โปรดอัปเดต README ให้สอดคล้องอีกครั้งเพื่อความถูกต้องในการใช้งานจริง
