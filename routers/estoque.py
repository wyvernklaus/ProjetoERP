from fastapi import APIRouter, Request, Form, Depends, Cookie, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from core.database import get_db
from core.modelos import ProdutoEstoque, MovimentacaoEstoque
from core.auth import verificar_acesso
import datetime

router = APIRouter(prefix="/administracao/estoque", tags=["Estoque Admin"])
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def painel_estoque(request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    usuario = verificar_acesso("administracao", usuario_logado, db)
    if not usuario: return RedirectResponse(url="/dashboard", status_code=302)
    
    # Busca produtos e as últimas movimentações
    produtos = db.query(ProdutoEstoque).all()
    movimentacoes = db.query(MovimentacaoEstoque).order_by(MovimentacaoEstoque.id.desc()).limit(100).all()
    
    return templates.TemplateResponse(request=request, name="estoque.html", context={"usuario": usuario, "produtos": produtos, "movimentacoes": movimentacoes})

@router.post("/entrada")
async def registrar_entrada_estoque(
    produto_id: int = Form(...),
    quantidade: float = Form(...),
    novo_custo: float = Form(0.0),
    espessura: str = Form(""),
    tamanho: str = Form(""),
    usuario_logado: str = Cookie(None),
    db: Session = Depends(get_db)
):
    usuario = verificar_acesso("administracao", usuario_logado, db)
    if not usuario: raise HTTPException(status_code=403)
    
    produto = db.query(ProdutoEstoque).filter(ProdutoEstoque.id == produto_id).first()
    if produto:
        produto.quantidade += quantidade
        if novo_custo > 0: produto.custo_unitario = novo_custo
        
        if espessura: produto.espessura = espessura
        if tamanho: produto.tamanho = tamanho
        
        produto.ultima_compra = datetime.datetime.utcnow()
        
        nova_movimentacao = MovimentacaoEstoque(
            produto_id=produto.id,
            nome_produto=produto.nome,
            tipo_movimento="ENTRADA",
            quantidade_movimentada=quantidade,
            usuario_responsavel=usuario.nome,
            os_referencia="COMPRA / ABASTECIMENTO"
        )
        db.add(nova_movimentacao)
        db.commit()
    return RedirectResponse(url="/administracao/estoque/", status_code=302)

@router.post("/novo")
async def registrar_novo_insumo(
    nome: str = Form(...),
    espessura: str = Form(""),
    tamanho: str = Form(""),
    quantidade: float = Form(0.0),
    estoque_minimo: float = Form(1.0),
    unidade: str = Form("un"),
    custo_unitario: float = Form(0.0),
    setores_alvo: str = Form("geral"),
    usuario_logado: str = Cookie(None),
    db: Session = Depends(get_db)
):
    usuario = verificar_acesso("administracao", usuario_logado, db)
    if not usuario: raise HTTPException(status_code=403)
    
    novo_produto = ProdutoEstoque(
        nome=nome.strip(),
        espessura=espessura.strip(),
        tamanho=tamanho.strip(),
        quantidade=quantidade,
        estoque_minimo=estoque_minimo,
        unidade=unidade.strip(),
        custo_unitario=custo_unitario,
        setores_alvo=setores_alvo.strip()
    )
    db.add(novo_produto)
    db.commit()
    
    return RedirectResponse(url="/administracao/estoque/", status_code=302) 