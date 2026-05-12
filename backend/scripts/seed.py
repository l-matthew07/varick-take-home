"""Idempotent seed data for the support ticket system."""

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required")

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal, init_db
from app.models.models import (
    RoutingRule,
    Team,
    Ticket,
    TicketCategory,
    TicketChannel,
    TicketHistory,
    TicketPriority,
    TicketStatus,
    User,
    UserRole,
)
from app.services.routing import route_ticket


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TEAMS = [
    {"name": "Engineering", "escalation_contact": "eng-lead@example.com"},
    {"name": "Billing", "escalation_contact": "billing-lead@example.com"},
    {"name": "Account Management", "escalation_contact": "am-lead@example.com"},
    {"name": "Security", "escalation_contact": "security-lead@example.com"},
]

USERS = [
    {"email": "agent@example.com", "password": "testpass123", "role": UserRole.AGENT},
    {"email": "lead@example.com", "password": "testpass123", "role": UserRole.LEAD},
]

ROUTING_RULES = [
    {
        "name": "Security Catch-All",
        "condition_field": "category",
        "condition_operator": "equals",
        "condition_value": "security",
        "target_team": "Security",
        "auto_priority": TicketPriority.P1,
        "priority_order": 1,
    },
    {
        "name": "High Priority Billing",
        "condition_field": "category",
        "condition_operator": "equals",
        "condition_value": "billing",
        "secondary_condition_field": "priority",
        "secondary_condition_operator": "in",
        "secondary_condition_value": json.dumps(["P1", "P2"]),
        "target_team": "Billing",
        "priority_order": 2,
    },
    {
        "name": "Low Priority Billing",
        "condition_field": "category",
        "condition_operator": "equals",
        "condition_value": "billing",
        "secondary_condition_field": "priority",
        "secondary_condition_operator": "in",
        "secondary_condition_value": json.dumps(["P3", "P4"]),
        "target_team": "Account Management",
        "priority_order": 3,
    },
    {
        "name": "Engineering",
        "condition_field": "category",
        "condition_operator": "equals",
        "condition_value": "engineering",
        "target_team": "Engineering",
        "priority_order": 4,
    },
    {
        "name": "Account Management Direct",
        "condition_field": "category",
        "condition_operator": "equals",
        "condition_value": "account_management",
        "target_team": "Account Management",
        "priority_order": 5,
    },
    {
        "name": "Default Catch-All",
        "condition_field": "category",
        "condition_operator": "equals",
        "condition_value": "general",
        "target_team": "Account Management",
        "auto_priority": TicketPriority.P3,
        "priority_order": 6,
    },
]


def ticket_seed_data(now: datetime) -> list[dict[str, Any]]:
    return [
        {
            "title": "Production database down",
            "category": TicketCategory.ENGINEERING,
            "priority": TicketPriority.P1,
            "channel": TicketChannel.WEB_FORM,
            "status": TicketStatus.IN_PROGRESS,
            "assigned_agent": "agent@example.com",
        },
        {
            "title": "Cannot process payments",
            "category": TicketCategory.BILLING,
            "priority": TicketPriority.P1,
            "channel": TicketChannel.EMAIL,
            "status": TicketStatus.OPEN,
            "created_at": now - timedelta(minutes=10),
        },
        {
            "title": "Billing charge incorrect",
            "category": TicketCategory.BILLING,
            "priority": TicketPriority.P2,
            "channel": TicketChannel.WEB_FORM,
            "status": TicketStatus.OPEN,
        },
        {
            "title": "Refund not received",
            "category": TicketCategory.BILLING,
            "priority": TicketPriority.P3,
            "channel": TicketChannel.API,
            "status": TicketStatus.IN_PROGRESS,
            "assigned_agent": "agent@example.com",
        },
        {
            "title": "Suspicious login detected",
            "category": TicketCategory.SECURITY,
            "priority": TicketPriority.P2,
            "channel": TicketChannel.EMAIL,
            "status": TicketStatus.OPEN,
        },
        {
            "title": "Account locked out",
            "category": TicketCategory.ACCOUNT_MANAGEMENT,
            "priority": TicketPriority.P3,
            "channel": TicketChannel.WEB_FORM,
            "status": TicketStatus.OPEN,
        },
        {
            "title": "Password reset not working",
            "category": TicketCategory.ENGINEERING,
            "priority": TicketPriority.P3,
            "channel": TicketChannel.WEB_FORM,
            "status": TicketStatus.RESOLVED,
            "resolved_at": now,
        },
        {
            "title": "API rate limit too low",
            "category": TicketCategory.ENGINEERING,
            "priority": TicketPriority.P2,
            "channel": TicketChannel.API,
            "status": TicketStatus.IN_PROGRESS,
            "assigned_agent": "agent@example.com",
        },
        {
            "title": "Unable to update billing address",
            "category": TicketCategory.BILLING,
            "priority": TicketPriority.P4,
            "channel": TicketChannel.WEB_FORM,
            "status": TicketStatus.CLOSED,
            "resolved_at": now - timedelta(hours=2),
        },
        {
            "title": "New user onboarding issue",
            "category": TicketCategory.ACCOUNT_MANAGEMENT,
            "priority": TicketPriority.P3,
            "channel": TicketChannel.EMAIL,
            "status": TicketStatus.OPEN,
        },
        {
            "title": "General inquiry about pricing",
            "category": TicketCategory.GENERAL,
            "priority": TicketPriority.P3,
            "channel": TicketChannel.WEB_FORM,
            "status": TicketStatus.OPEN,
        },
        {
            "title": "SSL certificate expiring",
            "category": TicketCategory.SECURITY,
            "priority": TicketPriority.P3,
            "channel": TicketChannel.API,
            "status": TicketStatus.OPEN,
        },
    ]


