
from digi.xbee.devices import XBeeDevice

# USB port of sender XBee
PORT = "/dev/ttyUSB0"

# Must match XCTU baud rate
BAUD_RATE = 9600


def main():

    device = XBeeDevice(PORT, BAUD_RATE)

    try:
        device.open()

        print("--------------------------------")
        print("      XBEE SENDER STARTED")
        print("--------------------------------")
        print("Type a message and press ENTER.")
        print("Type exit to stop.\n")

        while True:

            message = input("Enter message: ")

            if message.lower() == "exit":
                break

            if message.strip() == "":
                continue

            # Broadcast message to Zigbee network
            device.send_data_broadcast(message)

            print("Message transmitted:", message)

    except KeyboardInterrupt:
        print("\nSender stopped.")

    except Exception as e:
        print("Transmission error:", e)

    finally:
        if device.is_open():
            device.close()


if __name__ == "__main__":
    main()
