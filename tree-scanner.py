import time
import board
import busio
import numpy as np
import adafruit_mlx90640
from gpiozero import Button
from smbus2 import SMBus

# LCD setup
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

# Initialize LCD
try:
    lcd_init()
    lcd_string("Tree Scanner", LCD_LINE_1)
    lcd_string("Press button...", LCD_LINE_2)
    lcd_on = True
    print("LCD initialized")
except Exception as e:
    lcd_on = False
    print(f"LCD not available: {e}")

# Button setup
button = Button(17, pull_up=True)

# Sensor setup
i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ

DEAD_VARIANCE_THRESHOLD = 0.08

print("Tree Health Scanner")
print("Point sensor at tree and press button\n")

def scan_tree():
    if lcd_on:
        try:
            lcd_string("Scanning...", LCD_LINE_1)
            lcd_string("", LCD_LINE_2)
        except:
            pass
    print("Scanning", end="")

    try:
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
        relative_variance = variance / avg_temp if avg_temp != 0 else 0

        print(f"\nAvg Temp: {avg_temp:.1f}C")
        print(f"Variance: {variance:.2f}")
        print(f"Relative Variance: {relative_variance:.4f}")
        print(f"Range: {temp_range:.1f}C")

        if relative_variance < DEAD_VARIANCE_THRESHOLD:
            if lcd_on:
                try:
                    lcd_string("STATUS: DEAD", LCD_LINE_1)
                    lcd_string(f"Temp:{avg_temp:.1f}C", LCD_LINE_2)
                except:
                    pass
            print(">>> STATUS: DEAD / DORMANT TREE <<<\n")
        else:
            if lcd_on:
                try:
                    lcd_string("STATUS: HEALTHY", LCD_LINE_1)
                    lcd_string(f"Temp:{avg_temp:.1f}C", LCD_LINE_2)
                except:
                    pass
            print(">>> STATUS: HEALTHY TREE <<<\n")

        while button.is_pressed:
            time.sleep(0.1)

    except Exception as e:
        if lcd_on:
            try:
                lcd_string("Sensor error", LCD_LINE_1)
                lcd_string("", LCD_LINE_2)
            except:
                pass
        print(f"Error: {e}")

button.when_pressed = scan_tree

print("Ready - press button to scan")

try:
    while True:
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nScanner stopped")
