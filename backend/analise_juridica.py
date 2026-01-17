from sqlalchemy.orm import Session
from database_models import SessionLocal, Decisao

# 1. O Teu "Dicionário Jurídico" (Taxonomia Própria)
# Aqui definimos as regras. Se o texto conter X, a categoria é Y.
# Isso é o embrião da tua IA.

REGRA_CLASSIFICACAO = {
    "consumidor": [
        "banco",
        "telefonia",
        "indemnização",
        "danos morais",
        "consumidor",
        "aérea",
    ],
    "trabalhista": ["horas extras", "rescisão", "trabalho", "vínculo"],
    "tributario": ["imposto", "taxa", "execução fiscal", "icms"],
    "civil": ["contrato", "posse", "família", "sucessões"],
}

REGRA_RISCO = {
    "alto": ["tutela", "liminar", "urgência", "crime"],
    "medio": ["indenização", "cobranca", "monitória"],
    "baixo": ["homologação", "administrativo"],
}


def normalizar_processos():
    session = SessionLocal()

    # Busca todas as decisões que ainda não foram analisadas (ou todas para reprocessar)
    decisoes = session.query(Decisao).all()

    print(f"🧠 Iniciando análise jurídica de {len(decisoes)} processos...")

    for decisao in decisoes:
        texto_analise = (str(decisao.tema) + " " + str(decisao.texto_decisao)).lower()

        # 1. Identificar Área do Direito
        area_detectada = "Outros"
        for area, palavras_chave in REGRA_CLASSIFICACAO.items():
            if any(palavra in texto_analise for palavra in palavras_chave):
                area_detectada = area.upper()
                break  # Para na primeira correspondência

        # 2. Identificar Complexidade/Risco
        risco_detectado = "Indefinido"
        for nivel, palavras_chave in REGRA_RISCO.items():
            if any(palavra in texto_analise for palavra in palavras_chave):
                risco_detectado = nivel.upper()
                break

        # 3. Atualizar o registro no Banco (Simulando o resultado normalizado)
        # Aqui, estamos a usar o campo 'resultado' para guardar essa etiqueta temporariamente
        # No futuro, criaremos colunas específicas.

        etiqueta_final = f"[{area_detectada}] Risco: {risco_detectado}"

        # Só atualiza se for diferente para poupar processamento
        if decisao.resultado != etiqueta_final:
            decisao.resultado = etiqueta_final
            print(
                f"Processo {decisao.numero_processo} -> Classificado como: {etiqueta_final}"
            )

    session.commit()
    session.close()
    print("✅ Normalização Jurídica concluída!")


if __name__ == "__main__":
    normalizar_processos()
