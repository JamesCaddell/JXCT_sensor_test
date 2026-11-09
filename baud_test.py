#!/usr/bin/env python3
"""Find the sensor's baud rate (and address) by trying each combination.

  python3 baud_test.py                  # addr 1 at common bauds
  python3 baud_test.py --addr 255       # 255 = broadcast query (single sensor on bus only)
  python3 baud_test.py --scan-addr      # try addresses 1-247 at each baud (slow)
"""
import argparse
import time

from npk_sensor import ModbusError, Sensor

BAUDS = [9600, 4800, 2400, 19200, 38400, 57600, 115200]


def probe(s):
    """True if anything valid comes back (data or a Modbus exception)."""
    for reg in (0x0012, 0x0000):
        try:
            v = s.read_regs(reg, 1)
            return f"reg 0x{reg:04X} = {v[0]}"
        except ModbusError as e:
            return f"replied with {e}"
        except IOError:
            continue
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/serial0")
    ap.add_argument("--de-pin", default="BOARD11", help="physical pin as BOARDxx, or 'none'")
    ap.add_argument("--addr", type=int, default=1)
    ap.add_argument("--scan-addr", action="store_true")
    a = ap.parse_args()

    addrs = range(1, 248) if a.scan_addr else [a.addr]
    s = Sensor(a.port, BAUDS[0], addrs[0], a.de_pin, timeout=0.3)
    found = []
    try:
        for baud in BAUDS:
            s.set_baud(baud)
            print(f"baud {baud:>6} ...", end="", flush=True)
            hit = None
            for addr in addrs:
                s.addr = addr
                r = probe(s)
                if r:
                    hit = (baud, addr, r)
                    break
                time.sleep(0.02)
            if hit:
                print(f" FOUND  addr {hit[1]}  ({hit[2]})")
                found.append(hit)
            else:
                print(" no reply")
    finally:
        s.close()

    if found:
        b, ad, _ = found[0]
        print(f"\nUse: python3 read_all.py --baud {b} --addr {ad}")
    else:
        print("\nNothing answered. Check: sensor power, A/B swapped, common GND, "
              "serial enabled in raspi-config, DE/RE wiring (or try --de-pin none).")


if __name__ == "__main__":
    main()
