from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.models import (
    Ticket,
    TicketCategory,
    TicketChannel,
    TicketHistory,
    TicketPriority,
    TicketStatus,
    User,
)
from app.services.routing import SLA_WINDOWS_MINUTES, enum_value, route_ticket

router = APIRouter(tags=["tickets"])

STATUS_TRANSITIONS = {
    TicketStatus.OPEN: [TicketStatus.IN_PROGRESS],
    TicketStatus.IN_PROGRESS: [TicketStatus.RESOLVED],
    TicketStatus.RESOLVED: [TicketStatus.CLOSED, TicketStatus.IN_PROGRESS],
    TicketStatus.CLOSED: [],
}


class TicketCreate(BaseModel):
    title: str
    description: str
    channel: TicketChannel
    category: TicketCategory
    priority: TicketPriority


class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    assigned_agent: str | None = None
    assigned_team: str | None = None


class TicketHistoryResponse(BaseModel):
    id: UUID
    action: str
    old_value: str | None
    new_value: str | None
    changed_by: str
    timestamp: datetime


class TicketResponse(BaseModel):
    id: UUID
    title: str
    description: str
    channel: str
    status: str
    priority: str
    category: str
    assigned_team: str | None
    assigned_agent: str | None
    sla_deadline: datetime | None
    sla_status: str
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None


class TicketDetailResponse(TicketResponse):
    history: list[TicketHistoryResponse]


class TicketListResponse(BaseModel):
    items: list[TicketResponse]
    total: int
    limit: int
    offset: int


class TicketCreateResponse(BaseModel):
    ticket: TicketResponse
    routed_to: str
    final_priority: str
    sla_deadline: datetime | None
    rule_matched: str


class SLABreachTicketResponse(TicketResponse):
    sla_elapsed_seconds: int


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def ticket_sla_status(ticket: Ticket, now: datetime | None = None) -> str:
    if ticket.assigned_agent is not None or ticket.sla_deadline is None:
        return "on_track"

    current_time = now or utc_now()
    sla_deadline = ensure_aware(ticket.sla_deadline)
    if current_time > sla_deadline:
        return "breached"

    priority = enum_value(ticket.priority)
    total_seconds = SLA_WINDOWS_MINUTES[priority] * 60
    remaining_seconds = (sla_deadline - current_time).total_seconds()
    if remaining_seconds / total_seconds <= 0.20:
        return "at_risk"

    return "on_track"


def serialize_history(history: TicketHistory) -> TicketHistoryResponse:
    return TicketHistoryResponse(
        id=history.id,
        action=history.action,
        old_value=history.old_value,
        new_value=history.new_value,
        changed_by=history.changed_by,
        timestamp=history.timestamp,
    )


def serialize_ticket(ticket: Ticket) -> TicketResponse:
    return TicketResponse(
        id=ticket.id,
        title=ticket.title,
        description=ticket.description,
        channel=enum_value(ticket.channel),
        status=enum_value(ticket.status),
        priority=enum_value(ticket.priority),
        category=enum_value(ticket.category),
        assigned_team=ticket.assigned_team,
        assigned_agent=ticket.assigned_agent,
        sla_deadline=ticket.sla_deadline,
        sla_status=ticket_sla_status(ticket),
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
    )


def serialize_ticket_detail(ticket: Ticket) -> TicketDetailResponse:
    ticket_data = serialize_ticket(ticket).model_dump()
    return TicketDetailResponse(
        **ticket_data,
        history=[serialize_history(history) for history in ticket.history],
    )


def ticket_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")


@router.get("", response_model=TicketListResponse)
def list_tickets(
    status_filter: Annotated[TicketStatus | None, Query(alias="status")] = None,
    priority: TicketPriority | None = None,
    category: TicketCategory | None = None,
    assigned_team: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
) -> TicketListResponse:
    filters: list[Any] = []
    if status_filter is not None:
        filters.append(Ticket.status == status_filter)
    if priority is not None:
        filters.append(Ticket.priority == priority)
    if category is not None:
        filters.append(Ticket.category == category)
    if assigned_team is not None:
        filters.append(Ticket.assigned_team == assigned_team)

    total = db.scalar(select(func.count()).select_from(Ticket).where(*filters)) or 0
    tickets = db.scalars(
        select(Ticket)
        .where(*filters)
        .order_by(Ticket.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    return TicketListResponse(
        items=[serialize_ticket(ticket) for ticket in tickets],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=TicketCreateResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: TicketCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> TicketCreateResponse:
    ticket = Ticket(
        title=payload.title,
        description=payload.description,
        channel=payload.channel,
        category=payload.category,
        priority=payload.priority,
        status=TicketStatus.OPEN,
    )
    db.add(ticket)
    db.flush()

    ticket.history.append(
        TicketHistory(
            action="created",
            old_value=None,
            new_value=TicketStatus.OPEN.value,
            changed_by=current_user.email,
        )
    )
    ticket, rule_matched = route_ticket(db, ticket, changed_by=current_user.email)

    db.commit()
    db.refresh(ticket)

    return TicketCreateResponse(
        ticket=serialize_ticket(ticket),
        routed_to=ticket.assigned_team or "",
        final_priority=enum_value(ticket.priority),
        sla_deadline=ticket.sla_deadline,
        rule_matched=rule_matched,
    )


@router.get("/sla-breaches", response_model=list[SLABreachTicketResponse])
def list_sla_breaches(db: Session = Depends(get_db)) -> list[SLABreachTicketResponse]:
    now = utc_now()
    tickets = db.scalars(
        select(Ticket)
        .where(
            Ticket.sla_deadline < now,
            Ticket.assigned_agent.is_(None),
            Ticket.status.notin_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
        )
        .order_by(Ticket.sla_deadline.asc())
    ).all()

    results: list[SLABreachTicketResponse] = []
    for ticket in tickets:
        ticket_data = serialize_ticket(ticket).model_dump()
        sla_deadline = ensure_aware(ticket.sla_deadline)
        results.append(
            SLABreachTicketResponse(
                **ticket_data,
                sla_elapsed_seconds=int((now - sla_deadline).total_seconds()),
            )
        )
    return results


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
def get_ticket(ticket_id: UUID, db: Session = Depends(get_db)) -> TicketDetailResponse:
    ticket = db.scalar(
        select(Ticket).options(selectinload(Ticket.history)).where(Ticket.id == ticket_id)
    )
    if ticket is None:
        raise ticket_not_found()
    return serialize_ticket_detail(ticket)


@router.put("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    ticket_id: UUID,
    payload: TicketUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> TicketResponse | JSONResponse:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise ticket_not_found()

    updates = payload.model_fields_set
    if "status" in updates and payload.status is not None and payload.status != ticket.status:
        allowed = STATUS_TRANSITIONS[ticket.status]
        if payload.status not in allowed:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "detail": "Invalid transition",
                    "allowed": [enum_value(status_value) for status_value in allowed],
                },
            )

        old_status = enum_value(ticket.status)
        ticket.status = payload.status
        ticket.history.append(
            TicketHistory(
                action="status_changed",
                old_value=old_status,
                new_value=enum_value(ticket.status),
                changed_by=current_user.email,
            )
        )
        if ticket.status == TicketStatus.RESOLVED:
            ticket.resolved_at = utc_now()
        elif ticket.status == TicketStatus.IN_PROGRESS:
            ticket.resolved_at = None

    if "assigned_agent" in updates:
        ticket.assigned_agent = payload.assigned_agent
    if "assigned_team" in updates:
        ticket.assigned_team = payload.assigned_team

    db.commit()
    db.refresh(ticket)
    return serialize_ticket(ticket)
