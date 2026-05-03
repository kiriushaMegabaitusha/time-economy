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

            yield Select(options=member_options, id="member", prompt="Posted by")
            yield Input(placeholder="Title", id="title")
            yield Input(placeholder="Description", id="description")
            yield Input(placeholder="Hours estimated [1.0]", value="1.0", id="hours")

            with Horizontal():
                yield Button("Post", variant="primary", id="save")
                yield Button("Cancel", variant="error", id="cancel")

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
            self.notify("Please select a member", severity="error")
            return

        title = title_input.value.strip()
        description = desc_input.value.strip()
        if not title or not description:
            self.notify("Title and description are required", severity="error")
            return

        try:
            hours = float(hours_input.value or 1.0)
        except ValueError:
            hours = 1.0

        db = get_session()
        try:
            create_need(db, int(member_id), title, description, hours)
            self.notify("Need posted!")
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
            self.need = db.query(Member).filter(Member.id == self.need_id).first()
            # Actually need is from Need model, not Member
            from app.models import Need
            self.need = db.query(Need).filter(Need.id == self.need_id).first()
        finally:
            db.close()

        with Container(classes="modal-form"):
            yield Static("EDIT NEED", classes="modal-form-title")
            yield Input(placeholder="Title", value=self.need.title if self.need else "", id="title")
            yield Input(placeholder="Description", value=self.need.description if self.need else "", id="description")
            yield Input(placeholder="Hours estimated", value=str(self.need.hours_estimated) if self.need else "1.0", id="hours")
            with Horizontal():
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="error", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss()
            return

        title = self.query_one("#title", Input).value.strip()
        description = self.query_one("#description", Input).value.strip()

        if not title or not description:
            self.notify("Title and description are required", severity="error")
            return

        try:
            hours = float(self.query_one("#hours", Input).value or 1.0)
        except ValueError:
            hours = 1.0

        db = get_session()
        try:
            update_need(db, self.need_id, title, description, hours)
            self.notify("Need updated!")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            db.close()


class NeedsScreen(Screen):
    """Needs board screen."""

    needs_data = reactive([])
    selected_need_id = reactive(None)

    def compose(self) -> None:
        with Container(id="needs-container"):
            yield Static("TIME ECONOMY - NEEDS BOARD", id="header")
            yield Static("Keys: [n]eeds [d]ashboard [m]embers [t]ransactions [g]overnance [s]kills  [n]ew  [f]ulfill  [r]efresh  [q]uit", id="nav-bar")

            yield DataTable(id="needs-table")

            with Horizontal(id="needs-actions"):
                yield Button("Post Need", variant="primary", id="btn-new")
                yield Button("Edit", variant="primary", id="btn-edit")
                yield Button("Fulfill", variant="success", id="btn-fulfill")
                yield Button("Reopen", variant="warning", id="btn-reopen")
                yield Button("Close", variant="error", id="btn-close")
                yield Button("Delete", variant="error", id="btn-delete")
                yield Button("Refresh", variant="primary", id="btn-refresh")

            yield Static("Ready", id="footer")

    def on_mount(self) -> None:
        self.refresh_data()

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
                    "status": need.status,
                    "hours": need.hours_estimated,
                    "member": member.name if member else "?",
                    "title": need.title,
                    "description": need.description,
                })
            self.needs_data = data
        finally:
            db.close()

    def watch_needs_data(self, data) -> None:
        table = self.query_one("#needs-table", DataTable)
        table.clear(columns=True)
        table.add_columns("ID", "Date", "Status", "Hours", "Member", "Title")
        for need in data:
            table.add_row(
                str(need["id"]), need["date"], need["status"],
                str(need["hours"]), need["member"], need["title"][:30]
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = self.query_one("#needs-table", DataTable)
        data = table.get_row(event.row_key)
        self.selected_need_id = int(data[0])

        for need in self.needs_data:
            if need["id"] == self.selected_need_id:
                self.query_one("#footer", Static).update(
                    f"Selected: {need['member']} needs \"{need['title']}\" ({need['hours']}h) - {need['status']}"
                )
                break

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-new":
            self.push_screen(CreateNeedModal(), callback=lambda _: self.refresh_data())
        elif event.button.id == "btn-edit":
            if self.selected_need_id:
                self.push_screen(EditNeedModal(self.selected_need_id), callback=lambda _: self.refresh_data())
            else:
                self.notify("Select a need first", severity="warning")
        elif event.button.id == "btn-fulfill":
            if self.selected_need_id:
                db = get_session()
                try:
                    fulfill_need(db, self.selected_need_id)
                    self.notify("Need fulfilled!")
                    self.refresh_data()
                except Exception as e:
                    self.notify(f"Error: {e}", severity="error")
                finally:
                    db.close()
            else:
                self.notify("Select a need first", severity="warning")
        elif event.button.id == "btn-reopen":
            if self.selected_need_id:
                db = get_session()
                try:
                    reopen_need(db, self.selected_need_id)
                    self.notify("Need reopened!")
                    self.refresh_data()
                except Exception as e:
                    self.notify(f"Error: {e}", severity="error")
                finally:
                    db.close()
            else:
                self.notify("Select a need first", severity="warning")
        elif event.button.id == "btn-close":
            if self.selected_need_id:
                db = get_session()
                try:
                    close_need(db, self.selected_need_id)
                    self.notify("Need closed!")
                    self.refresh_data()
                except Exception as e:
                    self.notify(f"Error: {e}", severity="error")
                finally:
                    db.close()
            else:
                self.notify("Select a need first", severity="warning")
        elif event.button.id == "btn-delete":
            if self.selected_need_id:
                db = get_session()
                try:
                    delete_need(db, self.selected_need_id)
                    self.notify("Need deleted!")
                    self.selected_need_id = None
                    self.refresh_data()
                except Exception as e:
                    self.notify(f"Error: {e}", severity="error")
                finally:
                    db.close()
            else:
                self.notify("Select a need first", severity="warning")
        elif event.button.id == "btn-refresh":
            self.refresh_data()
