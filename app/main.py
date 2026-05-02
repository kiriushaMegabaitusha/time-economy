from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from . import models, schemas
from .database import engine, get_db
from .routers import members, transactions, needs, governance
from .routers.members import calculate_balance

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

app.include_router(members.router)
app.include_router(transactions.router)
app.include_router(needs.router)
app.include_router(governance.router)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    total_members = db.query(models.Member).filter(models.Member.status == "active").count()
    total_transactions = db.query(models.Transaction).count()
    total_hours = db.query(func.coalesce(func.sum(models.Transaction.hours), 0)).filter(
        models.Transaction.status == "completed"
    ).scalar() or 0
    active_needs = db.query(models.Need).filter(models.Need.status == "open").count()

    # Member balances
    members = db.query(models.Member).filter(models.Member.status == "active").all()
    member_balances = []
    total_balance = 0
    for member in members:
        bal = calculate_balance(db, member.id)
        member_balances.append({
            "id": member.id,
            "name": member.name,
            "balance": round(bal, 2)
        })
        total_balance += bal

    avg_balance = round(total_balance / len(members), 2) if members else 0

    # Recent transactions
    recent = db.query(models.Transaction).order_by(models.Transaction.created_at.desc()).limit(10).all()
    for t in recent:
        t.from_member = db.query(models.Member).filter(models.Member.id == t.from_member_id).first()
        t.to_member = db.query(models.Member).filter(models.Member.id == t.to_member_id).first()

    # Top skills
    skills = db.query(models.Skill.name, func.count(models.Skill.id).label("count")).group_by(
        models.Skill.name
    ).order_by(func.count(models.Skill.id).desc()).limit(10).all()
    top_skills = [{"name": s.name, "count": s.count} for s in skills]

    # Check for algedonic signals
    alerts = []
    for mb in member_balances:
        if mb["balance"] > 20:
            alerts.append({
                "type": "hoarding",
                "member": mb["name"],
                "balance": mb["balance"],
                "message": f"{mb['name']} has {mb['balance']} credits. Encourage spending to maintain liquidity."
            })
        elif mb["balance"] < -10:
            alerts.append({
                "type": "deficit",
                "member": mb["name"],
                "balance": mb["balance"],
                "message": f"{mb['name']} has a deficit of {abs(mb['balance'])} credits. Community check-in recommended."
            })

    # Transaction velocity (last 30 days)
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_hours = db.query(func.coalesce(func.sum(models.Transaction.hours), 0)).filter(
        models.Transaction.status == "completed",
        models.Transaction.completed_at >= thirty_days_ago
    ).scalar() or 0

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "total_members": total_members,
        "total_transactions": total_transactions,
        "total_hours": round(total_hours, 2),
        "active_needs": active_needs,
        "avg_balance": avg_balance,
        "member_balances": member_balances,
        "recent_transactions": recent,
        "top_skills": top_skills,
        "alerts": alerts,
        "recent_hours": round(recent_hours, 2)
    })


@app.get("/members", response_class=HTMLResponse)
def members_page(request: Request, db: Session = Depends(get_db)):
    members = db.query(models.Member).all()
    for member in members:
        member.balance = calculate_balance(db, member.id)
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

    # Get transaction history
    tx_given = db.query(models.Transaction).filter(
        models.Transaction.from_member_id == member_id
    ).order_by(models.Transaction.created_at.desc()).all()
    tx_received = db.query(models.Transaction).filter(
        models.Transaction.to_member_id == member_id
    ).order_by(models.Transaction.created_at.desc()).all()

    for t in tx_given + tx_received:
        t.from_member = db.query(models.Member).filter(models.Member.id == t.from_member_id).first()
        t.to_member = db.query(models.Member).filter(models.Member.id == t.to_member_id).first()

    return templates.TemplateResponse("member_detail.html", {
        "request": request,
        "member": member,
        "tx_given": tx_given,
        "tx_received": tx_received
    })


@app.get("/transactions", response_class=HTMLResponse)
def transactions_page(request: Request, db: Session = Depends(get_db)):
    transactions = db.query(models.Transaction).order_by(models.Transaction.created_at.desc()).all()
    members = db.query(models.Member).filter(models.Member.status == "active").all()
    for t in transactions:
        t.from_member = db.query(models.Member).filter(models.Member.id == t.from_member_id).first()
        t.to_member = db.query(models.Member).filter(models.Member.id == t.to_member_id).first()
    return templates.TemplateResponse("transactions.html", {
        "request": request,
        "transactions": transactions,
        "members": members
    })


@app.get("/needs", response_class=HTMLResponse)
def needs_page(request: Request, db: Session = Depends(get_db)):
    needs = db.query(models.Need).order_by(models.Need.created_at.desc()).all()
    members = db.query(models.Member).filter(models.Member.status == "active").all()
    for n in needs:
        n.member = db.query(models.Member).filter(models.Member.id == n.member_id).first()
    return templates.TemplateResponse("needs.html", {
        "request": request,
        "needs": needs,
        "members": members
    })


@app.get("/governance", response_class=HTMLResponse)
def governance_page(request: Request, db: Session = Depends(get_db)):
    entries = db.query(models.GovernanceLog).order_by(models.GovernanceLog.created_at.desc()).all()
    members = db.query(models.Member).filter(models.Member.status == "active").all()
    for e in entries:
        e.member = db.query(models.Member).filter(models.Member.id == e.member_id).first() if e.member_id else None
    return templates.TemplateResponse("governance.html", {
        "request": request,
        "entries": entries,
        "members": members
    })


@app.get("/skills", response_class=HTMLResponse)
def skills_page(request: Request, db: Session = Depends(get_db)):
    skills = db.query(models.Skill).all()
    wants = db.query(models.SkillWant).all()
    members = db.query(models.Member).filter(models.Member.status == "active").all()
    for s in skills:
        s.member = db.query(models.Member).filter(models.Member.id == s.member_id).first()
    for w in wants:
        w.member = db.query(models.Member).filter(models.Member.id == w.member_id).first()
    return templates.TemplateResponse("skills.html", {
        "request": request,
        "skills": skills,
        "wants": wants,
        "members": members
    })
