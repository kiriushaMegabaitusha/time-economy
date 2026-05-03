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


@router.put("/{member_id}", response_model=schemas.Member)
def update_member(member_id: int, member: schemas.MemberCreate, db: Session = Depends(get_db)):
    db_member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")
    for key, value in member.model_dump().items():
        setattr(db_member, key, value)
    db.commit()
    db.refresh(db_member)
    db_member.balance = calculate_balance(db, db_member.id)
    return db_member


@router.post("/{member_id}/update-web")
def update_member_web(
    request: Request,
    member_id: int,
    name: str = Form(None),
    email: str = Form(None),
    phone: str = Form(None),
    bio: str = Form(None),
    status: str = Form(None),
    db: Session = Depends(get_db)
):
    db_member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if db_member:
        if name:
            db_member.name = name
        if email:
            db_member.email = email
        if phone is not None:
            db_member.phone = phone
        if bio is not None:
            db_member.bio = bio
        if status:
            db_member.status = status
        db.commit()
    return RedirectResponse(url=f"/members/{member_id}", status_code=303)


@router.delete("/{member_id}")
def delete_member(member_id: int, db: Session = Depends(get_db)):
    db_member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(db_member)
    db.commit()
    return {"message": "Member deleted"}


@router.post("/{member_id}/delete-web")
def delete_member_web(member_id: int, db: Session = Depends(get_db)):
    db_member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if db_member:
        db.delete(db_member)
        db.commit()
    return RedirectResponse(url="/members", status_code=303)


@router.put("/skills/{skill_id}", response_model=schemas.Skill)
def update_skill(skill_id: int, skill: schemas.SkillCreate, db: Session = Depends(get_db)):
    db_skill = db.query(models.Skill).filter(models.Skill.id == skill_id).first()
    if not db_skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    for key, value in skill.model_dump().items():
        setattr(db_skill, key, value)
    db.commit()
    db.refresh(db_skill)
    return db_skill


@router.post("/{member_id}/skills/{skill_id}/update-web")
def update_skill_web(
    member_id: int,
    skill_id: int,
    name: str = Form(None),
    category: str = Form(None),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    db_skill = db.query(models.Skill).filter(models.Skill.id == skill_id).first()
    if db_skill:
        if name:
            db_skill.name = name
        if category is not None:
            db_skill.category = category
        if description is not None:
            db_skill.description = description
        db.commit()
    return RedirectResponse(url=f"/members/{member_id}", status_code=303)


@router.delete("/skills/{skill_id}")
def delete_skill(skill_id: int, db: Session = Depends(get_db)):
    db_skill = db.query(models.Skill).filter(models.Skill.id == skill_id).first()
    if not db_skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    db.delete(db_skill)
    db.commit()
    return {"message": "Skill deleted"}


@router.post("/{member_id}/skills/{skill_id}/delete-web")
def delete_skill_web(member_id: int, skill_id: int, db: Session = Depends(get_db)):
    db_skill = db.query(models.Skill).filter(models.Skill.id == skill_id).first()
    if db_skill:
        db.delete(db_skill)
        db.commit()
    return RedirectResponse(url=f"/members/{member_id}", status_code=303)


@router.put("/wants/{want_id}", response_model=schemas.SkillWant)
def update_want(want_id: int, want: schemas.SkillWantCreate, db: Session = Depends(get_db)):
    db_want = db.query(models.SkillWant).filter(models.SkillWant.id == want_id).first()
    if not db_want:
        raise HTTPException(status_code=404, detail="Want not found")
    for key, value in want.model_dump().items():
        setattr(db_want, key, value)
    db.commit()
    db.refresh(db_want)
    return db_want


@router.post("/{member_id}/wants/{want_id}/update-web")
def update_want_web(
    member_id: int,
    want_id: int,
    name: str = Form(None),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    db_want = db.query(models.SkillWant).filter(models.SkillWant.id == want_id).first()
    if db_want:
        if name:
            db_want.name = name
        if description is not None:
            db_want.description = description
        db.commit()
    return RedirectResponse(url=f"/members/{member_id}", status_code=303)


@router.delete("/wants/{want_id}")
def delete_want(want_id: int, db: Session = Depends(get_db)):
    db_want = db.query(models.SkillWant).filter(models.SkillWant.id == want_id).first()
    if not db_want:
        raise HTTPException(status_code=404, detail="Want not found")
    db.delete(db_want)
    db.commit()
    return {"message": "Want deleted"}


@router.post("/{member_id}/wants/{want_id}/delete-web")
def delete_want_web(member_id: int, want_id: int, db: Session = Depends(get_db)):
    db_want = db.query(models.SkillWant).filter(models.SkillWant.id == want_id).first()
    if db_want:
        db.delete(db_want)
        db.commit()
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
