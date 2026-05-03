"""Governance screen for Time Economy TUI."""

from textual.screen import Screen, ModalScreen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, DataTable, Input, Button, Label, Select
from textual.reactive import reactive

from app.services import (
    get_session, get_all_members, get_all_governance,
    create_governance, vote_governance, update_governance_status,
    update_governance, delete_governance
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

            yield Label("Decision Type *", id="lbl-type")
            yield Select(options=decision_types, id="decision_type", prompt="Select type")
            yield Label("Title *", id="lbl-title")
            yield Input(placeholder="Brief title for the decision", id="title")
            yield Label("Description *", id="lbl-desc")
            yield Input(placeholder="Detailed description of the proposal", id="description")
            yield Label("Proposed By", id="lbl-member")
            yield Select(options=member_options, id="member", prompt="Optional - select proposer")

            with Horizontal(classes="modal-form-actions"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="warning", id="cancel")

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
            self.notify("Select a decision type", severity="error")
            return

        title = title_input.value.strip()
        description = desc_input.value.strip()
        if not title:
            self.notify("Title is required", severity="error")
            return
        if not description:
            self.notify("Description is required", severity="error")
            return

        member_id = member_select.value
        if member_id is Select.BLANK or member_id is None:
            member_id = None

        db = get_session()
        try:
            create_governance(db, title, description, str(decision_type), member_id)
            self.notify("Governance entry created!", severity="information")
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
            yield Static("CAST YOUR VOTE", classes="modal-form-title")
            yield Static(f"Entry ID: {self.entry_id}")
            yield Static("Your vote matters - community decisions affect everyone.", classes="help-text")
            with Horizontal(classes="modal-form-actions"):
                yield Button("Vote FOR", variant="success", id="vote-for")
                yield Button("Vote AGAINST", variant="error", id="vote-against")
                yield Button("Cancel", variant="warning", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss()
            return

        vote = "for" if event.button.id == "vote-for" else "against"
        db = get_session()
        try:
            vote_governance(db, self.entry_id, vote)
            self.notify(f"Vote cast: {vote.upper()}", severity="information")
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
            yield Label("New Status *", id="lbl-status")
            yield Select(options=statuses, id="status", prompt="Select new status")

            with Horizontal(classes="modal-form-actions"):
                yield Button("Update", variant="primary", id="update")
                yield Button("Cancel", variant="warning", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss()
            return

        status_select = self.query_one("#status", Select)
        status = status_select.value
        if status is Select.BLANK:
            self.notify("Select a new status", severity="error")
            return

        db = get_session()
        try:
            update_governance_status(db, self.entry_id, str(status))
            self.notify("Status updated!", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            db.close()


class EditGovernanceModal(ModalScreen):
    """Modal for editing a governance entry."""

    def __init__(self, entry_id: int):
        super().__init__()
        self.entry_id = entry_id
        self.entry = None

    def compose(self) -> None:
        db = get_session()
        try:
            from app.models import GovernanceLog
            self.entry = db.query(GovernanceLog).filter(GovernanceLog.id == self.entry_id).first()
        finally:
            db.close()

        with Container(classes="modal-form"):
            yield Static("EDIT GOVERNANCE ENTRY", classes="modal-form-title")
            decision_types = [
                ("Rule Change", "rule_change"),
                ("Dispute Resolution", "dispute_resolution"),
                ("System Upgrade", "system_upgrade"),
                ("Meeting Note", "meeting_note"),
            ]
            yield Label("Decision Type *", id="lbl-type")
            yield Select(options=decision_types, id="decision_type", prompt="Select type")
            yield Label("Title *", id="lbl-title")
            yield Input(placeholder="Brief title", value=self.entry.title if self.entry else "", id="title")
            yield Label("Description *", id="lbl-desc")
            yield Input(placeholder="Detailed description", value=self.entry.description if self.entry else "", id="description")
            with Horizontal(classes="modal-form-actions"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="warning", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss()
            return

        type_select = self.query_one("#decision_type", Select)
        title_input = self.query_one("#title", Input)
        desc_input = self.query_one("#description", Input)

        decision_type = type_select.value
        if decision_type is Select.BLANK:
            self.notify("Select a decision type", severity="error")
            return

        title = title_input.value.strip()
        description = desc_input.value.strip()
        if not title:
            self.notify("Title is required", severity="error")
            return
        if not description:
            self.notify("Description is required", severity="error")
            return

        db = get_session()
        try:
            update_governance(db, self.entry_id, title, description, str(decision_type))
            self.notify("Governance entry updated!", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            db.close()


class DeleteGovernanceModal(ModalScreen):
    """Modal for confirming governance entry deletion."""

    def __init__(self, entry_id: int):
        super().__init__()
        self.entry_id = entry_id

    def compose(self) -> None:
        with Container(classes="modal-form"):
            yield Static("DELETE GOVERNANCE ENTRY", classes="modal-form-title")
            yield Static("!", classes="confirm-danger")
            yield Static(f"Confirm deletion of Governance Entry #{self.entry_id}?", classes="confirm-warning")
            yield Static("This action CANNOT be undone.")
            with Horizontal(classes="modal-form-actions"):
                yield Button("DELETE", variant="error", id="confirm")
                yield Button("Cancel", variant="primary", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss()
            return

        db = get_session()
        try:
            delete_governance(db, self.entry_id)
            self.notify("Governance entry deleted!", severity="warning")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            db.close()


class GovernanceScreen(Screen):
    """Governance log screen - consistent Universal Design layout."""

    governance_data = reactive([])
    selected_entry_id = reactive(None)
    _initial_load = True

    BINDINGS = [
        ("n", "action_new", "New"),
        ("e", "action_edit", "Edit"),
        ("v", "action_vote", "Vote"),
        ("u", "action_status", "Status"),
        ("x", "action_delete", "Delete"),
        ("r", "action_refresh", "Refresh"),
        ("enter", "action_select", "Select"),
    ]

    def compose(self) -> None:
        with Container(id="governance-container", classes="screen-container"):
            yield Static("TIME ECONOMY - GOVERNANCE", id="header")
            yield Static("D:Dash M:Members T:Trans N:Needs G:Govern S:Skills | N:New E:Edit V:Vote U:Status X:Del R:Refresh Q:Quit", id="nav-bar")

            with Container(id="content", classes="content-area"):
                yield DataTable(id="governance-table")

            with Horizontal(id="gov-actions", classes="action-bar"):
                yield Button("New Entry", variant="primary", id="btn-new")
                yield Button("Edit", variant="primary", id="btn-edit")
                yield Button("Vote", variant="success", id="btn-vote")
                yield Button("Status", variant="primary", id="btn-status")
                yield Button("Delete", variant="error", id="btn-delete")
                yield Button("Refresh", variant="primary", id="btn-refresh")

            yield Static("Use arrow keys to navigate, Enter to select", id="footer")

    def on_mount(self) -> None:
        self.refresh_data()
        # Focus is handled by watch_governance_data via set_timer

    def set_focus_table(self, table_id: str) -> None:
        """Focus the DataTable (not used for initial focus)."""
        pass

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
                    "status": self._format_status(entry.status),
                    "raw_status": entry.status,
                    "votes": f"+{entry.vote_for}/-{entry.vote_against}",
                    "member": member.name if member else "Community",
                    "title": entry.title,
                })
            self.governance_data = data
        finally:
            db.close()
            # Reset initial load flag so next refresh focuses properly
            self._initial_load = True

    def _format_status(self, status: str) -> str:
        status_map = {
            "proposed": "[>] proposed",
            "approved": "[v] approved",
            "rejected": "[x] rejected",
            "implemented": "[V] implemented",
        }
        return status_map.get(status, f"[?] {status}")

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
        # Focus table for keyboard navigation
        if data and self._initial_load:
            def do_focus():
                table.focus()
                self.app.set_focus(table)
                if table.row_count > 0:
                    table.move_cursor(row=0, column=0)
            self.set_timer(0.2, do_focus)
            self._initial_load = False

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = self.query_one("#governance-table", DataTable)
        data = table.get_row(event.row_key)
        self.selected_entry_id = int(data[0])

        for entry in self.governance_data:
            if entry["id"] == self.selected_entry_id:
                self.query_one("#footer", Static).update(
                    f"Selected: #{entry['id']} | {entry['status']} | {entry['title'][:40]} | Votes: {entry['votes']}"
                )
                break

    def action_new(self) -> None:
        """Keyboard shortcut: Create new governance entry."""
        self.app.push_screen(CreateGovernanceModal(), callback=lambda _: self.refresh_data())

    def action_edit(self) -> None:
        """Keyboard shortcut: Edit selected entry."""
        if self.selected_entry_id:
            self.app.push_screen(EditGovernanceModal(self.selected_entry_id), callback=lambda _: self.refresh_data())
        else:
            self.notify("Select an entry first - use arrow keys", severity="warning")

    def action_vote(self) -> None:
        """Keyboard shortcut: Vote on selected entry."""
        if self.selected_entry_id:
            self.app.push_screen(VoteModal(self.selected_entry_id), callback=lambda _: self.refresh_data())
        else:
            self.notify("Select an entry first - use arrow keys", severity="warning")

    def action_status(self) -> None:
        """Keyboard shortcut: Update entry status."""
        if self.selected_entry_id:
            self.app.push_screen(StatusModal(self.selected_entry_id), callback=lambda _: self.refresh_data())
        else:
            self.notify("Select an entry first - use arrow keys", severity="warning")

    def action_delete(self) -> None:
        """Keyboard shortcut: Delete entry."""
        if self.selected_entry_id:
            self.app.push_screen(DeleteGovernanceModal(self.selected_entry_id), callback=lambda _: self.refresh_data())
        else:
            self.notify("Select an entry first - use arrow keys", severity="warning")

    def action_select(self) -> None:
        """Keyboard shortcut: Select current row."""
        table = self.query_one("#governance-table", DataTable)
        if table.cursor_row is not None and table.row_count > 0:
            row_key = table.get_row_at(table.cursor_row)[0]
            try:
                self.selected_entry_id = int(row_key)
                for entry in self.governance_data:
                    if entry["id"] == self.selected_entry_id:
                        self.query_one("#footer", Static).update(
                            f"Selected: #{entry['id']} | {entry['status']} | {entry['title'][:40]} | Votes: {entry['votes']}"
                        )
                        break
            except (ValueError, TypeError):
                pass

    def action_refresh(self) -> None:
        """Keyboard shortcut: Refresh data."""
        self.refresh_data()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-new":
            self.app.push_screen(CreateGovernanceModal(), callback=lambda _: self.refresh_data())
        elif event.button.id == "btn-edit":
            if self.selected_entry_id:
                self.app.push_screen(EditGovernanceModal(self.selected_entry_id), callback=lambda _: self.refresh_data())
            else:
                self.notify("Select an entry first - use arrow keys", severity="warning")
        elif event.button.id == "btn-vote":
            if self.selected_entry_id:
                self.app.push_screen(VoteModal(self.selected_entry_id), callback=lambda _: self.refresh_data())
            else:
                self.notify("Select an entry first - use arrow keys", severity="warning")
        elif event.button.id == "btn-status":
            if self.selected_entry_id:
                self.app.push_screen(StatusModal(self.selected_entry_id), callback=lambda _: self.refresh_data())
            else:
                self.notify("Select an entry first - use arrow keys", severity="warning")
        elif event.button.id == "btn-delete":
            if self.selected_entry_id:
                self.app.push_screen(DeleteGovernanceModal(self.selected_entry_id), callback=lambda _: self.refresh_data())
            else:
                self.notify("Select an entry first - use arrow keys", severity="warning")
        elif event.button.id == "btn-refresh":
            self.refresh_data()