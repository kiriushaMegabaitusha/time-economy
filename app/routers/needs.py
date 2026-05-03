from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas
from ..database import get_db
from ..services import (
    get_all_needs, create_need, fulfill_need, close_need,
    reopen_need, update_need, delete_need
)

router = APIRouter(prefix="/api/needs", tags=["needs"])


@router.get("/", response_model=List[schemas.Need])
def list_needs(db: Session = Depends(get_db)):
    needs = db.query(models.Need).order_by(models.Need.created_at.desc()).all()
    return needs


@router.post("/", response_model=schemas.Need)
def create_need_api(need: schemas.NeedCreate, member_id: int, db: Session = Depends(get_db)):
    return create_need(db, member_id, need.title, need.description, need.hours_estimated)


@router.post("/web-create", include_in_schema=False)
def create_need_web(
    request: Request,
    member_id: int = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    hours_estimated: float = Form(1.0),
    db: Session = Depends(get_db)
):
    create_need(db, member_id, title, description, hours_estimated)
    return RedirectResponse(url="/needs", status_code=303)


@router.post("/{need_id}/fulfill")
def fulfill_need_api(need_id: int, db: Session = Depends(get_db)):
    need = fulfill_need(db, need_id)
    if not need:
        raise HTTPException(status_code=404, detail="Need not found")
    return need


@router.post("/{need_id}/fulfill-web", include_in_schema=False)
def fulfill_need_web(need_id: int, db: Session = Depends(get_db)):
    fulfill_need(db, need_id)
    return RedirectResponse(url="/needs", status_code=303)


@router.post("/{need_id}/close")
def close_need_api(need_id: int, db: Session = Depends(get_db)):
    need = close_need(db, need_id)
    if not need:
        raise HTTPException(status_code=404, detail="Need not found")
    return need


@router.put("/{need_id}", response_model=schemas.Need)
def update_need_api(need_id: int, need_update: schemas.NeedCreate, db: Session = Depends(get_db)):
    need = update_need(db, need_id, need_update.title, need_update.description, need_update.hours_estimated)
    if not need:
        raise HTTPException(status_code=404, detail="Need not found")
    return need


@router.post("/{need_id}/update-web", include_in_schema=False)
def update_need_web(
    need_id: int,
    title: str = Form(None),
    description: str = Form(None),
    hours_estimated: float = Form(None),
    db: Session = Depends(get_db)
):
    update_need(db, need_id, title, description, hours_estimated)
    return RedirectResponse(url="/needs", status_code=303)


@router.post("/{need_id}/reopen")
def reopen_need_api(need_id: int, db: Session = Depends(get_db)):
    need = reopen_need(db, need_id)
    if not need:
        raise HTTPException(status_code=404, detail="Need not found")
    return need


@router.post("/{need_id}/reopen-web", include_in_schema=False)
def reopen_need_web(need_id: int, db: Session = Depends(get_db)):
    reopen_need(db, need_id)
    return RedirectResponse(url="/needs", status_code=303)


@router.delete("/{need_id}")
def delete_need_api(need_id: int, db: Session = Depends(get_db)):
    if not delete_need(db, need_id):
        raise HTTPException(status_code=404, detail="Need not found")
    return {"message": "Need deleted"}


@router.post("/{need_id}/delete-web", include_in_schema=False)
def delete_need_web(need_id: int, db: Session = Depends(get_db)):
    delete_need(db, need_id)
    return RedirectResponse(url="/needs", status_code=303)
