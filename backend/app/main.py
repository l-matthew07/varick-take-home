from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import init_db
from app.routers import auth, health, metrics, tickets

app = FastAPI(title="Support Ticket System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api/auth")
app.include_router(tickets.router, prefix="/api/tickets")
app.include_router(metrics.router, prefix="/api")

# Compatibility mounts for frontend bundles built with the backend origin rather than /api.
app.include_router(health.router)
app.include_router(auth.router, prefix="/auth")
app.include_router(tickets.router, prefix="/tickets")
app.include_router(metrics.router)
