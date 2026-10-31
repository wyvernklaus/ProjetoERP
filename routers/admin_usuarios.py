from fastapi import APIRouter, Request, Depends, Cookie, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List
import jwt
from datetime import datetime, timedelta

from core.database import get_db
from core.modelos import Usuario, LogAuditoria
from core.auth import verificar_acesso, decodificar_token
from core.config import settings
from passlib.context import CryptContext
from core.email import enviar_email_background

router = APIRouter()
templates = Jinja2Templates(directory="templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.get("/funcionarios", response_class=HTMLResponse)
async def aba_funcionarios(request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    usuario_db = verificar_acesso("administracao", usuario_logado, db)
    if not usuario_db: return RedirectResponse(url="/dashboard", status_code=302)
    todos_usuarios = db.query(Usuario).all()
    return templates.TemplateResponse(request=request, name="funcionarios.html", context={"usuario": usuario_db, "lista_usuarios": todos_usuarios})

@router.post("/api/usuarios/novo")
async def criar_novo_usuario(
    nome: str = Form(...), usuario: str = Form(...), senha: str = Form(...), 
    email: str = Form(""), cargo: str = Form(...), 
    abas: List[str] = Form([]), maquinas: List[str] = Form([]),
    usuario_logado: str = Cookie(None), db: Session = Depends(get_db)
):
    if not verificar_acesso("administracao", usuario_logado, db) or db.query(Usuario).filter(Usuario.usuario == usuario.strip()).first(): 
        return RedirectResponse(url="/funcionarios", status_code=302)
    
    novo_func = Usuario(
        nome=nome.strip(), usuario=usuario.strip(), email=email.strip(), 
        senha_hash=pwd_context.hash(senha.strip()), cargo=cargo.strip(), 
        abas_permitidas=",".join(abas), maquinas_permitidas=",".join(maquinas),
        status_colaborador="Ativo"
    )
    db.add(novo_func)
    db.commit()
    return RedirectResponse(url="/funcionarios", status_code=302)

@router.post("/api/usuarios/editar")
async def editar_usuario(
    id_usuario: int = Form(...), nome: str = Form(...), usuario: str = Form(...), 
    email: str = Form(""), cargo: str = Form(...), 
    data_admissao: str = Form(""), status_colaborador: str = Form("Ativo"),
    abas: List[str] = Form([]), maquinas: List[str] = Form([]),
    usuario_logado: str = Cookie(None), db: Session = Depends(get_db)
):
    if not verificar_acesso("administracao", usuario_logado, db): raise HTTPException(status_code=403)
    func_db = db.query(Usuario).filter(Usuario.id == id_usuario).first()
    if func_db:
        func_db.nome = nome.strip()
        func_db.usuario = usuario.strip()
        func_db.email = email.strip()
        func_db.cargo = cargo.strip()
        func_db.data_admissao = data_admissao
        func_db.status_colaborador = status_colaborador
        func_db.abas_permitidas = ",".join(abas)
        func_db.maquinas_permitidas = ",".join(maquinas)
        db.commit()
    return RedirectResponse(url="/funcionarios", status_code=302)

@router.post("/api/usuarios/bloquear")
async def bloquear_usuario(id_usuario: int = Form(...), senha_admin: str = Form(...), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    username_admin = decodificar_token(usuario_logado)
    if not username_admin: raise HTTPException(status_code=401)
    admin_db = db.query(Usuario).filter(Usuario.usuario == username_admin).first()
    if not admin_db or "administracao" not in admin_db.abas_permitidas: raise HTTPException(status_code=403)
    if not pwd_context.verify(senha_admin.strip(), admin_db.senha_hash): return {"status": "erro", "mensagem": "Segurança: Senha do administrador incorreta!"}
    if admin_db.id == id_usuario: return {"status": "erro", "mensagem": "Segurança Máxima: Você não pode bloquear o seu próprio usuário de acesso!"}
        
    func_db = db.query(Usuario).filter(Usuario.id == id_usuario).first()
    if func_db:
        func_db.ativo = not func_db.ativo
        db.commit()
        return {"status": "sucesso", "novo_status": func_db.ativo}
    return {"status": "erro", "mensagem": "Funcionário não encontrado no sistema."}

@router.post("/api/usuarios/excluir")
async def excluir_usuario(id_usuario: int = Form(...), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    if not verificar_acesso("administracao", usuario_logado, db): raise HTTPException(status_code=403)
    func_db = db.query(Usuario).filter(Usuario.id == id_usuario).first()
    if func_db:
        db.delete(func_db)
        db.commit()
        return {"status": "sucesso"}
    return {"status": "erro"}

@router.post("/api/usuarios/solicitar-reset-senha")
async def solicitar_reset_senha(id_usuario: int = Form(...), usuario_logado: str = Cookie(None), db: Session = Depends(get_db), background_tasks: BackgroundTasks = None):
    if not verificar_acesso("administracao", usuario_logado, db): raise HTTPException(status_code=403)
    func_db = db.query(Usuario).filter(Usuario.id == id_usuario).first()
    if func_db and func_db.email:
        token_payload = {"sub": func_db.usuario, "exp": datetime.utcnow() + timedelta(hours=1)}
        segredo_unico = settings.SECRET_KEY + func_db.senha_hash 
        token_reset = jwt.encode(token_payload, segredo_unico, algorithm=settings.ALGORITHM)
        link_seguro = f"{settings.URL_BASE}/recuperar-senha?token={token_reset}"
        corpo_email = f"""<html>... (corpo do e-mail aqui) ...</html>"""
        background_tasks.add_task(enviar_email_background, func_db.email, "ERP: Redefinição de Senha", corpo_email)
        return {"status": "sucesso"}
    return {"status": "erro", "mensagem": "Funcionário sem e-mail corporativo cadastrado."}

@router.post("/api/usuarios/auto-solicitar-reset")
async def auto_solicitar_reset(usuario_logado: str = Cookie(None), db: Session = Depends(get_db), background_tasks: BackgroundTasks = None):
    username = decodificar_token(usuario_logado)
    if not username: raise HTTPException(status_code=401)
    func_db = db.query(Usuario).filter(Usuario.usuario == username).first()
    if func_db and func_db.email:
        token_payload = {"sub": func_db.usuario, "exp": datetime.utcnow() + timedelta(hours=1)}
        segredo_unico = settings.SECRET_KEY + func_db.senha_hash 
        token_reset = jwt.encode(token_payload, segredo_unico, algorithm=settings.ALGORITHM)
        link_seguro = f"{settings.URL_BASE}/recuperar-senha?token={token_reset}"
        corpo_email = f"""<html>... (corpo do e-mail aqui) ...</html>"""
        background_tasks.add_task(enviar_email_background, func_db.email, "ERP: Redefinição de Senha Solicitada", corpo_email)
        return {"status": "sucesso"}
    return {"status": "erro", "mensagem": "E-mail não configurado."}