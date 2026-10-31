import sqlite3

# Conecta diretamente no arquivo do banco de dados
conn = sqlite3.connect("erp.db") # Se o seu banco tiver outro nome, mude aqui
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE catalogo_servicos ADD COLUMN escopo_padrao TEXT DEFAULT ''")
    cursor.execute("ALTER TABLE catalogo_servicos ADD COLUMN materiais_estimados TEXT DEFAULT ''")
    print("✅ Banco atualizado com sucesso! Pode fechar e voltar a usar o ERP.")
except Exception as e:
    print("Aviso:", e)

conn.commit()
conn.close()