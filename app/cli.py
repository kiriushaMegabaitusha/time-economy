"""
Rich CLI for Time Economy.

A command-line interface with rich formatting for managing
the time-based economy from the terminal.

Usage:
    python -m app.cli [COMMAND]
    python -m app.cli dashboard
    python -m app.cli members list
    python -m app.cli tx create --from 1 --to 2 --hours 2.5 "Garden help"
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from datetime import datetime

from app.services import (
    get_session, get_dashboard_stats, get_member_balances,
    get_all_members, get_member_detail, create_member,
    update_member, update_member_status, delete_member,
    add_skill, add_want, update_skill, delete_skill, update_want, delete_want,
    get_all_transactions, create_transaction,
    complete_transaction, dispute_transaction, reopen_transaction, update_transaction, delete_transaction,
    get_all_needs, create_need, fulfill_need, close_need, reopen_need, update_need, delete_need,
    get_all_governance, create_governance, vote_governance,
    update_governance_status, update_governance, delete_governance,
    get_skills_directory, get_skill_matches
)

console = Console()
app = typer.Typer(help="Time Economy CLI")


# ==================== DASHBOARD ====================

@app.command()
def dashboard():
    """Show system dashboard."""
    db = get_session()
    try:
        stats = get_dashboard_stats(db)

        # Stats grid
        grid = Table.grid(padding=1)
        grid.add_column(style="bold cyan")
        grid.add_column(style="bold")
        grid.add_row("Active Members:", str(stats["total_members"]))
        grid.add_row("Total Transactions:", str(stats["total_transactions"]))
        grid.add_row("Total Hours:", str(stats["total_hours"]))
        grid.add_row("Open Needs:", str(stats["active_needs"]))
        grid.add_row("Avg Balance:", f"{stats['avg_balance']} credits")
        grid.add_row("Hours (30d):", str(stats["recent_hours"]))

        console.print(Panel(grid, title="[bold blue]Time Economy Dashboard[/bold blue]",
                           subtitle=f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"))

        # Alerts
        if stats["alerts"]:
            for alert in stats["alerts"]:
                color = "red" if alert["type"] == "deficit" else "yellow"
                console.print(f"[{color}][{alert['type'].upper()}][/{color}] {alert['message']}")

        # Recent transactions
        if stats["recent_transactions"]:
            table = Table(title="Recent Transactions", box=box.SIMPLE)
            table.add_column("Date", style="dim")
            table.add_column("From")
            table.add_column("To")
            table.add_column("Hours", justify="right")
            table.add_column("Status")
            table.add_column("Description")

            for tx in stats["recent_transactions"][:5]:
                from_name = tx.from_member.name if tx.from_member else "?"
                to_name = tx.to_member.name if tx.to_member else "?"
                status_style = "green" if tx.status == "completed" else "yellow" if tx.status == "pending" else "red"
                table.add_row(
                    tx.created_at.strftime("%Y-%m-%d"),
                    from_name, to_name, str(tx.hours),
                    f"[{status_style}]{tx.status}[/{status_style}]",
                    tx.service_description[:30]
                )
            console.print(table)

        # Top skills
        if stats["top_skills"]:
            skills_text = ", ".join([f"{s['name']} ({s['count']})" for s in stats["top_skills"][:5]])
            console.print(f"\n[dim]Top Skills:[/dim] {skills_text}")
    finally:
        db.close()


# ==================== MEMBERS ====================

members_app = typer.Typer(help="Member management")
app.add_typer(members_app, name="members")

@members_app.command("list")
def list_members():
    """List all members with balances."""
    db = get_session()
    try:
        members = get_member_balances(db)
        table = Table(title="Member Directory", box=box.SIMPLE_HEAVY)
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Name", style="bold")
        table.add_column("Email")
        table.add_column("Phone")
        table.add_column("Status")
        table.add_column("Balance", justify="right")

        for m in members:
            balance_style = "green" if m["balance"] >= 0 else "red"
            if m["balance"] > 20:
                balance_style = "yellow"
            table.add_row(
                str(m["id"]), m["name"], m["email"] or "",
                m["phone"] or "", m["status"],
                f"[{balance_style}]{m['balance']:+}[/{balance_style}]"
            )
        console.print(table)
    finally:
        db.close()

@members_app.command("add")
def add_member(
    name: str = typer.Argument(..., help="Member name"),
    email: str = typer.Argument(..., help="Member email"),
    phone: Optional[str] = typer.Option(None, help="Phone number"),
    bio: Optional[str] = typer.Option(None, help="Short bio"),
    initial_credit: float = typer.Option(5.0, help="Initial credit")
):
    """Add a new member."""
    db = get_session()
    try:
        member = create_member(db, name, email, phone, bio, initial_credit)
        console.print(f"[green]Member created:[/green] {member.name} (ID: {member.id})")
    finally:
        db.close()

@members_app.command("show")
def show_member(member_id: int = typer.Argument(..., help="Member ID")):
    """Show member details."""
    db = get_session()
    try:
        member = get_member_detail(db, member_id)
        if not member:
            console.print(f"[red]Member {member_id} not found[/red]")
            return

        console.print(Panel(
            f"[bold]{member.name}[/bold]\n"
            f"Email: {member.email}\n"
            f"Phone: {member.phone or 'N/A'}\n"
            f"Status: {member.status}\n"
            f"Joined: {member.joined_at.strftime('%Y-%m-%d')}\n"
            f"Balance: [bold]{'green' if -10 <= member.balance <= 20 else 'red' if member.balance < -10 else 'yellow'}]{member.balance:+.2f} credits[/bold]",
            title=f"Member #{member.id}"
        ))

        if member.skills_offered:
            skills = ", ".join([s.name for s in member.skills_offered])
            console.print(f"[dim]Skills:[/dim] {skills}")
        if member.skills_wanted:
            wants = ", ".join([w.name for w in member.skills_wanted])
            console.print(f"[dim]Wants:[/dim] {wants}")
    finally:
        db.close()

@members_app.command("skill")
def member_skill(
    member_id: int = typer.Argument(..., help="Member ID"),
    name: str = typer.Argument(..., help="Skill name"),
    category: Optional[str] = typer.Option(None, help="Category"),
    description: Optional[str] = typer.Option(None, help="Description")
):
    """Add a skill to a member."""
    db = get_session()
    try:
        skill = add_skill(db, member_id, name, category, description)
        console.print(f"[green]Skill added:[/green] {skill.name}")
    finally:
        db.close()

@members_app.command("want")
def member_want(
    member_id: int = typer.Argument(..., help="Member ID"),
    name: str = typer.Argument(..., help="Skill wanted"),
    description: Optional[str] = typer.Option(None, help="Description")
):
    """Add a skill want to a member."""
    db = get_session()
    try:
        want = add_want(db, member_id, name, description)
        console.print(f"[green]Want added:[/green] {want.name}")
    finally:
        db.close()

@members_app.command("edit")
def edit_member(
    member_id: int = typer.Argument(..., help="Member ID"),
    name: Optional[str] = typer.Option(None, help="New name"),
    email: Optional[str] = typer.Option(None, help="New email"),
    phone: Optional[str] = typer.Option(None, help="New phone"),
    bio: Optional[str] = typer.Option(None, help="New bio"),
    status: Optional[str] = typer.Option(None, help="New status: active, inactive, suspended")
):
    """Edit a member's details."""
    db = get_session()
    try:
        member = update_member(db, member_id, name, email, phone, bio)
        if status:
            update_member_status(db, member_id, status)
        if member:
            console.print(f"[green]Member {member_id} updated[/green]")
        else:
            console.print(f"[red]Member {member_id} not found[/red]")
    finally:
        db.close()

