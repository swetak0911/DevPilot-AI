"""
Database Engine & Session Management for DevPilot AI
"""
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

# Engine configuration
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    future=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database session lifecycle."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initializes tables in database and performs automatic column sync for development SQLite."""
    Base.metadata.create_all(bind=engine)

    # Automatic column sync for existing SQLite database files
    if settings.DATABASE_URL.startswith("sqlite"):
        with engine.connect() as conn:
            try:
                res = conn.execute(text("PRAGMA table_info(github_connections)")).fetchall()
                existing_cols = {row[1] for row in res}
                if existing_cols:  # table exists
                    if "github_avatar_url" not in existing_cols:
                        conn.execute(text("ALTER TABLE github_connections ADD COLUMN github_avatar_url VARCHAR(512)"))
                    if "token_type" not in existing_cols:
                        conn.execute(text("ALTER TABLE github_connections ADD COLUMN token_type VARCHAR(50) DEFAULT 'bearer'"))
                    if "last_synced_at" not in existing_cols:
                        conn.execute(text("ALTER TABLE github_connections ADD COLUMN last_synced_at DATETIME"))
                    conn.commit()

                # Sync code_chunks table
                chunk_res = conn.execute(text("PRAGMA table_info(code_chunks)")).fetchall()
                chunk_cols = {row[1] for row in chunk_res}
                if chunk_cols:
                    if "embedding" not in chunk_cols:
                        conn.execute(text("ALTER TABLE code_chunks ADD COLUMN embedding JSON"))
                    if "embedding_model" not in chunk_cols:
                        conn.execute(text("ALTER TABLE code_chunks ADD COLUMN embedding_model VARCHAR(100)"))
                    conn.commit()

                # Sync reviews table
                review_res = conn.execute(text("PRAGMA table_info(reviews)")).fetchall()
                review_cols = {row[1] for row in review_res}
                if review_cols:
                    if "score" not in review_cols:
                        conn.execute(text("ALTER TABLE reviews ADD COLUMN score FLOAT DEFAULT 8.5"))
                    if "risk_level" not in review_cols:
                        conn.execute(text("ALTER TABLE reviews ADD COLUMN risk_level VARCHAR(50) DEFAULT 'LOW'"))
                    conn.commit()

                # Sync workflow_runs table
                wf_res = conn.execute(text("PRAGMA table_info(workflow_runs)")).fetchall()
                wf_cols = {row[1] for row in wf_res}
                if wf_cols:
                    if "branch_name" not in wf_cols:
                        conn.execute(text("ALTER TABLE workflow_runs ADD COLUMN branch_name VARCHAR(100) DEFAULT 'main'"))
                    if "jobs_data" not in wf_cols:
                        conn.execute(text("ALTER TABLE workflow_runs ADD COLUMN jobs_data JSON"))
                    conn.commit()
            except Exception:
                pass
