# --- VEML6040 line follower + color detection + LEDs (loads refs from color_refs.json) ---
# - Follows left edge using W channel (P-only, pulsed drive)
# - Loads previously taught RED/GREEN/BLUE chroma refs from flash
# - On color confirm: brief stop + flash matching LED
# - LED pins: RED=25, GREEN=26, BLUE=32 (as in your working LED snippet)

import time, json
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

# Your motor pins
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
    left  = 0 if left  < 0 else (MAX_WHEEL if left  > MAX_WHEEL else left)
    right = 0 if right < 0 else (MAX_WHEEL if right > MAX_WHEEL else right)
    if 0 < left  < MIN_WHEEL:  left  = MIN_WHEEL
    if 0 < right < MIN_WHEEL:  right = MIN_WHEEL
    Motor_SetSpeed(left, right)

# ========================= LEDs =========================
# Your working pins
led_red   = Pin(25, Pin.OUT)
led_green = Pin(26, Pin.OUT)
led_blue  = Pin(32, Pin.OUT)

def all_off():
    led_red.value(0)
    led_green.value(0)
    led_blue.value(0)

def led_color(name, on=True):
    """Turn on exactly one color (or all off). name in {'RED','GREEN','BLUE'}."""
    name = (name or "").upper()
    if not on:
        all_off(); return
    if name == "RED":
        led_red.value(1); led_green.value(0); led_blue.value(0)
    elif name == "GREEN":
        led_red.value(0); led_green.value(1); led_blue.value(0)
    elif name == "BLUE":
        led_red.value(0); led_green.value(0); led_blue.value(1)
    else:
        all_off()

def pulse_color_led(name, ms=300, flashes=1, gap_ms=120):
    """Flash the named LED a few times."""
    for _ in range(max(1, int(flashes))):
        led_color(name, True)
        time.sleep_ms(int(ms))
        all_off()
        time.sleep_ms(int(gap_ms))

# ========================= Sensor =========================
i2c   = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)
sense = VEML6040(i2c)  # default IT ~1.28 s (slow but stable)

def read_RGBW_once():
    return sense.read_rgbw()   # (R,G,B,W)

# ========================= Math helpers =========================
def rgb_to_chroma(R,G,B):
    s = R + G + B
    if s <= 0: return (0.0,0.0,0.0)
    return (R/s, G/s, B/s)

