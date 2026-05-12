"""API integration tests."""

from collections.abc import Generator
from datetime import datetime, timedelta, timezone
import json
import os
from uuid import UUID

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ALGORITHM", "HS256")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import hash_password
from app.core.database import Base, get_db
from app.main import app
from app.models.models import (
    RoutingRule,
    Ticket,
    TicketCategory,
    TicketChannel,
    TicketPriority,
    TicketStatus,
    User,
    UserRole,
)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as session:
        seed_users(session)
        seed_routing_rules(session)
        session.commit()

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def seed_users(session: Session) -> None:
    session.add_all(
        [
            User(
                email="agent@example.com",
                hashed_password=hash_password("testpass123"),
                role=UserRole.AGENT,
            ),
            User(
                email="lead@example.com",
                hashed_password=hash_password("testpass123"),
                role=UserRole.LEAD,
            ),
        ]
    )


def seed_routing_rules(session: Session) -> None:
    session.add_all(
        [
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
    )


def login(client: TestClient, email: str = "agent@example.com") -> str:
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "testpass123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_ticket(
    client: TestClient,
    token: str,
    category: str = "engineering",
    priority: str = "P2",
    title: str = "Test ticket",
) -> dict:
    response = client.post(
        "/api/tickets",
        headers=auth_headers(token),
        json={
            "title": title,
            "description": "Ticket description",
            "channel": "web_form",
            "category": category,
            "priority": priority,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_login_with_valid_credentials_returns_token_and_role(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "agent@example.com", "password": "testpass123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["role"] == "agent"


def test_login_with_wrong_password_returns_401(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "agent@example.com", "password": "wrong"},
    )

    assert response.status_code == 401


def test_get_me_with_valid_token_returns_user_info(client):
    token = login(client)

    response = client.get("/api/auth/me", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["email"] == "agent@example.com"


def test_get_me_without_token_returns_401(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_create_ticket_returns_open_ticket_and_routing_result(client):
    token = login(client)

    body = create_ticket(client, token, category="engineering", priority="P2")

    assert body["ticket"]["status"] == "open"
    assert body["routed_to"] == "Engineering"
    assert body["final_priority"] == "P2"
    assert body["rule_matched"] == "Engineering"


def test_security_ticket_auto_priority_p1_in_response(client):
    token = login(client)

    body = create_ticket(client, token, category="security", priority="P3")

    assert body["ticket"]["priority"] == "P1"
    assert body["final_priority"] == "P1"
    assert body["routed_to"] == "Security"


def test_created_ticket_appears_in_ticket_list(client):
    token = login(client)
    created = create_ticket(client, token, title="Listed ticket")

    response = client.get("/api/tickets")

    assert response.status_code == 200
    assert any(item["id"] == created["ticket"]["id"] for item in response.json()["items"])


def test_ticket_list_returns_paginated_response(client):
    token = login(client)
    create_ticket(client, token)

    response = client.get("/api/tickets?limit=10&offset=0")

    assert response.status_code == 200
    body = response.json()
    assert {"items", "total", "limit", "offset"} <= body.keys()
    assert body["limit"] == 10
    assert body["offset"] == 0
    assert body["total"] >= 1


def test_ticket_list_filter_by_status_works(client):
    token = login(client)
    create_ticket(client, token)

    response = client.get("/api/tickets?status=open")

    assert response.status_code == 200
    assert all(item["status"] == "open" for item in response.json()["items"])


def test_ticket_list_filter_by_priority_works(client):
    token = login(client)
    create_ticket(client, token, category="security", priority="P3")

    response = client.get("/api/tickets?priority=P1")

    assert response.status_code == 200
    assert response.json()["total"] >= 1
    assert all(item["priority"] == "P1" for item in response.json()["items"])


def test_valid_status_transition_open_to_in_progress_succeeds(client):
    token = login(client)
    created = create_ticket(client, token)
    ticket_id = created["ticket"]["id"]

    response = client.put(
        f"/api/tickets/{ticket_id}",
        headers=auth_headers(token),
        json={"status": "in_progress"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_invalid_status_transition_returns_400_with_allowed_list(client):
    token = login(client)
    created = create_ticket(client, token)
    ticket_id = created["ticket"]["id"]

    response = client.put(
        f"/api/tickets/{ticket_id}",
        headers=auth_headers(token),
        json={"status": "resolved"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid transition", "allowed": ["in_progress"]}


def test_setting_assigned_agent_updates_ticket(client):
    token = login(client)
    created = create_ticket(client, token)
    ticket_id = created["ticket"]["id"]

    response = client.put(
        f"/api/tickets/{ticket_id}",
        headers=auth_headers(token),
        json={"assigned_agent": "agent@example.com"},
    )

    assert response.status_code == 200
    assert response.json()["assigned_agent"] == "agent@example.com"


def test_sla_breaches_returns_past_deadline_unassigned_tickets(client):
    token = login(client)
    created = create_ticket(client, token, category="engineering", priority="P1")
    ticket_id = created["ticket"]["id"]

    with next(app.dependency_overrides[get_db]()) as session:
        ticket = session.scalar(select(Ticket).where(Ticket.id == UUID(ticket_id)))
        ticket.sla_deadline = datetime.now(timezone.utc) - timedelta(minutes=1)
        ticket.assigned_agent = None
        session.commit()

    response = client.get("/api/tickets/sla-breaches")

    assert response.status_code == 200
    body = response.json()
    assert any(item["id"] == ticket_id for item in body)
    assert all("sla_elapsed_seconds" in item for item in body)


def test_sla_status_is_breached_on_past_deadline_unassigned_ticket(client):
    token = login(client)
    created = create_ticket(client, token, category="engineering", priority="P1")
    ticket_id = created["ticket"]["id"]

    with next(app.dependency_overrides[get_db]()) as session:
        ticket = session.scalar(select(Ticket).where(Ticket.id == UUID(ticket_id)))
        ticket.sla_deadline = datetime.now(timezone.utc) - timedelta(minutes=1)
        ticket.assigned_agent = None
        session.commit()

    response = client.get(f"/api/tickets/{ticket_id}")

    assert response.status_code == 200
    assert response.json()["sla_status"] == "breached"


def test_metrics_returns_403_for_agent_role(client):
    token = login(client, "agent@example.com")

    response = client.get("/api/metrics", headers=auth_headers(token))

    assert response.status_code == 403


def test_metrics_returns_shape_for_lead_role(client):
    token = login(client, "lead@example.com")

    response = client.get("/api/metrics", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert {
        "tickets_by_status",
        "tickets_by_priority",
        "tickets_by_team",
        "sla_breaches",
        "avg_resolution_seconds",
    } <= body.keys()


def test_health_returns_connected(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["db"] == "connected"
