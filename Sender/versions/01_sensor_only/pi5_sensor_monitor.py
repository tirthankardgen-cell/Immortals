#!/usr/bin/env python3
"""Compatibility launcher. The complete application is in main.py.

The original updated Downloads script is preserved in reference/.
"""
from pathlib import Path
import os
import sys

if __name__ == '__main__':
    os.execv(sys.executable, [sys.executable, str(Path(__file__).with_name('main.py')), *sys.argv[1:]])
