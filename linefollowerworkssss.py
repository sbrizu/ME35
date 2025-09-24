# --- Single-sensor PID edge follower with tiered overrides (right & left), decay, and slew limit ---

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
MAX_DELTA  = 18.0        # allow stronger steering when needed
PULSE_MS   = 80
READ_MS    = 1200

# Deadband around edge (don’t fuss when very close)
DEAD_BAND  = 0.06        # in normalized e_raw units (~6% of gap)

# Slew-limit steering changes (percent per cycle)
MAX_DELTA_STEP = 6.0     # max change of delta each decision

# ---- Tiered overrides ----
# Right-turn (white streak) — same idea as before
WHITE_STREAK_SMALL = 1
WHITE_STREAK_MED   = 4
WHITE_STREAK_LARGE = 10
DELTA_WHITE_SMALL  = 0.60 * MAX_DELTA
DELTA_WHITE_MED    = 1.00 * MAX_DELTA
DELTA_WHITE_LARGE  = 1.40 * MAX_DELTA

# NEW: Left-turn (black streak) — smaller tiers (you only need slight left)
BLACK_STREAK_SMALL = 2
BLACK_STREAK_MED   = 5
DELTA_BLACK_SMALL  = 0.40 * MAX_DELTA   # gentle left
DELTA_BLACK_MED    = 0.70 * MAX_DELTA   # moderate left

# Wheel limits
MIN_WHEEL = 10.0
MAX_WHEEL = 70.0

def main():
    W_low, W_high = calibrate_white_black(samples=10, delay_ms=100)
    gap   = max(1200.0, W_high - W_low)
    setp  = W_low + 0.50*gap
    white_hi = W_low + 0.85*gap         # very white
    black_lo = W_low + 0.15*gap         # very black (mirror threshold)
    print("\nSetpoint ~", int(setp), "gap ~", int(gap))

    last_e = 0.0
    I_term = 0.0
    white_streak = 0
    black_streak = 0
    prev_delta = 0.0
    next_tick = time.ticks_add(time.ticks_ms(), 0)

    print("\nFollowing (tiered L/R, decay, slew). Ctrl+C to stop.")
    try:
        while True:
            now = time.ticks_ms()
            if time.ticks_diff(now, next_tick) < 0:
                time.sleep_ms(10); continue
            next_tick = time.ticks_add(now, READ_MS)

            W = read_W_once()

            # normalized edge error
            e_raw = (W - setp) / gap
            e     = EDGE_SIGN * e_raw

            # streak updates with fast decay near center/opposite side
            if W >= white_hi:
                white_streak += 1
            else:
                # decay quickly once you’re off the very-white region or crossing left
                if e_raw <= 0 or W < (white_hi - 0.10*gap):
                    white_streak = max(0, white_streak - 3)
                else:
                    white_streak = max(0, white_streak - 1)

            if W <= black_lo:
                black_streak += 1
            else:
                if e_raw >= 0 or W > (black_lo + 0.10*gap):
                    black_streak = max(0, black_streak - 3)
                else:
                    black_streak = max(0, black_streak - 1)

            # PID (gentle) + deadband
            if abs(e_raw) < DEAD_BAND:
                u = 0.0
            else:
                P = Kp * e
                I_term = max(-I_CLAMP, min(I_CLAMP, I_term + Ki * e))
                D = Kd * (e - last_e)
                u = P + I_term + D
            last_e = e

            # Map PID to steering delta
            target_delta = max(-1.0, min(1.0, u)) * MAX_DELTA
            tier = "-"

            # --- Tiered overrides (choose based on current region first) ---
            if W >= white_hi:
                if   white_streak >= WHITE_STREAK_LARGE: target_delta, tier = -DELTA_WHITE_LARGE, "W-LARGE"
                elif white_streak >= WHITE_STREAK_MED:   target_delta, tier = -DELTA_WHITE_MED,   "W-MED"
                elif white_streak >= WHITE_STREAK_SMALL: target_delta, tier = -DELTA_WHITE_SMALL, "W-SMALL"
            elif W <= black_lo:
                if   black_streak >= BLACK_STREAK_MED:   target_delta, tier = +DELTA_BLACK_MED,   "B-MED"
                elif black_streak >= BLACK_STREAK_SMALL: target_delta, tier = +DELTA_BLACK_SMALL, "B-SMALL"

            # Slew limit: don’t jump steering too fast
            step = target_delta - prev_delta
            if step >  MAX_DELTA_STEP: step =  MAX_DELTA_STEP
            if step < -MAX_DELTA_STEP: step = -MAX_DELTA_STEP
            delta = prev_delta + step
            prev_delta = delta

            # compute wheel speeds (always forward)
            left  = BASE_FWD - delta
            right = BASE_FWD + delta
            left  = min(MAX_WHEEL, max(MIN_WHEEL, left))
            right = min(MAX_WHEEL, max(MIN_WHEEL, right))

            Motor_SetSpeed(left, right)
            time.sleep_ms(PULSE_MS)
            Motor_SetSpeed(0, 0)

            print("W=", int(W),
                  "| e_raw=", round(e_raw,3),
                  "| δ_tgt=", round(target_delta,1),
                  "| δ=", round(delta,1),
                  "| tier=", tier,
                  "| L/R=", int(left), int(right),
                  "| ws/bs=", white_streak, black_streak)

    except KeyboardInterrupt:
        pass
    finally:
        Motor_SetSpeed(0, 0)
        print("\nStopped.")

if __name__ == "__main__":
    main()
