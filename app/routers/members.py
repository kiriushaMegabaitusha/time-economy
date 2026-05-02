from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/members", tags=["members"])


@router.get("/", response_model=List[schemas.Member])
def list_members(db: Session = Depends(get_db)):
    members = db.query(models.Member).all()
    for member in members:
        member.balance = calculate_balance(db, member.id)
    return members


@router.get("/{member_id}", response_model=schemas.Member)
def get_member(member_id: int, db: Session = Depends(get_db)):
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    member.balance = calculate_balance(db, member_id)
    return member


@router.post("/", response_model=schemas.Member)
def create_member(member: schemas.MemberCreate, db: Session = Depends(get_db)):
    db_member = models.Member(**member.model_dump())
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    db_member.balance = calculate_balance(db, db_member.id)
    return db_member


@router.post("/web-create")
def create_member_web(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(None),
    bio: str = Form(None),
    db: Session = Depends(get_db)
):
    db_member = models.Member(name=name, email=email, phone=phone, bio=bio)
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return RedirectResponse(url="/members", status_code=303)


@router.post("/{member_id}/skills")
def add_skill(member_id: int, skill: schemas.SkillCreate, db: Session = Depends(get_db)):
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    db_skill = models.Skill(member_id=member_id, **skill.model_dump())
    db.add(db_skill)
    db.commit()
    db.refresh(db_skill)
    return db_skill


@router.post("/{member_id}/skills-web")
def add_skill_web(
    member_id: int,
    name: str = Form(...),
    category: str = Form(None),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    db_skill = models.Skill(member_id=member_id, name=name, category=category, description=description)
    db.add(db_skill)
    db.commit()
    db.refresh(db_skill)
    return RedirectResponse(url=f"/members/{member_id}", status_code=303)


@router.post("/{member_id}/wants")
def add_want(member_id: int, want: schemas.SkillWantCreate, db: Session = Depends(get_db)):
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    db_want = models.SkillWant(member_id=member_id, **want.model_dump())
    db.add(db_want)
    db.commit()
    db.refresh(db_want)
    return db_want


@router.post("/{member_id}/wants-web")
def add_want_web(
    member_id: int,
    name: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    db_want = models.SkillWant(member_id=member_id, name=name, description=description)
    db.add(db_want)
    db.commit()
    db.refresh(db_want)
    return RedirectResponse(url=f"/members/{member_id}", status_code=303)


def calculate_balance(db: Session, member_id: int) -> float:
    """Calculate member's time credit balance."""
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        return 0.0

    # Credits received (positive)
    received = db.query(func.coalesce(func.sum(models.Transaction.hours), 0)).filter(
        models.Transaction.to_member_id == member_id,
        models.Transaction.status == "completed"
    ).scalar()

    # Credits given (negative)
    given = db.query(func.coalesce(func.sum(models.Transaction.hours), 0)).filter(
        models.Transaction.from_member_id == member_id,
        models.Transaction.status == "completed"
    ).scalar()

    return member.initial_credit + received - given
