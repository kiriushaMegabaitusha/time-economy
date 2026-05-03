"""Shared service layer for database operations."""
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from app.models import Base, Member, Skill, SkillWant, Transaction, Need, GovernanceLog
from app.database import SessionLocal, get_db


def get_session() -> Session:
    return SessionLocal()


def calculate_balance(db: Session, member_id: int) -> float:
    """Calculate member's time credit balance."""
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        return 0.0

    received = db.query(func.coalesce(func.sum(Transaction.hours), 0)).filter(
        Transaction.to_member_id == member_id,
        Transaction.status == "completed"
    ).scalar() or 0

    given = db.query(func.coalesce(func.sum(Transaction.hours), 0)).filter(
        Transaction.from_member_id == member_id,
        Transaction.status == "completed"
    ).scalar() or 0

    return member.initial_credit + received - given


def get_member_balances(db: Session) -> List[Dict[str, Any]]:
    """Get all members with their calculated balances."""
    members = db.query(Member).filter(Member.status == "active").all()
    result = []
    for member in members:
        bal = calculate_balance(db, member.id)
        result.append({
            "id": member.id,
            "name": member.name,
            "email": member.email,
            "phone": member.phone,
            "bio": member.bio,
            "status": member.status,
            "joined_at": member.joined_at,
            "initial_credit": member.initial_credit,
            "balance": round(bal, 2)
        })
    return result


def get_dashboard_stats(db: Session) -> Dict[str, Any]:
    """Get all dashboard statistics."""
    total_members = db.query(Member).filter(Member.status == "active").count()
    total_transactions = db.query(Transaction).count()
    total_hours = db.query(func.coalesce(func.sum(Transaction.hours), 0)).filter(
        Transaction.status == "completed"
    ).scalar() or 0
    active_needs = db.query(Need).filter(Need.status == "open").count()

    member_balances = get_member_balances(db)
    total_balance = sum(mb["balance"] for mb in member_balances)
    avg_balance = round(total_balance / len(member_balances), 2) if member_balances else 0

    # Recent transactions
    recent = db.query(Transaction).order_by(Transaction.created_at.desc()).limit(10).all()
    for t in recent:
        t.from_member = db.query(Member).filter(Member.id == t.from_member_id).first()
        t.to_member = db.query(Member).filter(Member.id == t.to_member_id).first()

    # Top skills
    skills = db.query(Skill.name, func.count(Skill.id).label("count")).group_by(
        Skill.name
    ).order_by(func.count(Skill.id).desc()).limit(10).all()
    top_skills = [{"name": s.name, "count": s.count} for s in skills]

    # Algedonic alerts
    alerts = []
    for mb in member_balances:
        if mb["balance"] > 20:
            alerts.append({
                "type": "hoarding",
                "member": mb["name"],
                "balance": mb["balance"],
                "message": f"{mb['name']} has {mb['balance']} credits. Encourage spending to maintain liquidity."
            })
        elif mb["balance"] < -10:
            alerts.append({
                "type": "deficit",
                "member": mb["name"],
                "balance": mb["balance"],
                "message": f"{mb['name']} has a deficit of {abs(mb['balance'])} credits. Community check-in recommended."
            })

    # Transaction velocity (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_hours = db.query(func.coalesce(func.sum(Transaction.hours), 0)).filter(
        Transaction.status == "completed",
        Transaction.completed_at >= thirty_days_ago
    ).scalar() or 0

    return {
        "total_members": total_members,
        "total_transactions": total_transactions,
        "total_hours": round(total_hours, 2),
        "active_needs": active_needs,
        "avg_balance": avg_balance,
        "member_balances": member_balances,
        "recent_transactions": recent,
        "top_skills": top_skills,
        "alerts": alerts,
        "recent_hours": round(recent_hours, 2)
    }


def get_all_members(db: Session) -> List[Member]:
    return db.query(Member).order_by(Member.name).all()


def get_member_detail(db: Session, member_id: int) -> Optional[Member]:
    member = db.query(Member).filter(Member.id == member_id).first()
    if member:
        member.balance = calculate_balance(db, member_id)
    return member


