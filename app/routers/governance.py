from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas
from ..database import get_db
from ..services import (
    get_all_governance, create_governance, vote_governance,
    update_governance_status, update_governance, delete_governance
)

router = APIRouter(prefix="/api/governance", tags=["governance"])


@router.get("/", response_model=List[schemas.GovernanceLog])
def list_governance(db: Session = Depends(get_db)):
    entries = db.query(models.GovernanceLog).order_by(models.GovernanceLog.created_at.desc()).all()
    return entries


@router.post("/", response_model=schemas.GovernanceLog)
def create_governance_api(entry: schemas.GovernanceLogCreate, member_id: int = None, db: Session = Depends(get_db)):
    return create_governance(db, entry.title, entry.description, entry.decision_type, member_id)


@router.post("/web-create", include_in_schema=False)
def create_governance_web(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    decision_type: str = Form(...),
    member_id: int = Form(None),
    db: Session = Depends(get_db)
):
    create_governance(db, title, description, decision_type, member_id)
    return RedirectResponse(url="/governance", status_code=303)


@router.post("/{entry_id}/vote")
def vote_governance_api(entry_id: int, vote: str, db: Session = Depends(get_db)):
    if vote not in ("for", "against"):
        raise HTTPException(status_code=400, detail="Invalid vote")
    entry = vote_governance(db, entry_id, vote)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.post("/{entry_id}/vote-web", include_in_schema=False)
def vote_governance_web(entry_id: int, vote: str = Form(...), db: Session = Depends(get_db)):
    vote_governance(db, entry_id, vote)
    return RedirectResponse(url="/governance", status_code=303)


@router.post("/{entry_id}/status")
def update_status_api(entry_id: int, status: str, db: Session = Depends(get_db)):
    entry = update_governance_status(db, entry_id, status)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.put("/{entry_id}", response_model=schemas.GovernanceLog)
def update_governance_api(entry_id: int, entry_update: schemas.GovernanceLogCreate, db: Session = Depends(get_db)):
    entry = update_governance(db, entry_id, entry_update.title, entry_update.description, entry_update.decision_type)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.post("/{entry_id}/update-web", include_in_schema=False)
def update_governance_web(
    entry_id: int,
    title: str = Form(None),
    description: str = Form(None),
    decision_type: str = Form(None),
    db: Session = Depends(get_db)
):
    update_governance(db, entry_id, title, description, decision_type)
    return RedirectResponse(url="/governance", status_code=303)


@router.delete("/{entry_id}")
def delete_governance_api(entry_id: int, db: Session = Depends(get_db)):
    if not delete_governance(db, entry_id):
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"message": "Governance entry deleted"}


@router.post("/{entry_id}/delete-web", include_in_schema=False)
def delete_governance_web(entry_id: int, db: Session = Depends(get_db)):
    delete_governance(db, entry_id)
    return RedirectResponse(url="/governance", status_code=303)
