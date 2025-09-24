# --- Single-sensor PID edge follower with tiered right-turn override on "white streaks" ---

import time
from machine import Pin, PWM, SoftI2C
from veml6040 import VEML6040

# ---------------- Motor API ----------------
class Motor1PWM:
    def __init__(self, pwmA_pin, pwmB_pin, pwm_freq=20000):
        self.PWMA = PWM(Pin(pwmA_pin), freq=pwm_freq, duty_u16=0)
        self.PWMB = PWM(Pin(pwmB_pin), freq=pwm_freq, duty_u16=0)
    def _duty(self, pct):
        pct = 0 if pct < 0 else (100 if pct > 100 else pct)
        return int(pct * 65535 / 100)
    def set_speed(self, speed_pct):
        if speed_pct > 0:
            self.PWMA.duty_u16(self._duty(speed_pct)); self.PWMB.duty_u16(0)
        elif speed_pct < 0:
            self.PWMA.duty_u16(0); self.PWMB.duty_u16(self._duty(-speed_pct))
        else:
            self.PWMA.duty_u16(0); self.PWMB.duty_u16(0)

motorL = Motor1PWM(pwmA_pin=12, pwmB_pin=13)
motorR = Motor1PWM(pwmA_pin=27, pwmB_pin=14)

INVERT_L = False
INVERT_R = False
def Motor_SetSpeed(M1, M2):
    if INVERT_L: M1 = -M1
    if INVERT_R: M2 = -M2
    motorL.set_speed(max(0, M1))
    motorR.set_speed(max(0, M2))

# ---------------- Sensor ----------------
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)
sense = VEML6040(i2c)
def read_W_once():
    _,_,_,w = sense.read_rgbw()
    return w

# ---------------- Calibration ----------------
def calibrate_white_black(samples=20, delay_ms=80):
    print("\nPlace sensor over WHITE. Sampling in 1.5s…")
    time.sleep_ms(1500)
    s=0
    for _ in range(samples):
        s += read_W_once(); time.sleep_ms(delay_ms)
    W_white = s / samples
    print("W_white ≈", int(W_white))

    print("\nNow place sensor over BLACK (tape). Sampling in 1.5s…")
    time.sleep_ms(1500)
    s=0
    for _ in range(samples):
        s += read_W_once(); time.sleep_ms(delay_ms)
    W_black = s / samples
    print("W_black ≈", int(W_black))

    lo, hi = (min(W_white, W_black), max(W_white, W_black))
    return lo, hi

# ---------------- PID & motion params ----------------
FOLLOW_EDGE = 'left'
EDGE_SIGN   = +1 if FOLLOW_EDGE == 'left' else -1

Kp = 0.01
Ki = 0.0
Kd = 0.0
I_CLAMP = 3000.0

BASE_FWD   = 40.0
MAX_DELTA  = 18.0     # ↑ allow stronger steering when needed
PULSE_MS   = 80
READ_MS    = 1200

# Tiered right-turn override when we see lots of white in a row
WHITE_STREAK_SMALL = 1
WHITE_STREAK_MED   = 4
WHITE_STREAK_LARGE = 10
DELTA_WHITE_SMALL  = 0.60 * MAX_DELTA   # gentle right
DELTA_WHITE_MED    = 1.00 * MAX_DELTA   # strong right
DELTA_WHITE_LARGE  = 1.40 * MAX_DELTA   # very strong right (still forward)

# Keep wheels forward & tame top speed
MIN_WHEEL = 6.0
MAX_WHEEL = 60.0

def main():
    W_low, W_high = calibrate_white_black(samples=10, delay_ms=100)
    gap  = max(1200.0, W_high - W_low)
    setp = W_low + 0.50*gap
    white_hi = W_low + 0.85*gap
    print("\nSetpoint ~", int(setp), "gap ~", int(gap))

    last_e = 0.0
    I_term = 0.0
    white_streak = 0
    next_tick = time.ticks_add(time.ticks_ms(), 0)

    print("\nFollowing (tiered override). Ctrl+C to stop.")
    try:
        while True:
            now = time.ticks_ms()
            if time.ticks_diff(now, next_tick) < 0:
                time.sleep_ms(10); continue
            next_tick = time.ticks_add(now, READ_MS)

            W = read_W_once()

            e_raw = (W - setp) / gap
            e = EDGE_SIGN * e_raw

            if W >= white_hi:
                white_streak += 1
            else:
                white_streak = 0

            # Base PID (kept gentle)
            P = Kp * e
            I_term = max(-I_CLAMP, min(I_CLAMP, I_term + Ki * e))
            D = Kd * (e - last_e)
            u = P + I_term + D
            last_e = e
            delta = max(-1.0, min(1.0, u)) * MAX_DELTA

            # --- Tiered right-turn override on long white streaks ---
            if white_streak >= WHITE_STREAK_LARGE:
                delta = -DELTA_WHITE_LARGE
                tier = "LARGE"
            elif white_streak >= WHITE_STREAK_MED:
                delta = -DELTA_WHITE_MED
                tier = "MED"
            elif white_streak >= WHITE_STREAK_SMALL:
                delta = -DELTA_WHITE_SMALL
                tier = "SMALL"
            else:
                tier = "-"

            left  = BASE_FWD - delta
            right = BASE_FWD + delta

            # always forward + clamp
            left  = min(MAX_WHEEL, max(MIN_WHEEL, left))
            right = min(MAX_WHEEL, max(MIN_WHEEL, right))

            Motor_SetSpeed(left, right)
            time.sleep_ms(PULSE_MS)
            Motor_SetSpeed(0, 0)

            print("W=", int(W),
                  "| e_raw=", round(e_raw,3),
                  "| delta=", round(delta,1),
                  "| tier=", tier,
                  "| L/R=", int(left), int(right),
                  "| white_streak=", white_streak)

    except KeyboardInterrupt:
        pass
    finally:
        Motor_SetSpeed(0, 0)
        print("\nStopped.")

if __name__ == "__main__":
    main()
  