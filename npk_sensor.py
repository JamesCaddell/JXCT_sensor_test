"""Shared driver for the JXCT 7-in-1 RS-485 soil sensor (Modbus RTU via MAX485)."""
import struct
import time

import serial

# (name, register, scale, unit, signed)
MAPS = {
    "jxct": [  # most common JXCT 7-in-1 layout
        ("moisture", 0x0012, 0.1, "%", False),
        ("temp", 0x0013, 0.1, "C", True),
        ("ec", 0x0015, 1, "uS/cm", False),
        ("ph", 0x0006, 0.01, "", False),
        ("N", 0x001E, 1, "mg/kg", False),
        ("P", 0x001F, 1, "mg/kg", False),
        ("K", 0x0020, 1, "mg/kg", False),
    ],
    "alt": [  # sequential layout used by some batches
        ("moisture", 0x0000, 0.1, "%", False),
        ("temp", 0x0001, 0.1, "C", True),
        ("ec", 0x0002, 1, "uS/cm", False),
        ("ph", 0x0003, 0.1, "", False),
        ("N", 0x0004, 1, "mg/kg", False),
        ("P", 0x0005, 1, "mg/kg", False),
        ("K", 0x0006, 1, "mg/kg", False),
    ],
}


class ModbusError(IOError):
    """Sensor answered with a Modbus exception (link works, register doesn't)."""


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


class Sensor:
    def __init__(self, port="/dev/serial0", baud=9600, addr=1, de_pin="BOARD11", timeout=0.5):
        self.ser = serial.Serial(port, baud, bytesize=8, parity="N", stopbits=1, timeout=timeout)
        self.addr = addr
        self.de = None
        if de_pin and de_pin.lower() != "none":
            from gpiozero import DigitalOutputDevice
            self.de = DigitalOutputDevice(de_pin, initial_value=False)

    def set_baud(self, baud):
        self.ser.baudrate = baud

    def close(self):
        self.ser.close()
        if self.de:
            self.de.close()

    def read_regs(self, start, count=1):
        frame = struct.pack(">BBHH", self.addr, 0x03, start, count)
        frame += struct.pack("<H", crc16(frame))
        self.ser.reset_input_buffer()
        if self.de:
            self.de.on()
        self.ser.write(frame)
        self.ser.flush()  # block until bytes are on the wire
        if self.de:
            self.de.off()

        head = self.ser.read(3)
        if len(head) < 3:
            raise IOError(f"no/short reply ({len(head)} bytes)")
        if head[1] & 0x80:  # exception reply: addr, func|0x80, code, crc(2)
            rest = self.ser.read(2)
            raise ModbusError(f"modbus exception code {head[2]}")
        rest = self.ser.read(head[2] + 2)
        resp = head + rest
        if len(resp) != 5 + head[2]:
            raise IOError(f"short reply: {resp.hex(' ')}")
        if crc16(resp[:-2]) != struct.unpack("<H", resp[-2:])[0]:
            raise IOError(f"bad CRC: {resp.hex(' ')}")
        n = head[2] // 2
        return list(struct.unpack(f">{n}H", resp[3:3 + 2 * n]))

    def read_all(self, map_name="jxct"):
        out = {}
        for name, reg, scale, unit, signed in MAPS[map_name]:
            raw = self.read_regs(reg, 1)[0]
            if signed and raw > 0x7FFF:
                raw -= 0x10000
            out[name] = (round(raw * scale, 2), unit)
            time.sleep(0.05)
        return out
