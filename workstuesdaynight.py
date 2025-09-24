# --- Single-sensor VEML6040 line follower (WB + robust RGB calibration, no Wi-Fi) ---
# Stronger P, shorter pulses, gated color detection, better debug, and lost-line recovery.

import time
from machine import Pin, PWM, SoftI2C
from veml6040 import VEML6040

# ========================= Motors =========================
class Motor1PWM:
    def __init__(self, pwmA_pin, pwmB_pin, pwm_freq=20000):
        self.PWMA = PWM(Pin(pwmA_pin), freq=pwm_freq, duty_u16=0)
        self.PWMB = PWM(Pin(pwmB_pin), freq=pwm_freq, duty_u16=0)
    def _duty(self, pct):
        if pct < 0: pct = 0
        if pct > 100: pct = 100
        return int(pct * 65535 / 100)
    def set_speed(self, speed_pct):
        if speed_pct > 0:
            self.PWMA.duty_u16(self._duty(speed_pct)); self.PWMB.duty_u16(0)
        elif speed_pct < 0:
            self.PWMA.duty_u16(0); self.PWMB.duty_u16(self._duty(-speed_pct))
        else:
            self.PWMA.duty_u16(0); self.PWMB.duty_u16(0)

# Pins (adjust if needed)
motorL = Motor1PWM(pwmA_pin=12, pwmB_pin=13)
motorR = Motor1PWM(pwmA_pin=27, pwmB_pin=14)

INVERT_L = False
INVERT_R = False
def Motor_SetSpeed(M1, M2):
    if INVERT_L: M1 = -M1
    if INVERT_R: M2 = -M2
    motorL.set_speed(max(0, M1))
    motorR.set_speed(max(0, M2))

# Allow inner wheel to fully stop (better turning)
MIN_WHEEL = 12.0   # only applied to a wheel that is >0
MAX_WHEEL = 85.0
def drive_clamped(left, right):
    # 0..MAX on each; allow either to hit 0 (inner wheel)
    left  = 0 if left  < 0 else (MAX_WHEEL if left  > MAX_WHEEL else left)
    right = 0 if right < 0 else (MAX_WHEEL if right > MAX_WHEEL else right)
    if 0 < left  < MIN_WHEEL:  left  = MIN_WHEEL
    if 0 < right < MIN_WHEEL:  right = MIN_WHEEL
    Motor_SetSpeed(left, right)

# ========================= Sensor =========================
i2c   = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)
sense = VEML6040(i2c)  # defaults: Auto mode, IT ~1.28 s

def read_RGBW_once():
    return sense.read_rgbw()   # (R,G,B,W)

# ========================= Helpers =========================
def rgb_to_chroma(R,G,B):
    s = R + G + B
    if s <= 0: return (0.0,0.0,0.0)
    return (R/s, G/s, B/s)

