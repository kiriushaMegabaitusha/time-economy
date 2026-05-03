"""Members screen for Time Economy TUI."""

from textual.screen import Screen, ModalScreen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, DataTable, Input, Button, Label, Select, TextArea
from textual.reactive import reactive

from app.services import (
    get_session, get_all_members, get_member_detail, create_member,
    add_skill, add_want, update_member, delete_member, delete_skill, delete_want,
    calculate_balance
)


class CreateMemberModal(ModalScreen):
    """Modal for creating a new member."""

    def compose(self) -> None:
        with Container(classes="modal-form"):
            yield Static("ADD NEW MEMBER", classes="modal-form-title")
            yield Label("Name *", id="lbl-name")
            yield Input(placeholder="Enter member name", id="name")
            yield Label("Email *", id="lbl-email")
            yield Input(placeholder="Enter email address", id="email")
            yield Label("Phone", id="lbl-phone")
            yield Input(placeholder="Phone number (optional)", id="phone")
            yield Label("Bio", id="lbl-bio")
            yield Input(placeholder="Short bio (optional)", id="bio")
            yield Label("Initial Credit", id="lbl-credit")
            yield Input(placeholder="5.0", value="5.0", id="initial_credit")
            with Horizontal(classes="modal-form-actions"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="warning", id="cancel")

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

        if not name:
            self.notify("Name is required - enter a member name", severity="error")
            return
        if not email:
            self.notify("Email is required - enter an email address", severity="error")
            return

        db = get_session()
        try:
            member = create_member(db, name, email, phone, bio, initial)
            self.notify(f"Member '{name}' created successfully!", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            db.close()


class EditMemberModal(ModalScreen):
    """Modal for editing a member."""

    def __init__(self, member_id: int):
        super().__init__()
        self.member_id = member_id
        self.member = None

    def compose(self) -> None:
        db = get_session()
        try:
            self.member = get_member_detail(db, self.member_id)
        finally:
            db.close()

        with Container(classes="modal-form"):
            yield Static("EDIT MEMBER", classes="modal-form-title")
            yield Label("Name *", id="lbl-name")
            yield Input(placeholder="Enter member name", value=self.member.name if self.member else "", id="name")
            yield Label("Email *", id="lbl-email")
            yield Input(placeholder="Enter email address", value=self.member.email if self.member else "", id="email")
            yield Label("Phone", id="lbl-phone")
            yield Input(placeholder="Phone number", value=self.member.phone or "", id="phone")
            yield Label("Bio", id="lbl-bio")
            yield Input(placeholder="Short bio", value=self.member.bio or "", id="bio")
            yield Label("Status", id="lbl-status")
            status_options = [("Active", "active"), ("Inactive", "inactive"), ("Suspended", "suspended")]
            yield Select(options=status_options, id="status", value=self.member.status if self.member else "active")
            with Horizontal(classes="modal-form-actions"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="warning", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss()
            return

        name = self.query_one("#name", Input).value.strip()
        email = self.query_one("#email", Input).value.strip()
        phone = self.query_one("#phone", Input).value.strip() or None
        bio = self.query_one("#bio", Input).value.strip() or None
        status_select = self.query_one("#status", Select)
        status = status_select.value if status_select.value else "active"

        if not name:
            self.notify("Name is required", severity="error")
            return
        if not email:
            self.notify("Email is required", severity="error")
            return

        db = get_session()
        try:
            update_member(db, self.member_id, name, email, phone, bio)
            if status:
                from app.services import update_member_status
                update_member_status(db, self.member_id, str(status))
            self.notify("Member updated successfully!", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            db.close()


class DeleteMemberModal(ModalScreen):
    """Modal for confirming member deletion - destructive action requires confirmation."""

    def __init__(self, member_id: int, member_name: str):
        super().__init__()
        self.member_id = member_id
        self.member_name = member_name

    def compose(self) -> None:
        with Container(classes="modal-form"):
            yield Static("DELETE MEMBER", classes="modal-form-title")
            yield Static("!", classes="confirm-danger")
            yield Static(f"Are you sure you want to delete '{self.member_name}'?", classes="confirm-warning")
            yield Static("This will also delete all their skills, wants, needs, and governance entries.")
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
            if delete_member(db, self.member_id):
                self.notify(f"Member '{self.member_name}' deleted!", severity="warning")
                self.dismiss(True)
            else:
                self.notify("Member not found", severity="error")
                self.dismiss()
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            db.close()


class DeleteSkillModal(ModalScreen):
    """Modal for confirming skill deletion."""

    def __init__(self, skill_id: int, skill_name: str, member_name: str):
        super().__init__()
        self.skill_id = skill_id
        self.skill_name = skill_name
        self.member_name = member_name

    def compose(self) -> None:
        with Container(classes="modal-form"):
            yield Static("DELETE SKILL", classes="modal-form-title")
            yield Static("!", classes="confirm-danger")
            yield Static(f"Delete skill '{self.skill_name}' from '{self.member_name}'?", classes="confirm-warning")
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
            delete_skill(db, self.skill_id)
            self.notify(f"Skill '{self.skill_name}' deleted!", severity="warning")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            db.close()


class DeleteWantModal(ModalScreen):
    """Modal for confirming skill want deletion."""

    def __init__(self, want_id: int, want_name: str, member_name: str):
        super().__init__()
        self.want_id = want_id
        self.want_name = want_name
        self.member_name = member_name

    def compose(self) -> None:
        with Container(classes="modal-form"):
            yield Static("DELETE WANT", classes="modal-form-title")
            yield Static("!", classes="confirm-danger")
            yield Static(f"Delete want '{self.want_name}' from '{self.member_name}'?", classes="confirm-warning")
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
            delete_want(db, self.want_id)
            self.notify(f"Want '{self.want_name}' deleted!", severity="warning")
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
            yield Label("Skill Name *", id="lbl-name")
            yield Input(placeholder="Enter skill name", id="skill_name")
            yield Label("Category", id="lbl-category")
            yield Input(placeholder="e.g., cooking, tech, crafts", id="category")
            yield Label("Description", id="lbl-desc")
            yield Input(placeholder="Brief description (optional)", id="description")
            with Horizontal(classes="modal-form-actions"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="warning", id="cancel")

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
            self.notify(f"Skill '{name}' added!", severity="information")
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
            yield Label("Skill Wanted *", id="lbl-name")
            yield Input(placeholder="Enter skill you want to learn", id="want_name")
            yield Label("Description", id="lbl-desc")
            yield Input(placeholder="Brief description (optional)", id="description")
            with Horizontal(classes="modal-form-actions"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="warning", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss()
            return

        name = self.query_one("#want_name", Input).value.strip()
        description = self.query_one("#description", Input).value.strip() or None

        if not name:
            self.notify("Skill wanted is required", severity="error")
            return

        db = get_session()
        try:
            add_want(db, self.member_id, name, description)
            self.notify(f"Want '{name}' added!", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            db.close()


class MembersScreen(Screen):
    """Members directory screen - consistent Universal Design layout."""

    members_data = reactive([])
    selected_member_id = reactive(None)
    _initial_load = True

    BINDINGS = [
        ("n", "action_new", "New Member"),
        ("e", "action_edit", "Edit"),
        ("d", "action_delete", "Delete"),
        ("s", "action_add_skill", "Add Skill"),
        ("w", "action_add_want", "Add Want"),
        ("r", "action_refresh", "Refresh"),
        ("enter", "action_select", "Select"),
    ]

    def compose(self) -> None:
        with Container(id="members-container", classes="screen-container"):
            yield Static("TIME ECONOMY - MEMBERS", id="header")
            yield Static("D:Dash M:Members T:Trans N:Needs G:Govern S:Skills | N:New E:Edit D:Del S:Skill W:Want R:Refresh Q:Quit", id="nav-bar")

            with Horizontal(id="members-content", classes="content-area split-view"):
                with Container(id="members-list-container", classes="split-left"):
                    yield Static("MEMBERS LIST", classes="panel-title")
                    yield DataTable(id="members-table")

                with Container(id="member-detail-container", classes="split-right"):
                    yield Static("MEMBER DETAIL", classes="panel-title")
                    yield Static("Select a member from the list to view details\n\nTip: Use arrow keys to navigate, Enter to select", id="member-detail")

            with Horizontal(id="members-actions", classes="action-bar"):
                yield Button("New Member", variant="primary", id="btn-new")
                yield Button("Edit", variant="primary", id="btn-edit")
                yield Button("Delete", variant="error", id="btn-delete")
                yield Button("Add Skill", variant="success", id="btn-skill")
                yield Button("Add Want", variant="success", id="btn-want")
                yield Button("Refresh", variant="primary", id="btn-refresh")

            yield Static("Use arrow keys to navigate, Enter to select", id="footer")

    def on_mount(self) -> None:
        self.refresh_data()
        # Focus is handled by watch_members_data via set_timer

    def set_focus_table(self, table_id: str) -> None:
        """Focus the DataTable (not used for initial focus)."""
        pass

    def refresh_data(self) -> None:
        db = get_session()
        try:
            members = get_all_members(db)
            data = []
            for m in members:
                bal = calculate_balance(db, m.id)
                status_display = self._format_member_status(m.status)
                data.append({
                    "id": m.id,
                    "name": m.name,
                    "email": m.email,
                    "phone": m.phone or "",
                    "status": status_display,
                    "balance": bal,
                    "raw_status": m.status
                })
            self.members_data = data
        finally:
            db.close()
            # Reset initial load flag so next refresh focuses properly
            self._initial_load = True

    def _format_member_status(self, status: str) -> str:
        status_map = {
            "active": "[+] active",
            "inactive": "[-] inactive",
            "suspended": "[!] suspended",
        }
        return status_map.get(status, f"[?] {status}")

    def watch_members_data(self, data) -> None:
        table = self.query_one("#members-table", DataTable)
        # Preserve cursor position if possible
        old_row = table.cursor_row if hasattr(table, 'cursor_row') else 0
        table.clear(columns=True)
        table.add_columns("ID", "Name", "Email", "Phone", "Status", "Balance")
        for m in data:
            balance_str = f"{m['balance']:+.1f}"
            table.add_row(
                str(m["id"]), m["name"], m["email"],
                m["phone"], m["status"], balance_str
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
        table = self.query_one("#members-table", DataTable)
        row_key = event.row_key.value
        try:
            member_id = int(row_key)
        except (ValueError, TypeError):
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
                f"Status: {self._format_member_status(member.status)}",
                f"Joined: {member.joined_at.strftime('%Y-%m-%d')}",
                f"Balance: {member.balance:+.2f} credits",
                "",
            ]

            if member.skills_offered:
                lines.append("Skills Offered:")
                for skill in member.skills_offered:
                    cat = f" [{skill.category}]" if skill.category else ""
                    lines.append(f"  [*] {skill.name}{cat}")

            if member.skills_wanted:
                lines.append("Skills Wanted:")
                for want in member.skills_wanted:
                    lines.append(f"  [?] {want.name}")

            detail_widget = self.query_one("#member-detail", Static)
            detail_widget.update("\n".join(lines))

            self.query_one("#footer", Static).update(
                f"Selected: {member.name} ({member.status}) | Balance: {member.balance:+.2f} | [E]dit [S]kill [Del]ete"
            )
        finally:
            db.close()

    def action_new(self) -> None:
        """Keyboard shortcut: Create new member."""
        self.app.push_screen(CreateMemberModal(), callback=lambda _: self.refresh_data())

    def action_edit(self) -> None:
        """Keyboard shortcut: Edit selected member."""
        if self.selected_member_id:
            self.app.push_screen(EditMemberModal(self.selected_member_id), callback=lambda _: self.refresh_data())
        else:
            self.notify("Select a member first - use arrow keys to navigate list", severity="warning")

    def action_delete(self) -> None:
        """Keyboard shortcut: Delete selected member."""
        if self.selected_member_id:
            db = get_session()
            try:
                member = get_member_detail(db, self.selected_member_id)
                if member:
                    self.app.push_screen(DeleteMemberModal(self.selected_member_id, member.name), callback=lambda _: self.refresh_data())
                else:
                    self.notify("Member not found", severity="error")
            finally:
                db.close()
        else:
            self.notify("Select a member first - use arrow keys to navigate list", severity="warning")

    def action_add_skill(self) -> None:
        """Keyboard shortcut: Add skill to selected member."""
        if self.selected_member_id:
            self.app.push_screen(AddSkillModal(self.selected_member_id), callback=lambda _: self.refresh_data())
        else:
            self.notify("Select a member first - use arrow keys to navigate list", severity="warning")

    def action_add_want(self) -> None:
        """Keyboard shortcut: Add want to selected member."""
        if self.selected_member_id:
            self.app.push_screen(AddWantModal(self.selected_member_id), callback=lambda _: self.refresh_data())
        else:
            self.notify("Select a member first - use arrow keys to navigate list", severity="warning")

    def action_select(self) -> None:
        """Keyboard shortcut: Select current row."""
        table = self.query_one("#members-table", DataTable)
        if table.cursor_row is not None and table.row_count > 0:
            row_key = table.get_row_at(table.cursor_row)[0]
            try:
                self.selected_member_id = int(row_key)
                self.show_member_detail(self.selected_member_id)
            except (ValueError, TypeError):
                pass

    def action_refresh(self) -> None:
        """Keyboard shortcut: Refresh data."""
        self.refresh_data()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-new":
            self.app.push_screen(CreateMemberModal(), callback=lambda _: self.refresh_data())
        elif event.button.id == "btn-edit":
            if self.selected_member_id:
                self.app.push_screen(EditMemberModal(self.selected_member_id), callback=lambda _: self.refresh_data())
            else:
                self.notify("Select a member first - use arrow keys to navigate list", severity="warning")
        elif event.button.id == "btn-delete":
            if self.selected_member_id:
                db = get_session()
                try:
                    member = get_member_detail(db, self.selected_member_id)
                    if member:
                        self.app.push_screen(DeleteMemberModal(self.selected_member_id, member.name), callback=lambda _: self.refresh_data())
                    else:
                        self.notify("Member not found", severity="error")
                finally:
                    db.close()
            else:
                self.notify("Select a member first - use arrow keys to navigate list", severity="warning")
        elif event.button.id == "btn-skill":
            if self.selected_member_id:
                self.app.push_screen(AddSkillModal(self.selected_member_id), callback=lambda _: self.refresh_data())
            else:
                self.notify("Select a member first - use arrow keys to navigate list", severity="warning")
        elif event.button.id == "btn-want":
            if self.selected_member_id:
                self.app.push_screen(AddWantModal(self.selected_member_id), callback=lambda _: self.refresh_data())
            else:
                self.notify("Select a member first - use arrow keys to navigate list", severity="warning")
        elif event.button.id == "btn-refresh":
            self.refresh_data()