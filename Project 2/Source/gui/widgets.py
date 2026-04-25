"""Reusable Tkinter widget builders.

These helpers enforce the project's visual style and avoid repetitive
boilerplate. Using `tk.Label` instead of `tk.Button` is intentional:
on macOS the Aqua theme ignores the `bg` parameter of `tk.Button`,
making colored buttons render as gray. Label-based buttons respect
colors reliably across platforms.
"""
from __future__ import annotations
import tkinter as tk
from typing import Callable, Optional

from Source.gui.theme import PALETTE as P, HOVER_MAP, FONT


def section_header(parent: tk.Widget, text: str) -> None:
    """Small uppercase label used to separate sidebar/panel sections."""
    tk.Label(parent, text=text, font=(FONT, 8, "bold"),
             fg=P["lbl"], bg=P["panel"], anchor="w"
             ).pack(fill="x", padx=14, pady=(8, 2))


def separator(parent: tk.Widget) -> None:
    """Thin horizontal rule."""
    tk.Frame(parent, bg=P["brd"], height=1).pack(fill="x", padx=14, pady=6)


def label_button(parent: tk.Widget, text: str, command: Callable,
                 bg: str, fg: str = "#ffffff",
                 hover_bg: Optional[str] = None,
                 *, font: Optional[tuple] = None,
                 padx: int = 12, pady: int = 2, ipady: int = 5) -> tk.Label:
    """Create a colored clickable button using tk.Label.

    Works identically on Windows, Linux, and macOS.
    """
    if hover_bg is None:
        hover_bg = bg
    if font is None:
        font = (FONT, 9, "bold")

    btn = tk.Label(parent, text=text, font=font,
                   fg=fg, bg=bg, cursor="hand2", pady=ipady)
    btn.pack(fill="x", padx=padx, pady=pady)
    btn.bind("<Button-1>", lambda _e: command())
    btn.bind("<Enter>",    lambda _e: btn.config(bg=hover_bg))
    btn.bind("<Leave>",    lambda _e: btn.config(bg=bg))
    return btn


def action_button(parent: tk.Widget, text: str,
                  command: Callable, color: str) -> tk.Label:
    """Standard sidebar action button with automatic hover color."""
    hover = HOVER_MAP.get(color, color)
    return label_button(parent, text, command, color, "#ffffff", hover)
