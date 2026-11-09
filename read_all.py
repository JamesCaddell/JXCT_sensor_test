#!/usr/bin/env python3
"""Read moisture, temp, EC, pH, N, P, K from the JXCT 7-in-1 sensor.

  python3 read_all.py                      # print every 2 s
  python3 read_all.py --once               # single reading
  python3 read_all.py --csv log.csv        # also append to CSV
  python3 read_all.py --map alt            # alternate register layout
  python3 read_all.py --scan               # dump raw registers 0x00-0x22
"""
import argparse
import csv
import os
import sys
import time
from datetime import datetime

from npk_sensor import MAPS, Sensor


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/serial0")
    ap.add_argument("--baud", type=int, default=9600)
    ap.add_argument("--addr", type=int, default=1)
    ap.add_argument("--de-pin", default="BOARD11", help="physical pin as BOARDxx, or 'none'")
    ap.add_argument("--map", choices=MAPS, default="jxct")
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--csv")
    ap.add_argument("--scan", action="store_true")
    a = ap.parse_args()

    s = Sensor(a.port, a.baud, a.addr, a.de_pin)
    try:
        if a.scan:
            for reg in range(0x00, 0x23):
                try:
                    print(f"0x{reg:04X}: {s.read_regs(reg, 1)[0]}")
                except IOError as e:
                    print(f"0x{reg:04X}: -- ({e})")
                time.sleep(0.05)
            return

        writer = None
        if a.csv:
            new = not os.path.exists(a.csv)
            f = open(a.csv, "a", newline="")
            writer = csv.writer(f)
            if new:
                writer.writerow(["timestamp"] + [m[0] for m in MAPS[a.map]])

        print(f"{a.port} @ {a.baud}, addr {a.addr}, map={a.map}. Ctrl+C to stop.")
        while True:
            try:
                r = s.read_all(a.map)
                ts = datetime.now().isoformat(timespec="seconds")
                print(ts, " | ".join(f"{k} {v}{u}" for k, (v, u) in r.items()))
                if writer:
                    writer.writerow([ts] + [v for v, _ in r.values()])
                    f.flush()
            except IOError as e:
                print("read failed:", e, file=sys.stderr)
            if a.once:
                break
            time.sleep(a.interval)
    except KeyboardInterrupt:
        pass
    finally:
        s.close()


if __name__ == "__main__":
    main()
