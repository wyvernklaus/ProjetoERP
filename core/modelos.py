from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
import datetime
from core.database import Base



class Usuario(Base):
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    usuario = Column(String, unique=True)
    email = Column(String)
    senha_hash = Column(String)
    cargo = Column(String)
    ativo = Column(Boolean, default=True)
    abas_permitidas = Column(String)
    
    # ---------------------------------------------------------
    # COLUNA NOVA: Permissões Específicas de Trabalhos / Máquinas
    # ---------------------------------------------------------
    maquinas_permitidas = Column(String, default="")
    
    banco_horas = Column(String, default="0h")
    vendas_mes = Column(Float, default=0.0)
    endereco_vt = Column(String, nullable=True)
    espelho_ponto = Column(String, nullable=True)
    
    data_admissao = Column(String, nullable=True)
    status_colaborador = Column(String, default="Ativo")
    ferias_inicio = Column(String, nullable=True)
    ferias_fim = Column(String, nullable=True)

class FolhaMensal(Base):
    __tablename__ = "folhas_mensais"
    
    id = Column(Integer, primary_key=True, index=True)
    mes_ano = Column(String, unique=True)
    nome_exibicao = Column(String)
    dados_consolidados = Column(String)
    dias_uteis = Column(Integer, default=0) 
    calendario_mes = Column(String, default="{}")
    arquivo_bruto = Column(String, default="")
    
    # --- ESTAS DUAS LINHAS FALTAVAM PARA O PYTHON LER OS DADOS ---
    edicoes_manuais = Column(String, default="{}")
    excecoes_individuais = Column(String, default="{}")
    
    data_importacao = Column(DateTime, default=datetime.datetime.utcnow)

class Notificacao(Base):
    __tablename__ = "notificacoes"
    
    id = Column(Integer, primary_key=True, index=True)
    remetente = Column(String)
    destinatario_setor = Column(String, nullable=True)
    destinatario_usuario = Column(String, nullable=True)
    tipo = Column(String)
    mensagem = Column(String)
    anexo = Column(String, nullable=True)
    lida = Column(Boolean, default=False)
    data_criacao = Column(DateTime, default=datetime.datetime.utcnow)


class Empresa(Base):
    __tablename__ = "empresas"
    
    id = Column(Integer, primary_key=True, index=True)
    nome_fantasia = Column(String)
    cnpj = Column(String, default="")
    data_cadastro = Column(DateTime, default=datetime.datetime.utcnow)

class Cliente(Base):
    __tablename__ = "clientes"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, nullable=True) # Conecta à tabela Empresas
    nome = Column(String) # Ex: João (Comprador)
    
    # ----------------------------------------------------
    # NOVO CAMPO: Setor / Unidade da filial
    # ----------------------------------------------------
    setor_unidade = Column(String, default="") 
    
    telefone = Column(String, default="")
    endereco_padrao = Column(String, default="")
    data_cadastro = Column(DateTime, default=datetime.datetime.utcnow)

class ProdutoEstoque(Base):
    __tablename__ = "estoque"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    quantidade = Column(Float, default=0.0)
    unidade = Column(String, default="un") 
    tamanho = Column(String, default="N/A")
    espessura = Column(String, default="N/A")
    
    # 🚨 ESTAS ERAM AS COLUNAS QUE ESTAVAM FALTANDO E CAUSANDO O ERRO 500
    estoque_minimo = Column(Float, default=1.0)
    custo_unitario = Column(Float, default=0.0)
    setores_alvo = Column(String, default="geral")
    localizacao_fisica = Column(String, default="")
    ultima_compra = Column(DateTime)
    
class MovimentacaoEstoque(Base):
    __tablename__ = "movimentacao_estoque"
    id = Column(Integer, primary_key=True, index=True)
    produto_id = Column(Integer)
    nome_produto = Column(String)
    tipo_movimento = Column(String) 
    quantidade_movimentada = Column(Float)
    usuario_responsavel = Column(String)
    os_referencia = Column(String, nullable=True) 
    data_movimento = Column(DateTime, default=datetime.datetime.utcnow)

class Maquina(Base): 
    __tablename__ = "maquinas"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    setor = Column(String) 
    status = Column(String, default="Livre") 
    arquivo_atual = Column(String, default="")
    
    tamanho_util = Column(String, default="")
    materiais_permitidos = Column(String, default="")
    materiais_proibidos = Column(String, default="")
    velocidade_corte = Column(String, default="")

