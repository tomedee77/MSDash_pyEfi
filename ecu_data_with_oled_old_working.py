import time
import os
import serial
import struct
from PIL import Image, ImageDraw, ImageFont
import board
import digitalio
import adafruit_ssd1306

# ----- Configuration -----
PORT = "/dev/ttyUSB0"
BAUD = 115200
OLED_WIDTH = 128
OLED_HEIGHT = 32
BUTTON_PIN = board.D17  # adjust GPIO pin for your button

# ----- Wait for serial device -----
while not os.path.exists(PORT):
    print(f"Waiting for {PORT} to appear...")
    time.sleep(1)

# ----- Setup serial -----
ser = serial.Serial(PORT, BAUD, timeout=1)

# Channels to display
channels = [
    {"name": "coolant", "offset": 22, "scale": 0.02, "add": 2.44},
    {"name": "mat",     "offset": 20, "scale": 0.02, "add": 7.06},
    {"name": "afr1",    "offset": 28, "scale": 0.1, "add": 0.0},
    {"name": "map",     "offset": 18, "scale": 0.1, "add": 0.0},
]

# ----- Setup button -----
button = digitalio.DigitalInOut(BUTTON_PIN)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

# ----- Setup OLED -----
i2c = board.I2C()
oled = adafruit_ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)
oled.fill(0)
oled.show()

# Fonts
label_font = ImageFont.load_default()
value_font_default = ImageFont.load_default()

# Current channel index
current_index = 0
last_press = 0

def read_channel(data, off, scale, add):
    """Big-endian signed 16-bit read"""
    raw = struct.unpack_from(">h", data, off)[0]
    val = raw * scale + add
    return raw, val

def draw_display(name, val):
    """Draw label and value centered on OLED with minimal spacing"""
    image = Image.new("1", (OLED_WIDTH, OLED_HEIGHT))
    draw = ImageDraw.Draw(image)

    # Label on top
    bbox_label = draw.textbbox((0, 0), name, font=label_font)
    label_w = bbox_label[2] - bbox_label[0]
    label_h = bbox_label[3] - bbox_label[1]
    draw.text(((OLED_WIDTH - label_w) // 2, 0), name, font=label_font, fill=255)

    # Value below
    try:
        value_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14
        )
    except OSError:
        value_font = value_font_default

    val_str = f"{val:.2f}"
    bbox_val = draw.textbbox((0, 0), val_str, font=value_font)
    val_w = bbox_val[2] - bbox_val[0]
    val_h = bbox_val[3] - bbox_val[1]

    # Place value directly below label with 1px spacing
    y_pos = label_h + 1
    draw.text(((OLED_WIDTH - val_w) // 2, y_pos), val_str, font=value_font, fill=255)

    oled.image(image)
    oled.show()

def main():
    global current_index, last_press
    print("Press Ctrl+C to exit.")
    while True:
        # ----- request + read ECU -----
        ser.write(b"A")  # request ECU packet
        data = ser.read(200)
        if len(data) >= 32:
            ch = channels[current_index]
            raw, val = read_channel(data, ch["offset"], ch["scale"], ch["add"])
            print(f"{ch['name']}: raw={raw:5} val={val:.2f}")
            draw_display(ch["name"], val)

        # ----- check button fast -----
        if not button.value:  # active low
            now = time.time()
            if now - last_press > 0.3:  # debounce
                current_index = (current_index + 1) % len(channels)
                last_press = now

        time.sleep(0.05)  # quick loop for responsiveness

if __name__ == "__main__":
    main()
