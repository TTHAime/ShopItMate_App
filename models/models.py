from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(UUID(as_uuid=True), primary_key=True)
    line_user_id = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(255))
    bot_mode = Column(String(20), nullable=False, default="FULL")
    created_at = Column(DateTime(timezone=True), nullable=False)

    cases = relationship("Case", back_populates="customer")


class Case(Base):
    __tablename__ = "cases"

    case_id = Column(UUID(as_uuid=True), primary_key=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.customer_id"), nullable=False)

    status = Column(String, nullable=False, default="OPEN")
    priority = Column(String, nullable=False, default="medium")
    category = Column(String, nullable=False)
    summary = Column(Text)

    acknowledged_at = Column(DateTime(timezone=True))
    closed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False)

    customer = relationship("Customer", back_populates="cases")
    sla = relationship("CaseSLA", back_populates="case", uselist=False)
    events = relationship("CaseEvent", back_populates="case")


class CaseSLA(Base):
    __tablename__ = "case_sla"

    sla_id = Column(UUID(as_uuid=True), primary_key=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.case_id"), nullable=False, unique=True)
    policy_id = Column(UUID(as_uuid=True), nullable=False)

    ttr_due_at = Column(DateTime(timezone=True))
    ttc_due_at = Column(DateTime(timezone=True))
    ttr_breached = Column(Boolean, nullable=False, default=False)
    ttc_breached = Column(Boolean, nullable=False, default=False)
    ttr_met_at = Column(DateTime(timezone=True))
    last_notified_at = Column(DateTime(timezone=True))

    case = relationship("Case", back_populates="sla")


class AdminNotification(Base):
    __tablename__ = "admin_notifications"

    id = Column(UUID(as_uuid=True), primary_key=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.case_id"))
    type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False)


class CaseEvent(Base):
    __tablename__ = "case_events"

    id = Column(UUID(as_uuid=True), primary_key=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.case_id"), nullable=False)
    event_type = Column(String, nullable=False)
    actor_type = Column(String, nullable=False, default="system")
    details = Column(JSONB)
    created_at = Column(DateTime(timezone=True), nullable=False)

    case = relationship("Case", back_populates="events")