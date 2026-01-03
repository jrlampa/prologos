import sqlite3


def limpar_duplicatas():
    # Conecta ao banco de dados
    conn = sqlite3.connect("prologos_mvp.db")
    cursor = conn.cursor()

    print("🧹 Iniciando limpeza do banco de dados...")

    # 1. Contar quantos registros existem antes
    cursor.execute("SELECT COUNT(*) FROM decisoes")
    total_antes = cursor.fetchone()[0]

    # 2. A MÁGICA: Deletar duplicatas mantendo o ID mais alto (o mais recente)
    # A lógica é: "Apague desta tabela qualquer linha cujo ID NÃO SEJA o ID máximo daquele grupo de numero_processo"
    query_limpeza = """
    DELETE FROM decisoes 
    WHERE id NOT IN (
        SELECT MAX(id) 
        FROM decisoes 
        GROUP BY numero_processo
    );
    """

    cursor.execute(query_limpeza)
    conn.commit()

    # 3. Contar quantos restaram
    cursor.execute("SELECT COUNT(*) FROM decisoes")
    total_depois = cursor.fetchone()[0]

    removidos = total_antes - total_depois

    print(f"✅ Limpeza concluída!")
    print(f"📊 Total Antes: {total_antes}")
    print(f"📉 Total Depois: {total_depois}")
    print(f"🗑️ Lixo Removido: {removidos} processos duplicados.")

    if removidos > 0:
        print("✨ O banco está otimizado. Pode rodar o 'app.py' agora.")
    else:
        print("👍 O banco já estava limpo.")

    conn.close()


if __name__ == "__main__":
    limpar_duplicatas()
