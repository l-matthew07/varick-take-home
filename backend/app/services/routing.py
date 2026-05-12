"""Routing engine and SLA computation."""

from datetime import datetime, timedelta, timezone
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import RoutingRule, Ticket, TicketHistory

SLA_WINDOWS_MINUTES = {
    "P1": 5,
    "P2": 60,
    "P3": 24 * 60,
    "P4": 48 * 60,
}
DEFAULT_TEAM = "Account Management"
DEFAULT_PRIORITY = "P3"


def route_ticket(db: Session, ticket: Ticket, changed_by: str = "routing_engine") -> tuple[Ticket, str]:
    rules = db.scalars(select(RoutingRule).order_by(RoutingRule.priority_order)).all()
    matched_rule = next((rule for rule in rules if rule_matches_ticket(rule, ticket)), None)

    if matched_rule is not None:
        matched_rule_name = matched_rule.name
        assign_team(ticket, matched_rule.target_team, changed_by)

        if matched_rule.auto_priority is not None and ticket.priority != matched_rule.auto_priority:
            old_priority = enum_value(ticket.priority)
            ticket.priority = matched_rule.auto_priority
            ticket.history.append(
                TicketHistory(
                    action="priority_overridden",
                    old_value=old_priority,
                    new_value=enum_value(ticket.priority),
                    changed_by=changed_by,
                )
            )
    else:
        matched_rule_name = "Default Catch-All"
        assign_team(ticket, DEFAULT_TEAM, changed_by)
        if enum_value(ticket.priority) != DEFAULT_PRIORITY:
            old_priority = enum_value(ticket.priority)
            ticket.priority = DEFAULT_PRIORITY
            ticket.history.append(
                TicketHistory(
                    action="priority_overridden",
                    old_value=old_priority,
                    new_value=DEFAULT_PRIORITY,
                    changed_by=changed_by,
                )
            )

    created_at = ticket.created_at or datetime.now(timezone.utc)
    ticket.created_at = created_at
    ticket.sla_deadline = created_at + timedelta(minutes=SLA_WINDOWS_MINUTES[enum_value(ticket.priority)])

    return ticket, matched_rule_name


def assign_team(ticket: Ticket, target_team: str, changed_by: str) -> None:
    old_team = ticket.assigned_team
    ticket.assigned_team = target_team
    if old_team == target_team:
        return

    ticket.history.append(
        TicketHistory(
            action="classified",
            old_value=old_team,
            new_value=target_team,
            changed_by=changed_by,
        )
    )
    ticket.history.append(
        TicketHistory(
            action="assigned",
            old_value=None,
            new_value=target_team,
            changed_by=changed_by,
        )
    )


def rule_matches_ticket(rule: RoutingRule, ticket: Ticket) -> bool:
    if not condition_matches(
        get_ticket_field(ticket, rule.condition_field),
        rule.condition_operator,
        rule.condition_value,
    ):
        return False

    if rule.secondary_condition_field is None:
        return True

    return condition_matches(
        get_ticket_field(ticket, rule.secondary_condition_field),
        rule.secondary_condition_operator,
        rule.secondary_condition_value,
    )


def condition_matches(actual: Any, operator: str | None, expected: str | None) -> bool:
    if operator is None or expected is None:
        return False

    actual_value = enum_value(actual)

    if operator == "equals":
        return actual_value == expected
    if operator == "in":
        return actual_value in parse_list_value(expected)
    if operator == "contains":
        return actual_value in expected

    return False


def get_ticket_field(ticket: Ticket, field_name: str) -> Any:
    return getattr(ticket, field_name)


def enum_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def parse_list_value(value: str) -> list[str]:
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise ValueError(f"Expected list condition value, got {value!r}")
    return [str(item) for item in parsed]
