from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from . import models, schemas
from .database import engine, get_db
from .routers import members, transactions, needs, governance
from .services import (
    get_dashboard_stats, get_member_balances, calculate_balance,
    get_all_transactions, get_all_needs, get_all_governance, get_skills_directory
)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Time Economy",
    description="A cybernetic time-based labor market for small communities",
    version="1.0.0"
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
templates.env.globals['min'] = min
templates.env.globals['max'] = max

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    stats = get_dashboard_stats(db)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "total_members": stats["total_members"],
        "total_transactions": stats["total_transactions"],
        "total_hours": stats["total_hours"],
        "active_needs": stats["active_needs"],
        "avg_balance": stats["avg_balance"],
        "member_balances": stats["member_balances"],
        "recent_transactions": stats["recent_transactions"],
        "top_skills": stats["top_skills"],
        "alerts": stats["alerts"],
        "recent_hours": stats["recent_hours"]
    })


@app.get("/members", response_class=HTMLResponse)
def members_page(request: Request, db: Session = Depends(get_db)):
    members_data = get_member_balances(db)
    members = db.query(models.Member).all()
    for m in members:
        m.balance = calculate_balance(db, m.id)
    return templates.TemplateResponse("members.html", {
        "request": request,
        "members": members
    })


@app.get("/members/{member_id}", response_class=HTMLResponse)
def member_detail(request: Request, member_id: int, db: Session = Depends(get_db)):
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/members")
    member.balance = calculate_balance(db, member_id)

    tx_given = db.query(models.Transaction).options(
        joinedload(models.Transaction.from_member),
        joinedload(models.Transaction.to_member)
    ).filter(
        models.Transaction.from_member_id == member_id
    ).order_by(models.Transaction.created_at.desc()).all()

    tx_received = db.query(models.Transaction).options(
        joinedload(models.Transaction.from_member),
        joinedload(models.Transaction.to_member)
    ).filter(
        models.Transaction.to_member_id == member_id
    ).order_by(models.Transaction.created_at.desc()).all()

    return templates.TemplateResponse("member_detail.html", {
        "request": request,
        "member": member,
        "tx_given": tx_given,
        "tx_received": tx_received
    })


@app.get("/transactions", response_class=HTMLResponse)
def transactions_page(request: Request, db: Session = Depends(get_db)):
    transactions = db.query(models.Transaction).options(
        joinedload(models.Transaction.from_member),
        joinedload(models.Transaction.to_member)
    ).order_by(models.Transaction.created_at.desc()).all()
    members = db.query(models.Member).filter(models.Member.status == "active").all()
    return templates.TemplateResponse("transactions.html", {
        "request": request,
        "transactions": transactions,
        "members": members
    })


@app.get("/needs", response_class=HTMLResponse)
def needs_page(request: Request, db: Session = Depends(get_db)):
    needs = db.query(models.Need).options(
        joinedload(models.Need.member)
    ).order_by(models.Need.created_at.desc()).all()
    members = db.query(models.Member).filter(models.Member.status == "active").all()
    return templates.TemplateResponse("needs.html", {
        "request": request,
        "needs": needs,
        "members": members
    })


@app.get("/governance", response_class=HTMLResponse)
def governance_page(request: Request, db: Session = Depends(get_db)):
    entries = db.query(models.GovernanceLog).options(
        joinedload(models.GovernanceLog.member)
    ).order_by(models.GovernanceLog.created_at.desc()).all()
    members = db.query(models.Member).filter(models.Member.status == "active").all()
    return templates.TemplateResponse("governance.html", {
        "request": request,
        "entries": entries,
        "members": members
    })


@app.get("/skills", response_class=HTMLResponse)
def skills_page(request: Request, db: Session = Depends(get_db)):
    skills = db.query(models.Skill).options(
        joinedload(models.Skill.member)
    ).all()
    wants = db.query(models.SkillWant).options(
        joinedload(models.SkillWant.member)
    ).all()
    members = db.query(models.Member).filter(models.Member.status == "active").all()
    return templates.TemplateResponse("skills.html", {
        "request": request,
        "skills": skills,
        "wants": wants,
        "members": members
    })


# Include API routers AFTER HTML page routes so page routes take precedence
app.include_router(members.router)
app.include_router(transactions.router)
app.include_router(needs.router)
app.include_router(governance.router)
