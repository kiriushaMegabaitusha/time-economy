from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/governance", tags=["governance"])


@router.get("/", response_model=List[schemas.GovernanceLog])
def list_governance(db: Session = Depends(get_db)):
    entries = db.query(models.GovernanceLog).order_by(models.GovernanceLog.created_at.desc()).all()
    return entries


@router.post("/", response_model=schemas.GovernanceLog)
def create_governance(entry: schemas.GovernanceLogCreate, member_id: int = None, db: Session = Depends(get_db)):
    db_entry = models.GovernanceLog(member_id=member_id, **entry.model_dump())
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry


@router.post("/web-create")
def create_governance_web(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    decision_type: str = Form(...),
    member_id: int = Form(None),
    db: Session = Depends(get_db)
):
    db_entry = models.GovernanceLog(
        title=title,
        description=description,
        decision_type=decision_type,
        member_id=member_id,
        status="proposed"
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return RedirectResponse(url="/governance", status_code=303)


@router.post("/{entry_id}/vote")
def vote_governance(entry_id: int, vote: str, db: Session = Depends(get_db)):
    entry = db.query(models.GovernanceLog).filter(models.GovernanceLog.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    if vote == "for":
        entry.vote_for += 1
    elif vote == "against":
        entry.vote_against += 1
    else:
        raise HTTPException(status_code=400, detail="Invalid vote")

    db.commit()
    db.refresh(entry)
    return entry


@router.post("/{entry_id}/vote-web")
def vote_governance_web(entry_id: int, vote: str = Form(...), db: Session = Depends(get_db)):
    entry = db.query(models.GovernanceLog).filter(models.GovernanceLog.id == entry_id).first()
    if entry:
        if vote == "for":
            entry.vote_for += 1
        elif vote == "against":
            entry.vote_against += 1
        db.commit()
    return RedirectResponse(url="/governance", status_code=303)


@router.post("/{entry_id}/status")
def update_status(entry_id: int, status: str, db: Session = Depends(get_db)):
    entry = db.query(models.GovernanceLog).filter(models.GovernanceLog.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    entry.status = status
    db.commit()
    db.refresh(entry)
    return entry


@router.put("/{entry_id}", response_model=schemas.GovernanceLog)
def update_governance(entry_id: int, entry_update: schemas.GovernanceLogCreate, db: Session = Depends(get_db)):
    entry = db.query(models.GovernanceLog).filter(models.GovernanceLog.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    entry.title = entry_update.title
    entry.description = entry_update.description
    entry.decision_type = entry_update.decision_type
    db.commit()
    db.refresh(entry)
    return entry


@router.post("/{entry_id}/update-web")
def update_governance_web(
    entry_id: int,
    title: str = Form(None),
    description: str = Form(None),
    decision_type: str = Form(None),
    db: Session = Depends(get_db)
):
    entry = db.query(models.GovernanceLog).filter(models.GovernanceLog.id == entry_id).first()
    if entry:
        if title:
            entry.title = title
        if description:
            entry.description = description
        if decision_type:
            entry.decision_type = decision_type
        db.commit()
    return RedirectResponse(url="/governance", status_code=303)


@router.delete("/{entry_id}")
def delete_governance(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(models.GovernanceLog).filter(models.GovernanceLog.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(entry)
    db.commit()
    return {"message": "Governance entry deleted"}


@router.post("/{entry_id}/delete-web")
def delete_governance_web(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(models.GovernanceLog).filter(models.GovernanceLog.id == entry_id).first()
    if entry:
        db.delete(entry)
        db.commit()
    return RedirectResponse(url="/governance", status_code=303)