@members_app.command("delete")
def remove_member(member_id: int = typer.Argument(..., help="Member ID")):
    """Delete a member and all related data."""
    db = get_session()
    try:
        if delete_member(db, member_id):
            console.print(f"[green]Member {member_id} deleted[/green]")
        else:
            console.print(f"[red]Member {member_id} not found[/red]")
    finally:
        db.close()

@members_app.command("delete-skill")
def remove_skill(skill_id: int = typer.Argument(..., help="Skill ID")):
    """Delete a skill."""
    db = get_session()
    try:
        if delete_skill(db, skill_id):
            console.print(f"[green]Skill {skill_id} deleted[/green]")
        else:
            console.print(f"[red]Skill {skill_id} not found[/red]")
    finally:
        db.close()

@members_app.command("delete-want")
def remove_want(want_id: int = typer.Argument(..., help="Want ID")):
    """Delete a skill want."""
    db = get_session()
    try:
        if delete_want(db, want_id):
            console.print(f"[green]Want {want_id} deleted[/green]")
        else:
            console.print(f"[red]Want {want_id} not found[/red]")
    finally:
        db.close()


# ==================== TRANSACTIONS ====================

tx_app = typer.Typer(help="Transaction management")
app.add_typer(tx_app, name="tx")

@tx_app.command("list")
def list_transactions():
    """List all transactions."""
    db = get_session()
    try:
        transactions = get_all_transactions(db)
        table = Table(title="Transaction Log", box=box.SIMPLE)
        table.add_column("ID", justify="right")
        table.add_column("Date", style="dim")
        table.add_column("From")
        table.add_column("To")
        table.add_column("Hours", justify="right")
        table.add_column("Status")
        table.add_column("Description")

        for tx in transactions:
            from app.models import Member
            from_m = db.query(Member).filter(Member.id == tx.from_member_id).first()
            to_m = db.query(Member).filter(Member.id == tx.to_member_id).first()
            status_style = "green" if tx.status == "completed" else "yellow" if tx.status == "pending" else "red"
            table.add_row(
                str(tx.id), tx.created_at.strftime("%Y-%m-%d"),
                from_m.name if from_m else "?",
                to_m.name if to_m else "?",
                str(tx.hours),
                f"[{status_style}]{tx.status}[/{status_style}]",
                tx.service_description[:30]
            )
        console.print(table)
    finally:
        db.close()

