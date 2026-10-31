import sqlite3
conn = sqlite3.connect('banco.db')
cursor = conn.cursor()
try:
    cursor.execute("ALTER TABLE estoque ADD COLUMN tamanho VARCHAR DEFAULT 'N/A'")
    cursor.execute("ALTER TABLE estoque ADD COLUMN espessura VARCHAR DEFAULT 'N/A'")
    conn.commit()
    print("✅ Campos Tamanho e Espessura adicionados com sucesso!")
except Exception as e:
    print("⚠️ As colunas já parecem existir:", e)
conn.close() 