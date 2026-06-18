#!/usr/bin/env python3
"""Remainders - Lightweight system tray reminder app for Ubuntu"""

import sys
from pathlib import Path

# Add src/ so all implementation modules are importable
sys.path.insert(0, str(Path(__file__).parent / "src"))

from app import RemindersApp

if __name__ == "__main__":
    RemindersApp().run()
