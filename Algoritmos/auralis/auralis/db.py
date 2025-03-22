# auralis/db.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

# Cadena de conexión para MySQL
DATABASE_URL = f"mysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(
    DATABASE_URL,
    pool_size=5,         # Ajusta según tu carga
    max_overflow=10,     # Conexiones extra
    echo=False           # True para debug
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session():
    """Retorna una sesión de base de datos usando SQLAlchemy."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
