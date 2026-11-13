#!/usr/bin/env python3
"""Raspberry Pi 5 sensor monitor: AD8232+ADS1115, MAX30102, BMP180, DHT22, MLX90614."""
import time, sys
from datetime import datetime
import smbus2

BUS_NO = 1
ADS_ADDR, MAX_ADDR, BMP_ADDR, MLX_ADDR = 0x48, 0x57, 0x77, 0x5A

def s16(bus, addr, reg):
    b = bus.read_i2c_block_data(addr, reg, 2)
    n = (b[0] << 8) | b[1]
    return n - 65536 if n > 32767 else n

def u16(bus, addr, reg):
    b = bus.read_i2c_block_data(addr, reg, 2)
    return (b[0] << 8) | b[1]

class BMP180:
    def __init__(self, bus, addr=0x77, oss=1):
        self.b, self.a, self.oss = bus, addr, oss
        self.ac1=s16(bus,addr,0xAA); self.ac2=s16(bus,addr,0xAC)
        self.ac3=s16(bus,addr,0xAE); self.ac4=u16(bus,addr,0xB0)
        self.ac5=u16(bus,addr,0xB2); self.ac6=u16(bus,addr,0xB4)
        self.b1=s16(bus,addr,0xB6); self.b2=s16(bus,addr,0xB8)
        self.mc=s16(bus,addr,0xBC); self.md=s16(bus,addr,0xBE)
    def read(self):
        b,a,o=self.b,self.a,self.oss
        b.write_byte_data(a,0xF4,0x2E); time.sleep(.005)
        d=b.read_i2c_block_data(a,0xF6,2); ut=(d[0]<<8)|d[1]
        x1=((ut-self.ac6)*self.ac5)>>15
        den=x1+self.md
        if den == 0: raise RuntimeError("BMP180 compensation error")
        x2=(self.mc<<11)//den; b5=x1+x2
        temp=((b5+8)>>4)/10.0
        b.write_byte_data(a,0xF4,0x34+(o<<6))
        time.sleep([.005,.008,.014,.026][o])
        d=b.read_i2c_block_data(a,0xF6,3)
        up=((d[0]<<16)|(d[1]<<8)|d[2])>>(8-o)
        b6=b5-4000
        x1=(self.b2*((b6*b6)>>12))>>11; x2=(self.ac2*b6)>>11
        x3=x1+x2; b3=(((self.ac1*4+x3)<<o)+2)>>2
        x1=(self.ac3*b6)>>13; x2=(self.b1*((b6*b6)>>12))>>16
        x3=(x1+x2+2)>>2; b4=(self.ac4*(x3+32768))>>15
        if not b4: raise RuntimeError("BMP180 pressure divisor is zero")
        b7=(up-b3)*(50000>>o)
        p=(b7*2)//b4 if b7 < 0x80000000 else (b7//b4)*2
        x1=(p>>8)*(p>>8); x1=(x1*3038)>>16; x2=(-7357*p)>>16
        p=p+((x1+x2+3791)>>4)
        return temp,p


class MAX30102:
    def __init__(self, bus, addr=0x57):
        self.b = bus
        self.a = addr

        self.part = bus.read_byte_data(addr, 0xFF)

        if self.part != 0x15:
            raise RuntimeError(
                f"Unexpected MAX30102 Part ID: {hex(self.part)}"
            )

        # Reset sensor
        bus.write_byte_data(addr, 0x09, 0x40)
        time.sleep(0.2)

        # Configure sensor and clear FIFO
        for r, v in [
            (0x02, 0x00),
            (0x03, 0x00),
            (0x04, 0x00),
            (0x05, 0x00),
            (0x06, 0x00),
            (0x08, 0x4F),
            (0x09, 0x03),
            (0x0A, 0x27),
            (0x0C, 0x24),
            (0x0D, 0x24)
        ]:
            bus.write_byte_data(addr, r, v)

        time.sleep(0.1)

    def read_latest(self):
        from smbus2 import i2c_msg

        b, a = self.b, self.a

        wr = b.read_byte_data(a, 0x04) & 0x1F
        rd = b.read_byte_data(a, 0x06) & 0x1F

        count = (wr - rd) & 0x1F

        if count == 0:
            return None

        latest = None

        for _ in range(count):
            w = i2c_msg.write(a, [0x07])
            r = i2c_msg.read(a, 6)
            b.i2c_rdwr(w, r)

            d = list(r)

            red = ((d[0] << 16) |
                   (d[1] << 8) |
                   d[2]) & 0x3FFFF

            ir = ((d[3] << 16) |
                  (d[4] << 8) |
                  d[5]) & 0x3FFFF

            latest = (red, ir)

        return latest


def attempt(label, fn):
    try: return fn(), None
    except Exception as e: return None, f"{label}: {type(e).__name__}: {e}"


