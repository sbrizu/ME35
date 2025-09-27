import time
from machine import SoftI2C, Pin
from veml6040 import VEML6040

# === Setup I2C and sensor ===
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)
sensor = VEML6040(i2c)

# === Function to collect samples ===
def calibrate_color(name, num_samples=20, delay=0.1):
    samples = []
    
    print(f"Place the sensor on {name} and keep it steady...")
    time.sleep(5)  # short pause to get ready
    
    for i in range(num_samples):
        r, g, b, w = sensor.read_rgbw()
        samples.append((r, g, b, w))
        print(f"Sample {i+1}: R={r}, G={g}, B={b}, W={w}")
        time.sleep(delay)

    # Compute averages
    avg_r = sum(s[0] for s in samples) / num_samples
    avg_g = sum(s[1] for s in samples) / num_samples
    avg_b = sum(s[2] for s in samples) / num_samples
    avg_w = sum(s[3] for s in samples) / num_samples

    # Normalize (avoid division by zero)
    if avg_w > 0:
        norm_r = avg_r / avg_w
        norm_g = avg_g / avg_w
        norm_b = avg_b / avg_w
    else:
        norm_r = norm_g = norm_b = 0

    print(f"\n{name} averages:")
    print(f"Raw:    R={avg_r:.1f}, G={avg_g:.1f}, B={avg_b:.1f}, W={avg_w:.1f}")
    print(f"Normed: R={norm_r:.3f}, G={norm_g:.3f}, B={norm_b:.3f}\n")

    return (avg_r, avg_g, avg_b, avg_w), (norm_r, norm_g, norm_b)

# === Example usage ===
# Run one at a time with your sample objects/colors
#calibrate_color("RED")
calibrate_color("WHITE")
calibrate_color("BLACK")
