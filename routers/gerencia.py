from fastapi import APIRouter, Request, Depends, Cookie, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from datetime import datetime
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from core.database import get_db
from core.modelos import Notificacao, OrdemServico
from core.auth import decodificar_token, verificar_acesso

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/gerencia", response_class=HTMLResponse)
async def aba_gerencia(request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    usuario_db = verificar_acesso("gerencia", usuario_logado, db) or verificar_acesso("administracao", usuario_logado, db)
    if not usuario_db: return RedirectResponse(url="/dashboard", status_code=302)
    
    # 🧠 Busca as O.S. que o Comercial gerou e precisam de aprovação
    os_pendentes = db.query(OrdemServico).filter(OrdemServico.status == "Aguardando Gerência").order_by(OrdemServico.id.desc()).all()
    return templates.TemplateResponse(request=request, name="gerencia.html", context={"usuario": usuario_db, "ordens": os_pendentes})

    os_em_andamento = db.query(OrdemServico).filter(OrdemServico.status.notin_(["Aguardando Gerência", "Concluído"])).order_by(OrdemServico.id.desc()).all()

@router.post("/api/gerencia/liberar-os")
async def liberar_os(id_os: int = Form(...), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    username = decodificar_token(usuario_logado)
    os_db = db.query(OrdemServico).filter(OrdemServico.id == id_os).first()
    
    if os_db: 
        # 1. Muda o status para a Produção começar a ver
        os_db.status = "Fila"
        
        # 2. Manda notificação para todos os setores envolvidos na O.S.
        setores = os_db.setores_envolvidos.split(',')
        for setor in setores:
            if setor.strip():
                db.add(Notificacao(
                    remetente="Gerência", destinatario_setor=setor.strip(), tipo="urgente" if os_db.urgente else "setor", 
                    mensagem=f"🟢 LIBERADO: A O.S. #{os_db.numero_os} ({os_db.cliente}) foi aprovada para produção/instalação!", 
                    lida=False
                ))
        db.commit()
    return RedirectResponse(url="/gerencia", status_code=302)
# Procure onde você muda o status para aprovado e adicione:
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
    os_db.detalhes += f"\n<br>🔵 <i>[{agora}]</i> - Aprovada pela Gerência. Liberada para Produção."
    os_db.status = "Fila Produção" # Ou o status que você usa

@router.post("/api/gerencia/enviar-tarefa")
async def enviar_tarefa_setor(setor_destino: str = Form(...), mensagem_tarefa: str = Form(...), urgente: str = Form("nao"), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    username = decodificar_token(usuario_logado)
    db.add(Notificacao(remetente=username, destinatario_setor=setor_destino, tipo="urgente" if urgente == "sim" else "setor", mensagem=f"[{setor_destino.upper()}] {mensagem_tarefa}", lida=False))
    db.commit()
    return RedirectResponse(url="/gerencia", status_code=302)