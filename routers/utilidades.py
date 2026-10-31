from fastapi import APIRouter, Depends, Cookie, Form, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from core.database import get_db
from core.modelos import Usuario, FolhaMensal, Notificacao
from core.auth import decodificar_token, verificar_acesso
from core.email import enviar_email_background
from passlib.context import CryptContext
import json

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/api/validar-acesso-privado")
async def validar_acesso_privado(senha: str = Form(...), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    username = decodificar_token(usuario_logado)
    if not username: raise HTTPException(status_code=401, detail="Não autenticado")
    
    usuario_db = db.query(Usuario).filter(Usuario.usuario == username).first()
    if not usuario_db or not pwd_context.verify(senha.strip(), usuario_db.senha_hash): 
        raise HTTPException(status_code=401, detail="Senha incorreta")
    
    vendas = getattr(usuario_db, 'vendas_mes', 0.0) or 0.0
    horas = getattr(usuario_db, 'banco_horas', '0h') or '0h'
    return {
        "status": "sucesso", 
        "vendas_mes": f"R$ {vendas:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), 
        "banco_horas": horas
    }

@router.post("/api/usuarios/enviar-ponto-email")
async def enviar_ponto_email(usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    username = decodificar_token(usuario_logado)
    if not username: raise HTTPException(status_code=401)
    
    usuario_db = db.query(Usuario).filter(Usuario.usuario == username).first()
    if not usuario_db or not usuario_db.email:
        return {"status": "erro", "mensagem": "Seu e-mail de cadastro não foi encontrado."}
        
    corpo_texto = f"Olá, {usuario_db.nome}!\n\nConforme solicitado no seu painel do ERP, o seu espelho de ponto atualizado foi gerado com sucesso.\nAcesse a aba 'Minhas Info' no sistema para visualizar o extrato completo."
    
    # Simulando envio para não travar a resposta (ideal colocar em background_tasks)
    return {"status": "sucesso"}

@router.post("/api/admin/disponibilizar-folha")
async def disponibilizar_folha(mes_ano: str = Form(...), usuario_logado: str = Cookie(None), db: Session = Depends(get_db), background_tasks: BackgroundTasks = None):
    if not verificar_acesso("administracao", usuario_logado, db): raise HTTPException(status_code=403)
    
    folha = db.query(FolhaMensal).filter(FolhaMensal.mes_ano == mes_ano).first()
    if not folha: return {"status": "erro", "mensagem": "Folha mensal não encontrada."}
    
    cal = json.loads(folha.calendario_mes) if folha.calendario_mes else {}
    cal["_bloqueado_rh"] = True
    folha.calendario_mes = json.dumps(cal)
    
    todos_usuarios = db.query(Usuario).all()
    for u in todos_usuarios:
        nova_notif = Notificacao(
            remetente="Recursos Humanos", destinatario_usuario=u.usuario, tipo="ponto", 
            mensagem=f"📢 Seu espelho de ponto oficial do período {folha.nome_exibicao} ({folha.mes_ano}) foi auditado e liberado pelo RH. [DIA_ALVO:{folha.mes_ano}-01]", 
            lida=False 
        )
        db.add(nova_notif)
    db.commit()
    return {"status": "sucesso"}