import sqlite3
from core.database import engine, Base
from core.modelos import Usuario, FolhaMensal, Notificacao

print("🔄 Iniciando limpeza da tabela de histórico...")

# Deleta apenas a tabela de relatórios corrompida (mantém seus usuários intactos)
conn = sqlite3.connect('banco.db')
conn.execute("DROP TABLE IF EXISTS folhas_mensais")
conn.commit()
conn.close()

# Força o SQLAlchemy a recriar a tabela com as colunas perfeitas
Base.metadata.create_all(bind=engine)
print("✅ Sucesso! A tabela foi reconstruída com o Calendário Inteligente!")