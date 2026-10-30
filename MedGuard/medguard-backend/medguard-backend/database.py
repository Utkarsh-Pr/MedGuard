"""
database.py
------------
Sets up the connection to PostgreSQL using SQLAlchemy.

This file is imported by models.py (to get Base) and main.py
(to get the DB session for each request). You should not need
to change anything here for the demo — just set DATABASE_URL
correctly in your .env file.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load variables from the .env file into the environment
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Copy .env.example to .env and fill in "
        "your PostgreSQL username/password."
    )

# The "engine" is SQLAlchemy's connection to the actual database.
engine = create_engine(DATABASE_URL)

# SessionLocal is a factory that creates a new database session
# whenever we need to talk to the database (one per API request).
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is the parent class that all our ORM models (in models.py) inherit
# from. SQLAlchemy uses it to know which Python classes map to which
# database tables.
Base = declarative_base()


def get_db():
    """
    FastAPI dependency that provides a database session to a path
    function and makes sure it's closed afterwards, even if an
    error happens. Used like: `db: Session = Depends(get_db)`.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
