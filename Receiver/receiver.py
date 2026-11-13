"""Compatibility launcher for the original receiver.py command on the Pi."""
import runpy

if __name__ == '__main__':
    runpy.run_path('/home/pi/Desktop/Immortals_Receiver/main.py', run_name='__main__')
