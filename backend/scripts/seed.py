"""Idempotent seed data for the support ticket system."""

from datetime import datetime, timedelta, timezone
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
        "conditions": [{"field": "category", "operator": "equals", "value": "security"}],
        "target_team": "Security",
        "auto_priority": TicketPriority.P1,
        "priority_order": 1,
    },
    {
        "name": "High Priority Billing",
        "conditions": [
            {"field": "category", "operator": "equals", "value": "billing"},
            {"field": "priority", "operator": "in", "value": ["P1", "P2"]},
        ],
        "target_team": "Billing",
        "priority_order": 2,
    },
    {
        "name": "Low Priority Billing",
        "conditions": [
            {"field": "category", "operator": "equals", "value": "billing"},
            {"field": "priority", "operator": "in", "value": ["P3", "P4"]},
        ],
        "target_team": "Account Management",
        "priority_order": 3,
    },
    {
        "name": "Engineering",
        "conditions": [{"field": "category", "operator": "equals", "value": "engineering"}],
        "target_team": "Engineering",
        "priority_order": 4,
    },
    {
        "name": "Account Management Direct",
        "conditions": [{"field": "category", "operator": "equals", "value": "account_management"}],
        "target_team": "Account Management",
        "priority_order": 5,
    },
    {
        "name": "Default Catch-All",
        "conditions": [],
        "target_team": "Account Management",
        "auto_priority": TicketPriority.P3,
        "priority_order": 6,
    },
]


