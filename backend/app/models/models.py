"""SQLAlchemy models for users, teams, routing rules, tickets, and history."""

from datetime import datetime
from enum import Enum
from typing import Any
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def enum_values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class UserRole(str, Enum):
    AGENT = "agent"
    LEAD = "lead"


class TicketChannel(str, Enum):
    WEB_FORM = "web_form"
    EMAIL = "email"
    API = "api"


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class TicketCategory(str, Enum):
    BILLING = "billing"
    ENGINEERING = "engineering"
    ACCOUNT_MANAGEMENT = "account_management"
    SECURITY = "security"
    GENERAL = "general"


PriorityEnum = SqlEnum(TicketPriority, values_callable=enum_values, name="ticket_priority")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(UserRole, values_callable=enum_values, name="user_role"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    escalation_contact: Mapped[str] = mapped_column(String(255), nullable=False)


class RoutingRule(Base):
    __tablename__ = "routing_rules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    conditions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    target_team: Mapped[str] = mapped_column(String(120), nullable=False)
    auto_priority: Mapped[TicketPriority | None] = mapped_column(PriorityEnum, nullable=True)
    priority_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[TicketChannel] = mapped_column(
        SqlEnum(TicketChannel, values_callable=enum_values, name="ticket_channel"),
        nullable=False,
    )
    status: Mapped[TicketStatus] = mapped_column(
        SqlEnum(TicketStatus, values_callable=enum_values, name="ticket_status"),
        nullable=False,
    )
    priority: Mapped[TicketPriority] = mapped_column(PriorityEnum, nullable=False)
    category: Mapped[TicketCategory] = mapped_column(
        SqlEnum(TicketCategory, values_callable=enum_values, name="ticket_category"),
        nullable=False,
    )
    assigned_team: Mapped[str | None] = mapped_column(String(120), nullable=True)
    assigned_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sla_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        server_onupdate=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    history: Mapped[list["TicketHistory"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketHistory.timestamp",
    )


class TicketHistory(Base):
    __tablename__ = "ticket_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tickets.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    ticket: Mapped[Ticket] = relationship(back_populates="history")
