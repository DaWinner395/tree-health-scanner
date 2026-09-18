# Dead Tree Detection Scanner

## Demo Video

https://github.com/user-attachments/assets/f88f91da-985d-4a1d-8331-5d500184c699

---

A handheld device that identifies tree species using a camera and determines whether a tree is healthy or dead using thermal imaging. Built with a Raspberry Pi 5, an Arducam IMX708 12MP camera, and an MLX90640 infrared thermal array sensor.

**[Try the Live Demo →](https://dawinner395.github.io/tree-health-scanner/)**

---

## How It Works

When you press the button on the device, it runs a three-step scan:

1. **Species identification** — The camera takes a photo of the tree bark and sends it to the PlantNet API, which identifies the species and returns a confidence score.
2. **Thermal scan** — The MLX90640 thermal camera captures 5 frames of the bark surface and averages them to measure heat distribution across the tree's vascular layer.
3. **Health classification** — The device compares the thermal variance against a species-specific threshold. A healthy tree has active water and nutrient flow through its cambium layer, which shows up as uneven heat patterns. A dead or stressed tree shows uniform, low thermal variance. The result — **Healthy** or **Dead/Stressed** — is displayed on the LCD screen.

---

## Hardware

| Component | Details |
|---|---|
| Raspberry Pi 5 8GB | Main compute unit |
| Arducam IMX708 12MP | Camera for bark photos (CSI ribbon, golden cable) |
| MLX90640 Thermal Array | 32×24 IR sensor, I²C address 0x33 |
| 1602A LCD with I²C backpack | Display output, I²C address 0x27 |
| Tactile button | GPIO 27 (Pin 13) to trigger a scan |
| Nintendo Switch adapter | 27W USB-C power supply |

---

## Software

**Main file:** `tree_scanner.py`

**Dependencies:**
```
adafruit-circuitpython-mlx90640
picamera2
smbus2
gpiozero
requests
```

Install with:
```bash
pip3 install adafruit-circuitpython-mlx90640 smbus2 gpiozero requests --break-system-packages
```

**Run manually:**
```bash
python3 tree_scanner.py
```

**Auto-start on boot:**
```bash
sudo systemctl enable treescanner
sudo systemctl start treescanner
```

---

## Species Thresholds

The device uses relative variance (variance ÷ average temperature) as the health metric. Each species has a calibrated threshold — if the scan comes in above the threshold, the tree is healthy; below it, the tree is dead or stressed.

| Species | Threshold |
|---|---|
| Oak | 0.010 |
| Pine | 0.009 |
| Redwood | 0.011 |
| Maple | 0.010 |
| Cedar | 0.009 |
| Eucalyptus | 0.010 |
| Palm | 0.008 |
| Default | 0.010 |

---

## Wiring

**Thermal sensor (MLX90640) — I²C**
- VCC → Pin 1 (3.3V)
- GND → Pin 6 (Ground)
- SDA → Pin 3 (GPIO 2)
- SCL → Pin 5 (GPIO 3)

**LCD (1602A with I²C backpack)**
- VCC → Pin 2 (5V)
- GND → Pin 9 (Ground)
- SDA → Pin 3 (GPIO 2)
- SCL → Pin 5 (GPIO 3)

**Button**
- One leg → Pin 13 (GPIO 27)
- Other leg → Pin 9 (Ground)
