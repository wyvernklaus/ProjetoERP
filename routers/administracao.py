from fastapi import APIRouter, Request, Depends, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from core.database import get_db
from core.modelos import Usuario
from core.auth import verificar_acesso, decodificar_token
from core.modelos import LogAuditoria

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/administracao", response_class=HTMLResponse)
async def aba_administracao(request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    usuario_db = verificar_acesso("administracao", usuario_logado, db)
    if not usuario_db: return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request=request, name="administracao.html", context={"usuario": usuario_db})

# Rotas de Placeholders das outras abas (para não poluir o main)
@router.get("/pedidos-compra", response_class=HTMLResponse)
async def aba_pedidos_compra(request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    if not verificar_acesso("administracao", usuario_logado, db): return RedirectResponse(url="/dashboard", status_code=302)
    return HTMLResponse("<html><body style='background:#111827;color:#fff;padding:40px;'><h2>📦 Pedidos de Compra</h2><a href='/administracao' style='color:#3b82f6;'>Voltar</a></body></html>")

@router.get("/estoque", response_class=HTMLResponse)
async def aba_estoque(request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    if not verificar_acesso("administracao", usuario_logado, db): return RedirectResponse(url="/dashboard", status_code=302)
    return HTMLResponse("<html><body style='background:#111827;color:#fff;padding:40px;'><h2>📦 Estoque</h2><a href='/administracao' style='color:#3b82f6;'>Voltar</a></body></html>")

@router.get("/ordem-servico", response_class=HTMLResponse)
async def aba_ordem_servico(request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    if not verificar_acesso("administracao", usuario_logado, db): return RedirectResponse(url="/dashboard", status_code=302)
    return HTMLResponse("<html><body style='background:#111827;color:#fff;padding:40px;'><h2>🛠️ Ordens de Serviço</h2><a href='/administracao' style='color:#3b82f6;'>Voltar</a></body></html>")

@router.get("/administracao/auditoria", response_class=HTMLResponse)
async def painel_auditoria(request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    # Restrito a Administração / TI
    usuario_db = verificar_acesso("administracao", usuario_logado, db)
    if not usuario_db: return RedirectResponse(url="/dashboard", status_code=302)
    
    # Pega os últimos 300 movimentos do sistema
    logs = db.query(LogAuditoria).order_by(LogAuditoria.id.desc()).limit(300).all() 
    
    return templates.TemplateResponse(request=request, name="auditoria.html", context={"usuario": usuario_db, "logs": logs}) 