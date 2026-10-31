from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./banco.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

# 🔥 ATIVANDO O MODO ALTA PERFORMANCE (WAL) DO SQLITE
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL") # Permite leitura e escrita simultânea
    cursor.execute("PRAGMA synchronous=NORMAL") # Deixa a gravação muito mais rápida
    cursor.execute("PRAGMA temp_store=MEMORY") # Usa a memória RAM para acelerar
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 