# ใช้ Python 3.11
FROM python:3.11

# ตั้ง working directory
WORKDIR /app

# คัดลอกไฟล์ requirements.txt แล้วติดตั้ง dependencies
COPY requirements.txt .
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*


RUN pip install --no-cache-dir -r requirements.txt

# คัดลอกโปรเจกต์ทั้งหมดเข้า container
COPY . .

# เปิด port 8000
EXPOSE 8000

# รัน FastAPI app
# backend.main:app = main.py ในโฟลเดอร์ backend
# --reload = hot-reload สำหรับ dev mode
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
