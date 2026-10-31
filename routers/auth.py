from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import jwt
from datetime import datetime, timedelta

from core.database import get_db
from core.modelos import Usuario, LogAuditoria
from core.auth import criar_token_jwt, decodificar_token
from core.auditoria import registrar_log
from core.security import verificar_rate_limit, resetar_rate_limit
from core.config import settings
from passlib.context import CryptContext
from fastapi import Cookie

router = APIRouter()
templates = Jinja2Templates(directory="templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/api/login")
async def processar_login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "desconhecido"
    chave_rate = f"{ip}:{username.strip().lower()}"

    if not verificar_rate_limit(chave_rate):
        registrar_log(db, request, username.strip(), "LOGIN_RATE_LIMIT", "Tentativas excessivas de login.", "CRITICAL")
        return templates.TemplateResponse(request=request, name="login.html", context={"erro": "Muitas tentativas. Aguarde 5 minutos."})

    usuario_db = db.query(Usuario).filter(Usuario.usuario == username.strip()).first()

    if not usuario_db or not pwd_context.verify(password.strip(), usuario_db.senha_hash):
        registrar_log(db, request, username.strip(), "LOGIN_FALHOU", "Tentativa de acesso com senha incorreta ou usuário inexistente.", "CRITICAL")
        return templates.TemplateResponse(request=request, name="login.html", context={"erro": "Usuário ou senha incorretos!"})

    if not usuario_db.ativo:
        registrar_log(db, request, username.strip(), "LOGIN_BLOQUEADO", "Tentativa de login em uma conta desativada.", "WARNING")
        return templates.TemplateResponse(request=request, name="login.html", context={"erro": "Acesso Negado: Conta Desativada. Procure o RH."})

    resetar_rate_limit(chave_rate)
    token_seguro = criar_token_jwt(usuario_db.usuario)
    registrar_log(db, request, username.strip(), "LOGIN_SUCESSO", f"Usuário {usuario_db.nome} entrou no sistema.", "INFO")

    resposta = RedirectResponse(url="/resumo-diario", status_code=302)
    resposta.set_cookie(
        key="usuario_logado",
        value=token_seguro,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="strict",
        max_age=settings.COOKIE_MAX_AGE_HORAS * 3600,
    )
    return resposta

@router.get("/logout")
async def sair():
    resposta = RedirectResponse(url="/", status_code=302)
    resposta.delete_cookie("usuario_logado")
    return resposta

@router.get("/recuperar-senha", response_class=HTMLResponse)
async def tela_recuperar_senha(request: Request, token: str = "", db: Session = Depends(get_db)):
    try:
        payload_unverified = jwt.decode(token, options={"verify_signature": False})
        usuario = payload_unverified.get("sub")
        func_db = db.query(Usuario).filter(Usuario.usuario == usuario).first()
        if not func_db: raise Exception()
        
        segredo_unico = settings.SECRET_KEY + func_db.senha_hash
        jwt.decode(token, segredo_unico, algorithms=[settings.ALGORITHM])
        return templates.TemplateResponse(request=request, name="recuperar_senha.html", context={"usuario": usuario, "token": token})
    except:
        return HTMLResponse("<html><body style='background:#000; color:#ef4444; font-family:sans-serif; display:flex; align-items:center; justify-content:center; height:100vh;'><div style='background:#111827; padding:40px; border-radius:12px; border:1px solid #374151; text-align:center;'><h2>❌ Link Inválido ou Expirado</h2><p style='color:#9ca3af;'>Este link já foi utilizado ou passou do tempo limite de segurança.</p></div></body></html>")

@router.post("/api/usuarios/executar-reset")
async def executar_reset(token: str = Form(...), nova_senha: str = Form(...), db: Session = Depends(get_db)):
    try:
        payload_unverified = jwt.decode(token, options={"verify_signature": False})
        usuario = payload_unverified.get("sub")
        func_db = db.query(Usuario).filter(Usuario.usuario == usuario).first()
        if not func_db: raise Exception()
        
        segredo_unico = settings.SECRET_KEY + func_db.senha_hash
        jwt.decode(token, segredo_unico, algorithms=[settings.ALGORITHM])
        
        func_db.senha_hash = pwd_context.hash(nova_senha.strip())
        db.commit()
        return HTMLResponse("<html><body style='background:#000; color:#10b981; font-family:sans-serif; display:flex; align-items:center; justify-content:center; height:100vh;'><div style='background:#111827; padding:40px; border-radius:12px; border:1px solid #065f46; text-align:center;'><h2>✅ Senha atualizada com sucesso!</h2><p style='color:#9ca3af;'>Seu acesso está seguro. Você já pode fechar esta tela e fazer login no ERP.</p></div></body></html>")
    except:
        return HTMLResponse("<html><body style='background:#000; color:#ef4444; font-family:sans-serif; display:flex; align-items:center; justify-content:center; height:100vh;'><div style='background:#111827; padding:40px; border-radius:12px; border:1px solid #374151; text-align:center;'><h2>❌ Falha de Segurança</h2><p style='color:#9ca3af;'>A autenticação falhou. Tente solicitar um novo link.</p></div></body></html>")