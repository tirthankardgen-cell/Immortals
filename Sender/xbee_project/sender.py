
from digi.xbee.devices import XBeeDevice, RemoteXBeeDevice
from digi.xbee.models.address import XBee64BitAddress

PORT = "/dev/ttyUSB0"
BAUD_RATE = 9600
RECEIVER_ADDRESS = "0013A200408DF0CE"

def main():
    device = XBeeDevice(PORT, BAUD_RATE)

    try:
        device.open()

        receiver = RemoteXBeeDevice(
            device,
            XBee64BitAddress.from_hex_string(RECEIVER_ADDRESS)
        )

        print("XBee sender started.")
        print("Type a message, or 'exit' to quit.")

        while True:
            message = input("Enter message: ").strip()

            if message.lower() == "exit":
                break

            if not message:
                continue

            device.send_data(receiver, message)
            print("Message sent:", message)

    except Exception as e:
        print("Transmission error:", repr(e))

    finally:
        if device.is_open():
            device.close()

if __name__ == "__main__":
    main()