@tx_app.command("create")
def create_tx(
    from_member: int = typer.Option(..., "--from", help="From member ID"),
    to_member: int = typer.Option(..., "--to", help="To member ID"),
    hours: float = typer.Option(..., "--hours", help="Hours"),
    description: str = typer.Argument(..., help="Service description"),
    notes: Optional[str] = typer.Option(None, help="Notes")
):
    """Create a new transaction."""
    db = get_session()
    try:
        tx = create_transaction(db, from_member, to_member, hours, description, notes)
        console.print(f"[green]Transaction created:[/green] ID {tx.id}")
    finally:
        db.close()

@tx_app.command("complete")
def complete_tx(transaction_id: int = typer.Argument(..., help="Transaction ID")):
    """Mark a transaction as completed."""
    db = get_session()
    try:
        tx = complete_transaction(db, transaction_id)
        if tx:
            console.print(f"[green]Transaction {transaction_id} completed[/green]")
        else:
            console.print(f"[red]Transaction {transaction_id} not found[/red]")
    finally:
        db.close()

@tx_app.command("dispute")
def dispute_tx(transaction_id: int = typer.Argument(..., help="Transaction ID")):
    """Mark a transaction as disputed."""
    db = get_session()
    try:
        tx = dispute_transaction(db, transaction_id)
        if tx:
            console.print(f"[yellow]Transaction {transaction_id} disputed[/yellow]")
        else:
            console.print(f"[red]Transaction {transaction_id} not found[/red]")
    finally:
        db.close()

@tx_app.command("reopen")
def reopen_tx(transaction_id: int = typer.Argument(..., help="Transaction ID")):
    """Reopen a disputed transaction."""
    db = get_session()
    try:
        tx = reopen_transaction(db, transaction_id)
        if tx:
            console.print(f"[green]Transaction {transaction_id} reopened[/green]")
        else:
            console.print(f"[red]Transaction {transaction_id} not found[/red]")
    finally:
        db.close()

@tx_app.command("edit")
def edit_tx(
    transaction_id: int = typer.Argument(..., help="Transaction ID"),
    hours: Optional[float] = typer.Option(None, help="New hours"),
    description: Optional[str] = typer.Option(None, help="New description"),
    notes: Optional[str] = typer.Option(None, help="New notes")
):
    """Edit a transaction."""
    db = get_session()
    try:
        tx = update_transaction(db, transaction_id, hours, description, notes)
        if tx:
            console.print(f"[green]Transaction {transaction_id} updated[/green]")
        else:
            console.print(f"[red]Transaction {transaction_id} not found[/red]")
    finally:
        db.close()

@tx_app.command("delete")
def remove_tx(transaction_id: int = typer.Argument(..., help="Transaction ID")):
    """Delete a transaction."""
    db = get_session()
    try:
        if delete_transaction(db, transaction_id):
            console.print(f"[green]Transaction {transaction_id} deleted[/green]")
        else:
            console.print(f"[red]Transaction {transaction_id} not found[/red]")
    finally:
        db.close()


