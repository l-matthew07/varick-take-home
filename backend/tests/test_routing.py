"""Routing engine tests."""

from datetime import datetime, timedelta, timezone
import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.models import (
    RoutingRule,
    Ticket,
    TicketCategory,
    TicketChannel,
    TicketPriority,
    TicketStatus,
)
from app.routers.tickets import ticket_sla_status
from app.services.routing import condition_matches, route_ticket


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    session = SessionLocal()
    try:
        seed_routing_rules(session)
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def seed_routing_rules(session):
    rules = [
        RoutingRule(
            name="Security Catch-All",
            condition_field="category",
            condition_operator="equals",
            condition_value="security",
            target_team="Security",
            auto_priority=TicketPriority.P1,
            priority_order=1,
        ),
        RoutingRule(
            name="High Priority Billing",
            condition_field="category",
            condition_operator="equals",
            condition_value="billing",
            secondary_condition_field="priority",
            secondary_condition_operator="in",
            secondary_condition_value=json.dumps(["P1", "P2"]),
            target_team="Billing",
            priority_order=2,
        ),
        RoutingRule(
            name="Low Priority Billing",
            condition_field="category",
            condition_operator="equals",
            condition_value="billing",
            secondary_condition_field="priority",
            secondary_condition_operator="in",
            secondary_condition_value=json.dumps(["P3", "P4"]),
            target_team="Account Management",
            priority_order=3,
        ),
        RoutingRule(
            name="Engineering",
            condition_field="category",
            condition_operator="equals",
            condition_value="engineering",
            target_team="Engineering",
            priority_order=4,
        ),
        RoutingRule(
            name="Account Management Direct",
            condition_field="category",
            condition_operator="equals",
            condition_value="account_management",
            target_team="Account Management",
            priority_order=5,
        ),
        RoutingRule(
            name="Default Catch-All",
            condition_field="category",
            condition_operator="equals",
            condition_value="general",
            target_team="Account Management",
            auto_priority=TicketPriority.P3,
            priority_order=6,
        ),
    ]
    session.add_all(rules)
    session.commit()


def make_ticket(
    category: TicketCategory,
    priority: TicketPriority = TicketPriority.P3,
    status: TicketStatus = TicketStatus.OPEN,
) -> Ticket:
    return Ticket(
        title="Test ticket",
        description="Test description",
        channel=TicketChannel.WEB_FORM,
        status=status,
        priority=priority,
        category=category,
        created_at=datetime.now(timezone.utc),
    )


def route_and_flush(session, ticket: Ticket) -> tuple[Ticket, str]:
    session.add(ticket)
    session.flush()
    routed_ticket, rule_name = route_ticket(session, ticket, changed_by="tester@example.com")
    session.flush()
    return routed_ticket, rule_name


def test_condition_equals_operator_match_and_no_match():
    assert condition_matches("billing", "equals", "billing") is True
    assert condition_matches("billing", "equals", "security") is False


def test_condition_contains_operator_match_and_no_match():
    assert condition_matches("urgent production outage", "contains", "production") is True
    assert condition_matches("urgent production outage", "contains", "billing") is False


def test_condition_in_operator_match_and_no_match():
    assert condition_matches("P1", "in", json.dumps(["P1", "P2"])) is True
    assert condition_matches("P4", "in", json.dumps(["P1", "P2"])) is False


def test_unknown_condition_operator_returns_false():
    assert condition_matches("billing", "starts_with", "bill") is False


def test_security_ticket_routes_to_security_and_overrides_priority(db_session):
    ticket, rule_name = route_and_flush(
        db_session,
        make_ticket(TicketCategory.SECURITY, TicketPriority.P2),
    )

    assert rule_name == "Security Catch-All"
    assert ticket.assigned_team == "Security"
    assert ticket.priority == TicketPriority.P1


@pytest.mark.parametrize("priority", [TicketPriority.P1, TicketPriority.P2])
def test_high_priority_billing_routes_to_billing(db_session, priority):
    ticket, rule_name = route_and_flush(
        db_session,
        make_ticket(TicketCategory.BILLING, priority),
    )

    assert rule_name == "High Priority Billing"
    assert ticket.assigned_team == "Billing"


