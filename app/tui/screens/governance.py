"""Governance screen for Time Economy TUI."""

from textual.screen import Screen, ModalScreen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, DataTable, Input, Button, Label, Select
from textual.reactive import reactive

from app.services import (
    get_session, get_all_members, get_all_governance,
    create_governance, vote_governance, update_governance_status
)
from app.models import Member


class CreateGovernanceModal(ModalScreen):
    """Modal for creating a new governance entry."""

    def __init__(self):
        super().__init__()
        self.members = []

    def compose(self) -> None:
        with Container(classes="modal-form"):
            yield Static("NEW GOVERNANCE ENTRY", classes="modal-form-title")

            db = get_session()
            try:
                self.members = get_all_members(db)
                member_options = [("None", None)] + [(m.name, m.id) for m in self.members]
            finally:
                db.close()

            decision_types = [
                ("Rule Change", "rule_change"),
                ("Dispute Resolution", "dispute_resolution"),
                ("System Upgrade", "system_upgrade"),
                ("Meeting Note", "meeting_note"),
            ]

            yield Select(options=decision_types, id="decision_type", prompt="Decision type")
            yield Input(placeholder="Title", id="title")
            yield Input(placeholder="Description", id="description")
            yield Select(options=member_options, id="member", prompt="Proposed by (optional)")

            with Horizontal():
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="error", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss()
            return

        type_select = self.query_one("#decision_type", Select)
        title_input = self.query_one("#title", Input)
        desc_input = self.query_one("#description", Input)
        member_select = self.query_one("#member", Select)

        decision_type = type_select.value
        if decision_type is Select.BLANK:
            self.notify("Please select a decision type", severity="error")
            return

        title = title_input.value.strip()
        description = desc_input.value.strip()
        if not title or not description:
            self.notify("Title and description are required", severity="error")
            return

        member_id = member_select.value
        if member_id is Select.BLANK or member_id is None:
            member_id = None

        db = get_session()
        try:
            create_governance(db, title, description, str(decision_type), member_id)
            self.notify("Governance entry created!")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            db.close()


class VoteModal(ModalScreen):
    """Modal for voting on a governance entry."""

    def __init__(self, entry_id: int):
        super().__init__()
        self.entry_id = entry_id

    def compose(self) -> None:
        with Container(classes="modal-form"):
            yield Static("CAST VOTE", classes="modal-form-title")
            yield Static(f"Entry ID: {self.entry_id}")
            with Horizontal():
                yield Button("Vote FOR", variant="success", id="vote-for")
                yield Button("Vote AGAINST", variant="error", id="vote-against")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss()
            return

        vote = "for" if event.button.id == "vote-for" else "against"
        db = get_session()
        try:
            vote_governance(db, self.entry_id, vote)
            self.notify(f"Voted {vote}!")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            db.close()


class StatusModal(ModalScreen):
    """Modal for updating governance status."""

    def __init__(self, entry_id: int):
        super().__init__()
        self.entry_id = entry_id

    def compose(self) -> None:
        with Container(classes="modal-form"):
            yield Static("UPDATE STATUS", classes="modal-form-title")
            yield Static(f"Entry ID: {self.entry_id}")

            statuses = [
                ("Proposed", "proposed"),
                ("Approved", "approved"),
                ("Rejected", "rejected"),
                ("Implemented", "implemented"),
            ]
            yield Select(options=statuses, id="status", prompt="New status")

            with Horizontal():
                yield Button("Update", variant="primary", id="update")
                yield Button("Cancel", variant="error", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss()
            return

        status_select = self.query_one("#status", Select)
        status = status_select.value
        if status is Select.BLANK:
            self.notify("Please select a status", severity="error")
            return

        db = get_session()
        try:
            update_governance_status(db, self.entry_id, str(status))
            self.notify("Status updated!")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            db.close()


class GovernanceScreen(Screen):
    """Governance log screen."""

    governance_data = reactive([])
    selected_entry_id = reactive(None)

    def compose(self) -> None:
        with Container(id="governance-container"):
            yield Static("TIME ECONOMY - GOVERNANCE", id="header")
            yield Static("Keys: [g]overnance [d]ashboard [m]embers [t]ransactions [n]eeds [s]kills  [n]ew  [v]ote  [r]efresh  [q]uit", id="nav-bar")

            yield DataTable(id="governance-table")

            with Horizontal(id="gov-actions"):
                yield Button("New Entry", variant="primary", id="btn-new")
                yield Button("Vote", variant="success", id="btn-vote")
                yield Button("Status", variant="primary", id="btn-status")
                yield Button("Refresh", variant="primary", id="btn-refresh")

            yield Static("Ready", id="footer")

    def on_mount(self) -> None:
        self.refresh_data()

    def refresh_data(self) -> None:
        db = get_session()
        try:
            entries = get_all_governance(db)
            data = []
            for entry in entries:
                member = db.query(Member).filter(Member.id == entry.member_id).first()
                data.append({
                    "id": entry.id,
                    "date": entry.created_at.strftime("%Y-%m-%d"),
                    "type": entry.decision_type,
                    "status": entry.status,
                    "votes": f"+{entry.vote_for}/-{entry.vote_against}",
                    "member": member.name if member else "Community",
                    "title": entry.title,
                })
            self.governance_data = data
        finally:
            db.close()

    def watch_governance_data(self, data) -> None:
        table = self.query_one("#governance-table", DataTable)
        table.clear(columns=True)
        table.add_columns("ID", "Date", "Type", "Status", "Votes", "Proposed By", "Title")
        for entry in data:
            table.add_row(
                str(entry["id"]), entry["date"], entry["type"],
                entry["status"], entry["votes"], entry["member"],
                entry["title"][:30]
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = self.query_one("#governance-table", DataTable)
        data = table.get_row(event.row_key)
        self.selected_entry_id = int(data[0])

        for entry in self.governance_data:
            if entry["id"] == self.selected_entry_id:
                self.query_one("#footer", Static).update(
                    f"Selected: [{entry['status']}] {entry['title']} | Votes: {entry['votes']}"
                )
                break

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-new":
            self.push_screen(CreateGovernanceModal(), callback=lambda _: self.refresh_data())
        elif event.button.id == "btn-vote":
            if self.selected_entry_id:
                self.push_screen(VoteModal(self.selected_entry_id), callback=lambda _: self.refresh_data())
            else:
                self.notify("Select an entry first", severity="warning")
        elif event.button.id == "btn-status":
            if self.selected_entry_id:
                self.push_screen(StatusModal(self.selected_entry_id), callback=lambda _: self.refresh_data())
            else:
                self.notify("Select an entry first", severity="warning")
        elif event.button.id == "btn-refresh":
            self.refresh_data()
