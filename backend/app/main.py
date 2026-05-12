from fastapi import FastAPI

from app.routers import auth, health, metrics, tickets

app = FastAPI(title="Support Ticket System")

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api/auth")
app.include_router(tickets.router, prefix="/api/tickets")
app.include_router(metrics.router, prefix="/api")
