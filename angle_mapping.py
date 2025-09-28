import network, time, urequests
from machine import PWM, Pin

# -------- Wi-Fi ----------
SSID = "Tufts_Wireless"   # replace with IoT SSID or hotspot if captive portal
def wifi_connect():
    sta = network.WLAN(network.STA_IF)
    if not sta.isconnected():
        print("Connecting to Wi-Fi…")
        sta.active(True)
        sta.connect(SSID)            # open network: SSID only
        while not sta.isconnected():
            time.sleep(0.2)
    print("Wi-Fi:", sta.ifconfig())

wifi_connect()

# -------- Servo ----------
servo = PWM(Pin(4), freq=50, duty_u16=0)

def servo_angle(angle):
    """
    Move servo to angle 0–180.
    Using inverted mapping: 0°=2.5 ms, 180°=0.5 ms
    """
    angle = max(0, min(180, int(angle)))
    us = 2500 - (angle * 2000) // 180   # invert direction
    servo.duty_ns(us * 1000)
    print(f"Moved servo to {angle}° (pulse {us} µs)")

# -------- API Call ----------
URL = "https://open.er-api.com/v6/latest/USD"

# Map currencies to fixed angles
ANGLE_MAP = {
    "EUR": 0,
    "PYG": 30,
    "ARS": 60,
    "GBP": 90,
    "JPY": 120,
    "BRL": 150,
}

print("Fetching:", URL)

try:
    r = urequests.get(URL)
    print("HTTP status:", r.status_code)
    if r.status_code == 200:
        j = r.json()
        print("Result:", j.get("result"))
        print("Updated:", j.get("time_last_update_utc"))
        print("Base:", j.get("base_code"))

        rates = j.get("rates", {})

        # For each currency, print and move servo
        for code, angle in ANGLE_MAP.items():
            if code in rates:
                print(f"1 USD = {rates[code]} {code}  -> servo {angle}°")
                servo_angle(angle)
                time.sleep(2)   # hold for 2 sec before next currency
            else:
                print(f"{code} not in response")
    else:
        print("Error body:", r.text[:200])
    r.close()
except Exception as e:
    print("Request failed:", e)
