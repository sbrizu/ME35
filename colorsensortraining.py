# --- VEML6040 "teach colors" (RED/GREEN/BLUE) and classify by nearest chroma ---
# - 20+ samples per color with trimmed mean
# - Saves/loads refs to/from flash (color_refs.json)
# - Simple test loop prints nearest color + distance

import time, json
from machine import Pin, SoftI2C
from veml6040 import VEML6040

# ---------- Sensor ----------
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)
sense = VEML6040(i2c)   # default integration ~1.28 s on your driver

def read_RGBW_once():
    return sense.read_rgbw()   # (R,G,B,W)

# ---------- Math helpers ----------
def rgb_to_chroma(R, G, B):
    s = R + G + B
    if s <= 0:
        return (0.0, 0.0, 0.0)
    return (R/s, G/s, B/s)

def euclid(a, b):
    return ((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2) ** 0.5

def trimmed_mean(xs, trim=0.2):
    if not xs:
        return 0.0
    xs = sorted(xs)
    n = len(xs)
    k = int(n*trim)
    core = xs[k:n-k] if n-2*k > 0 else xs
    return sum(core)/len(core)

# ---------- Robust sampling ----------
READ_MS = 1250   # ~matches your VEML6040 integration pace
def robust_rgb_sample(samples=20, delay_ms=READ_MS, trim=0.2):
    n = max(20, int(samples))   # enforce 20+
    Rs, Gs, Bs = [], [], []
    for _ in range(n):
        R,G,B,_ = read_RGBW_once()
        Rs.append(R); Gs.append(G); Bs.append(B)
        time.sleep_ms(int(delay_ms))
    Rm = trimmed_mean(Rs, trim); Gm = trimmed_mean(Gs, trim); Bm = trimmed_mean(Bs, trim)
    return Rm, Gm, Bm

# ---------- Teach / persistence ----------
REFS_PATH = "color_refs.json"

def save_refs(refs):
    try:
        with open(REFS_PATH, "w") as f:
            json.dump(refs, f)
        print("Saved refs to", REFS_PATH)
    except Exception as e:
        print("Save failed:", e)

def load_refs():
    try:
        with open(REFS_PATH, "r") as f:
            raw = json.load(f)
        # ensure tuples
        refs = {k: tuple(v) for k, v in raw.items()}
        print("Loaded refs from", REFS_PATH, "->", refs)
        return refs
    except Exception as e:
        print("No refs loaded:", e)
        return {}

def teach_one(name, samples=20, delay_ms=READ_MS, trim=0.2):
    name = name.upper()
    print("\nPlace sensor on", name, "… starting in 1.0 s")
    time.sleep_ms(1000)
    Rm,Gm,Bm = robust_rgb_sample(samples=samples, delay_ms=delay_ms, trim=trim)
    c = rgb_to_chroma(Rm, Gm, Bm)
    print("%s RGB(trimmed) = %d,%d,%d  chroma = (%.3f, %.3f, %.3f)" %
          (name, int(Rm), int(Gm), int(Bm), c[0], c[1], c[2]))
    return c

def teach_colors(names=("RED","GREEN","BLUE"), samples=20):
    refs = {}
    for n in names:
        refs[n] = teach_one(n, samples=samples)
    # store as plain lists for JSON friendliness
    save_refs({k: [float(x) for x in v] for k,v in refs.items()})
    return refs

# ---------- Classify current reading ----------
# You can tighten/loosen these if needed:
DIST_THRESH  = 0.12   # max distance to accept as a match (lower = stricter)
DIST_MARGIN  = 0.04   # best must beat 2nd best by at least this
MIN_SAT      = 0.06   # chroma spread must be >= this (reject grey-ish)
MIN_W        = 8000   # ignore if too dim

def classify_once(refs):
    if not refs:
        print("No refs loaded.")
        return None
    R,G,B,W = read_RGBW_once()
    chroma = rgb_to_chroma(R,G,B)
    sat = max(chroma) - min(chroma)
    if W < MIN_W or sat < MIN_SAT:
        print("dim/desat | W=%d  chroma=(%.3f,%.3f,%.3f) sat=%.3f" %
              (W, chroma[0], chroma[1], chroma[2], sat))
        return None

    # nearest-neighbor with margin
    best=("?", 1e9); second=("?", 1e9)
    for name, ref in refs.items():
        d = euclid(chroma, ref)
        if d < best[1]:
            second = best; best = (name, d)
        elif d < second[1]:
            second = (name, d)
    margin = second[1] - best[1]
    matched = best[1] <= DIST_THRESH and margin >= DIST_MARGIN
    print("RGB=%d,%d,%d | W=%d | chroma=%.3f,%.3f,%.3f | nearest=%s d=%.3f margin=%.3f %s" %
          (R,G,B,W, chroma[0], chroma[1], chroma[2],
           best[0], best[1], margin, "<-- MATCH" if matched else ""))
    return best[0] if matched else None

# ---------- Simple CLI-ish flow ----------
def main():
    print("\nType one of: TEACH, LOAD, TEST")
    try:
        cmd = input(">> ").strip().upper()
    except Exception:
        cmd = "TEST"

    refs = {}
    if cmd == "TEACH":
        refs = teach_colors(("GREEN","RED","BLUE"), samples=20)
    elif cmd == "LOAD":
        refs = load_refs()
        if not refs:
            print("No refs found; run TEACH first.")
    else:
        # default: try load, else ask to TEACH
        refs = load_refs()
        if not refs:
            print("No refs saved yet; running TEACH…")
            refs = teach_colors(("GREEN","RED","BLUE"), samples=20)

    print("\n--- TEST LOOP: Ctrl+C to stop ---")
    while True:
        classify_once(refs)
        time.sleep_ms(READ_MS)  # wait for a fresh integration

if __name__ == "__main__":
    main()
