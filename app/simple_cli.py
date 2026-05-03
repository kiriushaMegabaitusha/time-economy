"""
Simple Plain-Text CLI for Time Economy.

A minimal, menu-driven command-line interface designed for low-income
communities with limited technology access. Works on any terminal.

Usage:
    python -m app.simple_cli

This is intentionally simple - no colors, no fancy formatting, just
clear numbered menus and plain text output.
"""

import os
import sys
import csv
import json
from datetime import datetime
from typing import Optional

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services import (
    get_session, get_dashboard_stats, get_member_balances,
    get_all_members, get_member_detail, create_member,
    add_skill, add_want, get_all_transactions, create_transaction,
    complete_transaction, dispute_transaction, delete_transaction,
    get_all_needs, create_need, fulfill_need, close_need,
    get_all_governance, create_governance, vote_governance,
    update_governance_status, get_skills_directory, get_skill_matches,
    calculate_balance
)
from app.models import Member


def clear_screen():
    """Clear screen in a cross-platform way."""
    os.system('cls' if os.name == 'nt' else 'clear')


def pause():
    """Wait for user to press Enter."""
    input("\nPress Enter to continue...")


def print_header(title: str):
    """Print a simple header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_menu(options: list):
    """Print numbered menu options."""
    print()
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")
    print(f"  0. Back / Exit")
    print()


def get_choice(max_choice: int) -> int:
    """Get a valid menu choice from user."""
    while True:
        try:
            choice = input("Choice: ").strip()
            if not choice:
                continue
            num = int(choice)
            if 0 <= num <= max_choice:
                return num
            print("Invalid choice. Try again.")
        except ValueError:
            print("Please enter a number.")


def get_input(prompt: str, required: bool = True) -> Optional[str]:
    """Get user input with optional requirement."""
    while True:
        value = input(prompt).strip()
        if value or not required:
            return value if value else None
        print("This field is required.")


def get_float_input(prompt: str, default: float = None) -> float:
    """Get a float input from user."""
    while True:
        value = input(prompt).strip()
        if not value and default is not None:
            return default
        try:
            return float(value)
        except ValueError:
            print("Please enter a valid number.")


# ==================== DASHBOARD ====================

def show_dashboard():
    """Display the main dashboard."""
    db = get_session()
    try:
        stats = get_dashboard_stats(db)

        print_header("TIME ECONOMY DASHBOARD")
        print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print()
        print("  SYSTEM OVERVIEW")
        print("  -" * 30)
        print(f"  Active Members:       {stats['total_members']}")
        print(f"  Total Transactions:   {stats['total_transactions']}")
        print(f"  Total Hours Exchanged: {stats['total_hours']}")
        print(f"  Active Needs:         {stats['active_needs']}")
        print(f"  Average Balance:      {stats['avg_balance']} credits")
        print(f"  Hours (last 30 days): {stats['recent_hours']}")

        if stats['alerts']:
            print()
            print("  ALGEDONIC ALERTS")
            print("  -" * 30)
            for alert in stats['alerts']:
                alert_type = "[!]" if alert['type'] == 'deficit' else "[*]"
                print(f"  {alert_type} {alert['message']}")

        if stats['recent_transactions']:
            print()
            print("  RECENT TRANSACTIONS")
            print("  -" * 30)
            for tx in stats['recent_transactions'][:5]:
                from_name = tx.from_member.name if tx.from_member else "?"
                to_name = tx.to_member.name if tx.to_member else "?"
                status = tx.status.upper()
                print(f"  {tx.created_at.strftime('%Y-%m-%d')}  {from_name} -> {to_name}  {tx.hours}h  \"{tx.service_description[:30]}\" [{status}]")

        if stats['top_skills']:
            print()
            print("  TOP SKILLS")
            print("  -" * 30)
            for skill in stats['top_skills'][:5]:
                print(f"  - {skill['name']} ({skill['count']} members)")

    finally:
        db.close()


# ==================== MEMBERS ====================

def show_members():
    """Display all members with balances."""
    db = get_session()
    try:
        members = get_member_balances(db)

        print_header("MEMBER DIRECTORY")
        if not members:
            print("  No members found.")
            return

        print(f"  {'ID':<4} {'Name':<25} {'Balance':<10} {'Status':<10}")
        print("  " + "-" * 55)
        for m in members:
            balance_str = f"{m['balance']:+}"
            print(f"  {m['id']:<4} {m['name']:<25} {balance_str:<10} {m['status']:<10}")
    finally:
        db.close()


def show_member_detail():
    """Show detailed information about a member."""
    member_id = get_float_input("Enter member ID: ")
    db = get_session()
    try:
        member = get_member_detail(db, int(member_id))
        if not member:
            print("Member not found.")
            return

        print_header(f"MEMBER: {member.name}")
        print(f"  ID:             {member.id}")
        print(f"  Email:          {member.email or 'N/A'}")
        print(f"  Phone:          {member.phone or 'N/A'}")
        print(f"  Bio:            {member.bio or 'N/A'}")
        print(f"  Status:         {member.status}")
        print(f"  Joined:         {member.joined_at.strftime('%Y-%m-%d')}")
        print(f"  Initial Credit: {member.initial_credit}")
        print(f"  Current Balance: {member.balance:+.2f}")

        if member.skills_offered:
            print()
            print("  SKILLS OFFERED")
            print("  -" * 30)
            for skill in member.skills_offered:
                cat = f" [{skill.category}]" if skill.category else ""
                print(f"  - {skill.name}{cat}")
                if skill.description:
                    print(f"    {skill.description}")

        if member.skills_wanted:
            print()
            print("  SKILLS WANTED")
            print("  -" * 30)
            for want in member.skills_wanted:
                print(f"  - {want.name}")
                if want.description:
                    print(f"    {want.description}")

        # Transaction history
        from app.models import Transaction
        tx_given = db.query(Transaction).filter(
            Transaction.from_member_id == member.id
        ).order_by(Transaction.created_at.desc()).all()
        tx_received = db.query(Transaction).filter(
            Transaction.to_member_id == member.id
        ).order_by(Transaction.created_at.desc()).all()

        if tx_given or tx_received:
            print()
            print("  RECENT TRANSACTIONS")
            print("  -" * 30)
            for tx in tx_given[:5]:
                to_m = db.query(Member).filter(Member.id == tx.to_member_id).first()
                print(f"  GAVE {tx.hours}h to {to_m.name if to_m else '?'} - \"{tx.service_description[:30]}\" [{tx.status}]")
            for tx in tx_received[:5]:
                from_m = db.query(Member).filter(Member.id == tx.from_member_id).first()
                print(f"  GOT {tx.hours}h from {from_m.name if from_m else '?'} - \"{tx.service_description[:30]}\" [{tx.status}]")
    finally:
        db.close()


def add_member():
    """Add a new member."""
    print_header("ADD NEW MEMBER")
    name = get_input("Name: ")
    email = get_input("Email: ")
    phone = get_input("Phone (optional): ", required=False)
    bio = get_input("Bio (optional): ", required=False)
    initial = get_float_input("Initial credit [5.0]: ", default=5.0)

    db = get_session()
    try:
        member = create_member(db, name, email, phone, bio, initial)
        print(f"\nMember created successfully! ID: {member.id}")
    finally:
        db.close()


def add_member_skill():
    """Add a skill to a member."""
    member_id = int(get_float_input("Member ID: "))
    name = get_input("Skill name: ")
    category = get_input("Category (optional): ", required=False)
    description = get_input("Description (optional): ", required=False)

    db = get_session()
    try:
        skill = add_skill(db, member_id, name, category, description)
        print(f"\nSkill added! ID: {skill.id}")
    finally:
        db.close()


def add_member_want():
    """Add a skill want to a member."""
    member_id = int(get_float_input("Member ID: "))
    name = get_input("Skill wanted: ")
    description = get_input("Description (optional): ", required=False)

    db = get_session()
    try:
        want = add_want(db, member_id, name, description)
        print(f"\nWant added! ID: {want.id}")
    finally:
        db.close()


def members_menu():
    """Members submenu."""
    while True:
        clear_screen()
        print_header("MEMBERS MENU")
        print_menu([
            "View All Members",
            "View Member Detail",
            "Add New Member",
            "Add Skill to Member",
            "Add Want to Member"
        ])
        choice = get_choice(5)

        if choice == 0:
            return
        elif choice == 1:
            show_members()
        elif choice == 2:
            show_member_detail()
        elif choice == 3:
            add_member()
        elif choice == 4:
            add_member_skill()
        elif choice == 5:
            add_member_want()
        pause()


# ==================== TRANSACTIONS ====================

def show_transactions():
    """Display all transactions."""
    db = get_session()
    try:
        transactions = get_all_transactions(db)

        print_header("TRANSACTION LOG")
        if not transactions:
            print("  No transactions found.")
            return

        print(f"  {'ID':<4} {'Date':<12} {'From':<15} {'To':<15} {'Hours':<6} {'Status':<10} {'Description'}")
        print("  " + "-" * 90)
        for tx in transactions:
            from_name = tx.from_member.name if tx.from_member else "?"
            to_name = tx.to_member.name if tx.to_member else "?"
            date = tx.created_at.strftime('%Y-%m-%d')
            desc = tx.service_description[:25]
            print(f"  {tx.id:<4} {date:<12} {from_name:<15} {to_name:<15} {tx.hours:<6} {tx.status:<10} {desc}")
    finally:
        db.close()


def add_transaction():
    """Create a new transaction."""
    print_header("CREATE TRANSACTION")

    db = get_session()
    try:
        members = get_all_members(db)
        if len(members) < 2:
            print("Need at least 2 members to create a transaction.")
            return

        print("Available members:")
        for m in members:
            bal = calculate_balance(db, m.id)
            print(f"  {m.id}. {m.name} (balance: {bal:+.1f})")
        print()

        from_id = int(get_float_input("From member ID: "))
        to_id = int(get_float_input("To member ID: "))
        hours = get_float_input("Hours: ")
        description = get_input("Service description: ")
        notes = get_input("Notes (optional): ", required=False)

        tx = create_transaction(db, from_id, to_id, hours, description, notes)
        print(f"\nTransaction created! ID: {tx.id}")
    finally:
        db.close()


def manage_transaction():
    """Complete, dispute, or delete a transaction."""
    tx_id = int(get_float_input("Transaction ID: "))

    print("\n1. Complete")
    print("2. Dispute")
    print("3. Delete")
    print("0. Cancel")
    choice = get_choice(3)

    db = get_session()
    try:
        if choice == 1:
            tx = complete_transaction(db, tx_id)
            if tx:
                print("Transaction marked as completed.")
            else:
                print("Transaction not found.")
        elif choice == 2:
            tx = dispute_transaction(db, tx_id)
            if tx:
                print("Transaction marked as disputed.")
            else:
                print("Transaction not found.")
        elif choice == 3:
            if delete_transaction(db, tx_id):
                print("Transaction deleted.")
            else:
                print("Transaction not found.")
    finally:
        db.close()


def transactions_menu():
    """Transactions submenu."""
    while True:
        clear_screen()
        print_header("TRANSACTIONS MENU")
        print_menu([
            "View All Transactions",
            "Create Transaction",
            "Manage Transaction (Complete/Dispute/Delete)"
        ])
        choice = get_choice(3)

        if choice == 0:
            return
        elif choice == 1:
            show_transactions()
        elif choice == 2:
            add_transaction()
        elif choice == 3:
            manage_transaction()
        pause()


# ==================== NEEDS ====================

def show_needs():
    """Display all needs."""
    db = get_session()
    try:
        needs = get_all_needs(db)

        print_header("NEEDS BOARD")
        if not needs:
            print("  No needs posted.")
            return

        print(f"  {'ID':<4} {'Date':<12} {'Status':<12} {'Hours':<6} {'Member':<15} {'Title'}")
        print("  " + "-" * 80)
        for need in needs:
            member = db.query(Member).filter(Member.id == need.member_id).first()
            date = need.created_at.strftime('%Y-%m-%d')
            print(f"  {need.id:<4} {date:<12} {need.status:<12} {need.hours_estimated:<6} {member.name if member else '?':<15} {need.title[:30]}")
    finally:
        db.close()


def add_need():
    """Create a new need."""
    print_header("POST A NEED")

    db = get_session()
    try:
        members = get_all_members(db)
        print("Members:")
        for m in members:
            print(f"  {m.id}. {m.name}")
        print()

        member_id = int(get_float_input("Member ID: "))
        title = get_input("Title: ")
        description = get_input("Description: ")
        hours = get_float_input("Hours estimated [1.0]: ", default=1.0)

        need = create_need(db, member_id, title, description, hours)
        print(f"\nNeed posted! ID: {need.id}")
    finally:
        db.close()


def manage_need():
    """Fulfill or close a need."""
    need_id = int(get_float_input("Need ID: "))

    print("\n1. Mark as Fulfilled")
    print("2. Close")
    print("0. Cancel")
    choice = get_choice(2)

    db = get_session()
    try:
        if choice == 1:
            need = fulfill_need(db, need_id)
            if need:
                print("Need marked as fulfilled.")
            else:
                print("Need not found.")
        elif choice == 2:
            need = close_need(db, need_id)
            if need:
                print("Need closed.")
            else:
                print("Need not found.")
    finally:
        db.close()


def needs_menu():
    """Needs submenu."""
    while True:
        clear_screen()
        print_header("NEEDS MENU")
        print_menu([
            "View All Needs",
            "Post a Need",
            "Manage Need (Fulfill/Close)"
        ])
        choice = get_choice(3)

        if choice == 0:
            return
        elif choice == 1:
            show_needs()
        elif choice == 2:
            add_need()
        elif choice == 3:
            manage_need()
        pause()


# ==================== GOVERNANCE ====================

def show_governance():
    """Display all governance entries."""
    db = get_session()
    try:
        entries = get_all_governance(db)

        print_header("GOVERNANCE LOG")
        if not entries:
            print("  No governance entries.")
            return

        print(f"  {'ID':<4} {'Date':<12} {'Type':<18} {'Status':<12} {'Votes':<12} {'Title'}")
        print("  " + "-" * 90)
        for entry in entries:
            member = db.query(Member).filter(Member.id == entry.member_id).first()
            date = entry.created_at.strftime('%Y-%m-%d')
            votes = f"+{entry.vote_for}/-{entry.vote_against}"
            print(f"  {entry.id:<4} {date:<12} {entry.decision_type:<18} {entry.status:<12} {votes:<12} {entry.title[:30]}")
    finally:
        db.close()


def add_governance():
    """Create a new governance entry."""
    print_header("NEW GOVERNANCE ENTRY")

    print("Decision types: rule_change, dispute_resolution, system_upgrade, meeting_note")
    decision_type = get_input("Decision type: ")
    title = get_input("Title: ")
    description = get_input("Description: ")

    db = get_session()
    try:
        members = get_all_members(db)
        print("\nMembers (optional):")
        print("  0. No member")
        for m in members:
            print(f"  {m.id}. {m.name}")

        member_id_input = get_float_input("Member ID [0]: ", default=0)
        member_id = int(member_id_input) if member_id_input != 0 else None

        entry = create_governance(db, title, description, decision_type, member_id)
        print(f"\nGovernance entry created! ID: {entry.id}")
    finally:
        db.close()


def manage_governance():
    """Vote on or change status of a governance entry."""
    entry_id = int(get_float_input("Entry ID: "))

    print("\n1. Vote FOR")
    print("2. Vote AGAINST")
    print("3. Change Status")
    print("0. Cancel")
    choice = get_choice(3)

    db = get_session()
    try:
        if choice == 1:
            entry = vote_governance(db, entry_id, "for")
            if entry:
                print("Vote recorded.")
            else:
                print("Entry not found.")
        elif choice == 2:
            entry = vote_governance(db, entry_id, "against")
            if entry:
                print("Vote recorded.")
            else:
                print("Entry not found.")
        elif choice == 3:
            print("\nStatus options: proposed, approved, rejected, implemented")
            status = get_input("New status: ")
            entry = update_governance_status(db, entry_id, status)
            if entry:
                print("Status updated.")
            else:
                print("Entry not found.")
    finally:
        db.close()


def governance_menu():
    """Governance submenu."""
    while True:
        clear_screen()
        print_header("GOVERNANCE MENU")
        print_menu([
            "View All Entries",
            "New Entry",
            "Vote / Update Status"
        ])
        choice = get_choice(3)

        if choice == 0:
            return
        elif choice == 1:
            show_governance()
        elif choice == 2:
            add_governance()
        elif choice == 3:
            manage_governance()
        pause()


# ==================== SKILLS ====================

def show_skills():
    """Display skills directory."""
    db = get_session()
    try:
        directory = get_skills_directory(db)

        print_header("SKILLS DIRECTORY")

        print()
        print("  SKILLS OFFERED")
        print("  -" * 30)
        if directory['skills']:
            for skill in directory['skills']:
                cat = f" [{skill.category}]" if skill.category else ""
                print(f"  - {skill.name}{cat} (by {skill.member_name})")
                if skill.description:
                    print(f"    {skill.description}")
        else:
            print("  No skills listed yet.")

        print()
        print("  SKILLS WANTED")
        print("  -" * 30)
        if directory['wants']:
            for want in directory['wants']:
                print(f"  - {want.name} (by {want.member_name})")
                if want.description:
                    print(f"    {want.description}")
        else:
            print("  No wants listed yet.")

        # Show matches
        matches = get_skill_matches(db)
        if matches:
            print()
            print("  MATCHES")
            print("  -" * 30)
            for match in matches[:10]:
                print(f"  {match['want_member']} needs {match['want_name']} -> {match['skill_member']} offers {match['skill_name']}")
    finally:
        db.close()


def skills_menu():
    """Skills submenu."""
    while True:
        clear_screen()
        print_header("SKILLS MENU")
        print_menu([
            "View Skills Directory"
        ])
        choice = get_choice(1)

        if choice == 0:
            return
        elif choice == 1:
            show_skills()
        pause()


# ==================== EXPORT ====================

def export_data():
    """Export data to CSV, JSON, or plain text."""
    print_header("EXPORT DATA")
    print("\n1. CSV (spreadsheet)")
    print("2. JSON (data backup)")
    print("3. Plain Text Report (printable)")
    print("0. Cancel")
    choice = get_choice(3)

    if choice == 0:
        return

    filename = get_input("Filename (without extension): ")
    if not filename:
        filename = f"time_economy_export_{datetime.now().strftime('%Y%m%d')}"

    db = get_session()
    try:
        if choice == 1:
            export_csv(db, filename)
        elif choice == 2:
            export_json(db, filename)
        elif choice == 3:
            export_text(db, filename)
    finally:
        db.close()


def export_csv(db, filename: str):
    """Export members and transactions to CSV."""
    # Members
    members_file = f"{filename}_members.csv"
    with open(members_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Name', 'Email', 'Phone', 'Status', 'Balance'])
        for m in get_member_balances(db):
            writer.writerow([m['id'], m['name'], m['email'], m['phone'] or '', m['status'], m['balance']])

    # Transactions
    tx_file = f"{filename}_transactions.csv"
    with open(tx_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Date', 'From', 'To', 'Hours', 'Description', 'Status', 'Notes'])
        for tx in get_all_transactions(db):
            from_name = tx.from_member.name if tx.from_member else '?'
            to_name = tx.to_member.name if tx.to_member else '?'
            writer.writerow([
                tx.id, tx.created_at.strftime('%Y-%m-%d'),
                from_name, to_name, tx.hours,
                tx.service_description, tx.status, tx.notes or ''
            ])

    print(f"\nExported to:")
    print(f"  - {members_file}")
    print(f"  - {tx_file}")


def export_json(db, filename: str):
    """Export all data to JSON."""
    data = {
        "export_date": datetime.now().isoformat(),
        "members": get_member_balances(db),
        "transactions": [
            {
                "id": tx.id,
                "from_member_id": tx.from_member_id,
                "to_member_id": tx.to_member_id,
                "hours": tx.hours,
                "service_description": tx.service_description,
                "status": tx.status,
                "created_at": tx.created_at.isoformat(),
                "completed_at": tx.completed_at.isoformat() if tx.completed_at else None,
                "notes": tx.notes
            }
            for tx in get_all_transactions(db)
        ],
        "needs": [
            {
                "id": n.id,
                "member_id": n.member_id,
                "title": n.title,
                "description": n.description,
                "hours_estimated": n.hours_estimated,
                "status": n.status,
                "created_at": n.created_at.isoformat()
            }
            for n in get_all_needs(db)
        ],
        "governance": [
            {
                "id": e.id,
                "title": e.title,
                "decision_type": e.decision_type,
                "status": e.status,
                "vote_for": e.vote_for,
                "vote_against": e.vote_against
            }
            for e in get_all_governance(db)
        ]
    }

    def json_serial(obj):
        """JSON serializer for objects not serializable by default."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    filepath = f"{filename}.json"
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=json_serial)
    print(f"\nExported to: {filepath}")


