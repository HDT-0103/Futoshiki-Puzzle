"""Legacy entry point — redirects to Source.gui.app.main().

This file exists for backward compatibility with `main.py`:
    from Source.gui.gui import main as gui_main
"""
from Source.gui.app import main

__all__ = ["main"]


if __name__ == "__main__":
    main()
