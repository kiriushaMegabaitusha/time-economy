from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    status = Column(String, default="active")  # active, inactive, suspended
    joined_at = Column(DateTime, default=datetime.utcnow)
    initial_credit = Column(Float, default=5.0)  # Starting credit loan

    skills_offered = relationship("Skill", back_populates="member", cascade="all, delete-orphan")
    skills_wanted = relationship("SkillWant", back_populates="member", cascade="all, delete-orphan")
    transactions_given = relationship("Transaction", foreign_keys="Transaction.from_member_id", back_populates="from_member")
    transactions_received = relationship("Transaction", foreign_keys="Transaction.to_member_id", back_populates="to_member")
    governance_entries = relationship("GovernanceLog", back_populates="member")
    needs = relationship("Need", back_populates="member", cascade="all, delete-orphan")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"))
    name = Column(String, index=True)
    category = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    member = relationship("Member", back_populates="skills_offered")


class SkillWant(Base):
    __tablename__ = "skill_wants"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"))
    name = Column(String, index=True)
    description = Column(Text, nullable=True)

    member = relationship("Member", back_populates="skills_wanted")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    from_member_id = Column(Integer, ForeignKey("members.id"))
    to_member_id = Column(Integer, ForeignKey("members.id"))
    hours = Column(Float)
    service_description = Column(Text)
    status = Column(String, default="pending")  # pending, completed, disputed
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    from_member = relationship("Member", foreign_keys=[from_member_id], back_populates="transactions_given")
    to_member = relationship("Member", foreign_keys=[to_member_id], back_populates="transactions_received")


class Need(Base):
    __tablename__ = "needs"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"))
    title = Column(String)
    description = Column(Text)
    hours_estimated = Column(Float, default=1.0)
    status = Column(String, default="open")  # open, in_progress, fulfilled, closed
    created_at = Column(DateTime, default=datetime.utcnow)
    fulfilled_at = Column(DateTime, nullable=True)

    member = relationship("Member", back_populates="needs")


class GovernanceLog(Base):
    __tablename__ = "governance_log"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=True)
    decision_type = Column(String)  # rule_change, dispute_resolution, system_upgrade, meeting_note
    title = Column(String)
    description = Column(Text)
    vote_for = Column(Integer, default=0)
    vote_against = Column(Integer, default=0)
    status = Column(String, default="proposed")  # proposed, approved, rejected, implemented
    created_at = Column(DateTime, default=datetime.utcnow)

    member = relationship("Member", back_populates="governance_entries")
