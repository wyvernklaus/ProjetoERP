from fastapi import APIRouter, Request, Depends, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from core.database import get_db
from core.auth import verificar_acesso
from core.modelos import LogAuditoria # <-- Importe o modelo de Logs aqui

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/ti", response_class=HTMLResponse)
async def aba_ti(request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    
    # 🔒 TRAVA DE SERVIDOR: Se tentarem digitar /ti no navegador sem permissão, são chutados pro Dashboard!
    usuario_db = verificar_acesso("manutencao_ti", usuario_logado, db) or verificar_acesso("administracao", usuario_logado, db) or verificar_acesso("gerencia", usuario_logado, db)
    
    if not usuario_db: 
        return RedirectResponse(url="/dashboard", status_code=302)
    
    # Busca os últimos 500 registros de auditoria e segurança
    logs_seguranca = db.query(LogAuditoria).order_by(LogAuditoria.id.desc()).limit(500).all()
    
    return templates.TemplateResponse(
        request=request,  
        name="ti.html", 
        context={"usuario": usuario_db, "logs": logs_seguranca}
    )