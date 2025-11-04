import requests

API_KEY = "gl3ye-kMFFW6eRuDp98Y2cyME19SXApyId_Y8QuL_b0"  # ใส่ API key ของคุณ
OCTOPRINT_URL = "http://192.168.214.181:5002"  # เปลี่ยนเป็น URL ของ OctoPrint

headers = {"Content-Type": "application/json", "X-Api-Key": API_KEY}

data = {"command": "cancel"}

response = requests.post(f"{OCTOPRINT_URL}/api/job", headers=headers, json=data)

if response.status_code == 204:
    print("✅ Print job cancelled successfully.")
elif response.status_code == 409:
    print("⚠️ No active print job to cancel.")
else:
    print(f"❌ Failed: {response.status_code} {response.text}")
