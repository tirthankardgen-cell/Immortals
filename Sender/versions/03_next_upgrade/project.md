# Version 03 - ready for the next upgrade

Independent runnable copy of the current Zigbee release, kept as the starting
point for the next phase. It has no experimental changes and is not auto-started.
It uses the parent project's Pi virtual environment and the same hardware-owner
lock, so stop the active sender before launching this version.

```sh
cd /home/pi/Desktop/Immortals_Monitor/versions/03_next_upgrade
../../.venv/bin/python main.py
```

Planned next stage, to be implemented after this transport work: improve the UI,
then add the other requested features. Preserve sensor source/quality labels,
unavailable/null readings, independent workers, and bounded live transport.
Do not deploy experimental code over the verified release until it is tested.
