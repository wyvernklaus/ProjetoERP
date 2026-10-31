from fastapi import APIRouter, Depends, Cookie, Form, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core.modelos import Notificacao, Usuario
from core.auth import decodificar_token, verificar_acesso
from fastapi.responses import RedirectResponse

router = APIRouter()

@router.get("/api/notificacoes")
async def obter_notificacoes(usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    username = decodificar_token(usuario_logado)
    if not username: return {"notificacoes": []}
    
    usuario_db = db.query(Usuario).filter(Usuario.usuario == username).first()
    if not usuario_db: return {"notificacoes": []}
    
    abas_permitidas = usuario_db.abas_permitidas.split(",") if usuario_db.abas_permitidas else []
    todas_notificacoes = db.query(Notificacao).order_by(Notificacao.id.desc()).limit(50).all()
    lista_notif = []
    
    for n in todas_notificacoes:
        dest_user = n.destinatario_usuario.lower() if n.destinatario_usuario else ""
        dest_setor = n.destinatario_setor.lower() if n.destinatario_setor else ""
        
        if dest_user == username.lower() or dest_setor in abas_permitidas:
            lista_notif.append({
                "id": n.id, "remetente": n.remetente, "tipo": n.tipo, "mensagem": n.mensagem, 
                "anexo": f"/{n.anexo}" if n.anexo else None, "lida": n.lida,
                "acao_pendente": True if n.tipo == "acao" and dest_setor == "administracao" and not n.lida else False 
            })
            
    return {"notificacoes": lista_notif}

@router.post("/api/admin/enviar-tarefa")
async def enviar_tarefa_setor(
    setor_destino: str = Form(...), mensagem_tarefa: str = Form(...), urgente: str = Form("nao"),
    usuario_logado: str = Cookie(None), db: Session = Depends(get_db)
):
    username = decodificar_token(usuario_logado)
    if not username: raise HTTPException(status_code=401)

    tipo_notif = "urgente" if urgente == "sim" else "setor"
    nova_tarefa = Notificacao(
        remetente=username, destinatario_setor=setor_destino, tipo=tipo_notif,
        mensagem=f"[{setor_destino.upper()}] {mensagem_tarefa}", lida=False
    )
    db.add(nova_tarefa)
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)

@router.post("/api/notificacoes/ler")
async def ler_notificacao(id_notificacao: int = Form(...), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    username = decodificar_token(usuario_logado)
    if not username: raise HTTPException(status_code=401)
    
    notif = db.query(Notificacao).filter(Notificacao.id == id_notificacao).first()
    if notif:
        notif.lida = True
        db.commit()
        return {"status": "sucesso"}
    return {"status": "erro"}