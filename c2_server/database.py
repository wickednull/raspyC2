from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./c2.db"

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} # Needed for SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    # This function will be called to create the database tables
    Base.metadata.create_all(bind=engine)
