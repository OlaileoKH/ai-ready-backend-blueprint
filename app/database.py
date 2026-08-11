from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Define where our database file will live on your computer
DATABASE_URL = "sqlite:///./tasks.db"

# create_engine handles the actual network connection pipeline to the database
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Crucial rule required specifically for SQLite with FastAPI
)

# SessionMaker is a factory class that generates unique transactional session instances
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Modern SQLAlchemy 2.0 Base class that all our future tables will inherit from
class Base(DeclarativeBase):
    pass
