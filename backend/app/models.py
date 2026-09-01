"""SQLAlchemy models — all 5 tables defined here."""

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, Text, Date, DateTime, Numeric, ForeignKey, func,
)
from sqlalchemy.orm import relationship
from app.database import Base


class Child(Base):
    __tablename__ = "children"

    id = Column(Integer, primary_key=True, autoincrement=True)
    anonymous_id = Column(Text, unique=True, nullable=False)
    interests = Column(Text, nullable=True)  # JSON array string
    created_at = Column(DateTime, server_default=func.now())

    wallet = relationship("Wallet", back_populates="child", uselist=False)
    transactions = relationship("Transaction", back_populates="child")
    goals = relationship("Goal", back_populates="child")
    grow_activities = relationship("GrowActivity", back_populates="child")


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False, unique=True)
    balance = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))

    child = relationship("Child", back_populates="wallet")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    type = Column(Text, nullable=False)  # SAVE | SPEND | GROW | GIVE
    amount = Column(Numeric(10, 2), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    child = relationship("Child", back_populates="transactions")


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    name = Column(Text, nullable=False)
    target_amount = Column(Numeric(10, 2), nullable=False)
    saved_amount = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    target_date = Column(Date, nullable=True)
    status = Column(Text, nullable=False, default="active")  # active | completed
    created_at = Column(DateTime, server_default=func.now())

    child = relationship("Child", back_populates="goals")


class GrowActivity(Base):
    __tablename__ = "grow_activities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    type = Column(Text, nullable=False)  # BUSINESS | INVESTMENT | SKILL
    details = Column(Text, nullable=True)  # JSON object string
    created_at = Column(DateTime, server_default=func.now())

    child = relationship("Child", back_populates="grow_activities")
