from fastapi import APIRouter, Request, Depends, Cookie, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from core.database import get_db
from core.modelos import ProdutoEstoque, OrdemServico, TarefaDiaria, Usuario
from core.auth import decodificar_token

router = APIRouter(prefix="/resumo-diario", tags=["Briefing"])
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def tela_resumo(request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    # Lê o login direto sem travar por cargo, evitando o loop infinito
    username = decodificar_token(usuario_logado)
    if not username: return RedirectResponse(url="/", status_code=302)
    
    usuario = db.query(Usuario).filter(Usuario.usuario == username).first()
    if not usuario: return RedirectResponse(url="/", status_code=302)
    
    hoje = datetime.now().strftime("%Y-%m-%d")
    
    # 1. Caça Estoque Baixo (Agora vai funcionar porque arrumamos o modelos.py!)
    estoque_alerta = db.query(ProdutoEstoque).filter(ProdutoEstoque.quantidade <= ProdutoEstoque.estoque_minimo).all()
    
    # 2. Caça O.S. paradas ou clientes aguardando
    os_espera = db.query(OrdemServico).filter(OrdemServico.status.in_(["Aguardando Gerência", "Fila"])).all()
    
    # 3. Busca Tarefas do Dia (Criadas manualmente ou pedidos)
    tarefas = db.query(TarefaDiaria).filter(TarefaDiaria.data_criacao == hoje).order_by(TarefaDiaria.concluida.asc()).all()
    
    return templates.TemplateResponse(
        request=request, 
        name="resumo.html", 
        context={
            "usuario": usuario, 
            "estoque_alerta": estoque_alerta, 
            "os_espera": os_espera, 
            "tarefas": tarefas,
            "hoje_formatado": datetime.now().strftime("%d/%m/%Y")
        }
    )

# Rota AJAX para riscar a tarefa na tela
@router.post("/concluir-tarefa/{id_tarefa}")
async def concluir_tarefa(id_tarefa: int, db: Session = Depends(get_db)):
    tarefa = db.query(TarefaDiaria).filter(TarefaDiaria.id == id_tarefa).first()
    if tarefa:
        tarefa.concluida = not tarefa.concluida # Inverte o status (marca/desmarca)
        db.commit()
        return {"status": "sucesso", "estado_atual": tarefa.concluida}
    return {"status": "erro"} 