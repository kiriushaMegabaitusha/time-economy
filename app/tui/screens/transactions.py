"""Transactions screen for Time Economy TUI."""

from textual.screen import Screen, ModalScreen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, DataTable, Input, Button, Label, Select
from textual.reactive import reactive

from app.services import (
    get_session, get_all_members, get_all_transactions,
    create_transaction, complete_transaction, dispute_transaction,
    reopen_transaction, update_transaction, delete_transaction, calculate_balance
)
from app.models import Member, Transaction


class CreateTransactionModal(ModalScreen):
    """Modal for creating a new transaction."""

    def __init__(self):
        super().__init__()
        self.members = []

    def compose(self) -> None:
        with Container(classes="modal-form"):
            yield Static("CREATE TRANSACTION", classes="modal-form-title")

            db = get_session()
            try:
                self.members = get_all_members(db)
                member_options = [(m.name, m.id) for m in self.members]
            finally:
                db.close()

            yield Label("From Member *", id="lbl-from")
            yield Select(options=member_options, id="from_member", prompt="Select sender")
            yield Label("To Member *", id="lbl-to")
            yield Select(options=member_options, id="to_member", prompt="Select recipient")
            yield Label("Hours *", id="lbl-hours")
            yield Input(placeholder="0.0", id="hours")
            yield Label("Service Description *", id="lbl-desc")
            yield Input(placeholder="What service was provided?", id="description")
            yield Label("Notes", id="lbl-notes")
            yield Input(placeholder="Additional notes (optional)", id="notes")

            with Horizontal(classes="modal-form-actions"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="warning", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss()
            return

        from_select = self.query_one("#from_member", Select)
        to_select = self.query_one("#to_member", Select)
        hours_input = self.query_one("#hours", Input)
        desc_input = self.query_one("#description", Input)
        notes_input = self.query_one("#notes", Input)

        from_id = from_select.value
        to_id = to_select.value

        if from_id is Select.BLANK:
            self.notify("Select a sender (From member)", severity="error")
            return
        if to_id is Select.BLANK:
            self.notify("Select a recipient (To member)", severity="error")
            return

        try:
            hours = float(hours_input.value)
        except ValueError:
            self.notify("Hours must be a number (e.g., 1.5)", severity="error")
            return

        description = desc_input.value.strip()
        if not description:
            self.notify("Service description is required", severity="error")
            return

        notes = notes_input.value.strip() or None

        if from_id == to_id:
            self.notify("Cannot send hours to yourself - select different members", severity="error")
            return

        db = get_session()
        try:
            create_transaction(db, int(from_id), int(to_id), hours, description, notes)
            self.notify("Transaction created successfully!", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            db.close()


class EditTransactionModal(ModalScreen):
    """Modal for editing a transaction."""

    def __init__(self, tx_id: int):
        super().__init__()
        self.tx_id = tx_id
        self.tx = None

    def compose(self) -> None:
        db = get_session()
        try:
            self.tx = db.query(Transaction).filter(Transaction.id == self.tx_id).first()
        finally:
            db.close()

        with Container(classes="modal-form"):
            yield Static("EDIT TRANSACTION", classes="modal-form-title")
            yield Label("Hours *", id="lbl-hours")
            yield Input(placeholder="0.0", value=str(self.tx.hours) if self.tx else "", id="hours")
            yield Label("Service Description *", id="lbl-desc")
            yield Input(placeholder="What service was provided?", value=self.tx.service_description if self.tx else "", id="description")
            yield Label("Notes", id="lbl-notes")
            yield Input(placeholder="Additional notes (optional)", value=self.tx.notes or "", id="notes")
            with Horizontal(classes="modal-form-actions"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="warning", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss()
            return

        try:
            hours = float(self.query_one("#hours", Input).value)
        except ValueError:
            self.notify("Hours must be a number (e.g., 1.5)", severity="error")
            return

        description = self.query_one("#description", Input).value.strip()
        if not description:
            self.notify("Service description is required", severity="error")
            return

        notes = self.query_one("#notes", Input).value.strip() or None

        db = get_session()
        try:
            update_transaction(db, self.tx_id, hours, description, notes)
            self.notify("Transaction updated!", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            db.close()


class ConfirmStatusChangeModal(ModalScreen):
    """Modal for confirming status changes (complete, reopen, dispute)."""

    def __init__(self, tx_id: int, action: str):
        super().__init__()
        self.tx_id = tx_id
        self.action = action

    def compose(self) -> None:
        action_text = {
            "complete": ("MARK AS COMPLETED", "completed"),
            "reopen": ("REOPEN TRANSACTION", "reopened"),
            "dispute": ("DISPUTE TRANSACTION", "disputed"),
        }
        title, desc = action_text.get(self.action, ("UPDATE STATUS", "updated"))

        with Container(classes="modal-form"):
            yield Static(title, classes="modal-form-title")
            yield Static(f"Transaction ID: {self.tx_id}")
            yield Static(f"Confirm: {desc}?", classes="confirm-warning")
            yield Static("This action can be undone later.")
            with Horizontal(classes="modal-form-actions"):
                yield Button("Confirm", variant="primary", id="confirm")
                yield Button("Cancel", variant="warning", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss()
            return

        db = get_session()
        try:
            if self.action == "complete":
                complete_transaction(db, self.tx_id)
                self.notify("Transaction marked as completed!", severity="information")
            elif self.action == "reopen":
                reopen_transaction(db, self.tx_id)
                self.notify("Transaction reopened!", severity="information")
            elif self.action == "dispute":
                dispute_transaction(db, self.tx_id)
                self.notify("Transaction disputed!", severity="warning")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            db.close()


class DeleteTransactionModal(ModalScreen):
    """Modal for confirming transaction deletion."""

    def __init__(self, tx_id: int):
        super().__init__()
        self.tx_id = tx_id

    def compose(self) -> None:
        with Container(classes="modal-form"):
            yield Static("DELETE TRANSACTION", classes="modal-form-title")
            yield Static("!", classes="confirm-danger")
            yield Static(f"Confirm deletion of Transaction #{self.tx_id}?", classes="confirm-warning")
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
            delete_transaction(db, self.tx_id)
            self.notify("Transaction deleted!", severity="warning")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            db.close()


class TransactionsScreen(Screen):
    """Transactions management screen."""

    selected_tx_id = reactive(None)
    transactions_data = reactive([])
    _initial_load = True

    BINDINGS = [
        ("n", "action_new", "New"),
        ("e", "action_edit", "Edit"),
        ("c", "action_complete", "Complete"),
        ("o", "action_reopen", "Reopen"),
        ("x", "action_dispute", "Dispute"),
        ("d", "action_delete", "Delete"),
        ("r", "action_refresh", "Refresh"),
        ("enter", "action_select", "Select"),
    ]

    def compose(self) -> None:
        with Container(id="transactions-container", classes="screen-container"):
            yield Static("TIME ECONOMY - TRANSACTIONS", id="header")
            yield Static("D:Dash M:Members T:Trans N:Needs G:Govern S:Skills | N:New E:Edit C:Comp O:Open X:Disp D:Del R:Refresh Q:Quit", id="nav-bar")

            with Container(id="content", classes="content-area"):
                yield DataTable(id="transactions-table")

            with Horizontal(id="tx-actions", classes="action-bar"):
                yield Button("New Transaction", variant="primary", id="btn-new")
                yield Button("Edit", variant="primary", id="btn-edit")
                yield Button("Complete", variant="success", id="btn-complete")
                yield Button("Reopen", variant="warning", id="btn-reopen")
                yield Button("Dispute", variant="error", id="btn-dispute")
                yield Button("Delete", variant="error", id="btn-delete")
                yield Button("Refresh", variant="primary", id="btn-refresh")

            yield Static("Use arrow keys to navigate, Enter to select", id="footer")

    def on_mount(self) -> None:
        self.refresh_data()
        self.set_focus_table("#transactions-table")

    def set_focus_table(self, table_id: str) -> None:
        """Focus the DataTable after data is loaded."""
        table = self.query_one(table_id, DataTable)
        table.focus()

    def refresh_data(self) -> None:
        db = get_session()
        try:
            transactions = get_all_transactions(db)
            data = []
            for tx in transactions:
                from_m = db.query(Member).filter(Member.id == tx.from_member_id).first()
                to_m = db.query(Member).filter(Member.id == tx.to_member_id).first()

                data.append({
                    "id": tx.id,
                    "date": tx.created_at.strftime("%Y-%m-%d"),
                    "from": from_m.name if from_m else "?",
                    "to": to_m.name if to_m else "?",
                    "hours": tx.hours,
                    "status": self._format_status(tx.status),
                    "raw_status": tx.status,
                    "description": tx.service_description,
                    "notes": tx.notes or "",
                })
            self.transactions_data = data
        finally:
            db.close()
            # Reset initial load flag so next refresh focuses properly
            self._initial_load = True

    def _format_status(self, status: str) -> str:
        status_map = {
            "pending": "[?] pending",
            "completed": "[*] completed",
            "disputed": "[!] disputed",
        }
        return status_map.get(status, f"[?] {status}")

    def watch_transactions_data(self, data) -> None:
        table = self.query_one("#transactions-table", DataTable)
        table.clear(columns=True)
        table.add_columns("ID", "Date", "From", "To", "Hours", "Status", "Description")
        for tx in data:
            table.add_row(
                str(tx["id"]), tx["date"], tx["from"], tx["to"],
                str(tx["hours"]), tx["status"], tx["description"][:35]
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
        table = self.query_one("#transactions-table", DataTable)
        data = table.get_row(event.row_key)
        self.selected_tx_id = int(data[0])

        for tx in self.transactions_data:
            if tx["id"] == self.selected_tx_id:
                self.query_one("#footer", Static).update(
                    f"Selected: #{tx['id']} | {tx['from']} -> {tx['to']} | {tx['hours']}h | {tx['status']} | {tx['description'][:40]}"
                )
                break

    def action_new(self) -> None:
        """Keyboard shortcut: Create new transaction."""
        self.app.push_screen(CreateTransactionModal(), callback=lambda _: self.refresh_data())

    def action_edit(self) -> None:
        """Keyboard shortcut: Edit selected transaction."""
        if self.selected_tx_id:
            self.app.push_screen(EditTransactionModal(self.selected_tx_id), callback=lambda _: self.refresh_data())
        else:
            self.notify("Select a transaction first - use arrow keys", severity="warning")

    def action_complete(self) -> None:
        """Keyboard shortcut: Mark transaction as complete."""
        if self.selected_tx_id:
            self.app.push_screen(ConfirmStatusChangeModal(self.selected_tx_id, "complete"), callback=lambda _: self.refresh_data())
        else:
            self.notify("Select a transaction first - use arrow keys", severity="warning")

    def action_reopen(self) -> None:
        """Keyboard shortcut: Reopen transaction."""
        if self.selected_tx_id:
            self.app.push_screen(ConfirmStatusChangeModal(self.selected_tx_id, "reopen"), callback=lambda _: self.refresh_data())
        else:
            self.notify("Select a transaction first - use arrow keys", severity="warning")

    def action_dispute(self) -> None:
        """Keyboard shortcut: Dispute transaction."""
        if self.selected_tx_id:
            self.app.push_screen(ConfirmStatusChangeModal(self.selected_tx_id, "dispute"), callback=lambda _: self.refresh_data())
        else:
            self.notify("Select a transaction first - use arrow keys", severity="warning")

    def action_delete(self) -> None:
        """Keyboard shortcut: Delete transaction."""
        if self.selected_tx_id:
            self.app.push_screen(DeleteTransactionModal(self.selected_tx_id), callback=lambda _: self.refresh_data())
        else:
            self.notify("Select a transaction first - use arrow keys", severity="warning")

    def action_select(self) -> None:
        """Keyboard shortcut: Select current row."""
        table = self.query_one("#transactions-table", DataTable)
        if table.cursor_row is not None and table.row_count > 0:
            row_key = table.get_row_at(table.cursor_row)[0]
            try:
                self.selected_tx_id = int(row_key)
                for tx in self.transactions_data:
                    if tx["id"] == self.selected_tx_id:
                        self.query_one("#footer", Static).update(
                            f"Selected: #{tx['id']} | {tx['from']} -> {tx['to']} | {tx['hours']}h | {tx['status']} | {tx['description'][:40]}"
                        )
                        break
            except (ValueError, TypeError):
                pass

    def action_refresh(self) -> None:
        """Keyboard shortcut: Refresh data."""
        self.refresh_data()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-new":
            self.app.push_screen(CreateTransactionModal(), callback=lambda _: self.refresh_data())
        elif event.button.id == "btn-edit":
            if self.selected_tx_id:
                self.app.push_screen(EditTransactionModal(self.selected_tx_id), callback=lambda _: self.refresh_data())
            else:
                self.notify("Select a transaction first - use arrow keys", severity="warning")
        elif event.button.id == "btn-complete":
            if self.selected_tx_id:
                self.app.push_screen(ConfirmStatusChangeModal(self.selected_tx_id, "complete"), callback=lambda _: self.refresh_data())
            else:
                self.notify("Select a transaction first - use arrow keys", severity="warning")
        elif event.button.id == "btn-reopen":
            if self.selected_tx_id:
                self.app.push_screen(ConfirmStatusChangeModal(self.selected_tx_id, "reopen"), callback=lambda _: self.refresh_data())
            else:
                self.notify("Select a transaction first - use arrow keys", severity="warning")
        elif event.button.id == "btn-dispute":
            if self.selected_tx_id:
                self.app.push_screen(ConfirmStatusChangeModal(self.selected_tx_id, "dispute"), callback=lambda _: self.refresh_data())
            else:
                self.notify("Select a transaction first - use arrow keys", severity="warning")
        elif event.button.id == "btn-delete":
            if self.selected_tx_id:
                self.app.push_screen(DeleteTransactionModal(self.selected_tx_id), callback=lambda _: self.refresh_data())
            else:
                self.notify("Select a transaction first - use arrow keys", severity="warning")
        elif event.button.id == "btn-refresh":
            self.refresh_data()