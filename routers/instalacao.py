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

# A PARTIR DAQUI COMEÇAM AS ROTAS REAIS (que devem ser mantidas):
@router.get("/instalacao", response_class=HTMLResponse)
async def aba_instalacao(request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    usuario_db = verificar_acesso("instalacao", usuario_logado, db) or verificar_acesso("gerencia", usuario_logado, db)
    if not usuario_db: return RedirectResponse(url="/resumo-diario", status_code=302)
    
    # Apenas O.S. que foram enviadas para Instalação
    ordens = db.query(OrdemServico).filter(OrdemServico.status == "Em Instalação").order_by(OrdemServico.urgente.desc(), OrdemServico.data_entrega.asc()).all()
    
    return templates.TemplateResponse(request=request, name="instalacao.html", context={"usuario": usuario_db, "ordens": ordens})


@router.get("/instalacao", response_class=HTMLResponse)
async def aba_instalacao(request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    usuario_db = verificar_acesso("instalacao", usuario_logado, db) or verificar_acesso("gerencia", usuario_logado, db)
    if not usuario_db: return RedirectResponse(url="/resumo-diario", status_code=302)
    
    # Apenas O.S. que foram enviadas para Instalação
    ordens = db.query(OrdemServico).filter(OrdemServico.status == "Em Instalação").order_by(OrdemServico.urgente.desc(), OrdemServico.data_entrega.asc()).all()
    
    return templates.TemplateResponse(request=request, name="instalacao.html", context={"usuario": usuario_db, "ordens": ordens})

@router.post("/api/instalacao/concluir")
async def concluir_instalacao(
    id_os: int = Form(...), 
    nome_recebedor: str = Form(...),
    documento_recebedor: str = Form(...),
    assinatura_base64: str = Form(""), # O código do desenho vem aqui
    usuario_logado: str = Cookie(None), 
    db: Session = Depends(get_db)
):
    username = decodificar_token(usuario_logado)
    os_db = db.query(OrdemServico).filter(OrdemServico.id == id_os).first()
    
    if os_db:
        agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
        os_db.status = "Concluído"
        
        # 1. Monta o Comprovante de Assinatura (Fica na área pública)
        bloco_assinatura = ""
        if assinatura_base64:
            bloco_assinatura = f"""
            <br><br>
            <div style="background:white; color:black; padding:10px; border-radius:8px; margin-top:10px; max-width:300px; border:2px solid #000; text-align:center;">
                <p style="font-size:10px; color:#333; font-weight:bold; margin-bottom:5px;">COMPROVANTE OFICIAL DE ENTREGA</p>
                <img src="{assinatura_base64}" style="width:100%; max-height:100px; object-fit:contain; border-bottom:1px dashed #999; padding-bottom:5px;">
                <p style="margin:5px 0 0 0; font-weight:bold; text-transform:uppercase; font-size:12px;">{nome_recebedor.strip()}</p>
                <p style="margin:0; font-size:10px; color:#555;">DOC: {documento_recebedor.strip()}</p>
                <p style="margin:0; font-size:8px; color:#999;">Registado eletronicamente em: {agora}</p>
            </div>
            """
        
        # 2. O Segredo: Injeta a assinatura ANTES do histórico oculto
        marcador = "<br><hr><br><b>📍 HISTÓRICO DE RASTREIO:</b>"
        if marcador in os_db.detalhes:
            partes = os_db.detalhes.split(marcador)
            os_db.detalhes = partes[0] + bloco_assinatura + marcador + partes[1]
        else:
            os_db.detalhes += bloco_assinatura
            
        # 3. Adiciona o log de encerramento no final da área oculta
        os_db.detalhes += f"\n<br>🏁 <i>[{agora}]</i> - Instalação finalizada e O.S. Encerrada."
        db.commit()
        
    return RedirectResponse(url="/instalacao", status_code=302)