TICKET_DESCRIPTIONS = {
    "Production database down": (
        "The primary RDS instance became unresponsive at 14:32 UTC. All write operations are "
        "failing with connection timeout errors. Read replicas are still serving traffic but "
        "the application is degraded. On-call engineer has been paged and is investigating."
    ),
    "Cannot process payments": (
        "Payment processing has been completely unavailable since 09:45 UTC. Customers are "
        "unable to complete checkout. The Stripe webhook is returning 503 errors. Revenue "
        "impact is approximately $2,400/minute based on average transaction volume. Requires "
        "immediate escalation to the payments infrastructure team."
    ),
    "Billing charge incorrect": (
        "Customer reports being charged $299 instead of $29 on their monthly subscription "
        "renewal on May 8th. Invoice #INV-20240508-4821. They have attached a screenshot of "
        "their bank statement. Please review the billing event log and issue a corrected "
        "invoice with a refund for the overcharge."
    ),
    "Refund not received": (
        "Customer submitted a refund request on April 30th (ticket #REF-2240) and was told "
        "to expect the refund within 5-7 business days. It is now 10 business days later and "
        "the $149 refund has not appeared in their account. Customer has contacted their bank "
        "who confirmed no pending credit. Please investigate the refund transaction status."
    ),
    "Suspicious login detected": (
        "Automated security monitoring flagged a successful login from an IP in Romania "
        "(185.220.101.47) at 03:12 UTC for account user@acmecorp.com. The account has never "
        "previously logged in from outside the US. MFA was not triggered due to a remembered "
        "device token from 30 days ago. The session performed several API key rotations "
        "before being detected. Account has been temporarily suspended pending review."
    ),
    "Account locked out": (
        "Customer is unable to log in to their account after changing their email address "
        "yesterday. They are receiving an 'account not found' error when attempting to sign "
        "in with the new email, and a 'password incorrect' error with the old email. "
        "Verification email to the new address was never received. Account ID: USR-88124."
    ),
    "Password reset not working": (
        "Multiple users on the acmecorp.com domain reported that password reset emails are "
        "not being delivered. The reset flow completes without error on the frontend but the "
        "email never arrives. Investigation found a misconfigured SPF record on the sending "
        "domain that was causing messages to be rejected by recipient mail servers. Fixed by "
        "updating the DNS record — affected users have been notified to retry."
    ),
    "API rate limit too low": (
        "The /api/v2/events endpoint is rate-limited at 100 requests/minute per API key, "
        "which is insufficient for our data pipeline. We're ingesting sensor data from 400 "
        "devices that each emit an event every 15 seconds, requiring approximately 1,600 "
        "requests/minute. We've implemented client-side batching but still hit the limit "
        "during peak hours. Requesting either a higher limit or a bulk-ingest endpoint."
    ),
    "Unable to update billing address": (
        "Customer attempted to update their billing address through the account settings "
        "page. The form submits successfully and shows a confirmation message, but the "
        "address reverts to the old value on page refresh. Affects only billing address — "
        "shipping address updates correctly. Customer needs the correct address on file "
        "before their invoice generates on the 15th."
    ),
    "New user onboarding issue": (
        "A batch of 12 new users invited via the admin console on May 10th never received "
        "their invitation emails. The admin dashboard shows the invitations as 'sent' but "
        "users confirmed no email was received (checked spam folders). The company starts "
        "their onboarding training tomorrow morning and needs all accounts active. "
        "Affected accounts: invited via admin@techstart.io, organization ID ORG-5521."
    ),
    "General inquiry about pricing": (
        "Prospective customer asking about pricing for a 200-seat enterprise plan. They are "
        "currently evaluating us against two competitors and have a budget decision deadline "
        "of May 20th. They specifically want to know if annual billing offers a discount, "
        "whether SSO and audit logs are included at the enterprise tier, and if a private "
        "cloud deployment option is available. Routed to Account Management for follow-up."
    ),
    "SSL certificate expiring": (
        "Automated certificate monitoring detected that the wildcard SSL certificate for "
        "*.api.example.com expires in 18 days (June 1st). The certificate is managed outside "
        "of Let's Encrypt and requires manual renewal through the CA portal. Last year's "
        "renewal was missed and caused a 4-hour outage. Assigned to the security team to "
        "initiate renewal and update the certificate rotation runbook."
    ),
}


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
            description=TICKET_DESCRIPTIONS[ticket_data["title"]],
            channel=ticket_data["channel"],
            status=ticket_data["status"],
            priority=ticket_data["priority"],
            category=ticket_data["category"],
            assigned_agent=ticket_data.get("assigned_agent"),
            created_at=ticket_data.get("created_at", now),
            resolved_at=ticket_data.get("resolved_at"),
        )
        session.add(ticket)
        session.flush()

        ticket.history.append(
            TicketHistory(
                action="created",
                old_value=None,
                new_value=TicketStatus.OPEN.value,
                changed_by="seed",
                timestamp=ticket.created_at,
            )
        )
        ticket, _ = route_ticket(session, ticket)
        append_seed_status_history(ticket)


def append_seed_status_history(ticket: Ticket) -> None:
    if ticket.status == TicketStatus.OPEN:
        return

    transition_time = ticket.created_at + timedelta(seconds=1)
    ticket.history.append(
        TicketHistory(
            action="status_changed",
            old_value=TicketStatus.OPEN.value,
            new_value=TicketStatus.IN_PROGRESS.value,
            changed_by="seed",
            timestamp=transition_time,
        )
    )
    if ticket.status == TicketStatus.IN_PROGRESS:
        return

    resolved_at = ticket.resolved_at or transition_time + timedelta(seconds=1)
    ticket.history.append(
        TicketHistory(
            action="resolved",
            old_value=TicketStatus.IN_PROGRESS.value,
            new_value=TicketStatus.RESOLVED.value,
            changed_by="seed",
            timestamp=resolved_at,
        )
    )
    if ticket.status == TicketStatus.RESOLVED:
        return

    ticket.history.append(
        TicketHistory(
            action="status_changed",
            old_value=TicketStatus.RESOLVED.value,
            new_value=TicketStatus.CLOSED.value,
            changed_by="seed",
            timestamp=resolved_at + timedelta(seconds=1),
        )
    )


if __name__ == "__main__":
    main()
