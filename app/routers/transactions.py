from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas
from ..database import get_db
from ..services import (
    calculate_balance,
    get_all_transactions, create_transaction,
    complete_transaction, dispute_transaction, reopen_transaction,
    update_transaction, delete_transaction
)

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("/", response_model=List[schemas.Transaction])
def list_transactions(db: Session = Depends(get_db)):
    transactions = db.query(models.Transaction).order_by(models.Transaction.created_at.desc()).all()
    return transactions


@router.post("/", response_model=schemas.Transaction)
def create_transaction_api(transaction: schemas.TransactionCreate, db: Session = Depends(get_db)):
    return create_transaction(db, transaction.from_member_id, transaction.to_member_id,
                              transaction.hours, transaction.service_description, transaction.notes)


@router.post("/web-create", include_in_schema=False)
def create_transaction_web(
    request: Request,
    from_member_id: int = Form(...),
    to_member_id: int = Form(...),
    hours: float = Form(...),
    service_description: str = Form(...),
    notes: str = Form(None),
    db: Session = Depends(get_db)
):
    create_transaction(db, from_member_id, to_member_id, hours, service_description, notes)
    return RedirectResponse(url="/transactions", status_code=303)


@router.post("/{transaction_id}/complete")
def complete_transaction_api(transaction_id: int, db: Session = Depends(get_db)):
    tx = complete_transaction(db, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@router.post("/{transaction_id}/complete-web", include_in_schema=False)
def complete_transaction_web(transaction_id: int, db: Session = Depends(get_db)):
    complete_transaction(db, transaction_id)
    return RedirectResponse(url="/transactions", status_code=303)


@router.post("/{transaction_id}/dispute")
def dispute_transaction_api(transaction_id: int, db: Session = Depends(get_db)):
    tx = dispute_transaction(db, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@router.put("/{transaction_id}", response_model=schemas.Transaction)
def update_transaction_api(transaction_id: int, transaction_update: schemas.TransactionCreate, db: Session = Depends(get_db)):
    tx = update_transaction(db, transaction_id, transaction_update.hours,
                            transaction_update.service_description, transaction_update.notes)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@router.post("/{transaction_id}/update-web", include_in_schema=False)
def update_transaction_web(
    transaction_id: int,
    hours: float = Form(None),
    service_description: str = Form(None),
    notes: str = Form(None),
    db: Session = Depends(get_db)
):
    update_transaction(db, transaction_id, hours, service_description, notes)
    return RedirectResponse(url="/transactions", status_code=303)


@router.post("/{transaction_id}/reopen")
def reopen_transaction_api(transaction_id: int, db: Session = Depends(get_db)):
    tx = reopen_transaction(db, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@router.post("/{transaction_id}/reopen-web", include_in_schema=False)
def reopen_transaction_web(transaction_id: int, db: Session = Depends(get_db)):
    reopen_transaction(db, transaction_id)
    return RedirectResponse(url="/transactions", status_code=303)


@router.delete("/{transaction_id}")
def delete_transaction_api(transaction_id: int, db: Session = Depends(get_db)):
    if not delete_transaction(db, transaction_id):
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"message": "Transaction deleted"}


@router.post("/{transaction_id}/delete-web", include_in_schema=False)
def delete_transaction_web(transaction_id: int, db: Session = Depends(get_db)):
    delete_transaction(db, transaction_id)
    return RedirectResponse(url="/transactions", status_code=303)