def euclid(a,b):
    return ((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2) ** 0.5

# ========================= WB calibration =========================
W_low=W_high=setp=gap=white_hi=black_lo=0.0

def update_cal_from_W(Wl, Wh):
    global W_low, W_high, setp, gap, white_hi, black_lo
    W_low, W_high = (min(Wl,Wh), max(Wl,Wh))
    gap  = max(1200.0, W_high - W_low)
    setp = W_low + 0.50*gap
    white_hi = W_low + 0.85*gap   # very white
    black_lo = W_low + 0.15*gap   # very black

def calibrate_white_black(samples=10, delay_ms=100):
    print("\n=== WB CALIBRATION ===")
    print("Place sensor over WHITE. Sampling in 1.5 s…")
    pulse_color_led("BLUE", 200)  # little cue
    time.sleep_ms(1500)
    s=0
    for _ in range(samples):
        _,_,_,w = read_RGBW_once(); s += w; time.sleep_ms(delay_ms)
    W_white = s/samples
    print("W_white ≈", int(W_white))

    print("Now place sensor over BLACK (tape). Sampling in 2.0 s…")
    pulse_color_led("RED", 200)
    time.sleep_ms(2000)
    s=0
    for _ in range(samples):
        _,_,_,w = read_RGBW_once(); s += w; time.sleep_ms(delay_ms)
    W_black = s/samples
    print("W_black ≈", int(W_black))

    update_cal_from_W(W_white, W_black)
    print("Setpoint ~", int(setp), " gap ~", int(gap), " white_hi ~", int(white_hi), " black_lo ~", int(black_lo))
    pulse_color_led("GREEN", 200, flashes=2)

# ========================= Load taught color refs =========================
REFS_PATH = "color_refs.json"
COLOR_REFS = {}   # {"RED": (r,g,b), "GREEN": (...), "BLUE": (...)}

def load_refs():
    global COLOR_REFS
    try:
        with open(REFS_PATH, "r") as f:
            raw = json.load(f)
        COLOR_REFS = {k: tuple(v) for k,v in raw.items()}
        print("Loaded color refs:", COLOR_REFS)
        pulse_color_led("GREEN", 120, flashes=3)
    except Exception as e:
        COLOR_REFS = {}
        print("No color refs loaded:", e, "\nRun the TEACH script first if you want color actions.")
        # short red blink to indicate no refs
        pulse_color_led("RED", 120, flashes=2)

# ========================= Color detection =========================
COLOR_MIN_W    = 8000    # too dim? skip color check
COLOR_MIN_SAT  = 0.06    # chroma spread must be at least this
DIST_THRESH    = 0.10    # must be close to a taught ref
DIST_MARGIN    = 0.06    # and clearly better than 2nd place
HIT_CONSEC_REQ = 2       # confirm after N consecutive hits
COLOR_COOLDOWN_MS = 2500 # avoid repeatedly firing on the same long strip

_last_color_name = None
_color_streak    = 0
_suppress_until  = 0

# Gate: only check color when centered on the edge & mid-light
COLOR_GATE_E      = 0.20         # |e_raw| <= 0.20
COLOR_GATE_W_FRAC = 0.25         # W within middle 50% of range

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

def color_confirm_step(R,G,B,W, e_raw, now_ms):
    global _last_color_name, _color_streak, _suppress_until

    if now_ms < _suppress_until:
        _last_color_name = None; _color_streak = 0
        return None

    centered = abs(e_raw) <= COLOR_GATE_E
    midlight = (W > (W_low + COLOR_GATE_W_FRAC*gap)) and (W < (W_high - COLOR_GATE_W_FRAC*gap))
    if not (centered and midlight):
        _last_color_name = None; _color_streak = 0
        return None

    status, name, chroma, sat, d, margin = classify_color(R,G,B,W, COLOR_REFS)
    if status != "HIT":
        _last_color_name = None; _color_streak = 0
        return None

    if name == _last_color_name:
        _color_streak += 1
    else:
        _last_color_name = name
        _color_streak = 1

    if _color_streak >= HIT_CONSEC_REQ:
        _suppress_until = now_ms + COLOR_COOLDOWN_MS
        print(">>> COLOR CONFIRMED:", name,
              "| W=%d" % W,
              "| chroma=%.3f,%.3f,%.3f" % chroma,
              "| d=%.3f margin=%.3f" % (d, margin))
        # Action: brief stop + flash the matching LED
        Motor_SetSpeed(0,0)
        pulse_color_led(name, ms=300, flashes=2, gap_ms=120)
        return name
    return None

# ========================= Line follower params =========================
FOLLOW_EDGE = 'left'
EDGE_SIGN   = +1 if FOLLOW_EDGE=='left' else -1

Kp = 0.15    # stronger P (slow sensor)
Ki = 0.0
Kd = 0.0

BASE_FWD   = 45.0
MAX_DELTA  = 50.0
PULSE_MS   = 60
READ_MS    = 1400   # match sensor cadence

DEAD_BAND      = 0.03
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

def follower_loop():
    print("\n=== FOLLOWING (Ctrl+C to stop) ===")
    print("Setpoint ~", int(setp), " gap ~", int(gap))
    last_e = 0.0
    white_streak = 0; black_streak = 0
    prev_delta = 0.0
    next_tick = time.ticks_add(time.ticks_ms(), 0)

    try:
        while True:
            now = time.ticks_ms()
            if time.ticks_diff(now, next_tick) < 0:
                time.sleep_ms(10); continue
            next_tick = time.ticks_add(now, READ_MS)

            R,G,B,W = read_RGBW_once()

            # --- edge error for line following ---
            e_raw = (W - setp) / gap
            e     = EDGE_SIGN * e_raw

            # --- color detection from saved refs ---
            if COLOR_REFS:
                color_confirm_step(R,G,B,W, e_raw, now)

            # streak logic for overrides
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

            # P-only control with small deadband
            if abs(e_raw) < DEAD_BAND:
                u = 0.0
            else:
                u = Kp * e

            # steering target with gentle nonlinearity
            nonlin = 1.0 + 0.8*abs(e)
            target_delta = max(-1.0, min(1.0, u*nonlin)) * MAX_DELTA

            # tiered overrides near extremes
            tier = "-"
            if W >= white_hi:
                if   white_streak >= WHITE_STREAK_LARGE: target_delta, tier = -DELTA_WHITE_LARGE, "W-LARGE"
                elif white_streak >= WHITE_STREAK_MED:   target_delta, tier = -DELTA_WHITE_MED,   "W-MED"
                elif white_streak >= WHITE_STREAK_SMALL: target_delta, tier = -DELTA_WHITE_SMALL, "W-SMALL"
            elif W <= black_lo:
                if   black_streak >= BLACK_STREAK_MED:   target_delta, tier = +DELTA_BLACK_MED,   "B-MED"
                elif black_streak >= BLACK_STREAK_SMALL: target_delta, tier = +DELTA_BLACK_SMALL, "B-SMALL"

            # slew limit
            step = target_delta - prev_delta
            if step >  MAX_DELTA_STEP: step =  MAX_DELTA_STEP
            if step < -MAX_DELTA_STEP: step = -MAX_DELTA_STEP
            delta = prev_delta + step
            prev_delta = delta

            # wheel speeds (forward only), pulsed
            left  = BASE_FWD - delta
            right = BASE_FWD + delta
            drive_clamped(left, right)
            time.sleep_ms(PULSE_MS)
            Motor_SetSpeed(0, 0)

            print("W=%d | e_raw=%.3f | δ_tgt=%.2f | δ=%.2f (tier=%s) | L/R=%.1f/%.1f | ws/bs=%d/%d" %
                  (int(W), e_raw, target_delta, delta, tier,
                   left, right, white_streak, black_streak))

    except KeyboardInterrupt:
        pass
    finally:
        Motor_SetSpeed(0,0)
        all_off()
        print("\nStopped.")

# ========================= Main =========================
def main():
    all_off()
    calibrate_white_black(samples=10, delay_ms=100)
    load_refs()           # loads color_refs.json if present
    follower_loop()

if __name__ == "__main__":
    main()
