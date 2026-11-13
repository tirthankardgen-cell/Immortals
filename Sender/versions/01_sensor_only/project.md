# Version 01 - original sensor-only monitor

Recovered byte-for-byte from the verified pre-Zigbee backup `before-zigbee.tar.gz`.
Local sensing, processing and HDMI dashboard are implemented; the old Zigbee
button is cosmetic and there is no radio forwarding backend.

This is an independent rollback copy. It is not started automatically. Stop the
active sender before using it; both versions use the same single-instance lock.
On the sender Pi run:

```sh
cd /home/pi/Desktop/Immortals_Monitor/versions/01_sensor_only
../../.venv/bin/python main.py
```

Use the parent project's Pi virtual environment, since sensor dependencies are
platform-specific. The preserved desktop launcher points to the active parent
application; use the command above to launch this historical version explicitly.