# ==================== NEEDS ====================

needs_app = typer.Typer(help="Needs board management")
app.add_typer(needs_app, name="needs")

@needs_app.command("list")
def list_needs():
    """List all needs."""
    db = get_session()
    try:
        needs = get_all_needs(db)
        table = Table(title="Needs Board", box=box.SIMPLE)
        table.add_column("ID", justify="right")
        table.add_column("Date", style="dim")
        table.add_column("Status")
        table.add_column("Hours", justify="right")
        table.add_column("Member")
        table.add_column("Title")

        for need in needs:
            from app.models import Member
            member = db.query(Member).filter(Member.id == need.member_id).first()
            status_style = "green" if need.status == "open" else "blue" if need.status == "fulfilled" else "dim"
            table.add_row(
                str(need.id), need.created_at.strftime("%Y-%m-%d"),
                f"[{status_style}]{need.status}[/{status_style}]",
                str(need.hours_estimated),
                member.name if member else "?",
                need.title[:30]
            )
        console.print(table)
    finally:
        db.close()

@needs_app.command("create")
def create_need_cmd(
    member_id: int = typer.Option(..., "--member", help="Member ID"),
    title: str = typer.Argument(..., help="Need title"),
    description: str = typer.Argument(..., help="Need description"),
    hours: float = typer.Option(1.0, "--hours", help="Estimated hours")
):
    """Post a new need."""
    db = get_session()
    try:
        need = create_need(db, member_id, title, description, hours)
        console.print(f"[green]Need posted:[/green] ID {need.id}")
    finally:
        db.close()

@needs_app.command("fulfill")
def fulfill_need_cmd(need_id: int = typer.Argument(..., help="Need ID")):
    """Mark a need as fulfilled."""
    db = get_session()
    try:
        need = fulfill_need(db, need_id)
        if need:
            console.print(f"[green]Need {need_id} fulfilled[/green]")
        else:
            console.print(f"[red]Need {need_id} not found[/red]")
    finally:
        db.close()

@needs_app.command("close")
def close_need_cmd(need_id: int = typer.Argument(..., help="Need ID")):
    """Close a need."""
    db = get_session()
    try:
        need = close_need(db, need_id)
        if need:
            console.print(f"[green]Need {need_id} closed[/green]")
        else:
            console.print(f"[red]Need {need_id} not found[/red]")
    finally:
        db.close()

@needs_app.command("reopen")
def reopen_need_cmd(need_id: int = typer.Argument(..., help="Need ID")):
    """Reopen a fulfilled or closed need."""
    db = get_session()
    try:
        need = reopen_need(db, need_id)
        if need:
            console.print(f"[green]Need {need_id} reopened[/green]")
        else:
            console.print(f"[red]Need {need_id} not found[/red]")
    finally:
        db.close()

@needs_app.command("edit")
def edit_need(
    need_id: int = typer.Argument(..., help="Need ID"),
    title: Optional[str] = typer.Option(None, help="New title"),
    description: Optional[str] = typer.Option(None, help="New description"),
    hours: Optional[float] = typer.Option(None, "--hours", help="New estimated hours")
):
    """Edit a need."""
    db = get_session()
    try:
        need = update_need(db, need_id, title, description, hours)
        if need:
            console.print(f"[green]Need {need_id} updated[/green]")
        else:
            console.print(f"[red]Need {need_id} not found[/red]")
    finally:
        db.close()

@needs_app.command("delete")
def remove_need(need_id: int = typer.Argument(..., help="Need ID")):
    """Delete a need."""
    db = get_session()
    try:
        if delete_need(db, need_id):
            console.print(f"[green]Need {need_id} deleted[/green]")
        else:
            console.print(f"[red]Need {need_id} not found[/red]")
    finally:
        db.close()


# ==================== GOVERNANCE ====================

gov_app = typer.Typer(help="Governance management")
app.add_typer(gov_app, name="gov")

