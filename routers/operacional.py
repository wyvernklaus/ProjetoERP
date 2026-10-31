import re
import subprocess
from fastapi import APIRouter, Request, Depends, Cookie, Form, HTTPException,Body
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from core.database import get_db
from datetime import datetime
from core.auth import verificar_acesso, decodificar_token
from core.modelos import Notificacao, OrdemServico, ProdutoEstoque, CatalogoServico, Maquina, CncFresa, CncMaterial, CncParametro

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/operacional", response_class=HTMLResponse)
async def aba_operacional(request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    usuario_db = verificar_acesso("operacional", usuario_logado, db)
    if not usuario_db: return RedirectResponse(url="/dashboard", status_code=302)
    
    # 1. Puxa O.S. Ativas e Concluídas
    os_ativas = db.query(OrdemServico).filter(
        OrdemServico.status.in_(["Fila", "Em Andamento"]),
        OrdemServico.setores_envolvidos.contains("operacional")
    ).order_by(OrdemServico.urgente.desc(), OrdemServico.id.asc()).all()
    
    os_entregues = db.query(OrdemServico).filter(
        OrdemServico.status == "Concluido",
        OrdemServico.setores_envolvidos.contains("operacional")
    ).order_by(OrdemServico.id.desc()).limit(20).all()
    
    # 2. Puxa Insumos e Máquinas (Usado nas abas gerais)
    insumos = db.query(ProdutoEstoque).order_by(ProdutoEstoque.nome).all()
    maquinas = db.query(Maquina).all() # Puxando todas para o Mini-CAM também funcionar
    
    # 3. 🧠 BUSCANDO DADOS PARA O MINI-CAM DA CNC
    fresas_cnc = db.query(CncFresa).all()
    materiais_cnc = db.query(CncMaterial).all()

    # UM ÚNICO RETURN PARA MANDAR TUDO PRA TELA!
    return templates.TemplateResponse(request=request, name="operacional.html", context={
        "usuario": usuario_db, 
        "os_ativas": os_ativas, 
        "os_entregues": os_entregues, 
        "insumos": insumos,
        "maquinas": maquinas,
        "fresas": fresas_cnc,
        "materiais_cnc": materiais_cnc
    })
# =================================================================
# NOVA ROTA: CADASTRAR FRESAS
# =================================================================
@router.post("/api/operacional/nova-fresa")
async def criar_fresa(nome: str = Form(...), diametro: float = Form(...), max_stepdown: float = Form(...), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    if not verificar_acesso("operacional", usuario_logado, db): raise HTTPException(status_code=403)
    nova_fresa = CncFresa(nome=nome.strip(), diametro=diametro, max_stepdown=max_stepdown)
    db.add(nova_fresa)
    db.commit()
    return RedirectResponse(url="/operacional", status_code=302)
# =================================================================
# ROTA: EXCLUIR FRESA DA BIBLIOTECA
# =================================================================
@router.post("/api/operacional/excluir-fresa")
async def excluir_fresa(id_fresa: int = Form(...), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    if not verificar_acesso("operacional", usuario_logado, db): raise HTTPException(status_code=403)
    fresa = db.query(CncFresa).filter(CncFresa.id == id_fresa).first()
    if fresa:
        db.delete(fresa)
        db.commit()
    return RedirectResponse(url="/operacional", status_code=302)

# 🔄 ATUALIZAR STATUS DA O.S.
@router.post("/api/operacional/atualizar-os")
async def atualizar_os(id_os: int = Form(...), acao: str = Form(...), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    usuario_db = verificar_acesso("operacional", usuario_logado, db)
    if not usuario_db: raise HTTPException(status_code=403)
    username = usuario_db.usuario
    os_db = db.query(OrdemServico).filter(OrdemServico.id == id_os).first()
    
    if os_db:
        agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
        
        if acao == "iniciar":
            os_db.status = "Em Andamento"
            os_db.detalhes += f"\n<br>▶️ <i>[{agora}]</i> - Usinagem/Impressão iniciada no Operacional por {username}."
        elif acao == "concluir":
            os_db.status = "Em Instalação" # 👈 Agora o Operacional também manda para a RUA!
            os_db.detalhes += f"\n<br>✅ <i>[{agora}]</i> - Peças prontas. Finalizado por {username} e enviado p/ Instalação."
            
        db.commit()
    return RedirectResponse(url="/operacional", status_code=302)

# 🚨 BOTÃO DE PÂNICO: AVISAR COMPRAS SOBRE INSUMO 
@router.post("/api/operacional/alerta-estoque")
async def alerta_estoque(nome_insumo: str = Form(...), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    usuario_db = verificar_acesso("operacional", usuario_logado, db)
    if not usuario_db: raise HTTPException(status_code=403)
    username = usuario_db.usuario
    db.add(Notificacao(
        remetente=f"{username} (Operacional)", destinatario_setor="administracao", tipo="urgente",
        mensagem=f"🚨 ALERTA DE MÁQUINA: O insumo '{nome_insumo}' está zerado ou em falta na fábrica. Por favor, providenciar compra urgente!",
        lida=False
    ))
    db.commit()
    return RedirectResponse(url="/operacional", status_code=302)

# ➕ ADICIONAR NOVO INSUMO NO ESTOQUE
@router.post("/api/operacional/novo-insumo")
async def novo_insumo(nome: str = Form(...), quantidade: float = Form(0), unidade: str = Form("un"), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    if not verificar_acesso("operacional", usuario_logado, db): raise HTTPException(status_code=403)
    db.add(ProdutoEstoque(nome=nome.strip(), quantidade=quantidade, unidade=unidade))
    db.commit()
    return RedirectResponse(url="/operacional", status_code=302)

# ➕ ADICIONAR NOVO SERVIÇO AO CATÁLOGO (COMERCIAL)
@router.post("/api/operacional/novo-servico")
async def novo_servico(nome: str = Form(...), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    if not verificar_acesso("operacional", usuario_logado, db): raise HTTPException(status_code=403)
    db.add(CatalogoServico(nome=nome.strip(), setores="operacional", terceirizado=False))
    db.commit()
    return RedirectResponse(url="/operacional", status_code=302)
# ➕ ADICIONAR NOVA MÁQUINA
# ➕ ADICIONAR NOVA MÁQUINA (AGORA COM FICHA TÉCNICA)
# 🧠 ROBÔ CONVERSOR: Transforma mm/s, m/min, etc em Metros por Hora (Mt/H)
def converter_para_mth(texto: str) -> str:
    if not texto: return ""
    padrao = r'(\d+(?:[.,]\d+)?)\s*(mt/min|m/min|mt/s|m/s|cm/min|cm/s|mm/s|mm/min)'
    
    def substituir(match):
        valor = float(match.group(1).replace(',', '.'))
        unidade = match.group(2).lower()
        
        # A matemática da conversão para Mt/H
        if unidade in ['mt/min', 'm/min']: novo_valor = valor * 60
        elif unidade in ['mt/s', 'm/s']: novo_valor = valor * 3600
        elif unidade in ['cm/min']: novo_valor = valor * 0.6
        elif unidade in ['cm/s']: novo_valor = valor * 36
        elif unidade in ['mm/s']: novo_valor = valor * 3.6
        elif unidade in ['mm/min']: novo_valor = valor * 0.06
        else: return match.group(0)
            
        return f"{novo_valor:g} Mt/H" # Formata limpo, sem zeros sobrando
        
    return re.sub(padrao, substituir, texto, flags=re.IGNORECASE)

# ➕ ADICIONAR NOVA MÁQUINA (COM CONVERSÃO AUTOMÁTICA DE MATEMÁTICA)
@router.post("/api/operacional/nova-maquina")
async def nova_maquina(
    nome: str = Form(...), status: str = Form("Livre"), tamanho_util: str = Form(""),
    materiais_permitidos: str = Form(""), materiais_proibidos: str = Form(""),
    velocidade_corte: str = Form(""), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)
):
    if not verificar_acesso("operacional", usuario_logado, db): raise HTTPException(status_code=403)
    # Passa o texto pelo Robô antes de salvar no banco
    velocidade_padronizada = converter_para_mth(velocidade_corte.strip())
    
    db.add(Maquina(
        nome=nome.strip(), setor="operacional", status=status,
        tamanho_util=tamanho_util.strip(), materiais_permitidos=materiais_permitidos.strip(),
        materiais_proibidos=materiais_proibidos.strip(), velocidade_corte=velocidade_padronizada
    ))
    db.commit()
    return RedirectResponse(url="/operacional", status_code=302)

# 🤖 ROTA IoT: ONDE AS MÁQUINAS (ONYX / PRODUCTION MANAGER) ENVIAM O STATUS SOZINHAS
@router.post("/api/maquinas/webhook")
async def webhook_maquinas(payload: dict = Body(...), db: Session = Depends(get_db)):
    """
    Formato esperado: {"nome": "HP Latex 360", "status": "Operando", "arquivo": "lona_fachada.pdf"}
    """
    nome_maq = payload.get("nome")
    status_maq = payload.get("status")
    arquivo = payload.get("arquivo", "")
    
    maquina = db.query(Maquina).filter(Maquina.nome == nome_maq).first()
    if maquina:
        maquina.status = status_maq
        maquina.arquivo_atual = arquivo
        db.commit()
    return {"mensagem": "Recebido"}

# ✋ ROTA MANUAL: PARA A ROUTER DDCS 3.1 OU MÁQUINAS OFFLINE
@router.post("/api/operacional/atualizar-maquina")
async def atualizar_maquina_manual(id_maquina: int = Form(...), status: str = Form(...), arquivo: str = Form(""), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    if not verificar_acesso("operacional", usuario_logado, db): raise HTTPException(status_code=403)
    maquina = db.query(Maquina).filter(Maquina.id == id_maquina).first()
    if maquina:
        maquina.status = status
        maquina.arquivo_atual = arquivo.strip()
        db.commit()
    return RedirectResponse(url="/operacional", status_code=302)
# ✏️ EDITAR MÁQUINA EXISTENTE (COM RE-CÁLCULO DE VELOCIDADE)
@router.post("/api/operacional/editar-maquina")
async def editar_maquina(
    id_maquina: int = Form(...), nome: str = Form(...), status: str = Form(...),
    tamanho_util: str = Form(""), materiais_permitidos: str = Form(""),
    materiais_proibidos: str = Form(""), velocidade_corte: str = Form(""), 
    usuario_logado: str = Cookie(None), db: Session = Depends(get_db)
):
    if not verificar_acesso("operacional", usuario_logado, db): raise HTTPException(status_code=403)
    maquina = db.query(Maquina).filter(Maquina.id == id_maquina).first()
    if maquina:
        maquina.nome = nome.strip()
        maquina.status = status
        maquina.tamanho_util = tamanho_util.strip()
        maquina.materiais_permitidos = materiais_permitidos.strip()
        maquina.materiais_proibidos = materiais_proibidos.strip()
        
        # Se a velocidade foi alterada, passa pelo robô conversor de Mt/H de novo
        maquina.velocidade_corte = converter_para_mth(velocidade_corte.strip())
        db.commit()
        
    return RedirectResponse(url="/operacional", status_code=302)

import os
import shutil
from fastapi import UploadFile, File

# Garante que a pasta de arquivos da CNC existe
os.makedirs("uploads/cnc_arquivos", exist_ok=True)

# Garante que a pasta existe
os.makedirs("uploads/cnc_arquivos", exist_ok=True)

@router.post("/api/operacional/processar-cnc")
async def processar_arquivo_cnc(
    id_os: int = Form(...),
    id_maquina: int = Form(...),
    id_material: int = Form(...),
    id_fresa: int = Form(...),
    espessura: float = Form(...),
    arquivo_vetor: UploadFile = File(...),
    usuario_logado: str = Cookie(None),
    db: Session = Depends(get_db)
):
    if not verificar_acesso("operacional", usuario_logado, db): raise HTTPException(status_code=403)
    # 1. Valida se a extensão é permitida
    extensao = arquivo_vetor.filename.split('.')[-1].lower()
    if extensao not in ['dxf', 'svg', 'cdr']:
        return {"status": "erro", "mensagem": "Formato inválido! Envie apenas .DXF, .SVG ou .CDR"}
    
    nome_base = f"OS_{id_os}_revisado"
    caminho_final = f"uploads/cnc_arquivos/{nome_base}.{extensao}"
    
    # 2. Salva o arquivo temporariamente (seja SVG, DXF ou CDR)
    with open(caminho_final, "wb+") as buffer:
        shutil.copyfileobj(arquivo_vetor.file, buffer)

    extensao_final = extensao

    # 3. 🪄 A MÁGICA DA CONVERSÃO: Se for CDR, transforma em SVG
    if extensao == 'cdr':
        caminho_svg = f"uploads/cnc_arquivos/{nome_base}.svg"
        try:
            # Chama o Inkscape invisível no Windows para converter
            subprocess.run([
                "inkscape", 
                caminho_final, 
                "--export-type=svg", 
                f"--export-filename={caminho_svg}"
            ], check=True)
            
            # Apaga o arquivo .CDR pesado para não lotar o HD, mantendo só o SVG leve
            os.remove(caminho_final) 
            extensao_final = "svg"
            caminho_final = caminho_svg
            print(f"✅ Conversão de CDR para SVG feita com sucesso: {caminho_svg}")
        except Exception as e:
            print(f"Erro na conversão: {e}")
            # Se não conseguir converter, vai manter o CDR original por segurança
            
    # 4. Atualiza a O.S. avisando que está pronto
    os_db = db.query(OrdemServico).filter(OrdemServico.id == id_os).first()
    if os_db:
        os_db.detalhes = f"{os_db.detalhes}\n\n[CNC PREPARADA]: Vetor processado ({extensao_final.upper()}) - Espessura: {espessura}mm."
        db.commit()
    
    return RedirectResponse(url="/operacional", status_code=302)