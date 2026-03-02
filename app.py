#!/usr/bin/env python3
"""Global Stock Monitor TUI - Toss Invest style dashboard."""
from __future__ import annotations

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from textual.app import App
from textual.binding import Binding

from screens.dashboard import DashboardScreen


class StockMonitorApp(App):
    """Main application for Global Stock Monitor."""

    TITLE = "Global Stock Monitor"
    SUB_TITLE = "US & KR Markets"
    CSS_PATH = "styles/app.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
    ]

    SCREENS = {
        "dashboard": DashboardScreen,
    }

    def on_mount(self) -> None:
        self.push_screen("dashboard")


if __name__ == "__main__":
    app = StockMonitorApp()
    app.run()