@gov_app.command("list")
def list_governance():
    """List governance entries."""
    db = get_session()
    try:
        entries = get_all_governance(db)
        table = Table(title="Governance Log", box=box.SIMPLE)
        table.add_column("ID", justify="right")
        table.add_column("Date", style="dim")
        table.add_column("Type")
        table.add_column("Status")
        table.add_column("Votes")
        table.add_column("Title")

        for entry in entries:
            status_style = {
                "proposed": "yellow",
                "approved": "green",
                "rejected": "red",
                "implemented": "blue"
            }.get(entry.status, "white")
            table.add_row(
                str(entry.id), entry.created_at.strftime("%Y-%m-%d"),
                entry.decision_type,
                f"[{status_style}]{entry.status}[/{status_style}]",
                f"+{entry.vote_for}/-{entry.vote_against}",
                entry.title[:35]
            )
        console.print(table)
    finally:
        db.close()

@gov_app.command("create")
def create_gov(
    title: str = typer.Argument(..., help="Title"),
    description: str = typer.Argument(..., help="Description"),
    decision_type: str = typer.Option("meeting_note", "--type", help="Type: rule_change, dispute_resolution, system_upgrade, meeting_note"),
    member_id: Optional[int] = typer.Option(None, "--member", help="Proposed by member ID")
):
    """Create a governance entry."""
    db = get_session()
    try:
        entry = create_governance(db, title, description, decision_type, member_id)
        console.print(f"[green]Governance entry created:[/green] ID {entry.id}")
    finally:
        db.close()

@gov_app.command("vote")
def vote_gov(
    entry_id: int = typer.Argument(..., help="Entry ID"),
    vote: str = typer.Argument(..., help="Vote: for or against")
):
    """Vote on a governance entry."""
    db = get_session()
    try:
        entry = vote_governance(db, entry_id, vote)
        if entry:
            console.print(f"[green]Voted {vote} on entry {entry_id}[/green]")
        else:
            console.print(f"[red]Entry {entry_id} not found[/red]")
    finally:
        db.close()

@gov_app.command("status")
def status_gov(
    entry_id: int = typer.Argument(..., help="Entry ID"),
    status: str = typer.Argument(..., help="New status: proposed, approved, rejected, implemented")
):
    """Update governance entry status."""
    db = get_session()
    try:
        entry = update_governance_status(db, entry_id, status)
        if entry:
            console.print(f"[green]Entry {entry_id} status updated to {status}[/green]")
        else:
            console.print(f"[red]Entry {entry_id} not found[/red]")
    finally:
        db.close()

@gov_app.command("edit")
def edit_gov(
    entry_id: int = typer.Argument(..., help="Entry ID"),
    title: Optional[str] = typer.Option(None, help="New title"),
    description: Optional[str] = typer.Option(None, help="New description"),
    decision_type: Optional[str] = typer.Option(None, "--type", help="New decision type")
):
    """Edit a governance entry."""
    db = get_session()
    try:
        entry = update_governance(db, entry_id, title, description, decision_type)
        if entry:
            console.print(f"[green]Entry {entry_id} updated[/green]")
        else:
            console.print(f"[red]Entry {entry_id} not found[/red]")
    finally:
        db.close()

@gov_app.command("delete")
def remove_gov(entry_id: int = typer.Argument(..., help="Entry ID")):
    """Delete a governance entry."""
    db = get_session()
    try:
        if delete_governance(db, entry_id):
            console.print(f"[green]Entry {entry_id} deleted[/green]")
        else:
            console.print(f"[red]Entry {entry_id} not found[/red]")
    finally:
        db.close()


# ==================== SKILLS ====================

@app.command()
def skills():
    """Show skills directory."""
    db = get_session()
    try:
        directory = get_skills_directory(db)

        if directory["skills"]:
            table = Table(title="Skills Offered", box=box.SIMPLE)
            table.add_column("Skill", style="bold")
            table.add_column("Category", style="dim")
            table.add_column("Member")
            for skill in directory["skills"]:
                table.add_row(skill.name, skill.category or "", skill.member_name or "?")
            console.print(table)

        if directory["wants"]:
            table = Table(title="Skills Wanted", box=box.SIMPLE)
            table.add_column("Want", style="bold")
            table.add_column("Member")
            for want in directory["wants"]:
                table.add_row(want.name, want.member_name or "?")
            console.print(table)

        matches = get_skill_matches(db)
        if matches:
            console.print("\n[bold cyan]Matches:[/bold cyan]")
            for match in matches:
                console.print(f"  {match['want_member']} needs {match['want_name']} -> {match['skill_member']} offers {match['skill_name']}")
    finally:
        db.close()


if __name__ == "__main__":
    app()
