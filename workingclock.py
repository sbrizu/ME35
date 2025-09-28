from machine import Pin, PWM
import time

# === Servo setup ===
SERVO_PIN = 4          # change if your signal wire is on a different GPIO
pwm = PWM(Pin(SERVO_PIN), freq=50)  # 50 Hz for hobby servos

# Flip this to True if your servo moves the opposite way you want
INVERT = True

def set_servo_deg(deg):
    """Move servo to 0–180° using 0.5–2.5 ms pulse width."""
    deg = max(0, min(180, int(deg)))
    if INVERT:
        deg = 180 - deg
    us = 500 + (deg * 2000) // 180    # 500–2500 microseconds
    pwm.duty_ns(us * 1000)            # convert µs → ns for duty_ns

# === Clock-like loop: seconds → angle ===
last_sec = -1
try:
    while True:
        sec = time.localtime()[5]         # 0..59 (ESP32 RTC is fine even without NTP)
        if sec != last_sec:               # update once per second
            angle = int((sec / 59) * 180) if sec else 0
            set_servo_deg(angle)
            print("%02d s -> %3d°" % (sec, angle))
            last_sec = sec
        time.sleep_ms(50)                 # light polling for when the second flips
except KeyboardInterrupt:
    pass
finally:
    pwm.deinit()
