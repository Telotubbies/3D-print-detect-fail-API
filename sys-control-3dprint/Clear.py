import time
import requests

# ตั้งค่า
API_KEY = "gl3ye-kMFFW6eRuDp98Y2cyME19SXApyId_Y8QuL_b0"
OCTOPRINT_URL = "http://192.168.214.181:5002"
HOST_URL = OCTOPRINT_URL  # ใช้ตัวเดียวกันได้

UI_API_KEY = API_KEY  # ถ้าเป็น key ตัวเดียวกัน

headers = {"Content-Type": "application/json", "X-Api-Key": API_KEY}

# ตัวแปรควบคุม
test = 0
clear = 0
last_remaining = 0

# G-code เคลียร์โมเดล
clear_gcode = [
    "G91",
    "G1 Z10",
    "G1 X110 Y218 F3000",
    "G1 Z1",
    "G90",
    "G1 X110 Y1 Z1 F2400",
]


def set_active(active: bool):
    return requests.post(
        f"{HOST_URL}/plugin/continuousprint/set_active",
        headers={"X-Api-Key": UI_API_KEY},
        data={"active": str(active).lower()},
    ).json()


def get_state():
    return requests.get(
        f"{HOST_URL}/plugin/continuousprint/state/get",
        headers={"X-Api-Key": UI_API_KEY},
    ).json()


def cancel_job():
    data = {"command": "cancel"}
    return requests.post(f"{OCTOPRINT_URL}/api/job", headers=headers, json=data)


def send_gcode(commands):
    data = {"commands": commands}
    return requests.post(
        f"{OCTOPRINT_URL}/api/printer/command", headers=headers, json=data
    )


# =============================
# Loop หลัก
# =============================
while True:
    state = get_state()
    try:
        remaining = state["queues"][0]["jobs"][0]["remaining"]
    except (KeyError, IndexError):
        remaining = 0

    # ---------------------------
    # กรณี remaining เพิ่มขึ้น
    # ---------------------------
    if remaining > last_remaining:
        print("📌 พบว่า remaining เพิ่มขึ้น → รอ 20 นาที")
        time.sleep(20 * 60)
        send_gcode(clear_gcode)
        set_active(True)

    last_remaining = remaining

    # ---------------------------
    # กรณี clear == 1
    # ---------------------------
    if clear == 1:
        print("📌 clear mode: cancel + รอ 20 นาที + clear gcode + restart")
        cancel_job()
        time.sleep(20 * 60)
        send_gcode(clear_gcode)
        set_active(True)
        clear = 0

    # ---------------------------
    # กรณี test == 1
    # ---------------------------
    if test == 1:
        print("📌 test mode: cancel + clear gcode + restart")
        cancel_job()
        send_gcode(clear_gcode)
        set_active(True)
        test = 0

    time.sleep(10)  # หน่วง 10 วินาทีค่อยตรวจซ้ำ
