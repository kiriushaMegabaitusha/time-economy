"""Needs screen for Time Economy TUI."""

from textual.screen import Screen, ModalScreen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, DataTable, Input, Button, Label, Select
from textual.reactive import reactive

from app.services import (
    get_session, get_all_members, get_all_needs,
    create_need, fulfill_need, close_need, reopen_need, update_need, delete_need
)
from app.models import Member


class CreateNeedModal(ModalScreen):
    """Modal for creating a new need."""

    def __init__(self):
        super().__init__()
        self.members = []

    def compose(self) -> None:
        with Container(classes="modal-form"):
            yield Static("POST A NEED", classes="modal-form-title")

            db = get_session()
            try:
                self.members = get_all_members(db)
                member_options = [(m.name, m.id) for m in self.members]
            finally:
                db.close()

            yield Label("Posted By *", id="lbl-member")
            yield Select(options=member_options, id="member", prompt="Select member")
            yield Label("Title *", id="lbl-title")
            yield Input(placeholder="Brief title for the need", id="title")
            yield Label("Description *", id="lbl-desc")
            yield Input(placeholder="Detailed description of what you need", id="description")
            yield Label("Hours Estimated", id="lbl-hours")
            yield Input(placeholder="1.0", value="1.0", id="hours")

            with Horizontal(classes="modal-form-actions"):
                yield Button("Post", variant="primary", id="save")
                yield Button("Cancel", variant="warning", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss()
            return

        member_select = self.query_one("#member", Select)
        title_input = self.query_one("#title", Input)
        desc_input = self.query_one("#description", Input)
        hours_input = self.query_one("#hours", Input)

        member_id = member_select.value
        if member_id is Select.BLANK:
            self.notify("Select who is posting this need", severity="error")
            return

        title = title_input.value.strip()
        description = desc_input.value.strip()
        if not title:
            self.notify("Title is required - what do you need?", severity="error")
            return
        if not description:
            self.notify("Description is required - explain the need", severity="error")
            return

        try:
            hours = float(hours_input.value or 1.0)
        except ValueError:
            hours = 1.0

        db = get_session()
        try:
            create_need(db, int(member_id), title, description, hours)
            self.notify("Need posted successfully!", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            db.close()


class EditNeedModal(ModalScreen):
    """Modal for editing a need."""

    def __init__(self, need_id: int):
        super().__init__()
        self.need_id = need_id
        self.need = None

    def compose(self) -> None:
        db = get_session()
        try:
            from app.models import Need
            self.need = db.query(Need).filter(Need.id == self.need_id).first()
        finally:
            db.close()

        with Container(classes="modal-form"):
            yield Static("EDIT NEED", classes="modal-form-title")
            yield Label("Title *", id="lbl-title")
            yield Input(placeholder="Brief title", value=self.need.title if self.need else "", id="title")
            yield Label("Description *", id="lbl-desc")
            yield Input(placeholder="Detailed description", value=self.need.description if self.need else "", id="description")
            yield Label("Hours Estimated", id="lbl-hours")
            yield Input(placeholder="1.0", value=str(self.need.hours_estimated) if self.need else "1.0", id="hours")
            with Horizontal(classes="modal-form-actions"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="warning", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss()
            return

        title = self.query_one("#title", Input).value.strip()
        description = self.query_one("#description", Input).value.strip()

        if not title:
            self.notify("Title is required", severity="error")
            return
        if not description:
            self.notify("Description is required", severity="error")
            return

        try:
            hours = float(self.query_one("#hours", Input).value or 1.0)
        except ValueError:
            hours = 1.0

        db = get_session()
        try:
            update_need(db, self.need_id, title, description, hours)
            self.notify("Need updated!", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            db.close()


class ConfirmStatusModal(ModalScreen):
    """Modal for confirming status changes (fulfill, reopen, close)."""

    def __init__(self, need_id: int, action: str):
        super().__init__()
        self.need_id = need_id
        self.action = action

    def compose(self) -> None:
        action_text = {
            "fulfill": ("FULFILL NEED", "fulfilled", "marked as fulfilled"),
            "reopen": ("REOPEN NEED", "reopened", "reopened"),
            "close": ("CLOSE NEED", "closed", "closed"),
        }
        title, key, desc = action_text.get(self.action, ("UPDATE STATUS", "updated", "updated"))

        variant_map = {
            "fulfill": "success",
            "reopen": "warning",
            "close": "primary",
        }

        with Container(classes="modal-form"):
            yield Static(title, classes="modal-form-title")
            yield Static(f"Need ID: {self.need_id}")
            yield Static(f"Confirm: {desc}?", classes="confirm-warning")
            yield Static("This action can be undone later.")
            with Horizontal(classes="modal-form-actions"):
                yield Button("Confirm", variant=variant_map.get(self.action, "primary"), id="confirm")
                yield Button("Cancel", variant="warning", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss()
            return

        db = get_session()
        try:
            if self.action == "fulfill":
                fulfill_need(db, self.need_id)
                self.notify("Need fulfilled! Great work helping community.", severity="information")
            elif self.action == "reopen":
                reopen_need(db, self.need_id)
                self.notify("Need reopened!", severity="information")
            elif self.action == "close":
                close_need(db, self.need_id)
                self.notify("Need closed!", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            db.close()


class DeleteNeedModal(ModalScreen):
    """Modal for confirming need deletion."""

    def __init__(self, need_id: int):
        super().__init__()
        self.need_id = need_id

    def compose(self) -> None:
        with Container(classes="modal-form"):
            yield Static("DELETE NEED", classes="modal-form-title")
            yield Static("!", classes="confirm-danger")
            yield Static(f"Confirm deletion of Need #{self.need_id}?", classes="confirm-warning")
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
            delete_need(db, self.need_id)
            self.notify("Need deleted!", severity="warning")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            db.close()


class NeedsScreen(Screen):
    """Needs board screen - consistent Universal Design layout."""

    needs_data = reactive([])
    selected_need_id = reactive(None)
    _initial_load = True

    BINDINGS = [
        ("n", "action_new", "New"),
        ("e", "action_edit", "Edit"),
        ("f", "action_fulfill", "Fulfill"),
        ("o", "action_reopen", "Reopen"),
        ("c", "action_close", "Close"),
        ("d", "action_delete", "Delete"),
        ("r", "action_refresh", "Refresh"),
        ("enter", "action_select", "Select"),
    ]

    def compose(self) -> None:
        with Container(id="needs-container", classes="screen-container"):
            yield Static("TIME ECONOMY - NEEDS BOARD", id="header")
            yield Static("D:Dash M:Members T:Trans N:Needs G:Govern S:Skills | N:New E:Edit F:Fulfill O:Reopen C:Close D:Del R:Refresh Q:Quit", id="nav-bar")

            with Container(id="content", classes="content-area"):
                yield DataTable(id="needs-table")

            with Horizontal(id="needs-actions", classes="action-bar"):
                yield Button("Post Need", variant="primary", id="btn-new")
                yield Button("Edit", variant="primary", id="btn-edit")
                yield Button("Fulfill", variant="success", id="btn-fulfill")
                yield Button("Reopen", variant="warning", id="btn-reopen")
                yield Button("Close", variant="primary", id="btn-close")
                yield Button("Delete", variant="error", id="btn-delete")
                yield Button("Refresh", variant="primary", id="btn-refresh")

            yield Static("Use arrow keys to navigate, Enter to select", id="footer")

    def on_mount(self) -> None:
        self.refresh_data()
        # Focus is handled by watch_needs_data via set_timer

    def set_focus_table(self, table_id: str) -> None:
        """Focus the DataTable (not used for initial focus)."""
        pass

    def refresh_data(self) -> None:
        db = get_session()
        try:
            needs = get_all_needs(db)
            data = []
            for need in needs:
                member = db.query(Member).filter(Member.id == need.member_id).first()
                data.append({
                    "id": need.id,
                    "date": need.created_at.strftime("%Y-%m-%d"),
                    "status": self._format_status(need.status),
                    "raw_status": need.status,
                    "hours": need.hours_estimated,
                    "member": member.name if member else "?",
                    "title": need.title,
                    "description": need.description,
                })
            self.needs_data = data
        finally:
            db.close()
            # Reset initial load flag so next refresh focuses properly
            self._initial_load = True

    def _format_status(self, status: str) -> str:
        status_map = {
            "open": "[+] open",
            "fulfilled": "[v] fulfilled",
            "closed": "[-] closed",
        }
        return status_map.get(status, f"[?] {status}")

    def watch_needs_data(self, data) -> None:
        table = self.query_one("#needs-table", DataTable)
        table.clear(columns=True)
        table.add_columns("ID", "Date", "Status", "Hours", "Member", "Title")
        for need in data:
            table.add_row(
                str(need["id"]), need["date"], need["status"],
                str(need["hours"]), need["member"], need["title"][:30]
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
        table = self.query_one("#needs-table", DataTable)
        data = table.get_row(event.row_key)
        self.selected_need_id = int(data[0])

        for need in self.needs_data:
            if need["id"] == self.selected_need_id:
                self.query_one("#footer", Static).update(
                    f"Selected: #{need['id']} | {need['member']} needs \"{need['title']}\" ({need['hours']}h) | {need['status']}"
                )
                break

    def action_new(self) -> None:
        """Keyboard shortcut: Post new need."""
        self.app.push_screen(CreateNeedModal(), callback=lambda _: self.refresh_data())

    def action_edit(self) -> None:
        """Keyboard shortcut: Edit selected need."""
        if self.selected_need_id:
            self.app.push_screen(EditNeedModal(self.selected_need_id), callback=lambda _: self.refresh_data())
        else:
            self.notify("Select a need first - use arrow keys", severity="warning")

    def action_fulfill(self) -> None:
        """Keyboard shortcut: Fulfill need."""
        if self.selected_need_id:
            self.app.push_screen(ConfirmStatusModal(self.selected_need_id, "fulfill"), callback=lambda _: self.refresh_data())
        else:
            self.notify("Select a need first - use arrow keys", severity="warning")

    def action_reopen(self) -> None:
        """Keyboard shortcut: Reopen need."""
        if self.selected_need_id:
            self.app.push_screen(ConfirmStatusModal(self.selected_need_id, "reopen"), callback=lambda _: self.refresh_data())
        else:
            self.notify("Select a need first - use arrow keys", severity="warning")

    def action_close(self) -> None:
        """Keyboard shortcut: Close need."""
        if self.selected_need_id:
            self.app.push_screen(ConfirmStatusModal(self.selected_need_id, "close"), callback=lambda _: self.refresh_data())
        else:
            self.notify("Select a need first - use arrow keys", severity="warning")

    def action_delete(self) -> None:
        """Keyboard shortcut: Delete need."""
        if self.selected_need_id:
            self.app.push_screen(DeleteNeedModal(self.selected_need_id), callback=lambda _: self.refresh_data())
        else:
            self.notify("Select a need first - use arrow keys", severity="warning")

    def action_select(self) -> None:
        """Keyboard shortcut: Select current row."""
        table = self.query_one("#needs-table", DataTable)
        if table.cursor_row is not None and table.row_count > 0:
            row_key = table.get_row_at(table.cursor_row)[0]
            try:
                self.selected_need_id = int(row_key)
                for need in self.needs_data:
                    if need["id"] == self.selected_need_id:
                        self.query_one("#footer", Static).update(
                            f"Selected: #{need['id']} | {need['member']} needs \"{need['title']}\" ({need['hours']}h) | {need['status']}"
                        )
                        break
            except (ValueError, TypeError):
                pass

    def action_refresh(self) -> None:
        """Keyboard shortcut: Refresh data."""
        self.refresh_data()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-new":
            self.app.push_screen(CreateNeedModal(), callback=lambda _: self.refresh_data())
        elif event.button.id == "btn-edit":
            if self.selected_need_id:
                self.app.push_screen(EditNeedModal(self.selected_need_id), callback=lambda _: self.refresh_data())
            else:
                self.notify("Select a need first - use arrow keys", severity="warning")
        elif event.button.id == "btn-fulfill":
            if self.selected_need_id:
                self.app.push_screen(ConfirmStatusModal(self.selected_need_id, "fulfill"), callback=lambda _: self.refresh_data())
            else:
                self.notify("Select a need first - use arrow keys", severity="warning")
        elif event.button.id == "btn-reopen":
            if self.selected_need_id:
                self.app.push_screen(ConfirmStatusModal(self.selected_need_id, "reopen"), callback=lambda _: self.refresh_data())
            else:
                self.notify("Select a need first - use arrow keys", severity="warning")
        elif event.button.id == "btn-close":
            if self.selected_need_id:
                self.app.push_screen(ConfirmStatusModal(self.selected_need_id, "close"), callback=lambda _: self.refresh_data())
            else:
                self.notify("Select a need first - use arrow keys", severity="warning")
        elif event.button.id == "btn-delete":
            if self.selected_need_id:
                self.app.push_screen(DeleteNeedModal(self.selected_need_id), callback=lambda _: self.refresh_data())
            else:
                self.notify("Select a need first - use arrow keys", severity="warning")
        elif event.button.id == "btn-refresh":
            self.refresh_data()