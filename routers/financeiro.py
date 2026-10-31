from fastapi import APIRouter, Request, Depends, Cookie, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from core.database import get_db
from core.modelos import LancamentoFinanceiro
from core.auth import verificar_acesso, decodificar_token
from datetime import datetime
import json

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/financeiro", response_class=HTMLResponse)
async def painel_financeiro(request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    usuario_db = verificar_acesso("administracao", usuario_logado, db) or verificar_acesso("gerencia", usuario_logado, db)
    if not usuario_db: return RedirectResponse(url="/dashboard", status_code=302)
    
    lancamentos = db.query(LancamentoFinanceiro).order_by(LancamentoFinanceiro.id.desc()).all()
    
    # Cálculos simples para os cards do topo
    total_receber = sum(l.valor for l in lancamentos if l.tipo == "RECEITA" and l.status == "Pendente")
    total_pagar = sum(l.valor for l in lancamentos if l.tipo == "DESPESA" and l.status == "Pendente")
    recebido_mes = sum(l.valor for l in lancamentos if l.tipo == "RECEITA" and l.status == "Pago")
    pago_mes = sum(l.valor for l in lancamentos if l.tipo == "DESPESA" and l.status == "Pago")
    
    saldo = recebido_mes - pago_mes

    return templates.TemplateResponse(request=request, name="financeiro.html", context={
        "usuario": usuario_db, 
        "lancamentos": lancamentos,
        "total_receber": total_receber,
        "total_pagar": total_pagar,
        "saldo": saldo
    })

@router.post("/api/financeiro/novo")
async def criar_lancamento(
    tipo: str = Form(...), descricao: str = Form(...), valor: float = Form(...),
    categoria: str = Form("Geral"), data_vencimento: str = Form(...),
    usuario_logado: str = Cookie(None), db: Session = Depends(get_db)
):
    username = decodificar_token(usuario_logado)
    if not username: raise HTTPException(status_code=401)
    
    novo = LancamentoFinanceiro(
        tipo=tipo, descricao=descricao.strip(), valor=valor,
        categoria=categoria.strip(), data_vencimento=data_vencimento,
        criado_por=username
    )
    db.add(novo)
    db.commit()
    return RedirectResponse(url="/financeiro", status_code=302)

@router.post("/api/financeiro/baixar")
async def baixar_lancamento(id_lancamento: int = Form(...), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    if not decodificar_token(usuario_logado): raise HTTPException(status_code=401)
    
    lanc = db.query(LancamentoFinanceiro).filter(LancamentoFinanceiro.id == id_lancamento).first()
    if lanc:
        lanc.status = "Pago"
        lanc.data_pagamento = datetime.now().strftime("%Y-%m-%d")
        db.commit()
    return RedirectResponse(url="/financeiro", status_code=302)