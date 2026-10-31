from core.database import SessionLocal, engine, Base
from core.modelos import CncMaterial, Maquina

print("📚 Iniciando a leitura do conhecimento dos manuais para o Banco de Dados...")
Base.metadata.create_all(bind=engine)
db = SessionLocal()

# =================================================================
# 1. CADASTRANDO A BIBLIOTECA DE MATERIAIS GERAIS (DOS DOIS MANUAIS)
# =================================================================
materiais_manuais = [
    "Acrílico", "MDF", "ACM", "Alumínio", "Latão", "Madeira Maciça",
    "PVC Expandido", "PS", "Polipropileno", "XPS", "EPS", "Policarbonato",
    "Compensado Comum", "Balsa", "Bambu", "Tecidos", "Couro", "Papelão", "PETG", "EVA"
]

print("📦 Injetando Materiais Base...")
for mat in materiais_manuais:
    # Só adiciona se ainda não existir
    if not db.query(CncMaterial).filter(CncMaterial.nome == mat).first():
        db.add(CncMaterial(nome=mat, espessura_padrao=3.0))

# =================================================================
# 2. CONFIGURANDO A MÁQUINA ROUTER (RMC SONO PLUS)
# =================================================================
router = db.query(Maquina).filter(Maquina.nome.like("%Router%")).first()
if not router:
    router = Maquina(nome="Router CNC RMC", setor="operacional", status="Livre")
    db.add(router)

router.tamanho_util = "Não especificado"
router.materiais_permitidos = "Alumínio, Latão, ACM, Acrílico, MDF, Madeira Maciça, PVC Expandido, PS, Polipropileno, XPS, EPS, Policarbonato"
router.materiais_proibidos = "Vidro, Aço Carbono, Inox, Cerâmica"
# Injetando a base de cálculo de Chipload no painel visual
router.velocidade_corte = """Alumínio/Latão: Chipload 0.05-0.12mm
ACM: Chipload 0.15-0.25mm
Acrílico: Chipload 0.07-0.15mm
MDF/Madeira: Chipload 0.10-0.20mm"""

# =================================================================
# 3. CONFIGURANDO A MÁQUINA LASER (GLC-1290)
# =================================================================
laser = db.query(Maquina).filter(Maquina.nome.like("%Laser%")).first()
if not laser:
    laser = Maquina(nome="Laser GLC 1290", setor="operacional", status="Livre")
    db.add(laser)

laser.tamanho_util = "120 x 90 cm"
laser.materiais_permitidos = "Acrílico, MDF, Compensado Comum, Balsa, Madeira Maciça, Bambu, Tecidos, Couro, Papelão, Papel, Polipropileno, PETG, EVA"
laser.materiais_proibidos = "PVC, Vinil, Teflon, Policarbonato, ABS, Fibra de carbono, Fibra de vidro"
laser.velocidade_corte = "Potência Recomendada: 15% a 80%"

db.commit()
db.close() 
print("✅ Conhecimento industrial injetado com sucesso! Pode abrir o sistema.")