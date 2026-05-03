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
from app.models import Member


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

            yield Select(options=member_options, id="from_member", prompt="From member")
            yield Select(options=member_options, id="to_member", prompt="To member")
            yield Input(placeholder="Hours", id="hours")
            yield Input(placeholder="Service description", id="description")
            yield Input(placeholder="Notes (optional)", id="notes")

            with Horizontal():
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="error", id="cancel")

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

        if from_id is Select.BLANK or to_id is Select.BLANK:
            self.notify("Please select both members", severity="error")
            return

        try:
            hours = float(hours_input.value)
        except ValueError:
            self.notify("Hours must be a number", severity="error")
            return

        description = desc_input.value.strip()
        if not description:
            self.notify("Description is required", severity="error")
            return

        notes = notes_input.value.strip() or None

        if from_id == to_id:
            self.notify("Cannot send to same member", severity="error")
            return

        db = get_session()
        try:
            create_transaction(db, int(from_id), int(to_id), hours, description, notes)
            self.notify("Transaction created!")
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
            yield Input(placeholder="Hours", value=str(self.tx.hours) if self.tx else "", id="hours")
            yield Input(placeholder="Service description", value=self.tx.service_description if self.tx else "", id="description")
            yield Input(placeholder="Notes", value=self.tx.notes or "", id="notes")
            with Horizontal():
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="error", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss()
            return

        try:
            hours = float(self.query_one("#hours", Input).value)
        except ValueError:
            self.notify("Hours must be a number", severity="error")
            return

        description = self.query_one("#description", Input).value.strip()
        if not description:
            self.notify("Description is required", severity="error")
            return

        notes = self.query_one("#notes", Input).value.strip() or None

        db = get_session()
        try:
            update_transaction(db, self.tx_id, hours, description, notes)
            self.notify("Transaction updated!")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            db.close()


class TransactionsScreen(Screen):
    """Transactions log screen."""

    transactions_data = reactive([])
    selected_tx_id = reactive(None)

    def compose(self) -> None:
        with Container(id="transactions-container"):
            yield Static("TIME ECONOMY - TRANSACTIONS", id="header")
            yield Static("Keys: [t]ransactions [d]ashboard [m]embers [n]eeds [g]overnance [s]kills  [n]ew  [c]omplete  [r]efresh  [q]uit", id="nav-bar")

            yield DataTable(id="transactions-table")

            with Horizontal(id="tx-actions"):
                yield Button("New Transaction", variant="primary", id="btn-new")
                yield Button("Edit", variant="primary", id="btn-edit")
                yield Button("Complete", variant="success", id="btn-complete")
                yield Button("Reopen", variant="warning", id="btn-reopen")
                yield Button("Dispute", variant="error", id="btn-dispute")
                yield Button("Delete", variant="error", id="btn-delete")
                yield Button("Refresh", variant="primary", id="btn-refresh")

            yield Static("Ready", id="footer")

    def on_mount(self) -> None:
        self.refresh_data()

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
                    "status": tx.status,
                    "description": tx.service_description,
                    "notes": tx.notes or "",
                })
            self.transactions_data = data
        finally:
            db.close()

    def watch_transactions_data(self, data) -> None:
        table = self.query_one("#transactions-table", DataTable)
        table.clear(columns=True)
        table.add_columns("ID", "Date", "From", "To", "Hours", "Status", "Description")
        for tx in data:
            table.add_row(
                str(tx["id"]), tx["date"], tx["from"], tx["to"],
                str(tx["hours"]), tx["status"], tx["description"][:35]
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = self.query_one("#transactions-table", DataTable)
        data = table.get_row(event.row_key)
        self.selected_tx_id = int(data[0])

        for tx in self.transactions_data:
            if tx["id"] == self.selected_tx_id:
                self.query_one("#footer", Static).update(
                    f"Selected: {tx['from']} -> {tx['to']} | {tx['hours']}h | {tx['status']} | {tx['description'][:40]}"
                )
                break

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-new":
            self.push_screen(CreateTransactionModal(), callback=lambda _: self.refresh_data())
        elif event.button.id == "btn-edit":
            if self.selected_tx_id:
                self.push_screen(EditTransactionModal(self.selected_tx_id), callback=lambda _: self.refresh_data())
            else:
                self.notify("Select a transaction first", severity="warning")
        elif event.button.id == "btn-complete":
            if self.selected_tx_id:
                db = get_session()
                try:
                    complete_transaction(db, self.selected_tx_id)
                    self.notify("Transaction completed!")
                    self.refresh_data()
                except Exception as e:
                    self.notify(f"Error: {e}", severity="error")
                finally:
                    db.close()
            else:
                self.notify("Select a transaction first", severity="warning")
        elif event.button.id == "btn-reopen":
            if self.selected_tx_id:
                db = get_session()
                try:
                    reopen_transaction(db, self.selected_tx_id)
                    self.notify("Transaction reopened!")
                    self.refresh_data()
                except Exception as e:
                    self.notify(f"Error: {e}", severity="error")
                finally:
                    db.close()
            else:
                self.notify("Select a transaction first", severity="warning")
        elif event.button.id == "btn-dispute":
            if self.selected_tx_id:
                db = get_session()
                try:
                    dispute_transaction(db, self.selected_tx_id)
                    self.notify("Transaction disputed!")
                    self.refresh_data()
                except Exception as e:
                    self.notify(f"Error: {e}", severity="error")
                finally:
                    db.close()
            else:
                self.notify("Select a transaction first", severity="warning")
        elif event.button.id == "btn-delete":
            if self.selected_tx_id:
                db = get_session()
                try:
                    delete_transaction(db, self.selected_tx_id)
                    self.notify("Transaction deleted!")
                    self.selected_tx_id = None
                    self.refresh_data()
                except Exception as e:
                    self.notify(f"Error: {e}", severity="error")
                finally:
                    db.close()
            else:
                self.notify("Select a transaction first", severity="warning")
        elif event.button.id == "btn-refresh":
            self.refresh_data()
