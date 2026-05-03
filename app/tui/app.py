"""
Time Economy TUI Application.

A rich terminal user interface for managing the time-based economy.
Built with Textual.

Usage:
    python -m app.tui.app
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Header, Footer

from app.tui.screens.dashboard import DashboardScreen
from app.tui.screens.members import MembersScreen
from app.tui.screens.transactions import TransactionsScreen
from app.tui.screens.needs import NeedsScreen
from app.tui.screens.governance import GovernanceScreen
from app.tui.screens.skills import SkillsScreen


class TimeEconomyApp(App):
    """Main TUI application."""

    CSS_PATH = "styles.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "switch_screen('dashboard')", "Dashboard"),
        ("m", "switch_screen('members')", "Members"),
        ("t", "switch_screen('transactions')", "Transactions"),
        ("n", "switch_screen('needs')", "Needs"),
        ("g", "switch_screen('governance')", "Governance"),
        ("s", "switch_screen('skills')", "Skills"),
        ("r", "refresh", "Refresh"),
    ]

    SCREENS = {
        "dashboard": DashboardScreen,
        "members": MembersScreen,
        "transactions": TransactionsScreen,
        "needs": NeedsScreen,
        "governance": GovernanceScreen,
        "skills": SkillsScreen,
    }

    def on_mount(self) -> None:
        self.title = "Time Economy"
        self.push_screen("dashboard")

    def action_refresh(self) -> None:
        current = self.screen
        if hasattr(current, 'refresh_data'):
            current.refresh_data()


def main():
    app = TimeEconomyApp()
    app.run()


if __name__ == "__main__":
    main()
