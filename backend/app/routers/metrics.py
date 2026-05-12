from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import require_role
from app.core.database import get_db
from app.core.utils import ensure_aware, enum_value
from app.models.models import Ticket, TicketPriority, TicketStatus, User

router = APIRouter(tags=["metrics"])


class MetricsResponse(BaseModel):
    tickets_by_status: dict[str, int]
    tickets_by_priority: dict[str, int]
    tickets_by_team: dict[str, int]
    sla_breaches: int
    avg_resolution_seconds: float | None


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics(
    _: Annotated[User, Depends(require_role("lead"))],
    db: Session = Depends(get_db),
) -> MetricsResponse:
    status_counts = {
        status.value: 0
        for status in [
            TicketStatus.OPEN,
            TicketStatus.IN_PROGRESS,
            TicketStatus.RESOLVED,
            TicketStatus.CLOSED,
        ]
    }
    for ticket_status, count in db.execute(
        select(Ticket.status, func.count()).group_by(Ticket.status)
    ):
        status_counts[enum_value(ticket_status)] = count

    priority_counts = {
        priority.value: 0
        for priority in [
            TicketPriority.P1,
            TicketPriority.P2,
            TicketPriority.P3,
            TicketPriority.P4,
        ]
    }
    for priority, count in db.execute(
        select(Ticket.priority, func.count()).group_by(Ticket.priority)
    ):
        priority_counts[enum_value(priority)] = count

    team_counts = {
        team: count
        for team, count in db.execute(
            select(Ticket.assigned_team, func.count())
            .where(Ticket.assigned_team.is_not(None))
            .group_by(Ticket.assigned_team)
        )
    }

    now = datetime.now(timezone.utc)
    sla_breaches = db.scalar(
        select(func.count())
        .select_from(Ticket)
        .where(
            Ticket.sla_deadline < now,
            Ticket.assigned_agent.is_(None),
            Ticket.status.notin_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
        )
    ) or 0

    resolved_tickets = db.execute(
        select(Ticket.created_at, Ticket.resolved_at).where(
            Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
            Ticket.resolved_at.is_not(None),
        )
    ).all()
    resolution_seconds = [
        (ensure_aware(resolved_at) - ensure_aware(created_at)).total_seconds()
        for created_at, resolved_at in resolved_tickets
    ]
    avg_resolution_seconds = (
        sum(resolution_seconds) / len(resolution_seconds)
        if resolution_seconds
        else None
    )

    return MetricsResponse(
        tickets_by_status=status_counts,
        tickets_by_priority=priority_counts,
        tickets_by_team=team_counts,
        sla_breaches=sla_breaches,
        avg_resolution_seconds=avg_resolution_seconds,
    )
