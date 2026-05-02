from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/needs", tags=["needs"])


@router.get("/", response_model=List[schemas.Need])
def list_needs(db: Session = Depends(get_db)):
    needs = db.query(models.Need).order_by(models.Need.created_at.desc()).all()
    return needs


@router.post("/", response_model=schemas.Need)
def create_need(need: schemas.NeedCreate, member_id: int, db: Session = Depends(get_db)):
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    db_need = models.Need(member_id=member_id, **need.model_dump())
    db.add(db_need)
    db.commit()
    db.refresh(db_need)
    return db_need


@router.post("/web-create")
def create_need_web(
    request: Request,
    member_id: int = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    hours_estimated: float = Form(1.0),
    db: Session = Depends(get_db)
):
    db_need = models.Need(
        member_id=member_id,
        title=title,
        description=description,
        hours_estimated=hours_estimated,
        status="open"
    )
    db.add(db_need)
    db.commit()
    db.refresh(db_need)
    return RedirectResponse(url="/needs", status_code=303)


@router.post("/{need_id}/fulfill")
def fulfill_need(need_id: int, db: Session = Depends(get_db)):
    need = db.query(models.Need).filter(models.Need.id == need_id).first()
    if not need:
        raise HTTPException(status_code=404, detail="Need not found")

    need.status = "fulfilled"
    need.fulfilled_at = datetime.utcnow()
    db.commit()
    db.refresh(need)
    return need


@router.post("/{need_id}/fulfill-web")
def fulfill_need_web(need_id: int, db: Session = Depends(get_db)):
    need = db.query(models.Need).filter(models.Need.id == need_id).first()
    if need:
        need.status = "fulfilled"
        need.fulfilled_at = datetime.utcnow()
        db.commit()
    return RedirectResponse(url="/needs", status_code=303)


@router.post("/{need_id}/close")
def close_need(need_id: int, db: Session = Depends(get_db)):
    need = db.query(models.Need).filter(models.Need.id == need_id).first()
    if not need:
        raise HTTPException(status_code=404, detail="Need not found")

    need.status = "closed"
    db.commit()
    db.refresh(need)
    return need
