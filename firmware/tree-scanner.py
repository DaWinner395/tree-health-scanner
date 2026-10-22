import time
import board
import busio
import numpy as np
import adafruit_mlx90640
from gpiozero import Button
from smbus2 import SMBus
from picamera2 import Picamera2
from libcamera import controls
import requests

# =====================
# CONFIGURATION
# =====================
API_KEY = "2b10WnrrJdpIrhv8zsLqreCzO"

SPECIES_THRESHOLDS = {
    "oak":        0.010,
    "pine":       0.009,
    "redwood":    0.011,
    "maple":      0.010,
    "cedar":      0.009,
    "eucalyptus": 0.010,
    "birch":      0.009,
    "palm":       0.008,
    "spider":     0.008,
    "default":    0.010
}

# =====================
# LCD SETUP
# =====================
LCD_ADDR = 0x27
LCD_CHR = 1
LCD_CMD = 0
LCD_LINE_1 = 0x80
LCD_LINE_2 = 0xC0
ENABLE = 0b00000100
BACKLIGHT = 0x08

def lcd_toggle(bits):
    with SMBus(1) as bus:
        time.sleep(0.0005)
        bus.write_byte(LCD_ADDR, (bits | ENABLE))
        time.sleep(0.0005)
        bus.write_byte(LCD_ADDR, (bits & ~ENABLE))
        time.sleep(0.0005)

def lcd_byte(bits, mode):
    with SMBus(1) as bus:
        bits_high = mode | (bits & 0xF0) | BACKLIGHT
        bits_low = mode | ((bits << 4) & 0xF0) | BACKLIGHT
        bus.write_byte(LCD_ADDR, bits_high)
    lcd_toggle(bits_high)
    with SMBus(1) as bus:
        bus.write_byte(LCD_ADDR, bits_low)
    lcd_toggle(bits_low)

def lcd_init():
    time.sleep(0.05)
    lcd_byte(0x33, LCD_CMD)
    time.sleep(0.05)
    lcd_byte(0x32, LCD_CMD)
    time.sleep(0.05)
    lcd_byte(0x28, LCD_CMD)
    time.sleep(0.05)
    lcd_byte(0x0C, LCD_CMD)
    time.sleep(0.05)
    lcd_byte(0x01, LCD_CMD)
    time.sleep(0.05)
    lcd_byte(0x06, LCD_CMD)
    time.sleep(0.05)

def lcd_string(message, line):
    message = message.ljust(16, " ")
    lcd_byte(line, LCD_CMD)
    for i in range(16):
        lcd_byte(ord(message[i]), LCD_CHR)

try:
    lcd_init()
    lcd_string("Tree Scanner", LCD_LINE_1)
    lcd_string("Press button...", LCD_LINE_2)
    lcd_on = True
    print("LCD initialized")
except Exception as e:
    lcd_on = False
    print(f"LCD not available: {e}")

# =====================
# BUTTON SETUP
# =====================
button = Button(27, pull_up=True)

# =====================
# CAMERA SETUP
# =====================
camera = Picamera2()
config = camera.create_still_configuration()
camera.configure(config)
camera.start()
camera.set_controls({"AfMode": controls.AfModeEnum.Continuous})
time.sleep(2)
print("Camera ready")

# =====================
# THERMAL SENSOR SETUP
# =====================
i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ
print("Thermal sensor ready")

# =====================
# FUNCTIONS
# =====================
def identify_species():
    print("Taking photo...")
    if lcd_on:
        try:
            lcd_string("Identifying...", LCD_LINE_1)
            lcd_string("", LCD_LINE_2)
        except:
            pass

    camera.capture_file("bark.jpg")

    url = f"https://my-api.plantnet.org/v2/identify/all?api-key={API_KEY}"
    with open("bark.jpg", "rb") as image_file:
        files = [("images", ("bark.jpg", image_file, "image/jpeg"))]
        data = {"organs": ["bark"]}
        response = requests.post(url, files=files, data=data)

    result = response.json()

    if result.get("results"):
        top = result["results"][0]
        common_names = top["species"].get("commonNames", [])
        species = common_names[0] if common_names else top["species"]["scientificNameWithoutAuthor"]
        score = top["score"]
        print(f"Species: {species} ({score:.0%} confidence)")
        return species.lower(), score
    else:
        print("Could not identify species")
        return "unknown", 0

def thermal_scan():
    print("Scanning thermal data", end="")
    if lcd_on:
        try:
            lcd_string("Thermal scan...", LCD_LINE_1)
            lcd_string("", LCD_LINE_2)
        except:
            pass

    all_temps = []
    for i in range(5):
        frame = [0] * 768
        mlx.getFrame(frame)
        all_temps.append(np.array(frame).reshape(24, 32))
        print(".", end="", flush=True)
        time.sleep(0.5)

    print()
    avg_temps = np.mean(all_temps, axis=0)
    avg_temp = np.mean(avg_temps)
    variance = np.var(avg_temps)
    temp_range = np.max(avg_temps) - np.min(avg_temps)
    std_dev = np.std(avg_temps)
    relative_variance = variance / avg_temp if avg_temp != 0 else 0

    return avg_temp, variance, temp_range, std_dev, relative_variance

def get_threshold(species):
    for key in SPECIES_THRESHOLDS:
        if key in species:
            return SPECIES_THRESHOLDS[key]
    return SPECIES_THRESHOLDS["default"]

def scan():
    print("\n--- Starting scan ---")

    try:
        species, confidence = identify_species()
    except Exception as e:
        print(f"Camera/API error: {e}")
        species = "unknown"
        confidence = 0

    try:
        avg_temp, variance, temp_range, std_dev, relative_variance = thermal_scan()
    except Exception as e:
        print(f"Thermal sensor error: {e}")
        if lcd_on:
            try:
                lcd_string("Sensor error", LCD_LINE_1)
                lcd_string("", LCD_LINE_2)
            except:
                pass
        return

    threshold = get_threshold(species)
    is_dead = relative_variance < threshold

    print(f"\nSpecies: {species} ({confidence:.0%})")
    print(f"Avg Temp: {avg_temp:.1f}C")
    print(f"Variance: {variance:.2f}")
    print(f"Relative Variance: {relative_variance:.4f}")
    print(f"Threshold used: {threshold}")
    print(f"Range: {temp_range:.1f}C")

    if is_dead:
        status = "DEAD / DORMANT"
        print(">>> STATUS: DEAD / DORMANT TREE <<<")
    else:
        status = "HEALTHY"
        print(">>> STATUS: HEALTHY TREE <<<")

    if lcd_on:
        try:
            species_short = species[:16]
            lcd_string(species_short, LCD_LINE_1)
            lcd_string(f"{status[:10]} {avg_temp:.1f}C", LCD_LINE_2)
        except:
            pass

    while button.is_pressed:
        time.sleep(0.1)

# =====================
# MAIN LOOP
# =====================
print("\nTree Health Scanner ready")
print("Press button to scan\n")

if lcd_on:
    try:
        lcd_string("Tree Scanner", LCD_LINE_1)
        lcd_string("Press button...", LCD_LINE_2)
    except:
        pass

button.when_pressed = scan

try:
    while True:
        time.sleep(0.1)

except KeyboardInterrupt:
    camera.stop()
    print("\nScanner stopped")
