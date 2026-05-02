from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app import models

def seed_data():
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Check if already seeded
    if db.query(models.Member).first():
        print("Database already has data. Skipping seed.")
        db.close()
        return

    # Create demo members
    members_data = [
        {"name": "Alice Chen", "email": "alice@community.local", "phone": "555-0101", "bio": "Web developer and amateur gardener"},
        {"name": "Bob Martinez", "email": "bob@community.local", "phone": "555-0102", "bio": "Licensed plumber, loves fixing things"},
        {"name": "Carol Williams", "email": "carol@community.local", "phone": "555-0103", "bio": "Graphic designer and language tutor"},
        {"name": "David Kim", "email": "david@community.local", "phone": "555-0104", "bio": "Accountant and amateur chef"},
        {"name": "Elena Rossi", "email": "elena@community.local", "phone": "555-0105", "bio": "Counselor and yoga instructor"},
    ]

    created_members = []
    for m_data in members_data:
        member = models.Member(**m_data)
        db.add(member)
        db.commit()
        db.refresh(member)
        created_members.append(member)
        print(f"Created member: {member.name}")

    # Add skills
    skills_data = [
        (created_members[0], "Web Development", "Technology", "Frontend and backend web dev"),
        (created_members[0], "Gardening", "Home", "Vegetable and flower gardening"),
        (created_members[1], "Plumbing", "Home", "Repairs and installations"),
        (created_members[1], "Carpentry", "Home", "Basic woodworking"),
        (created_members[2], "Graphic Design", "Creative", "Logos, branding, illustration"),
        (created_members[2], "Language Tutoring", "Education", "Spanish and Italian"),
        (created_members[3], "Accounting", "Business", "Personal and small business taxes"),
        (created_members[3], "Meal Prep", "Home", "Healthy meal planning"),
        (created_members[4], "Counseling", "Wellness", "Peer counseling and support"),
        (created_members[4], "Yoga Instruction", "Wellness", "Beginner to intermediate"),
    ]

    for member, name, category, desc in skills_data:
        skill = models.Skill(member_id=member.id, name=name, category=category, description=desc)
        db.add(skill)
    db.commit()
    print("Added skills")

    # Add wants
    wants_data = [
        (created_members[0], "Plumbing", "Fix kitchen sink leak"),
        (created_members[0], "Graphic Design", "Logo for side project"),
        (created_members[1], "Web Development", "Build portfolio website"),
        (created_members[1], "Accounting", "Tax preparation help"),
        (created_members[2], "Gardening", "Help setting up raised beds"),
        (created_members[2], "Meal Prep", "Learn batch cooking"),
        (created_members[3], "Yoga Instruction", "Stress relief techniques"),
        (created_members[3], "Language Tutoring", "Learn basic Spanish"),
        (created_members[4], "Carpentry", "Build bookshelf"),
        (created_members[4], "Web Development", "Set up personal blog"),
    ]

    for member, name, desc in wants_data:
        want = models.SkillWant(member_id=member.id, name=name, description=desc)
        db.add(want)
    db.commit()
    print("Added wants")

    # Add some completed transactions
    transactions_data = [
        (created_members[0], created_members[1], 2.0, "Fixed kitchen sink leak", "Completed plumbing repair"),
        (created_members[1], created_members[2], 1.5, "Logo design for plumbing business", "Great logo design"),
        (created_members[2], created_members[3], 1.0, "Tax preparation consultation", "Helped with deductions"),
        (created_members[3], created_members[4], 1.0, "Yoga session for stress relief", "Relaxing session"),
        (created_members[4], created_members[0], 2.0, "Garden bed setup consultation", "Planned spring garden"),
    ]

    from datetime import datetime
    for from_m, to_m, hours, service, notes in transactions_data:
        tx = models.Transaction(
            from_member_id=from_m.id,
            to_member_id=to_m.id,
            hours=hours,
            service_description=service,
            notes=notes,
            status="completed",
            completed_at=datetime.utcnow()
        )
        db.add(tx)
    db.commit()
    print("Added transactions")

    # Add needs
    needs_data = [
        (created_members[0], "Help moving furniture", "Need help moving a couch upstairs, estimated 1 hour", 1.0),
        (created_members[2], "Proofreading resume", "Need someone to review and suggest edits", 0.5),
        (created_members[4], "Dog walking", "Need someone to walk my dog on Tuesday afternoon", 1.0),
    ]

    for member, title, desc, hours in needs_data:
        need = models.Need(member_id=member.id, title=title, description=desc, hours_estimated=hours, status="open")
        db.add(need)
    db.commit()
    print("Added needs")

    # Add governance entries
    gov_data = [
        (created_members[0], "rule_change", "Credit Cap at 20", "Proposed soft limit on credit accumulation to encourage circulation. Members with >20 credits should be encouraged to spend.", "approved"),
        (created_members[1], "rule_change", "Deficit Limit at -10", "Members accumulating more than -10 credits should have a community check-in to discuss barriers to contributing.", "approved"),
        (created_members[2], "meeting_note", "First Community Meeting", "Discussed system setup, onboarding process, and initial skill inventory. All members present. Next meeting in 2 weeks.", "implemented"),
    ]

    for member, dtype, title, desc, status in gov_data:
        gov = models.GovernanceLog(
            member_id=member.id,
            decision_type=dtype,
            title=title,
            description=desc,
            status=status,
            vote_for=5,
            vote_against=0
        )
        db.add(gov)
    db.commit()
    print("Added governance entries")

    db.close()
    print("\nSeed complete! Start the app and visit http://localhost:8000")

if __name__ == "__main__":
    seed_data()
