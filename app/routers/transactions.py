from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from .. import models, schemas
from ..database import get_db
from .members import calculate_balance

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/", response_model=List[schemas.Transaction])
def list_transactions(db: Session = Depends(get_db)):
    transactions = db.query(models.Transaction).order_by(models.Transaction.created_at.desc()).all()
    return transactions


@router.post("/", response_model=schemas.Transaction)
def create_transaction(transaction: schemas.TransactionCreate, db: Session = Depends(get_db)):
    # Validate members exist
    from_member = db.query(models.Member).filter(models.Member.id == transaction.from_member_id).first()
    to_member = db.query(models.Member).filter(models.Member.id == transaction.to_member_id).first()
    if not from_member or not to_member:
        raise HTTPException(status_code=404, detail="Member not found")

    db_transaction = models.Transaction(**transaction.model_dump(), status="pending")
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction


@router.post("/web-create")
def create_transaction_web(
    request: Request,
    from_member_id: int = Form(...),
    to_member_id: int = Form(...),
    hours: float = Form(...),
    service_description: str = Form(...),
    notes: str = Form(None),
    db: Session = Depends(get_db)
):
    db_transaction = models.Transaction(
        from_member_id=from_member_id,
        to_member_id=to_member_id,
        hours=hours,
        service_description=service_description,
        notes=notes,
        status="pending"
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return RedirectResponse(url="/transactions", status_code=303)


@router.post("/{transaction_id}/complete")
def complete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    transaction = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    transaction.status = "completed"
    transaction.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(transaction)
    return transaction


@router.post("/{transaction_id}/complete-web")
def complete_transaction_web(transaction_id: int, db: Session = Depends(get_db)):
    transaction = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if transaction:
        transaction.status = "completed"
        transaction.completed_at = datetime.utcnow()
        db.commit()
    return RedirectResponse(url="/transactions", status_code=303)


@router.post("/{transaction_id}/dispute")
def dispute_transaction(transaction_id: int, db: Session = Depends(get_db)):
    transaction = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    transaction.status = "disputed"
    db.commit()
    db.refresh(transaction)
    return transaction


@router.delete("/{transaction_id}")
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    transaction = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(transaction)
    db.commit()
    return {"message": "Transaction deleted"}
