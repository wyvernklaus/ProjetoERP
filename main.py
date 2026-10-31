import os
import uvicorn
from fastapi import FastAPI, Request, Depends, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from contextlib import asynccontextmanager

from core.database import engine, Base, get_db
from core.modelos import Usuario, OrdemServico, Cliente, ProdutoEstoque, CatalogoServico, Empresa, Notificacao, MovimentacaoEstoque, LogAuditoria, Maquina, LancamentoFinanceiro
from core.auth import decodificar_token, verificar_acesso
from core.config import settings

# Rotas
from routers import auth, admin_usuarios, ponto, comercial, utilidades, producao, operacional, manutencao, financeiro, notificacoes, administracao, info, gerencia, instalacao, estoque, resumo

# =========================================================
# INICIALIZAÇÃO DO BANCO DE DADOS
# =========================================================
def verificar_e_atualizar_banco():
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)

    if inspector.has_table("ordens_servico"):
        col_os = [c['name'] for c in inspector.get_columns('ordens_servico')]
        with engine.begin() as conn:
            if 'servicos' not in col_os: conn.execute(text("ALTER TABLE ordens_servico ADD COLUMN servicos VARCHAR DEFAULT ''"))
            if 'setores_envolvidos' not in col_os: conn.execute(text("ALTER TABLE ordens_servico ADD COLUMN setores_envolvidos VARCHAR DEFAULT ''"))
            if 'materiais_usados' not in col_os: conn.execute(text("ALTER TABLE ordens_servico ADD COLUMN materiais_usados VARCHAR DEFAULT ''"))
            if 'data_entrega' not in col_os: conn.execute(text("ALTER TABLE ordens_servico ADD COLUMN data_entrega VARCHAR DEFAULT ''"))
            if 'anexo' not in col_os: conn.execute(text("ALTER TABLE ordens_servico ADD COLUMN anexo VARCHAR"))
            if 'valor_total' not in col_os: conn.execute(text("ALTER TABLE ordens_servico ADD COLUMN valor_total FLOAT DEFAULT 0.0")) # NOVO

    if inspector.has_table("usuarios"):
        colunas_existentes = [c['name'] for c in inspector.get_columns('usuarios')]
        with engine.begin() as conn:
            if 'banco_horas' not in colunas_existentes: conn.execute(text("ALTER TABLE usuarios ADD COLUMN banco_horas VARCHAR DEFAULT '0h'"))
            if 'vendas_mes' not in colunas_existentes: conn.execute(text("ALTER TABLE usuarios ADD COLUMN vendas_mes FLOAT DEFAULT 0.0"))
            if 'endereco_vt' not in colunas_existentes: conn.execute(text("ALTER TABLE usuarios ADD COLUMN endereco_vt VARCHAR"))
            if 'espelho_ponto' not in colunas_existentes: conn.execute(text("ALTER TABLE usuarios ADD COLUMN espelho_ponto VARCHAR"))
            if 'ferias_inicio' not in colunas_existentes: conn.execute(text("ALTER TABLE usuarios ADD COLUMN ferias_inicio VARCHAR"))
            if 'ferias_fim' not in colunas_existentes: conn.execute(text("ALTER TABLE usuarios ADD COLUMN ferias_fim VARCHAR"))
            if 'data_admissao' not in colunas_existentes: conn.execute(text("ALTER TABLE usuarios ADD COLUMN data_admissao VARCHAR"))
            if 'status_colaborador' not in colunas_existentes: conn.execute(text("ALTER TABLE usuarios ADD COLUMN status_colaborador VARCHAR DEFAULT 'Ativo'"))
            if 'maquinas_permitidas' not in colunas_existentes: conn.execute(text("ALTER TABLE usuarios ADD COLUMN maquinas_permitidas VARCHAR DEFAULT ''"))

    if not inspector.has_table("lancamentos_financeiros"):
        LancamentoFinanceiro.__table__.create(engine)
    if not inspector.has_table("logs_auditoria"): 
        LogAuditoria.__table__.create(engine)
    if not inspector.has_table("movimentacao_estoque"): 
        MovimentacaoEstoque.__table__.create(engine)
    if not inspector.has_table("empresas"): 
        Empresa.__table__.create(engine)
    if not inspector.has_table("catalogo_servicos"): 
        CatalogoServico.__table__.create(engine)
    if not inspector.has_table("maquinas"): 
        Maquina.__table__.create(engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    verificar_e_atualizar_banco()
    yield

app = FastAPI(lifespan=lifespan)

# --- PASTAS DE ARQUIVOS ESTÁTICOS E UPLOADS ---
os.makedirs("uploads/comprovantes_vt", exist_ok=True)
os.makedirs("uploads/os_anexos", exist_ok=True)
os.makedirs("static/js", exist_ok=True)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# =========================================================
# ROTAS GERAIS (Apenas login page e redirecionamento)
# =========================================================
@app.get("/", response_class=HTMLResponse)
async def pagina_login(request: Request): 
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/dashboard")
async def redirecionamento_inteligente(request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    username = decodificar_token(usuario_logado)
    if not username: return RedirectResponse(url="/", status_code=302)
    usuario_db = db.query(Usuario).filter(Usuario.usuario == username).first()
    if not usuario_db: return RedirectResponse(url="/", status_code=302)
    abas = usuario_db.abas_permitidas or ""
    if "gerencia" in abas or "administracao" in abas: return RedirectResponse(url="/visao-macro", status_code=302)
    elif "comercial" in abas: return RedirectResponse(url="/comercial", status_code=302)
    elif "producao" in abas: return RedirectResponse(url="/producao", status_code=302)
    elif "operacional" in abas: return RedirectResponse(url="/operacional", status_code=302)
    else: return RedirectResponse(url="/info", status_code=302)

@app.get("/visao-macro", response_class=HTMLResponse)
async def visao_macro(request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    usuario_db = verificar_acesso("administracao", usuario_logado, db) or verificar_acesso("gerencia", usuario_logado, db)
    if not usuario_db: return RedirectResponse(url="/dashboard", status_code=302)
    dados_macro = {"vendas_mes": 0.00, "vendas_ano": 0.00, "faturamento_mes": 0.00, "faturamento_ano": 0.00, "gastos_mes": 0.00, "gastos_ano": 0.00, "clientes_ativos": 0}
    return templates.TemplateResponse(request=request, name="visao_macro.html", context={"usuario": usuario_db, "macro": dados_macro})

# =========================================================
# LIGAÇÃO DOS MÓDULOS (ROUTERS INTEGRADOS)
# =========================================================
app.include_router(auth.router)
app.include_router(admin_usuarios.router)
app.include_router(ponto.router)
app.include_router(comercial.router)
app.include_router(producao.router)
app.include_router(operacional.router)
app.include_router(manutencao.router)
app.include_router(administracao.router)
app.include_router(info.router)
app.include_router(gerencia.router)
app.include_router(instalacao.router)
app.include_router(estoque.router)
app.include_router(resumo.router)
app.include_router(financeiro.router)
app.include_router(notificacoes.router)
app.include_router(utilidades.router)

if __name__ == "__main__":
    import subprocess
    import time

    print("\n" + "="*60)
    print("🚀 [SERVIDOR ERP] - Inicialização")
    print("="*60)
    os.system('taskkill /F /FI "WINDOWTITLE eq Tunel_ERP*" /T >nul 2>&1')
    time.sleep(1)
    try:
        subprocess.Popen('start "Tunel_ERP" tailscale funnel 1687', shell=True)
        print("✅ [REDE] Janela do Tailscale iniciada com sucesso!")
    except Exception as e:
        print(f"⚠️ [REDE] Aviso: Falha ao acionar Tailscale ({e})")
    uvicorn.run("main:app", host="0.0.0.0", port=1687, reload=True)