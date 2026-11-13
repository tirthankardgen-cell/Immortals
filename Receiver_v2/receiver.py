"""Compatibility launcher for the original receiver.py command on the Pi."""
import runpy

if __name__ == '__main__':
    from pathlib import Path
    runpy.run_path(str(Path(__file__).with_name('main.py')), run_name='__main__')