class CatalogoServico(Base):
    __tablename__ = "catalogo_servicos"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), unique=True)
    setores = Column(String(200)) # Ex: "operacional,producao"
    terceirizado = Column(Boolean, default=False)
    
    # 🧠 NOVOS CAMPOS PARA O CÉREBRO DO ERP:
    escopo_padrao = Column(Text, default="") # O texto com as instruções da fábrica
    materiais_estimados = Column(Text, default="") # Ex: "1 chapa de acrílico, 50 leds..."

class OrdemServico(Base):
    __tablename__ = "ordens_servico"
    
    id = Column(Integer, primary_key=True, index=True)
    numero_os = Column(String, unique=True)
    empresa = Column(String, default="")
    cliente = Column(String)
    valor_total = Column(Float, default=0.0)
    endereco = Column(String, default="")
    
    data_entrega = Column(String, default="") 
    
    status = Column(String, default="Pendente")
    criado_por = Column(String)
    data_criacao = Column(DateTime, default=datetime.datetime.utcnow)
    
    # NOVOS CAMPOS MULTI-SETORIAIS
    servicos = Column(String, default="")
    setores_envolvidos = Column(String, default="")
    materiais_usados = Column(String, default="")
    
    detalhes = Column(String)
    tempo_estimado = Column(String, default="")
    urgente = Column(Boolean, default=False)
    anexo = Column(String, nullable=True)

class CncFresa(Base):
    __tablename__ = "cnc_fresas"
    id = Column(Integer, primary_key=True, index=True)

    nome = Column(String)            # Ex: "Metal Duro 1 Corte" ou "Reta 2 Cortes"
    diametro = Column(Float)         # Ex: 3.0 (mm)
    max_stepdown = Column(Float)     # Ex: 5.0 (Máximo que essa fresa aguenta descer por vez)

class CncMaterial(Base):
    __tablename__ = "cnc_materiais"
    id = Column(Integer, primary_key=True, index=True)

    nome = Column(String)            # Ex: "Acrílico Cast", "MDF", "ACM"
    espessura_padrao = Column(Float) # Ex: 3.0, 5.0, 15.0 (mm)

class CncParametro(Base):
    __tablename__ = "cnc_parametros_corte"
    id = Column(Integer, primary_key=True, index=True)
    
    # Fazemos a ligação lógica
    id_fresa = Column(Integer)
    id_material = Column(Integer)
    
    # --- O SEU MANUAL DE INTELIGÊNCIA ENTRA AQUI ---
    
    # 1. Movimento Z (Descida)
    passada_z = Column(Float)        # O famoso Stepdown. Ex: 2.5mm por passada
    plunge_rate = Column(Integer)    # Velocidade da descida no material (mm/min)
    
    # 2. Movimento X/Y (Corte)
    feedrate_reta = Column(Integer)  # Avanço para vetores longos e retos (mm/min)
    feedrate_curva = Column(Integer) # Avanço reduzido para letras pequenas e curvas (mm/min)
    
    # 3. Spindle
    spindle_rpm = Column(Integer)    # Rotação do motor (Ex: 18000, 24000)
    sentido_corte = Column(String, default="Discordante") # "Discordante" (Padrão) ou "Concordante" (Bom p/ Acrílico)

class TarefaDiaria(Base):

    __tablename__ = "tarefas_diarias"

    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String)
    setor_alvo = Column(String, default="geral")
    concluida = Column(Boolean, default=False)
    data_criacao = Column(String)

class LogAuditoria(Base):
    __tablename__ = "logs_auditoria"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario = Column(String, default="DESCONHECIDO")
    acao = Column(String)
    detalhes = Column(String)
    ip_origem = Column(String, default="0.0.0.0")
    nivel = Column(String, default="INFO") # INFO, WARNING, CRITICAL
    data_hora = Column(DateTime, default=datetime.datetime.utcnow)

class LancamentoFinanceiro(Base):
    __tablename__ = "lancamentos_financeiros"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String) # "RECEITA" (o que a empresa ganha) ou "DESPESA" (o que ela paga)
    descricao = Column(String)
    valor = Column(Float)
    categoria = Column(String, default="Geral")
    data_vencimento = Column(String) # Formato YYYY-MM-DD
    data_pagamento = Column(String, nullable=True) # Preenchido quando a conta for paga/recebida
    status = Column(String, default="Pendente") # "Pendente" ou "Pago"
    os_referencia = Column(String, nullable=True) # Guarda o nº da O.S. se o lançamento veio de lá
    criado_por = Column(String)
    data_criacao = Column(DateTime, default=datetime.datetime.utcnow)