def main():
    try:
        import board
        import adafruit_dht
    except Exception:
        board = None
        adafruit_dht = None

    try:
        import busio
        import adafruit_ads1x15.ads1115 as ADS
        from adafruit_ads1x15.analog_in import AnalogIn
    except Exception:
        busio = ADS = AnalogIn = None

    bus = smbus2.SMBus(BUS_NO)

    ecg = None
    maxs = None
    bmp = None
    mlx = False
    dht = None

    print("Raspberry Pi 5 sensor monitor")
    print("Press Ctrl+C to stop")

    warnings = []

    # ADS1115 / ECG
    if busio and ADS and board:
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            adc = ADS.ADS1115(i2c, address=ADS_ADDR)
            adc.gain = 1
            ecg = AnalogIn(adc, ADS.P0)
        except Exception as e:
            warnings.append(f"ECG initialization: {e}")

    # MAX30102
    maxs, err = attempt(
        "MAX30102",
        lambda: MAX30102(bus, MAX_ADDR)
    )
    if err:
        warnings.append(err)

    # BMP180
    bmp, err = attempt(
        "BMP180",
        lambda: BMP180(bus, BMP_ADDR)
    )
    if err:
        warnings.append(err)

    # MLX90614
    try:
        bus.read_word_data(MLX_ADDR, 0x06)
        mlx = True
    except Exception as e:
        warnings.append(f"MLX90614: {e}")

    # DHT22
    if board and adafruit_dht:
        try:
            dht = adafruit_dht.DHT22(
                board.D4,
                use_pulseio=False
            )
        except Exception as e:
            warnings.append(f"DHT22: {e}")

    for warning in warnings:
        print("WARNING:", warning)

    # Independent sensor schedules
    last_ecg = 0
    last_bmp = 0
    last_mlx = 0
    last_dht = 0

    # ECG and MAX30102 polling intervals
    ECG_INTERVAL = 0.02
    MAX_INTERVAL = 0.05

    last_max = 0

    try:
        while True:

            now = time.monotonic()
            out = []

            timestamp = datetime.now().strftime(
                "[%Y-%m-%d %H:%M:%S]"
            )

            # MAX30102: frequent FIFO reading
            if maxs and now - last_max >= MAX_INTERVAL:
                last_max = now

                v, e = attempt(
                    "MAX30102",
                    maxs.read_latest
                )

                if e:
                    out.append(f"MAX30102 ERROR: {e}")

                elif v is None:
                    out.append("MAX30102: waiting")

                else:
                    out.append(
                        f"MAX30102 RED={v[0]} IR={v[1]}"
                    )

            # ECG
            if ecg and now - last_ecg >= ECG_INTERVAL:
                last_ecg = now

                v, e = attempt(
                    "ECG",
                    lambda: (ecg.value, ecg.voltage)
                )

                if e:
                    out.append(f"ECG ERROR: {e}")
                else:
                    out.append(
                        f"ECG raw={v[0]}, voltage={v[1]:.4f} V"
                    )

            # BMP180: every 1 second
            if bmp and now - last_bmp >= 1.0:
                last_bmp = now

                v, e = attempt("BMP180", bmp.read)

                if e:
                    out.append(f"BMP180 ERROR: {e}")
                else:
                    out.append(
                        f"BMP180={v[0]:.2f} C, "
                        f"pressure={v[1]/100:.2f} hPa"
                    )

            # MLX90614: every 0.5 seconds
            if mlx and now - last_mlx >= 0.5:
                last_mlx = now

                v, e = attempt(
                    "MLX90614",
                    lambda: (
                        bus.read_word_data(MLX_ADDR, 0x06)
                        * 0.02 - 273.15,

                        bus.read_word_data(MLX_ADDR, 0x07)
                        * 0.02 - 273.15
                    )
                )

                if e:
                    out.append(f"MLX90614 ERROR: {e}")
                else:
                    out.append(
                        f"MLX ambient={v[0]:.2f} C, "
                        f"object={v[1]:.2f} C"
                    )

            # DHT22: at least 2.1 seconds between reads
            if dht and now - last_dht >= 2.1:
                last_dht = now

                v, e = attempt(
                    "DHT22",
                    lambda: (
                        dht.temperature,
                        dht.humidity
                    )
                )

                if e or not v or v[0] is None:
                    out.append("DHT22: reading unavailable")
                else:
                    out.append(
                        f"DHT22={v[0]:.2f} C, "
                        f"humidity={v[1]:.1f}%"
                    )

            if out:
                print(
                    timestamp + " | " + " | ".join(out),
                    flush=True
                )

            time.sleep(0.005)

    except KeyboardInterrupt:
        print("\nSensor monitoring stopped.")

    finally:
        if dht:
            try:
                dht.exit()
            except Exception:
                pass


        bus.close()


if __name__ == "__main__":
    main()


if __name__=="__main__":
    main()
