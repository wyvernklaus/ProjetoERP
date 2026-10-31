from fastapi import APIRouter, Request, Depends, Cookie, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from core.database import get_db
from core.auth import verificar_acesso, decodificar_token
from core.modelos import OrdemServico


router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/producao", response_class=HTMLResponse)
async def aba_producao(request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    usuario_db = verificar_acesso("producao", usuario_logado, db)
    if not usuario_db: return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request=request, name="producao.html", context={"usuario": usuario_db})


@router.post("/api/producao/avancar-os")
async def avancar_os_producao(id_os: int = Form(...), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    username = decodificar_token(usuario_logado)
    os_db = db.query(OrdemServico).filter(OrdemServico.id == id_os).first()
    
    if os_db:
        agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
        os_db.status = "Em Instalação" # 👈 Manda direto para o app do carro!
        os_db.detalhes += f"\n<br>📦 <i>[{agora}]</i> - Montagem finalizada na Produção por {username}. Enviado para a frota de Instalação."
        db.commit()
        
    return RedirectResponse(url="/producao", status_code=302) 