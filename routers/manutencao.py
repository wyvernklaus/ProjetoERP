from fastapi import APIRouter, Request, Depends, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from core.database import get_db
from core.modelos import Notificacao
from core.auth import verificar_acesso

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/ti", response_class=HTMLResponse)
async def aba_ti(request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    usuario_db = verificar_acesso("manutencao_ti", usuario_logado, db)
    if not usuario_db: return RedirectResponse(url="/dashboard", status_code=302)
    logs_auditoria = db.query(Notificacao).filter(Notificacao.remetente == "SISTEMA").order_by(Notificacao.id.desc()).all()
    return templates.TemplateResponse(request=request, name="ti.html", context={"usuario": usuario_db, "logs": logs_auditoria}) 