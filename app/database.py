from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Adjust connection pool size and overflow for better concurrency
engine = create_engine(
    DATABASE_URL,
    connect_args={"sslmode": "prefer"},
    pool_size=20,  # Increase pool size for concurrent access
    max_overflow=10,  # Allow overflow for burst loads
    pool_timeout=30,  # Wait time before giving up on a connection
    pool_recycle=1800,  # Recycle connections every 30 minutes
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()