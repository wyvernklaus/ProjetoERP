import jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from core.modelos import Usuario
from core.config import settings

def criar_token_jwt(username: str) -> str:
    validade = datetime.utcnow() + timedelta(hours=settings.COOKIE_MAX_AGE_HORAS)
    payload = {"sub": username, "exp": validade}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decodificar_token(token: str):
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except Exception:
        return None

def verificar_acesso(aba_requisitada: str, token_cookie: str, db: Session):
    """Retorna o usuário se tiver acesso à aba, senão None."""
    username = decodificar_token(token_cookie)
    if not username:
        return None
    usuario_db = db.query(Usuario).filter(Usuario.usuario == username).first()
    if not usuario_db:
        return None
    abas = usuario_db.abas_permitidas or ""   # ← proteção contra None
    if aba_requisitada not in abas:
        return None
    return usuario_db