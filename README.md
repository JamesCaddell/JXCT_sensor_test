# npk-sensor

Python tools for the **JXCT 7-in-1 RS-485 soil sensor** (moisture, temperature, EC, pH, N, P, K) on a **Raspberry Pi 4** through a **MAX485** module.

| File | Purpose |
|---|---|
| `baud_test.py` | Finds the sensor's baud rate (and address) |
| `read_all.py` | Reads all 7 values; optional CSV logging |
| `npk_sensor.py` | Shared Modbus RTU driver used by both scripts |

## Wiring (physical pin numbers)

| From | To |
|---|---|
| Pi pin 2 (5V) | MAX485 VCC |
| Pi pin 6 (GND) | MAX485 GND |
| Pi pin 8 (TXD) | MAX485 DI |
| Pi pin 10 (RXD) | MAX485 RO * |
| Pi pin 11 | MAX485 DE + RE (bridged together) |
| Sensor yellow | MAX485 A |
| Sensor blue | MAX485 B |
| Sensor brown | Power supply + (5–24 V) |
| Sensor black | Power supply − |
| Power supply − | Pi pin 6 (common ground) |

\* RO outputs 5 V logic. Use a level shifter or voltage divider, or power the MAX485 from pin 1 (3.3 V) instead of pin 2.

If your MAX485 board switches direction automatically (no DE/RE pins), skip pin 11 and add `--de-pin none` to every command.

## Setup

```bash
# 1. Enable the hardware UART
sudo raspi-config
#    Interface Options -> Serial Port
#    Login shell over serial? NO
#    Serial port hardware enabled? YES
sudo reboot

# 2. Get the code
git clone https://github.com/<your-username>/npk-sensor.git
cd npk-sensor
pip install -r requirements.txt --break-system-packages

# 3. Check that the UART exists
ls -l /dev/serial0
```

## Usage

### 1. Find the baud rate
```bash
python3 baud_test.py
```
It tries 9600, 4800, 2400, 19200, 38400, 57600, and 115200 at address 1, then prints the `read_all.py` command to use.

If nothing answers:
- `python3 baud_test.py --addr 255` sends a broadcast query (only use this with one sensor on the bus)
- `python3 baud_test.py --scan-addr` tries addresses 1–247 (slow)

### 2. Read all values
```bash
python3 read_all.py                     # every 2 s
python3 read_all.py --baud 4800         # use the baud baud_test.py found
python3 read_all.py --once              # one reading
python3 read_all.py --csv log.csv       # also log to CSV
python3 read_all.py --interval 10       # every 10 s
```

### Values look wrong?
Different sensor batches store the readings at different registers.
```bash
python3 read_all.py --scan       # dump raw registers 0x00–0x22
python3 read_all.py --map alt    # try the alternate layout
```
Quick check: put the probe in a cup of water. Moisture should jump and EC should rise.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `no/short reply` at every baud | Swap A/B, check sensor power, confirm common ground, check that serial is enabled |
| `Permission denied: /dev/serial0` | `sudo usermod -aG dialout $USER`, then log out and back in |
| `bad CRC` | Loose wire or noise; keep the A/B pair twisted and short |
| Readings are all 0 | Probe isn't in soil/water, or you're using the wrong `--map` |
| `modbus exception code 2` | Link works but the register doesn't exist; use `--scan` |

## Register maps

**`jxct` (default)**

| Value | Register | Scale |
|---|---|---|
| pH | 0x0006 | ×0.01 |
| Moisture % | 0x0012 | ×0.1 |
| Temp °C | 0x0013 | ×0.1 (signed) |
| EC µS/cm | 0x0015 | ×1 |
| N / P / K mg/kg | 0x001E / 0x001F / 0x0020 | ×1 |

**`alt`**

| Value | Register | Scale |
|---|---|---|
| Moisture % | 0x0000 | ×0.1 |
| Temp °C | 0x0001 | ×0.1 (signed) |
| EC µS/cm | 0x0002 | ×1 |
| pH | 0x0003 | ×0.1 |
| N / P / K mg/kg | 0x0004 / 0x0005 / 0x0006 | ×1 |

Protocol: Modbus RTU, function 0x03, 8N1, default address 1.