def euclid(a,b):
    return ((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2) ** 0.5

def trimmed_mean(xs, trim=0.2):
    if not xs: return 0.0
    xs = sorted(xs); n = len(xs); k = int(n*trim)
    core = xs[k:n-k] if n-2*k > 0 else xs
    return sum(core)/len(core)

def robust_rgb_sample(samples=20, delay_ms=1400, trim=0.2):
    n = max(20, int(samples))
    Rs, Gs, Bs = [], [], []
    for _ in range(n):
        R,G,B,_ = read_RGBW_once()
        Rs.append(R); Gs.append(G); Bs.append(B)
        time.sleep_ms(int(delay_ms))  # match VEML6040 cadence
    return trimmed_mean(Rs,trim), trimmed_mean(Gs,trim), trimmed_mean(Bs,trim)

# ========================= Calibration =========================
W_low=W_high=setp=gap=white_hi=black_lo=0.0

def update_cal_from_W(Wl, Wh):
    global W_low, W_high, setp, gap, white_hi, black_lo
    W_low, W_high = (min(Wl,Wh), max(Wl,Wh))
    gap  = max(1200.0, W_high - W_low)
    setp = W_low + 0.50*gap
    white_hi = W_low + 0.85*gap
    black_lo = W_low + 0.15*gap

def calibrate_white_black(samples=10, delay_ms=100):
    print("\n=== WB CALIBRATION ===")
    print("Place sensor over WHITE. Sampling in 1.5 s…")
    time.sleep_ms(1500)
    s=0
    for _ in range(samples):
        _,_,_,w = read_RGBW_once(); s += w; time.sleep_ms(delay_ms)
    W_white = s/samples
    print("W_white ≈", int(W_white))

    print("Now place sensor over BLACK (tape). Sampling in 2.0 s…")
    time.sleep_ms(2000)
    s=0
    for _ in range(samples):
        _,_,_,w = read_RGBW_once(); s += w; time.sleep_ms(delay_ms)
    W_black = s/samples
    print("W_black ≈", int(W_black))

    update_cal_from_W(W_white, W_black)
    print("Setpoint ~", int(setp), " gap ~", int(gap), " white_hi ~", int(white_hi), " black_lo ~", int(black_lo))

# ========================= Color calibration/detect =========================
COLOR_REFS = {}

def calibrate_one_color(name, samples=20, delay_ms=1400, trim=0.2):
    name = name.upper()
    print("\n=== CAL %s ===" % name)
    print("Place sensor over %s. Sampling in 1.0 s…" % name)
    time.sleep_ms(1000)
    Rm,Gm,Bm = robust_rgb_sample(samples=samples, delay_ms=delay_ms, trim=trim)
    c = rgb_to_chroma(Rm,Gm,Bm)
    print("%s RGB (trimmed) ≈ %d,%d,%d | chroma ≈ (%.3f, %.3f, %.3f)" %
          (name, int(Rm), int(Gm), int(Bm), c[0], c[1], c[2]))
    return c

def calibrate_rgb_refs(order=('GREEN','RED','BLUE'), samples=20, delay_ms=1400, trim=0.2):
    global COLOR_REFS
    refs = {}
    for name in order:
        refs[name] = calibrate_one_color(name, samples=samples, delay_ms=delay_ms, trim=trim)
    COLOR_REFS = refs
    print("\nCOLOR_REFS =", {k: tuple(round(v[i],3) for i in range(3)) for k,v in refs.items()})

# Color detection thresholds (stricter to avoid false hits)
COLOR_MIN_W    = 8000
COLOR_MIN_SAT  = 0.06
DIST_THRESH    = 0.10   # was 0.14
DIST_MARGIN    = 0.06   # was 0.04
HIT_CONSEC_REQ = 2

_last_color_name = None
_color_streak    = 0

def classify_color(R,G,B,W, refs):
    if not refs: return ("NOREFS", None, (0,0,0), 0.0, None, None)
    c = rgb_to_chroma(R,G,B)
    sat = max(c) - min(c)
    if W < COLOR_MIN_W:     return ("NOHIT","dim", c, sat, None, None)
    if sat < COLOR_MIN_SAT: return ("NOHIT","desat", c, sat, None, None)

    best=("?",1e9); second=("?",1e9)
    for name, ref in refs.items():
        d = euclid(c, ref)
        if d < best[1]:
            second = best; best = (name, d)
        elif d < second[1]:
            second = (name, d)
    margin = second[1] - best[1]
    if best[1] <= DIST_THRESH and margin >= DIST_MARGIN:
        return ("HIT", best[0], c, sat, best[1], margin)
    else:
        return ("MAYBE", best[0], c, sat, best[1], margin)

def color_confirm_step(R,G,B,W):
    global _last_color_name, _color_streak
    status, name, chroma, sat, d, margin = classify_color(R,G,B,W, COLOR_REFS)
    if status == "HIT":
        if name == _last_color_name:
            _color_streak += 1
        else:
            _last_color_name = name
            _color_streak = 1
        if _color_streak >= HIT_CONSEC_REQ:
            print(">>> COLOR CONFIRMED:", name,
                  "| W=%d" % W,
                  "| chroma=%.3f,%.3f,%.3f" % (chroma[0],chroma[1],chroma[2]),
                  "| d=%.3f margin=%.3f" % (d, margin))
            Motor_SetSpeed(0,0); time.sleep_ms(300)
    else:
        _last_color_name = None
        _color_streak = 0

# ========================= Line follower params =========================
FOLLOW_EDGE = 'left'
EDGE_SIGN   = +1 if FOLLOW_EDGE=='left' else -1

# Stronger P so u isn’t ~0
Kp = 0.15
Ki = 0.0
Kd = 0.0
I_CLAMP = 3000.0

BASE_FWD   = 45.0
MAX_DELTA  = 50.0
PULSE_MS   = 60
READ_MS    = 1400   # match slow integration cadence

DEAD_BAND  = 0.03
MAX_DELTA_STEP = 8.0

WHITE_STREAK_SMALL = 1
WHITE_STREAK_MED   = 4
WHITE_STREAK_LARGE = 8

BLACK_STREAK_SMALL = 2
BLACK_STREAK_MED   = 5
BLACK_STREAK_LARGE = 8

DELTA_WHITE_SMALL  = 0.60 * MAX_DELTA
DELTA_WHITE_MED    = 1.00 * MAX_DELTA
DELTA_WHITE_LARGE  = 2.00 * MAX_DELTA

DELTA_BLACK_SMALL  = 0.40 * MAX_DELTA
DELTA_BLACK_MED    = 0.70 * MAX_DELTA
DELTA_BLACK_LARGE  = 1.20 * MAX_DELTA

# Only check color when we’re centered and mid-light (reduces false hits)
COLOR_GATE_E = 0.20          # |e_raw| <= 0.20
COLOR_GATE_W_FRAC = 0.25     # inside [W_low+25%gap, W_high-25%gap]

# -------- Lost-line recovery: timed, pulsed search with fresh reads --------
def recover(direction, tries=3, base=38.0, corr=10.0):
    """direction: 'right' for too-white, 'left' for too-black"""
    print("!! RECOVER", direction, "tries=", tries)
    for k in range(tries):
        bump = corr + 6*k
        if direction == 'right':
            # turn right: inner/right slows/stops
            left  = base + bump
            right = base - bump
        else:
            # turn left
            left  = base - bump
            right = base + bump

        drive_clamped(left, right)
        time.sleep_ms(PULSE_MS)
        Motor_SetSpeed(0,0)
        time.sleep_ms(READ_MS)   # wait for fresh integration
        _,_,_,W = read_RGBW_once()
        if black_lo < W < white_hi:
            print(".. recovered, W=", int(W))
            return True
    print(".. not recovered")
    return False

def follower_loop():
    print("\n=== FOLLOWING (Ctrl+C to stop) ===")
    print("Setpoint ~", int(setp), " gap ~", int(gap))
    last_e = 0.0; I_term = 0.0
    white_streak = 0; black_streak = 0
    prev_delta = 0.0
    next_tick = time.ticks_add(time.ticks_ms(), 0)

    global _last_color_name, _color_streak

    try:
        while True:
            now = time.ticks_ms()
            if time.ticks_diff(now, next_tick) < 0:
                time.sleep_ms(10); continue
            next_tick = time.ticks_add(now, READ_MS)

            R,G,B,W = read_RGBW_once()

            # --- compute error (needed for gating + control) ---
            e_raw = (W - setp) / gap
            e     = EDGE_SIGN * e_raw

            # ----- gated color check -----
            centered = abs(e_raw) <= COLOR_GATE_E
            midlight = (W > (W_low + COLOR_GATE_W_FRAC*gap)) and (W < (W_high - COLOR_GATE_W_FRAC*gap))
            if centered and midlight:
                color_confirm_step(R,G,B,W)
            else:
                _last_color_name = None
                _color_streak = 0

            # streak logic (for overrides/recovery)
            if W >= white_hi:
                white_streak += 1
            else:
                if e_raw <= 0 or W < (white_hi - 0.10*gap): white_streak = max(0, white_streak - 3)
                else:                                       white_streak = max(0, white_streak - 1)

            if W <= black_lo:
                black_streak += 1
            else:
                if e_raw >= 0 or W > (black_lo + 0.10*gap): black_streak = max(0, black_streak - 3)
                else:                                       black_streak = max(0, black_streak - 1)

            # LOST-LINE RECOVERY
            if white_streak >= WHITE_STREAK_LARGE:
                if recover('right', tries=3):
                    white_streak = 0; black_streak = 0
                    continue
            if black_streak >= BLACK_STREAK_LARGE:
                if recover('left', tries=3):
                    white_streak = 0; black_streak = 0
                    continue

            # PID (gentle) with deadband
            if abs(e_raw) < DEAD_BAND:
                u = 0.0
            else:
                P = Kp * e
                I_term = max(-I_CLAMP, min(I_CLAMP, I_term + Ki * e))
                D = Kd * (e - last_e)
                u = P + I_term + D
            last_e = e

            # steering target (nonlinear boost helps big errors turn harder)
            nonlin = 1.0 + 0.8*abs(e)   # gentle near center, stronger when far
            target_delta = max(-1.0, min(1.0, u*nonlin)) * MAX_DELTA

            # Tiered overrides
            tier = "-"
            if W >= white_hi:
                if   white_streak >= WHITE_STREAK_LARGE: target_delta, tier = -DELTA_WHITE_LARGE, "W-LARGE"
                elif white_streak >= WHITE_STREAK_MED:   target_delta, tier = -DELTA_WHITE_MED,   "W-MED"
                elif white_streak >= WHITE_STREAK_SMALL: target_delta, tier = -DELTA_WHITE_SMALL, "W-SMALL"
            elif W <= black_lo:
                if   black_streak >= BLACK_STREAK_MED:   target_delta, tier = +DELTA_BLACK_MED,   "B-MED"
                elif black_streak >= BLACK_STREAK_SMALL: target_delta, tier = +DELTA_BLACK_SMALL, "B-SMALL"

            # Slew limit
            step = target_delta - prev_delta
            if step >  MAX_DELTA_STEP: step =  MAX_DELTA_STEP
            if step < -MAX_DELTA_STEP: step = -MAX_DELTA_STEP
            delta = prev_delta + step
            prev_delta = delta

            # wheel speeds (forward only)
            left  = BASE_FWD - delta
            right = BASE_FWD + delta
            drive_clamped(left, right)

            time.sleep_ms(PULSE_MS)
            Motor_SetSpeed(0, 0)

            print("W=%d | e_raw=%.3f | P=%.3f u=%.4f | δ_tgt=%.3f | δ=%.3f (tier=%s) | L/R=%.1f/%.1f | ws/bs=%d/%d" %
                  (int(W), e_raw, Kp*e, u, target_delta, delta, tier,
                   left, right, white_streak, black_streak))

    except KeyboardInterrupt:
        pass
    finally:
        Motor_SetSpeed(0,0)
        print("\nStopped.")

# ========================= Main =========================
def main():
    calibrate_white_black(samples=10, delay_ms=100)
    calibrate_rgb_refs(order=('GREEN','RED','BLUE'), samples=20, delay_ms=1400, trim=0.2)
    follower_loop()

if __name__ == "__main__":
    main()
