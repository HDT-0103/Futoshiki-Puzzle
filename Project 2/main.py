#!/usr/bin/env python3
"""Project launcher.

This repository now keeps a single main entrypoint for GUI usage.
"""

from __future__ import annotations

from Source.gui.gui import main as gui_main


if __name__ == "__main__":
    gui_main()
