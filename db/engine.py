"""Database engine and session factory.

Reads DATABASE_URL from the .env file (via python-dotenv).
Adds a short connect timeout for PostgreSQL so the Streamlit app
doesn't hang if Docker isn't running.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://mathforge:mathforge@localhost:5432/mathforge",
)

# Short timeout so the app doesn't block when Postgres is down.
_connect_args: dict = {}
if DATABASE_URL.startswith("postgresql"):
    _connect_args["connect_timeout"] = 3

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine)

