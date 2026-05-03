"""Members screen for Time Economy TUI."""

from textual.screen import Screen, ModalScreen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, DataTable, Input, Button, Label, Select, TextArea
from textual.reactive import reactive

from app.services import (
    get_session, get_all_members, get_member_detail, create_member,
    add_skill, add_want, calculate_balance
)


class CreateMemberModal(ModalScreen):
    """Modal for creating a new member."""

    def compose(self) -> None:
        with Container(classes="modal-form"):
            yield Static("ADD NEW MEMBER", classes="modal-form-title")
            yield Input(placeholder="Name", id="name")
            yield Input(placeholder="Email", id="email")
            yield Input(placeholder="Phone (optional)", id="phone")
            yield Input(placeholder="Bio (optional)", id="bio")
            yield Input(placeholder="Initial credit [5.0]", value="5.0", id="initial_credit")
            with Horizontal():
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="error", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss()
            return

        name = self.query_one("#name", Input).value.strip()
        email = self.query_one("#email", Input).value.strip()
        phone = self.query_one("#phone", Input).value.strip() or None
        bio = self.query_one("#bio", Input).value.strip() or None

        try:
            initial = float(self.query_one("#initial_credit", Input).value or 5.0)
        except ValueError:
            initial = 5.0

        if not name or not email:
            self.notify("Name and email are required", severity="error")
            return

        db = get_session()
        try:
            member = create_member(db, name, email, phone, bio, initial)
            self.notify(f"Member '{name}' created!")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            db.close()


class AddSkillModal(ModalScreen):
    """Modal for adding a skill to a member."""

    def __init__(self, member_id: int):
        super().__init__()
        self.member_id = member_id

    def compose(self) -> None:
        with Container(classes="modal-form"):
            yield Static("ADD SKILL", classes="modal-form-title")
            yield Input(placeholder="Skill name", id="skill_name")
            yield Input(placeholder="Category (optional)", id="category")
            yield Input(placeholder="Description (optional)", id="description")
            with Horizontal():
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="error", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss()
            return

        name = self.query_one("#skill_name", Input).value.strip()
        category = self.query_one("#category", Input).value.strip() or None
        description = self.query_one("#description", Input).value.strip() or None

        if not name:
            self.notify("Skill name is required", severity="error")
            return

        db = get_session()
        try:
            add_skill(db, self.member_id, name, category, description)
            self.notify("Skill added!")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            db.close()


class AddWantModal(ModalScreen):
    """Modal for adding a skill want to a member."""

    def __init__(self, member_id: int):
        super().__init__()
        self.member_id = member_id

    def compose(self) -> None:
        with Container(classes="modal-form"):
            yield Static("ADD WANT", classes="modal-form-title")
            yield Input(placeholder="Skill wanted", id="want_name")
            yield Input(placeholder="Description (optional)", id="description")
            with Horizontal():
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="error", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss()
            return

        name = self.query_one("#want_name", Input).value.strip()
        description = self.query_one("#description", Input).value.strip() or None

        if not name:
            self.notify("Want name is required", severity="error")
            return

        db = get_session()
        try:
            add_want(db, self.member_id, name, description)
            self.notify("Want added!")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            db.close()


class MembersScreen(Screen):
    """Members directory screen."""

    members_data = reactive([])
    selected_member_id = reactive(None)

    def compose(self) -> None:
        with Container(id="members-container"):
            yield Static("TIME ECONOMY - MEMBERS", id="header")
            yield Static("Keys: [m]embers [d]ashboard [t]ransactions [n]eeds [g]overnance [s]kills  [n]ew  [r]efresh  [q]uit", id="nav-bar")

            with Horizontal(id="members-content"):
                with Container(id="members-list-container"):
                    yield Static("MEMBERS", classes="panel-title")
                    yield DataTable(id="members-table")

                with Container(id="member-detail-container"):
                    yield Static("MEMBER DETAIL", classes="panel-title")
                    yield Static("Select a member to view details", id="member-detail")

            with Horizontal(id="members-actions"):
                yield Button("New Member", variant="primary", id="btn-new")
                yield Button("Add Skill", variant="success", id="btn-skill")
                yield Button("Add Want", variant="success", id="btn-want")
                yield Button("Refresh", variant="primary", id="btn-refresh")

            yield Static("Ready", id="footer")

    def on_mount(self) -> None:
        self.refresh_data()

    def refresh_data(self) -> None:
        db = get_session()
        try:
            members = get_all_members(db)
            data = []
            for m in members:
                bal = calculate_balance(db, m.id)
                data.append({
                    "id": m.id,
                    "name": m.name,
                    "email": m.email,
                    "phone": m.phone or "",
                    "status": m.status,
                    "balance": bal
                })
            self.members_data = data
        finally:
            db.close()

    def watch_members_data(self, data) -> None:
        table = self.query_one("#members-table", DataTable)
        table.clear(columns=True)
        table.add_columns("ID", "Name", "Email", "Phone", "Status", "Balance")
        for m in data:
            balance_str = f"{m['balance']:+.1f}"
            table.add_row(
                str(m["id"]), m["name"], m["email"],
                m["phone"], m["status"], balance_str
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = self.query_one("#members-table", DataTable)
        row_key = event.row_key.value
        try:
            member_id = int(row_key)
        except (ValueError, TypeError):
            # Handle case where row_key is the first column value
            data = table.get_row(event.row_key)
            member_id = int(data[0])

        self.selected_member_id = member_id
        self.show_member_detail(member_id)

    def show_member_detail(self, member_id: int) -> None:
        db = get_session()
        try:
            member = get_member_detail(db, member_id)
            if not member:
                return

            lines = [
                f"Name: {member.name}",
                f"Email: {member.email}",
                f"Phone: {member.phone or 'N/A'}",
                f"Status: {member.status}",
                f"Joined: {member.joined_at.strftime('%Y-%m-%d')}",
                f"Balance: {member.balance:+.2f} credits",
                "",
            ]

            if member.skills_offered:
                lines.append("Skills Offered:")
                for skill in member.skills_offered:
                    cat = f" [{skill.category}]" if skill.category else ""
                    lines.append(f"  - {skill.name}{cat}")

            if member.skills_wanted:
                lines.append("Skills Wanted:")
                for want in member.skills_wanted:
                    lines.append(f"  - {want.name}")

            detail_widget = self.query_one("#member-detail", Static)
            detail_widget.update("\n".join(lines))
        finally:
            db.close()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-new":
            self.push_screen(CreateMemberModal(), callback=lambda _: self.refresh_data())
        elif event.button.id == "btn-skill":
            if self.selected_member_id:
                self.push_screen(AddSkillModal(self.selected_member_id), callback=lambda _: self.refresh_data())
            else:
                self.notify("Select a member first", severity="warning")
        elif event.button.id == "btn-want":
            if self.selected_member_id:
                self.push_screen(AddWantModal(self.selected_member_id), callback=lambda _: self.refresh_data())
            else:
                self.notify("Select a member first", severity="warning")
        elif event.button.id == "btn-refresh":
            self.refresh_data()
