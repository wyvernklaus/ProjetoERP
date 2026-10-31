# Crie o arquivo: core/auditoria.py
from sqlalchemy.orm import Session
from core.modelos import LogAuditoria
from fastapi import Request

def registrar_log(db: Session, request: Request, usuario: str, acao: str, detalhes: str, nivel: str = "INFO"):
    # Tenta capturar o IP de quem está acessando (ajuda a achar hackers)
    ip = request.client.host if request and request.client else "IP_OCULTO"
    
    novo_log = LogAuditoria(
        usuario=usuario.upper(),
        acao=acao.upper(),
        detalhes=detalhes,
        ip_origem=ip,
        nivel=nivel.upper()
    )
    db.add(novo_log)
    try:
        db.commit()
    except:
        db.rollback() 