def main() -> None:
    init_db()
    now = datetime.now(timezone.utc)

    with SessionLocal() as session:
        with session.begin():
            seed_teams(session)
            seed_users(session)
            seed_routing_rules(session)
            session.flush()
            seed_tickets(session, now)


def seed_teams(session: Session) -> None:
    for team_data in TEAMS:
        team = session.scalar(select(Team).where(Team.name == team_data["name"]))
        if team is None:
            session.add(Team(**team_data))
        else:
            team.escalation_contact = team_data["escalation_contact"]


def seed_users(session: Session) -> None:
    for user_data in USERS:
        user = session.scalar(select(User).where(User.email == user_data["email"]))
        hashed_password = password_context.hash(user_data["password"])
        if user is None:
            session.add(
                User(
                    email=user_data["email"],
                    hashed_password=hashed_password,
                    role=user_data["role"],
                )
            )
        else:
            user.hashed_password = hashed_password
            user.role = user_data["role"]


def seed_routing_rules(session: Session) -> None:
    for rule_data in ROUTING_RULES:
        rule = session.scalar(select(RoutingRule).where(RoutingRule.name == rule_data["name"]))
        if rule is None:
            session.add(RoutingRule(**rule_data))
            continue

        for field, value in normalized_rule_data(rule_data).items():
            setattr(rule, field, value)


def normalized_rule_data(rule_data: dict[str, Any]) -> dict[str, Any]:
    data = {
        "secondary_condition_field": None,
        "secondary_condition_operator": None,
        "secondary_condition_value": None,
        "auto_priority": None,
    }
    data.update(rule_data)
    return data


def seed_tickets(session: Session, now: datetime) -> None:
    for ticket_data in ticket_seed_data(now):
        for existing_ticket in session.scalars(select(Ticket).where(Ticket.title == ticket_data["title"])):
            session.delete(existing_ticket)
        session.flush()

        ticket = Ticket(
            title=ticket_data["title"],
            description=f"Seed ticket: {ticket_data['title']}",
            channel=ticket_data["channel"],
            status=ticket_data["status"],
            priority=ticket_data["priority"],
            category=ticket_data["category"],
            assigned_agent=ticket_data.get("assigned_agent"),
            created_at=ticket_data.get("created_at", now),
            resolved_at=ticket_data.get("resolved_at"),
        )
        session.add(ticket)

        route_ticket(session, ticket)
        if ticket.status == TicketStatus.CLOSED:
            ticket.history.append(
                TicketHistory(
                    action="status_changed",
                    old_value=TicketStatus.RESOLVED.value,
                    new_value=TicketStatus.CLOSED.value,
                    changed_by="seed",
                    timestamp=ticket.resolved_at,
                )
            )


if __name__ == "__main__":
    main()
