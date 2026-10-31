from fastapi import APIRouter, Request, Depends, Cookie, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from core.database import get_db
from core.auth import verificar_acesso, decodificar_token
from core.modelos import Notificacao, OrdemServico, Cliente, CatalogoServico, ProdutoEstoque, Empresa
from typing import List
import os
import json
import shutil
from core.modelos import LancamentoFinanceiro
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/comercial", response_class=HTMLResponse)
async def aba_comercial(request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    usuario_db = verificar_acesso("comercial", usuario_logado, db)
    if not usuario_db: return RedirectResponse(url="/dashboard", status_code=302)
    
    empresas_db = db.query(Empresa).order_by(Empresa.nome_fantasia).all()
    clientes_db = db.query(Cliente).order_by(Cliente.nome).all()
    
    empresas_map = {e.id: e.nome_fantasia for e in empresas_db}
    clientes_formatados = []
    for c in clientes_db:
        emp_nome = empresas_map.get(c.empresa_id, "Particular / Avulso") if c.empresa_id else "Particular / Avulso"
        clientes_formatados.append({"id": c.id, "nome": c.nome, "empresa_id": c.empresa_id, "empresa": emp_nome, "setor": c.setor_unidade, "endereco": c.endereco_padrao, "telefone": c.telefone})
    
    catalogo = db.query(CatalogoServico).order_by(CatalogoServico.nome).all()
    catalogo_js = json.dumps([{"nome": c.nome, "setores": c.setores} for c in catalogo])
    
    estoque = db.query(ProdutoEstoque).order_by(ProdutoEstoque.nome).all()
    os_andamento = db.query(OrdemServico).filter(OrdemServico.status != "Concluido").order_by(OrdemServico.id.desc()).all()
    
    return templates.TemplateResponse(request=request, name="comercial.html", context={
        "usuario": usuario_db, "empresas": empresas_db, "clientes_formatados": clientes_formatados, 
        "catalogo": catalogo, "catalogo_js": catalogo_js, "estoque": estoque, "os_andamento": os_andamento
    })

@router.post("/api/comercial/novo-cliente")
async def criar_cliente(empresa_id: int = Form(0), nome: str = Form(...), setor_unidade: str = Form(""), telefone: str = Form(""), endereco: str = Form(""), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    emp_id_salvar = empresa_id if empresa_id > 0 else None
    db.add(Cliente(empresa_id=emp_id_salvar, nome=nome.strip(), setor_unidade=setor_unidade.strip(), telefone=telefone.strip(), endereco_padrao=endereco.strip()))
    db.commit()
    return RedirectResponse(url="/comercial", status_code=302)

@router.post("/api/comercial/editar-cliente")
async def editar_cliente(id_cliente: int = Form(...), empresa_id: int = Form(0), nome: str = Form(...), setor_unidade: str = Form(""), telefone: str = Form(""), endereco: str = Form(""), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    cli = db.query(Cliente).filter(Cliente.id == id_cliente).first()
    if cli:
        cli.empresa_id = empresa_id if empresa_id > 0 else None
        cli.nome = nome.strip(); cli.setor_unidade = setor_unidade.strip(); cli.telefone = telefone.strip(); cli.endereco_padrao = endereco.strip()
        db.commit()
    return RedirectResponse(url="/comercial", status_code=302)

@router.post("/api/comercial/excluir-cliente")
async def excluir_cliente(id_cliente: int = Form(...), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    cli = db.query(Cliente).filter(Cliente.id == id_cliente).first()
    if cli: db.delete(cli); db.commit()
    return RedirectResponse(url="/comercial", status_code=302)

@router.post("/api/comercial/nova-empresa")
async def criar_empresa(nome_fantasia: str = Form(...), cnpj: str = Form(""), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    db.add(Empresa(nome_fantasia=nome_fantasia.strip(), cnpj=cnpj.strip()))
    db.commit(); return RedirectResponse(url="/comercial", status_code=302)

from core.modelos import OrdemServico, CatalogoServico # Importe o CatalogoServico!

@router.post("/api/comercial/nova-os")
async def criar_os(
    cliente: str = Form(...),
    empresa: str = Form(""),
    endereco: str = Form(""),
    detalhes: str = Form(...),
    urgente: bool = Form(False),
    valor_total: float = Form(0.0),
    
    # NOVOS CAMPOS DO CÉREBRO:
    salvar_padrao: str = Form("false"),
    nome_padrao: str = Form(""),
    setores_padrao: str = Form(""),
    materiais_padrao: str = Form(""),
    
    usuario_logado: str = Cookie(None),
    db: Session = Depends(get_db)
):
    username = decodificar_token(usuario_logado)
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
    
    # 🧠 PARTE 1: O SISTEMA APRENDENDO O PADRÃO NOVO
    if salvar_padrao == "true" and nome_padrao:
        # Verifica se já não existe um padrão com esse nome
        padrao_existente = db.query(CatalogoServico).filter(CatalogoServico.nome == nome_padrao).first()
        if not padrao_existente:
            novo_servico = CatalogoServico(
                nome=nome_padrao.strip(),
                setores=setores_padrao,
                escopo_padrao=detalhes.strip(), # Salva a receita de bolo!
                materiais_estimados=materiais_padrao.strip() # Salva a lista de compras!
            )
            db.add(novo_servico)
            # Nota: Isso vai pro banco e na próxima vez você pode puxar no Javascript!
            
    # 📄 PARTE 2: CRIANDO A O.S. NORMALMENTE
    detalhes_formatados = detalhes.strip()
    detalhes_formatados += f"\n<br><hr><br><b>📍 HISTÓRICO DE RASTREIO:</b>"
    detalhes_formatados += f"\n<br>🟢 <i>[{agora}]</i> - O.S. Emitida pelo Comercial ({username})."

    nova_os = OrdemServico(
        cliente=cliente.strip(),
        empresa=empresa.strip(),
        endereco=endereco.strip(),
        detalhes=detalhes_formatados,
        status="Aguardando Gerência",
        urgente=urgente,
        valor_total=valor_total, # <--- SALVANDO NA O.S.
        criado_por=username
    )
    db.add(nova_os)
    
    # db.flush() serve para o banco gerar o ID da O.S. antes do commit final
    db.flush() 

    # MÁGICA FINANCEIRA: Se tiver valor, cria a conta a receber automaticamente
    if valor_total > 0:
        vencimento_padrao = datetime.now().strftime("%Y-%m-%d") # Pode ajustar para + 30 dias se quiser
        
        novo_lancamento = LancamentoFinanceiro(
            tipo="RECEITA",
            descricao=f"O.S. #{nova_os.numero_os} - {cliente.strip()}",
            valor=valor_total,
            categoria="Vendas de Serviço",
            data_vencimento=vencimento_padrao,
            status="Pendente",
            os_referencia=nova_os.numero_os,
            criado_por=username
        )
        db.add(novo_lancamento)

    db.commit()
    
    return RedirectResponse(url="/comercial", status_code=302)

@router.get("/os/{id_os}/imprimir", response_class=HTMLResponse)
async def imprimir_os(id_os: int, request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    os_db = db.query(OrdemServico).filter(OrdemServico.id == id_os).first()
    return templates.TemplateResponse(request=request, name="os_impressao.html", context={"os": os_db})

@router.post("/api/comercial/editar-os")
async def editar_os(id_os: int = Form(...), detalhes_add: str = Form(...), tempo_estimado: str = Form(...), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    os_db = db.query(OrdemServico).filter(OrdemServico.id == id_os).first()
    if os_db:
        if detalhes_add.strip(): os_db.detalhes = f"{os_db.detalhes}\n\n[ATUALIZADO]: {detalhes_add.strip()}"
        if tempo_estimado.strip(): os_db.tempo_estimado = tempo_estimado.strip()
        db.commit()
    return RedirectResponse(url="/comercial", status_code=302)

@router.post("/api/comercial/excluir-os")
async def excluir_os(id_os: int = Form(...), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    os_db = db.query(OrdemServico).filter(OrdemServico.id == id_os).first()
    if os_db: db.delete(os_db); db.commit()
    return RedirectResponse(url="/comercial", status_code=302)

@router.post("/api/comercial/verificar-estoque")
async def verificar_estoque_digitado(texto: str = Form(""), db: Session = Depends(get_db)):
    estoque = db.query(ProdutoEstoque).all()
    faltantes = [item.nome for item in estoque if item.nome.lower() in texto.lower() and item.quantidade <= 0]
    return {"faltantes": faltantes}

@router.post("/api/comercial/novo-servico-padrao")
async def criar_servico_padrao(nome: str = Form(...), setores: List[str] = Form([]), terceirizado: str = Form("nao"), db: Session = Depends(get_db)):
    db.add(CatalogoServico(nome=nome.strip(), setores="terceirizado" if terceirizado == "sim" else ",".join(setores), terceirizado=(terceirizado == "sim")))
    db.commit()
    return RedirectResponse(url="/comercial", status_code=302)

@router.post("/api/comercial/ajax-novo-cliente")
async def criar_cliente_ajax(
    empresa_id: int = Form(0),
    nome: str = Form(...),
    setor_unidade: str = Form(""),
    telefone: str = Form(""),
    endereco: str = Form(""),
    empresa_nome: str = Form(""),
    db: Session = Depends(get_db)
):
    emp_id_salvar = empresa_id if empresa_id > 0 else None
    novo_cli = Cliente(empresa_id=emp_id_salvar, nome=nome.strip(), setor_unidade=setor_unidade.strip(), telefone=telefone.strip(), endereco_padrao=endereco.strip())
    db.add(novo_cli)
    db.commit()
    db.refresh(novo_cli)
    
    emp_nome = "Particular / Avulso"
    if emp_id_salvar:
        emp = db.query(Empresa).filter(Empresa.id == emp_id_salvar).first()
        if emp: emp_nome = emp.nome_fantasia
        
    return JSONResponse(content={
        "status": "sucesso",
        "cliente": {"id": novo_cli.id, "nome": novo_cli.nome, "empresa_id": emp_id_salvar or 0, "empresa": emp_nome, "setor": novo_cli.setor_unidade, "endereco": novo_cli.endereco_padrao, "telefone": novo_cli.telefone}
    })
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
    texto_formatado += f"\n<br><hr><br><b>📍 HISTÓRICO DE RASTREIO:</b>" 
    texto_formatado += f"\n<br>🟢 <i>[{agora}]</i> - O.S. Emitida pelo Comercial." 

@router.get("/historico-geral", response_class=HTMLResponse)
async def historico_geral(request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    # Trava: Só Comercial, Gerência ou Adm podem entrar aqui
    usuario_db = verificar_acesso("comercial", usuario_logado, db) or verificar_acesso("gerencia", usuario_logado, db) or verificar_acesso("administracao", usuario_logado, db)
    if not usuario_db: return RedirectResponse(url="/resumo-diario", status_code=302)
    
    # Puxa as últimas 150 O.S. de toda a empresa
    ordens = db.query(OrdemServico).order_by(OrdemServico.id.desc()).limit(150).all()
    return templates.TemplateResponse(request=request, name="historico.html", context={"usuario": usuario_db, "ordens": ordens})