@pytest.mark.parametrize("priority", [TicketPriority.P3, TicketPriority.P4])
def test_low_priority_billing_routes_to_account_management(db_session, priority):
    ticket, rule_name = route_and_flush(
        db_session,
        make_ticket(TicketCategory.BILLING, priority),
    )

    assert rule_name == "Low Priority Billing"
    assert ticket.assigned_team == "Account Management"


def test_engineering_ticket_routes_to_engineering(db_session):
    ticket, rule_name = route_and_flush(
        db_session,
        make_ticket(TicketCategory.ENGINEERING),
    )

    assert rule_name == "Engineering"
    assert ticket.assigned_team == "Engineering"


def test_account_management_ticket_routes_to_account_management(db_session):
    ticket, rule_name = route_and_flush(
        db_session,
        make_ticket(TicketCategory.ACCOUNT_MANAGEMENT),
    )

    assert rule_name == "Account Management Direct"
    assert ticket.assigned_team == "Account Management"


def test_general_ticket_hits_catch_all(db_session):
    ticket, rule_name = route_and_flush(
        db_session,
        make_ticket(TicketCategory.GENERAL, TicketPriority.P4),
    )

    assert rule_name == "Default Catch-All"
    assert ticket.assigned_team == "Account Management"
    assert ticket.priority == TicketPriority.P3


def test_first_match_wins(db_session):
    db_session.add(
        RoutingRule(
            name="Late Security Rule",
            condition_field="category",
            condition_operator="equals",
            condition_value="security",
            target_team="Billing",
            auto_priority=TicketPriority.P4,
            priority_order=99,
        )
    )
    db_session.commit()

    ticket, rule_name = route_and_flush(
        db_session,
        make_ticket(TicketCategory.SECURITY, TicketPriority.P2),
    )

    assert rule_name == "Security Catch-All"
    assert ticket.assigned_team == "Security"
    assert ticket.priority == TicketPriority.P1


def test_auto_priority_override_is_logged(db_session):
    ticket, _ = route_and_flush(
        db_session,
        make_ticket(TicketCategory.SECURITY, TicketPriority.P2),
    )

    assert "priority_overridden" in [entry.action for entry in ticket.history]


def test_classified_and_assigned_history_entries_are_created(db_session):
    ticket, _ = route_and_flush(
        db_session,
        make_ticket(TicketCategory.ENGINEERING),
    )

    actions = [entry.action for entry in ticket.history]
    assert "classified" in actions
    assert "assigned" in actions


def test_sla_status_assigned_agent_is_on_track():
    ticket = make_ticket(TicketCategory.ENGINEERING, TicketPriority.P1)
    ticket.assigned_agent = "agent@example.com"
    ticket.sla_deadline = datetime.now(timezone.utc) - timedelta(hours=1)

    assert ticket_sla_status(ticket) == "on_track"


def test_sla_status_past_deadline_is_breached():
    ticket = make_ticket(TicketCategory.ENGINEERING, TicketPriority.P1)
    ticket.sla_deadline = datetime.now(timezone.utc) - timedelta(seconds=1)

    assert ticket_sla_status(ticket) == "breached"


def test_sla_status_within_twenty_percent_window_is_at_risk():
    now = datetime.now(timezone.utc)
    ticket = make_ticket(TicketCategory.ENGINEERING, TicketPriority.P2)
    ticket.sla_deadline = now + timedelta(minutes=10)

    assert ticket_sla_status(ticket, now=now) == "at_risk"


def test_sla_status_more_than_twenty_percent_remaining_is_on_track():
    now = datetime.now(timezone.utc)
    ticket = make_ticket(TicketCategory.ENGINEERING, TicketPriority.P2)
    ticket.sla_deadline = now + timedelta(minutes=20)

    assert ticket_sla_status(ticket, now=now) == "on_track"
