from fastapi import APIRouter, Request, Depends, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from core.database import get_db
from core.modelos import Usuario, FolhaMensal
from core.auth import decodificar_token
import json

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/info", response_class=HTMLResponse)
async def aba_info(request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    username = decodificar_token(usuario_logado)
    if not username: return RedirectResponse(url="/", status_code=302)
    usuario_db = db.query(Usuario).filter(Usuario.usuario == username).first()
    if not usuario_db: return RedirectResponse(url="/", status_code=302)
    
    espelho_dados = None
    ponto_liberado = False
    
    if getattr(usuario_db, 'espelho_ponto', None):
        try: 
            dados = json.loads(usuario_db.espelho_ponto)
            if dados.get("detalhes_dias"):
                primeiro_dia = dados["detalhes_dias"][0].get("data_raw", "")
                if "-" in primeiro_dia:
                    ano_mes = "-".join(primeiro_dia.split("-")[:2])
                    folha = db.query(FolhaMensal).filter(FolhaMensal.mes_ano == ano_mes).first()
                    if folha:
                        cal = json.loads(folha.calendario_mes) if folha.calendario_mes else {}
                        if cal.get("_bloqueado_rh", False):
                            espelho_dados = dados
                            ponto_liberado = True
        except Exception: pass

    if not ponto_liberado:
        usuario_db.espelho_ponto = None
        espelho_dados = None

    return templates.TemplateResponse(request=request, name="info.html", context={"usuario": usuario_db, "espelho": espelho_dados, "is_bloqueado": ponto_liberado})