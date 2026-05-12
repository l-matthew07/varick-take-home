from collections.abc import Generator
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required")

SQLALCHEMY_DATABASE_URL = (
    DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
    if DATABASE_URL.startswith("postgresql://")
    else DATABASE_URL
)

connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    migrate_routing_rule_conditions()
    install_updated_at_trigger()


def migrate_routing_rule_conditions() -> None:
    if engine.dialect.name != "postgresql":
        return

    with engine.begin() as connection:
        condition_column_exists = connection.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'routing_rules'
                      AND column_name = 'conditions'
                )
                """
            )
        ).scalar()
        if condition_column_exists:
            return

        connection.execute(text("ALTER TABLE routing_rules ADD COLUMN conditions JSONB"))
        connection.execute(
            text(
                """
                UPDATE routing_rules
                SET conditions = jsonb_build_array(
                    jsonb_build_object(
                        'field', condition_field,
                        'operator', condition_operator,
                        'value', condition_value
                    )
                ) ||
                CASE
                    WHEN secondary_condition_field IS NULL THEN '[]'::jsonb
                    ELSE jsonb_build_array(
                        jsonb_build_object(
                            'field', secondary_condition_field,
                            'operator', secondary_condition_operator,
                            'value',
                            CASE
                                WHEN secondary_condition_operator = 'in'
                                THEN secondary_condition_value::jsonb
                                ELSE to_jsonb(secondary_condition_value)
                            END
                        )
                    )
                END
                WHERE conditions IS NULL
                """
            )
        )
        connection.execute(text("ALTER TABLE routing_rules ALTER COLUMN conditions SET NOT NULL"))


def install_updated_at_trigger() -> None:
    if engine.dialect.name != "postgresql":
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE OR REPLACE FUNCTION set_ticket_updated_at()
                RETURNS trigger AS $$
                BEGIN
                    NEW.updated_at = clock_timestamp();
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                """
            )
        )
        connection.execute(
            text(
                """
                DROP TRIGGER IF EXISTS tickets_set_updated_at ON tickets;
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TRIGGER tickets_set_updated_at
                BEFORE UPDATE ON tickets
                FOR EACH ROW
                EXECUTE FUNCTION set_ticket_updated_at();
                """
            )
        )
