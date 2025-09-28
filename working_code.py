import network, time, urequests, ntptime, urandom
from machine import Pin, PWM

#Wifi
def wifi_connect():
    sta = network.WLAN(network.STA_IF)
    if not sta.isconnected():
        print("Connecting to Wi-Fi…")
        sta.active(True)
        sta.connect("Tufts_Wireless")
        while not sta.isconnected():
            time.sleep(0.25)
    print("Wi-Fi:", sta.ifconfig())

wifi_connect()

#time
try:
    ntptime.host = "pool.ntp.org"
    ntptime.settime() 
    print("NTP time set.")
except Exception as e:
    print("NTP failed:", e)

# Optional local timezone offset (hours)
TZ_OFFSET_HOURS = -4 
def localtime():
    t = time.time() + TZ_OFFSET_HOURS * 3600
    return time.localtime(t)

# ========= Servo =========
# Servo starts
servo = PWM(Pin(4), freq=50, duty_u16=0)
def servo_angle(angle_deg):
    angle = max(0, min(180, int(angle_deg)))
    us = 2500 - (angle * 2000) // 180
    servo.duty_ns(us * 1000)

# button
BTN_PIN = 35
btn = Pin(BTN_PIN, Pin.IN)  # external pull-up required!
DEBOUNCE_MS = 200
last_btn_state = 1  # idle HIGH with pull-up
last_toggle_ms = time.ticks_ms()

# api
URL = "https://open.er-api.com/v6/latest/USD"
ANGLE_MAP = {
    "EUR": 0,
    "PYG": 30,
    "ARS": 60,
    "GBP": 90,
    "JPY": 120,
    "BRL": 150,
}
ANGLE_LIST = list(ANGLE_MAP.items())

def fetch_rates():
    try:
        r = urequests.get(URL)
        if r.status_code == 200:
            j = r.json(); r.close()
            return j.get("rates", {})
        else:
            print("FX HTTP error:", r.status_code)
            r.close()
    except Exception as e:
        print("FX request failed:", e)
    return {}

# angles
deck = [] 

def refill_deck():
    global deck
    deck = ANGLE_LIST[:]  

def draw_random_from_deck():
    """Pop one random (code, angle) from deck; refill when empty."""
    global deck
    if not deck:
        refill_deck()
    idx = urandom.getrandbits(16) % len(deck)
    return deck.pop(idx)

# define states
STATE_CLOCK = 0
STATE_FX    = 1
state = STATE_CLOCK
prev_state = state
print("Start in State 1 (Clock). Press button on D35 to toggle.")

# Behavior flags
SINGLE_ON_ENTRY = True

# state 1 clock
def update_clock_mode():
    _, _, _, _, _, ss, _, _ = localtime()
    angle = 0 if ss == 0 else int((ss / 59) * 180)
    servo_angle(angle)

# state 2: currencies
current_fx_choice = None  

def run_fx_once(rates):
    """Pick ONE random (code, angle), move there, then sit until toggled out."""
    global current_fx_choice
    current_fx_choice = draw_random_from_deck()
    code, angle = current_fx_choice
    if rates and (code in rates):
        print(f"[FX one-shot] {code}: 1 USD = {rates[code]} -> {angle}°")
    else:
        print(f"[FX one-shot] {code}: (no rate) -> {angle}°")
    servo_angle(angle)

def run_fx_cycle_random(rates):
    """Continuously pick random (code, angle) with no repeats until deck is empty."""
    code, angle = draw_random_from_deck()
    if rates and (code in rates):
        print(f"[FX cycle] {code}: 1 USD = {rates[code]} -> {angle}°")
    else:
        print(f"[FX cycle] {code}: (no rate) -> {angle}°")
    servo_angle(angle)

    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < 1200:
        if check_button_toggle():
            return True
        time.sleep_ms(20)
    return False

def check_button_toggle():
    """Poll button with debounce; toggle global state when pressed (HIGH->LOW)."""
    global last_btn_state, last_toggle_ms, state
    now = time.ticks_ms()
    cur = btn.value()
    if cur != last_btn_state:
        if time.ticks_diff(now, last_toggle_ms) > DEBOUNCE_MS:
            last_toggle_ms = now
            last_btn_state = cur
            if cur == 0:  # active-low press
                state = STATE_FX if state == STATE_CLOCK else STATE_CLOCK
                print("Toggled to:", "FX" if state == STATE_FX else "Clock")
                return True
    return False

# main loop
rates_cache = {}
last_rates_fetch_ms = 0
RATES_REFRESH_MS = 5 * 60 * 1000 

while True:
    # state switch
    if state != prev_state:
        if state == STATE_FX:
            
            if not deck:
                refill_deck()
            
            rates_cache = fetch_rates()
            last_rates_fetch_ms = time.ticks_ms()

            if SINGLE_ON_ENTRY:
                run_fx_once(rates_cache)  
        prev_state = state

    if state == STATE_CLOCK:
        update_clock_mode()
        
        for _ in range(10):
            if check_button_toggle():
                break
            time.sleep_ms(100)

    else:  
        
        if time.ticks_diff(time.ticks_ms(), last_rates_fetch_ms) > RATES_REFRESH_MS and not SINGLE_ON_ENTRY:
            rates_cache = fetch_rates()
            last_rates_fetch_ms = time.ticks_ms()

        if SINGLE_ON_ENTRY:
        
            if check_button_toggle():
                continue
            time.sleep_ms(50)
        else:
            
            if run_fx_cycle_random(rates_cache):
                continue