def create_member(db: Session, name: str, email: str, phone: str = None,
                  bio: str = None, initial_credit: float = 5.0) -> Member:
    member = Member(
        name=name,
        email=email,
        phone=phone,
        bio=bio,
        initial_credit=initial_credit
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def update_member_status(db: Session, member_id: int, status: str) -> Optional[Member]:
    member = db.query(Member).filter(Member.id == member_id).first()
    if member:
        member.status = status
        db.commit()
        db.refresh(member)
    return member


def add_skill(db: Session, member_id: int, name: str, category: str = None,
              description: str = None) -> Skill:
    skill = Skill(
        member_id=member_id,
        name=name,
        category=category,
        description=description
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


def add_want(db: Session, member_id: int, name: str, description: str = None) -> SkillWant:
    want = SkillWant(
        member_id=member_id,
        name=name,
        description=description
    )
    db.add(want)
    db.commit()
    db.refresh(want)
    return want


def get_all_transactions(db: Session) -> List[Transaction]:
    return db.query(Transaction).order_by(Transaction.created_at.desc()).all()


def create_transaction(db: Session, from_member_id: int, to_member_id: int,
                       hours: float, service_description: str,
                       notes: str = None) -> Transaction:
    tx = Transaction(
        from_member_id=from_member_id,
        to_member_id=to_member_id,
        hours=hours,
        service_description=service_description,
        notes=notes,
        status="pending"
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def complete_transaction(db: Session, transaction_id: int) -> Optional[Transaction]:
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if tx:
        tx.status = "completed"
        tx.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(tx)
    return tx


def dispute_transaction(db: Session, transaction_id: int) -> Optional[Transaction]:
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if tx:
        tx.status = "disputed"
        db.commit()
        db.refresh(tx)
    return tx


def delete_transaction(db: Session, transaction_id: int) -> bool:
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if tx:
        db.delete(tx)
        db.commit()
        return True
    return False


def get_all_needs(db: Session) -> List[Need]:
    return db.query(Need).order_by(Need.created_at.desc()).all()


def create_need(db: Session, member_id: int, title: str, description: str,
                hours_estimated: float = 1.0) -> Need:
    need = Need(
        member_id=member_id,
        title=title,
        description=description,
        hours_estimated=hours_estimated,
        status="open"
    )
    db.add(need)
    db.commit()
    db.refresh(need)
    return need


def fulfill_need(db: Session, need_id: int) -> Optional[Need]:
    need = db.query(Need).filter(Need.id == need_id).first()
    if need:
        need.status = "fulfilled"
        need.fulfilled_at = datetime.utcnow()
        db.commit()
        db.refresh(need)
    return need


def close_need(db: Session, need_id: int) -> Optional[Need]:
    need = db.query(Need).filter(Need.id == need_id).first()
    if need:
        need.status = "closed"
        db.commit()
        db.refresh(need)
    return need


def get_all_governance(db: Session) -> List[GovernanceLog]:
    return db.query(GovernanceLog).order_by(GovernanceLog.created_at.desc()).all()


def create_governance(db: Session, title: str, description: str,
                      decision_type: str, member_id: int = None) -> GovernanceLog:
    entry = GovernanceLog(
        title=title,
        description=description,
        decision_type=decision_type,
        member_id=member_id,
        status="proposed"
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def vote_governance(db: Session, entry_id: int, vote: str) -> Optional[GovernanceLog]:
    entry = db.query(GovernanceLog).filter(GovernanceLog.id == entry_id).first()
    if entry:
        if vote == "for":
            entry.vote_for += 1
        elif vote == "against":
            entry.vote_against += 1
        db.commit()
        db.refresh(entry)
    return entry


def update_governance_status(db: Session, entry_id: int, status: str) -> Optional[GovernanceLog]:
    entry = db.query(GovernanceLog).filter(GovernanceLog.id == entry_id).first()
    if entry:
        entry.status = status
        db.commit()
        db.refresh(entry)
    return entry


def get_skills_directory(db: Session) -> Dict[str, Any]:
    """Get all skills offered and wanted."""
    skills = db.query(Skill).all()
    wants = db.query(SkillWant).all()

    # Enhance with member names
    for s in skills:
        s.member_name = db.query(Member.name).filter(Member.id == s.member_id).scalar()
    for w in wants:
        w.member_name = db.query(Member.name).filter(Member.id == w.member_id).scalar()

    return {"skills": skills, "wants": wants}


def get_skill_matches(db: Session) -> List[Dict[str, Any]]:
    """Find skill/want matches."""
    skills = db.query(Skill).all()
    wants = db.query(SkillWant).all()

    matches = []
    for want in wants:
        for skill in skills:
            if want.member_id != skill.member_id:
                # Simple name-based matching (case-insensitive substring)
                want_name = want.name.lower()
                skill_name = skill.name.lower()
                if want_name in skill_name or skill_name in want_name:
                    matches.append({
                        "want_member": db.query(Member.name).filter(Member.id == want.member_id).scalar(),
                        "want_name": want.name,
                        "skill_member": db.query(Member.name).filter(Member.id == skill.member_id).scalar(),
                        "skill_name": skill.name
                    })
    return matches
