from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime, timezone

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    fio = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    email = Column(String(255), nullable=False)
    consent_given = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    subscriptions = relationship("Subscription", back_populates="user", lazy="dynamic")
    payments = relationship("Payment", back_populates="user", lazy="dynamic")

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False, index=True)
    status = Column(String(50), default="active", index=True)  # active, expired, cancelled
    reminder_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="subscriptions")

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    promo_code = Column(String(100), nullable=True)
    discount = Column(Numeric(10, 2), default=0)
    status = Column(String(50), default="pending", index=True)  # pending, success, failed
    payment_id = Column(String(255), nullable=True)  # external payment ID
    period_months = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="payments")

class PromoCode(Base):
    __tablename__ = "promo_codes"

    id = Column(Integer, primary_key=True)
    code = Column(String(100), unique=True, nullable=False, index=True)
    discount_value = Column(Numeric(10, 2), nullable=False)  # fixed discount amount
    owner = Column(String(255), nullable=True)  # ambassador name
    active = Column(Boolean, default=True, index=True)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