def export_text(db, filename: str):
    """Export a human-readable text report."""
    stats = get_dashboard_stats(db)
    filepath = f"{filename}.txt"

    with open(filepath, 'w') as f:
        f.write("TIME ECONOMY REPORT\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")

        f.write("MEMBER BALANCES\n")
        f.write("-" * 40 + "\n")
        for mb in stats['member_balances']:
            alert = ""
            if mb['balance'] > 20:
                alert = " [HOARDING ALERT]"
            elif mb['balance'] < -10:
                alert = " [CHECK-IN NEEDED]"
            f.write(f"{mb['name']:<25} {mb['balance']:+8.1f} credits{alert}\n")

        f.write("\nRECENT TRANSACTIONS\n")
        f.write("-" * 40 + "\n")
        for tx in stats['recent_transactions'][:10]:
            from_name = tx.from_member.name if tx.from_member else "?"
            to_name = tx.to_member.name if tx.to_member else "?"
            f.write(f"{tx.created_at.strftime('%Y-%m-%d')}  {from_name} -> {to_name}  {tx.hours}h  \"{tx.service_description}\" [{tx.status}]\n")

        f.write("\nOPEN NEEDS\n")
        f.write("-" * 40 + "\n")
        from app.models import Need
        needs = db.query(Need).filter(Need.status == "open").all()
        for need in needs:
            member = db.query(Member).filter(Member.id == need.member_id).first()
            f.write(f"#{need.id} {member.name if member else '?'} needs: \"{need.title}\" ({need.hours_estimated}h)\n")

        f.write("\nGOVERNANCE\n")
        f.write("-" * 40 + "\n")
        for entry in get_all_governance(db)[:10]:
            f.write(f"[{entry.status}] {entry.title} (+{entry.vote_for}/-{entry.vote_against})\n")

        f.write("\n" + "=" * 60 + "\n")
        f.write("End of report\n")

    print(f"\nExported to: {filepath}")


# ==================== MAIN MENU ====================

def main_menu():
    """Main application menu."""
    while True:
        clear_screen()
        print_header("TIME ECONOMY - MAIN MENU")
        print("  A cybernetic time-based labor market")
        print("  for small communities (5-10 people)")
        print()
        print_menu([
            "Dashboard",
            "Members",
            "Transactions",
            "Needs Board",
            "Governance",
            "Skills Directory",
            "Export Data"
        ])
        choice = get_choice(7)

        if choice == 0:
            clear_screen()
            print("Goodbye!")
            sys.exit(0)
        elif choice == 1:
            clear_screen()
            show_dashboard()
            pause()
        elif choice == 2:
            members_menu()
        elif choice == 3:
            transactions_menu()
        elif choice == 4:
            needs_menu()
        elif choice == 5:
            governance_menu()
        elif choice == 6:
            skills_menu()
        elif choice == 7:
            export_data()
            pause()


def main():
    """Entry point."""
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
