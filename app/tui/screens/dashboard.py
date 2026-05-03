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

    def compose(self) -> None:
        with Container(id="dashboard-container"):
            yield Static("TIME ECONOMY - DASHBOARD", id="header")
            yield Static("Press keys: [d]ashboard [m]embers [t]ransactions [n]eeds [g]overnance [s]kills  [r]efresh  [q]uit", id="nav-bar")

            with Grid(id="dashboard-grid"):
                # Stats cards
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

            with Horizontal(id="bottom-panels"):
                with Container(id="alerts-panel"):
                    yield Static("ALERTS", classes="panel-title")
                    yield Static("No alerts", id="alerts-content")

                with Container(id="recent-panel"):
                    yield Static("RECENT TRANSACTIONS", classes="panel-title")
                    yield DataTable(id="recent-table")

            yield Static("Ready", id="footer")

    def on_mount(self) -> None:
        self.refresh_data()

    def refresh_data(self) -> None:
        db = get_session()
        try:
            stats = get_dashboard_stats(db)
            self.stats = stats
        finally:
            db.close()

    def watch_stats(self, stats) -> None:
        if not stats:
            return

        # Update stat cards
        self.query_one("#stat-members", Static).update(str(stats["total_members"]))
        self.query_one("#stat-transactions", Static).update(str(stats["total_transactions"]))
        self.query_one("#stat-hours", Static).update(str(stats["total_hours"]))
        self.query_one("#stat-needs", Static).update(str(stats["active_needs"]))
        self.query_one("#stat-avg", Static).update(str(stats["avg_balance"]))
        self.query_one("#stat-velocity", Static).update(str(stats["recent_hours"]))

        # Update alerts
        alerts_widget = self.query_one("#alerts-content", Static)
        if stats["alerts"]:
            alert_texts = []
            for alert in stats["alerts"]:
                icon = "[!]" if alert["type"] == "deficit" else "[*]"
                alert_texts.append(f"{icon} {alert['message']}")
            alerts_widget.update("\n".join(alert_texts))
        else:
            alerts_widget.update("No alerts. System healthy.")

        # Update recent transactions table
        table = self.query_one("#recent-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Date", "From", "To", "Hours", "Status", "Description")
        for tx in stats["recent_transactions"]:
            from_name = tx.from_member.name if tx.from_member else "?"
            to_name = tx.to_member.name if tx.to_member else "?"
            status_class = f"status-{tx.status}"
            date = tx.created_at.strftime("%Y-%m-%d")
            table.add_row(date, from_name, to_name, str(tx.hours), tx.status, tx.service_description[:30])

        self.query_one("#footer", Static).update(
            f"Total members: {stats['total_members']} | Avg balance: {stats['avg_balance']} | Top skill: {stats['top_skills'][0]['name'] if stats['top_skills'] else 'N/A'}"
        )
