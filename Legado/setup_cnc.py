# Arquivo: setup_cnc.py
from core.database import engine, SessionLocal
from core.modelos import CncFresa, CncMaterial, CncParametro

print("⚙️ Injetando novas tabelas da CNC no banco de dados...")
CncFresa.__table__.create(engine, checkfirst=True)
CncMaterial.__table__.create(engine, checkfirst=True)
CncParametro.__table__.create(engine, checkfirst=True)

db = SessionLocal()
# Verifica se os materiais já existem, se não, ele cria!
if not db.query(CncMaterial).first():
    print("📦 Cadastrando materiais base permitidos...")
    db.add_all([
        CncMaterial(nome="Acrílico", espessura_padrao=3.0),
        CncMaterial(nome="MDF", espessura_padrao=15.0),
        CncMaterial(nome="ACM", espessura_padrao=3.0),
        CncMaterial(nome="PVC Expandido", espessura_padrao=10.0),
    ])
    db.commit()
    print("✅ Materiais cadastrados com sucesso!")

db.close()
print("🚀 Tudo pronto! Pode iniciar o seu 'python main.py' novamente.") 