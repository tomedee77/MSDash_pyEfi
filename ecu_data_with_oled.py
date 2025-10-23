import time
import os
import serial
import struct

# ----- Configuration -----
PORT = "/dev/ttyUSB0"         # Pi → ECU
LILLYGO_PORT = "/dev/serial0" # Pi → LilyGO
LG_BAUD = 38400
ECU_BAUD = 115200

# ----- Wait for serial devices -----
while not os.path.exists(PORT):
    print(f"Waiting for {PORT} to appear...")
    time.sleep(1)

while not os.path.exists(LILLYGO_PORT):
    print(f"Waiting for {LILLYGO_PORT} to appear...")
    time.sleep(1)

# ----- Setup serial -----
ser = serial.Serial(PORT, ECU_BAUD, timeout=1)           # ECU
lily_serial = serial.Serial(LILLYGO_PORT, LG_BAUD, timeout=1)  # LilyGO

# ----- Channels to display -----
channels = [
    {"name": "coolant", "offset": 22, "scale": 0.02, "add": 2.44},
    {"name": "mat",     "offset": 20, "scale": 0.02, "add": 7.06},
    {"name": "afr1",    "offset": 28, "scale": 0.1,  "add": 0.0},
    {"name": "map",     "offset": 18, "scale": 0.1,  "add": 0.0},
]

def read_channel(data, off, scale, add):
    """Big-endian signed 16-bit read"""
    raw = struct.unpack_from(">h", data, off)[0]
    val = raw * scale + add
    return raw, val

def main():
    print("ECU data parser started — Press Ctrl+C to exit.")
    while True:
        # ----- request + read ECU -----
        ser.write(b"A")  # request ECU packet
        data = ser.read(200)

        if len(data) >= 32:
            print(f"\nReceived {len(data)} bytes from ECU")

            # Extract and print values
            afr_raw, afr_val = read_channel(data, channels[2]["offset"], channels[2]["scale"], channels[2]["add"])
            mat_raw, mat_val = read_channel(data, channels[1]["offset"], channels[1]["scale"], channels[1]["add"])
            coolant_raw, coolant_val = read_channel(data, channels[0]["offset"], channels[0]["scale"], channels[0]["add"])
            ls_raw, ls_val = read_channel(data, channels[3]["offset"], channels[3]["scale"], channels[3]["add"])

            # Create CSV
            csv_line = f"{afr_val:.1f},{mat_val:.0f},{coolant_val:.0f},{ls_val:.2f}\n"

            # Print parsed values and what’s sent to LilyGO
            print(f"AFR={afr_val:.1f}, MAT={mat_val:.0f}, CLT={coolant_val:.0f}, MAP={ls_val:.2f}")
            print(f"→ Sending to LilyGO: {csv_line.strip()}")

            # Send to LilyGO
            lily_serial.write(csv_line.encode("utf-8"))

        else:
            print("No valid ECU data received.")

        time.sleep(0.2)

if __name__ == "__main__":
    main()
