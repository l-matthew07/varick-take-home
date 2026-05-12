"""Ticket business logic: status transition rules."""

from app.models.models import TicketStatus

STATUS_TRANSITIONS: dict[TicketStatus, list[TicketStatus]] = {
    TicketStatus.OPEN: [TicketStatus.IN_PROGRESS],
    TicketStatus.IN_PROGRESS: [TicketStatus.RESOLVED],
    TicketStatus.RESOLVED: [TicketStatus.CLOSED, TicketStatus.IN_PROGRESS],
    TicketStatus.CLOSED: [],
}


def allowed_transitions(current: TicketStatus) -> list[TicketStatus]:
    return STATUS_TRANSITIONS[current]


def is_valid_transition(current: TicketStatus, next_status: TicketStatus) -> bool:
    return next_status in STATUS_TRANSITIONS[current]
