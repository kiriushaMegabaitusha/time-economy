from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class SkillBase(BaseModel):
    name: str
    category: Optional[str] = None
    description: Optional[str] = None


class SkillCreate(SkillBase):
    pass


class Skill(SkillBase):
    id: int
    member_id: int

    class Config:
        from_attributes = True


class SkillWantBase(BaseModel):
    name: str
    description: Optional[str] = None


class SkillWantCreate(SkillWantBase):
    pass


class SkillWant(SkillWantBase):
    id: int
    member_id: int

    class Config:
        from_attributes = True


class MemberBase(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    bio: Optional[str] = None


class MemberCreate(MemberBase):
    initial_credit: Optional[float] = 5.0


class Member(MemberBase):
    id: int
    status: str
    joined_at: datetime
    initial_credit: float
    skills_offered: List[Skill] = []
    skills_wanted: List[SkillWant] = []
    balance: float = 0.0

    class Config:
        from_attributes = True


class TransactionBase(BaseModel):
    from_member_id: int
    to_member_id: int
    hours: float
    service_description: str
    notes: Optional[str] = None


class TransactionCreate(TransactionBase):
    pass


class Transaction(TransactionBase):
    id: int
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    from_member: Optional[Member] = None
    to_member: Optional[Member] = None

    class Config:
        from_attributes = True


class NeedBase(BaseModel):
    title: str
    description: str
    hours_estimated: Optional[float] = 1.0


class NeedCreate(NeedBase):
    pass


class Need(NeedBase):
    id: int
    member_id: int
    status: str
    created_at: datetime
    fulfilled_at: Optional[datetime] = None
    member: Optional[Member] = None

    class Config:
        from_attributes = True


class GovernanceLogBase(BaseModel):
    decision_type: str
    title: str
    description: str


class GovernanceLogCreate(GovernanceLogBase):
    pass


class GovernanceLog(GovernanceLogBase):
    id: int
    member_id: Optional[int] = None
    vote_for: int
    vote_against: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_members: int
    total_hours_exchanged: float
    total_transactions: int
    active_needs: int
    average_balance: float
    recent_transactions: List[Transaction] = []
    member_balances: List[dict] = []
    top_skills: List[dict] = []
