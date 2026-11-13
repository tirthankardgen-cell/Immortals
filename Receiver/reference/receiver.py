from digi.xbee.devices import XBeeDevice

# USB port of receiver XBee
PORT = "/dev/ttyUSB0"

# Must match XCTU baud rate
BAUD_RATE = 9600


def main():

    device = XBeeDevice(PORT, BAUD_RATE)

    try:
        device.open()

        print("--------------------------------")
        print("     XBEE RECEIVER STARTED")
        print("--------------------------------")
        print("Waiting for wireless messages...")
        print("Press CTRL+C to exit\n")

        def receive_callback(xbee_message):

            sender = xbee_message.remote_device
            data = xbee_message.data.decode(
                "utf-8", errors="replace"
            )

            print(f"\nReceived from {sender.get_64bit_addr()}:")
            print(data)
            print("\nWaiting for next message...")

        # Register incoming data callback
        device.add_data_received_callback(receive_callback)

        # Keep program running
        while True:
            input()

    except KeyboardInterrupt:
        print("\nReceiver stopped.")

    except Exception as e:
        print("Error:", e)

    finally:
        if device.is_open():
            device.close()


if __name__ == "__main__":
    main()
