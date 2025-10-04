# ใช้ nginx เป็น base image
FROM nginx:1.27-alpine

# คัดลอกไฟล์ frontend (HTML/CSS/JS) เข้าไป nginx
COPY . /usr/share/nginx/html

# expose port 80
EXPOSE 80

# รัน nginx
CMD ["nginx", "-g", "daemon off;"]
