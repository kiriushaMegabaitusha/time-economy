"""Dashboard screen for Time Economy TUI."""

from textual.screen import Screen
from textual.containers import Container, Grid, Horizontal, Vertical
from textual.widgets import Static, DataTable, Label, Button, Rule
from textual.reactive import reactive
from textual.coordinate import Coordinate

from app.services import get_session, get_dashboard_stats


class DashboardScreen(Screen):
    """Main dashboard showing system overview."""

    stats = reactive(None)
    _initial_load = True

    BINDINGS = [
        ("r", "action_refresh", "Refresh"),
        ("enter", "action_select", "Select"),
    ]

    def compose(self) -> None:
        with Container(id="dashboard-container"):
            yield Static("TIME ECONOMY - DASHBOARD", id="header")
            yield Static("D:Dash M:Members T:Trans N:Needs G:Govern S:Skills | R:Refresh Q:Quit", id="nav-bar")

            with Vertical(id="content"):
                with Grid(id="dashboard-grid"):
                    with Container(classes="stat-card"):
                        yield Static("0", id="stat-members", classes="stat-value")
                        yield Static("Active Members", classes="stat-label")

                    with Container(classes="stat-card"):
                        yield Static("0", id="stat-transactions", classes="stat-value")
                        yield Static("Transactions", classes="stat-label")

                    with Container(classes="stat-card"):
                        yield Static("0", id="stat-hours", classes="stat-value")
                        yield Static("Total Hours", classes="stat-label")

                    with Container(classes="stat-card"):
                        yield Static("0", id="stat-needs", classes="stat-value")
                        yield Static("Open Needs", classes="stat-label")

                    with Container(classes="stat-card"):
                        yield Static("0", id="stat-avg", classes="stat-value")
                        yield Static("Avg Balance", classes="stat-label")

                    with Container(classes="stat-card"):
                        yield Static("0", id="stat-velocity", classes="stat-value")
                        yield Static("Hours (30d)", classes="stat-label")

                with Horizontal(id="bottom-panels", classes="content-area"):
                    with Container(id="alerts-panel", classes="split-left"):
                        yield Static("ALERTS", classes="panel-title")
                        yield DataTable(id="alerts-table")

                    with Container(id="recent-panel", classes="split-right"):
                        yield Static("RECENT TRANSACTIONS", classes="panel-title")
                        yield DataTable(id="recent-table")

            with Horizontal(id="action-bar", classes="action-bar"):
                yield Button("Refresh", variant="primary", id="btn-refresh")

            yield Static("Ready - Press [?] for keyboard shortcuts", id="footer")

    def on_mount(self) -> None:
        self.refresh_data()
        # Focus is handled by watch_stats via set_timer

    def refresh_data(self) -> None:
        db = get_session()
        try:
            stats = get_dashboard_stats(db)
            self.stats = stats
        finally:
            db.close()
            # Reset initial load flag so next refresh focuses properly
            self._initial_load = True

    def watch_stats(self, stats) -> None:
        if not stats:
            return

        self.query_one("#stat-members", Static).update(str(stats["total_members"]))
        self.query_one("#stat-transactions", Static).update(str(stats["total_transactions"]))
        self.query_one("#stat-hours", Static).update(str(stats["total_hours"]))
        self.query_one("#stat-needs", Static).update(str(stats["active_needs"]))
        self.query_one("#stat-avg", Static).update(str(stats["avg_balance"]))
        self.query_one("#stat-velocity", Static).update(str(stats["recent_hours"]))

        alerts_table = self.query_one("#alerts-table", DataTable)
        alerts_table.clear(columns=True)
        alerts_table.add_columns("Icon", "Type", "Message")
        if stats["alerts"]:
            for alert in stats["alerts"]:
                icon = "[!]" if alert["type"] == "deficit" else "[*]"
                alerts_table.add_row(icon, alert["type"], alert["message"])
        else:
            alerts_table.add_row("[OK]", "healthy", "System healthy - no alerts")

        table = self.query_one("#recent-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Date", "From", "To", "Hours", "Status", "Description")
        for tx in stats["recent_transactions"]:
            from_name = tx.from_member.name if tx.from_member else "?"
            to_name = tx.to_member.name if tx.to_member else "?"
            date = tx.created_at.strftime("%Y-%m-%d")
            status_display = self._format_status(tx.status)
            table.add_row(date, from_name, to_name, str(tx.hours), status_display, tx.service_description[:30])

        # Focus table for keyboard navigation
        if self._initial_load:
            def do_focus():
                table.focus()
                self.app.set_focus(table)
                if table.row_count > 0:
                    table.move_cursor(row=0, column=0)
            self.set_timer(0.2, do_focus)
            self._initial_load = False

        self.query_one("#footer", Static).update(
            f"Members: {stats['total_members']} | Avg: {stats['avg_balance']} | Top: {stats['top_skills'][0]['name'] if stats['top_skills'] else 'N/A'} | Press [R] to refresh"
        )

    def _format_status(self, status: str) -> str:
        status_map = {
            "pending": "[?] pending",
            "completed": "[*] completed",
            "disputed": "[!] disputed",
        }
        return status_map.get(status, f"[?] {status}")

    def action_refresh(self) -> None:
        """Keyboard shortcut: Refresh data."""
        self.refresh_data()

    def action_select(self) -> None:
        """Keyboard shortcut: Focus recent transactions table."""
        table = self.query_one("#recent-table", DataTable)
        table.focus()
        self.app.set_focus(table)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-refresh":
            self.refresh_data()