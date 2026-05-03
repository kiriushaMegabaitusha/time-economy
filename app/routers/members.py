from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas
from ..database import get_db
from ..services import calculate_balance, create_member, update_member, update_member_status
from ..services import delete_member, add_skill, add_want, update_skill, delete_skill, update_want, delete_want

router = APIRouter(prefix="/api/members", tags=["members"])


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
def create_member_api(member: schemas.MemberCreate, db: Session = Depends(get_db)):
    member.balance = 5.0
    db_member = create_member(db, member.name, member.email, member.phone, member.bio, member.initial_credit)
    db_member.balance = calculate_balance(db, db_member.id)
    return db_member


@router.post("/web-create", include_in_schema=False)
def create_member_web(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(None),
    bio: str = Form(None),
    db: Session = Depends(get_db)
):
    create_member(db, name, email, phone, bio)
    return RedirectResponse(url="/members", status_code=303)


@router.post("/{member_id}/skills")
def add_skill_api(member_id: int, skill: schemas.SkillCreate, db: Session = Depends(get_db)):
    return add_skill(db, member_id, skill.name, skill.category, skill.description)


@router.post("/{member_id}/skills-web", include_in_schema=False)
def add_skill_web(
    member_id: int,
    name: str = Form(...),
    category: str = Form(None),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    add_skill(db, member_id, name, category, description)
    return RedirectResponse(url=f"/members/{member_id}", status_code=303)


@router.post("/{member_id}/wants")
def add_want_api(member_id: int, want: schemas.SkillWantCreate, db: Session = Depends(get_db)):
    return add_want(db, member_id, want.name, want.description)


@router.post("/{member_id}/wants-web", include_in_schema=False)
def add_want_web(
    member_id: int,
    name: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    add_want(db, member_id, name, description)
    return RedirectResponse(url=f"/members/{member_id}", status_code=303)


@router.put("/{member_id}", response_model=schemas.Member)
def update_member_api(member_id: int, member: schemas.MemberCreate, db: Session = Depends(get_db)):
    db_member = update_member(db, member_id, member.name, member.email, member.phone, member.bio)
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")
    db_member.balance = calculate_balance(db, member_id)
    return db_member


@router.post("/{member_id}/update-web", include_in_schema=False)
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
    update_member(db, member_id, name, email, phone, bio)
    if status:
        update_member_status(db, member_id, status)
    return RedirectResponse(url=f"/members/{member_id}", status_code=303)


@router.delete("/{member_id}")
def delete_member_api(member_id: int, db: Session = Depends(get_db)):
    if not delete_member(db, member_id):
        raise HTTPException(status_code=404, detail="Member not found")
    return {"message": "Member deleted"}


@router.post("/{member_id}/delete-web", include_in_schema=False)
def delete_member_web(member_id: int, db: Session = Depends(get_db)):
    delete_member(db, member_id)
    return RedirectResponse(url="/members", status_code=303)


@router.put("/skills/{skill_id}", response_model=schemas.Skill)
def update_skill_api(skill_id: int, skill: schemas.SkillCreate, db: Session = Depends(get_db)):
    db_skill = update_skill(db, skill_id, skill.name, skill.category, skill.description)
    if not db_skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return db_skill


@router.post("/{member_id}/skills/{skill_id}/update-web", include_in_schema=False)
def update_skill_web(
    member_id: int,
    skill_id: int,
    name: str = Form(None),
    category: str = Form(None),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    update_skill(db, skill_id, name, category, description)
    return RedirectResponse(url=f"/members/{member_id}", status_code=303)


@router.delete("/skills/{skill_id}")
def delete_skill_api(skill_id: int, db: Session = Depends(get_db)):
    if not delete_skill(db, skill_id):
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"message": "Skill deleted"}


@router.post("/{member_id}/skills/{skill_id}/delete-web", include_in_schema=False)
def delete_skill_web(member_id: int, skill_id: int, db: Session = Depends(get_db)):
    delete_skill(db, skill_id)
    return RedirectResponse(url=f"/members/{member_id}", status_code=303)


@router.put("/wants/{want_id}", response_model=schemas.SkillWant)
def update_want_api(want_id: int, want: schemas.SkillWantCreate, db: Session = Depends(get_db)):
    db_want = update_want(db, want_id, want.name, want.description)
    if not db_want:
        raise HTTPException(status_code=404, detail="Want not found")
    return db_want


@router.post("/{member_id}/wants/{want_id}/update-web", include_in_schema=False)
def update_want_web(
    member_id: int,
    want_id: int,
    name: str = Form(None),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    update_want(db, want_id, name, description)
    return RedirectResponse(url=f"/members/{member_id}", status_code=303)


@router.delete("/wants/{want_id}")
def delete_want_api(want_id: int, db: Session = Depends(get_db)):
    if not delete_want(db, want_id):
        raise HTTPException(status_code=404, detail="Want not found")
    return {"message": "Want deleted"}


@router.post("/{member_id}/wants/{want_id}/delete-web", include_in_schema=False)
def delete_want_web(member_id: int, want_id: int, db: Session = Depends(get_db)):
    delete_want(db, want_id)
    return RedirectResponse(url=f"/members/{member_id}", status_code=303)
