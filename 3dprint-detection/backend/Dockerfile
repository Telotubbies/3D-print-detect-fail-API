# backend/Dockerfile

# ใช้ base image Python 3.10 slim
FROM python:3.10-slim

# ตั้ง working directory ใน container
WORKDIR /app

# คัดลอก requirements.txt เข้า container ก่อน (เพื่อ cache pip install)
COPY requirements.txt .

# อัปเกรด pip และติดตั้ง dependencies
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# คัดลอก source code ทั้งหมดเข้า container
COPY . .

# expose port ของ backend
EXPOSE 8000

# คำสั่งรัน backend (แก้ตาม framework ของคุณ)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
