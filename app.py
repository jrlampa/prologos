import streamlit as st
import pandas as pd
import plotly.express as px
import time
import os
import numpy as np
from dotenv import load_dotenv

# --- IMPORTS DE IA E UTILITÁRIOS ---
from sentence_transformers import SentenceTransformer, util
from pydantic import ValidationError
from pypdf import PdfReader
from sqlalchemy.orm import Session

# --- SEUS MÓDULOS LOCAIS ---
import ingestor_datajud

# Importamos Base e engine para criar o banco se ele não existir
from database_models import SessionLocal, Decisao, Juiz, Tribunal, Base, engine

# Carrega .env (se existir) e expõe GROQ_API_KEY
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

try:
    from groq import Groq
except ImportError:
    Groq = None

# --- INICIALIZAÇÃO DO BANCO (CRÍTICO PARA DEPLOY) ---
# Cria as tabelas vazias se o arquivo .db não existir
Base.metadata.create_all(bind=engine)


# --- FUNÇÕES UTILITÁRIAS (GROQ) ---
def _discover_groq_models(client, prefer_prefixes=("llama3", "llama")):
    """Descobre modelos disponíveis na conta Groq com fallback seguro."""
    try:
        models = []
        # Tenta via SDK
        if hasattr(client, "models") and hasattr(client.models, "list"):
            try:
                resp = client.models.list()
                for m in resp:
                    name = (
                        m.get("name")
                        if isinstance(m, dict)
                        else getattr(m, "name", None)
                    )
                    if name:
                        models.append(name)
            except:
                pass

        # Filtra e ordena
        candidates = [
            m for m in models if any(m.startswith(p) for p in prefer_prefixes)
        ]
        if not candidates and models:
            return models
        return list(set(candidates))
    except:
        return []


# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="PRÓLOGOS | Jurimetria", page_icon="⚖️", layout="wide")


# --- CARREGAMENTO DE DADOS BLINDADO ---
def carregar_dados():
    session = SessionLocal()
    try:
        query = (
            session.query(
                Decisao.numero_processo,
                Decisao.tema,
                Decisao.resultado,
                Decisao.data_decisao,
                Juiz.nome.label("juiz_nome"),
                Juiz.vara,
            )
            .join(Juiz, Decisao.juiz_id == Juiz.id)
            .all()
        )

        # Definição das colunas padrão
        colunas = ["Processo", "Tema", "Resultado/Risco", "Data", "Juiz", "Vara"]

        if not query:
            # Retorna DataFrame vazio MAS com as colunas definidas
            return pd.DataFrame(columns=colunas)

        return pd.DataFrame(query, columns=colunas)

    except Exception as e:
        # Em caso de erro de conexão ou tabela inexistente
        return pd.DataFrame(
            columns=["Processo", "Tema", "Resultado/Risco", "Data", "Juiz", "Vara"]
        )
    finally:
        session.close()


@st.cache_resource
def carregar_modelo_ia():
    return SentenceTransformer("all-MiniLM-L6-v2")


# --- INTERFACE PRINCIPAL ---

st.title("⚖️ PRÓLOGOS")
st.markdown("**Inteligência Jurídica & Previsibilidade**")

# Inicializa estado da sessão para controle do clone
if "juiz_ativo" not in st.session_state:
    st.session_state["juiz_ativo"] = None
if "dossie_ia" not in st.session_state:
    st.session_state["dossie_ia"] = None  # Variável para guardar o perfil do juiz

# --- SIDEBAR: BOTÃO VOLTAR/RESET ---
with st.sidebar:
    st.header("Navegação")
    if st.button("🔄 Voltar / Novo Juiz", type="secondary"):
        st.session_state["juiz_ativo"] = None
        st.session_state["dossie_ia"] = None  # Limpa a memória ao trocar de juiz
        st.rerun()
    st.divider()

# --- ÁREA 1: SETUP E CLONAGEM (INGESTOR) ---
# Só mostra se não tiver juiz ativo
if st.session_state["juiz_ativo"] is None:
    with st.expander(
        "🧬 Clonagem de Perfil (Setup do Juiz)",
        expanded=True,
    ):
        col_input, col_btn = st.columns([3, 1])

        with col_input:
            processo_ref = st.text_input(
                "Processo de Referência (CNJ)",
                placeholder="Ex: 1002345-88.2023.8.26.0100",
                help="Insira um nº de processo que está na vara/juiz que você deseja analisar.",
            )

        with col_btn:
            st.write("")
            st.write("")
            btn_clonar = st.button("🔍 Clonar Juiz", type="primary")

        if btn_clonar and processo_ref:
            # UX: Loading Bonitinho
            with st.status(
                "🚀 Iniciando clonagem estatística...", expanded=True
            ) as status:
                st.write("📡 Conectando ao DataJud...")
                time.sleep(1)

                st.write("📍 Identificando Vara e Competência...")

                # Chama o módulo importado
                resultado = ingestor_datajud.clonar_perfil_juiz(processo_ref)

                if resultado["sucesso"]:
                    st.write(f"✅ Vara localizada: {resultado['juiz_nome']}")
                    st.write("📥 Baixando histórico de sentenças (50 últimos casos)...")

                    # Barra de progresso visual
                    progress_bar = st.progress(0)
                    for i in range(100):
                        time.sleep(0.01)
                        progress_bar.progress(i + 1)

                    status.update(
                        label="✅ Perfil clonado com sucesso!",
                        state="complete",
                        expanded=False,
                    )
                    st.session_state["juiz_ativo"] = resultado["juiz_nome"]
                    st.rerun()
                else:
                    status.update(label="❌ Falha na clonagem", state="error")
                    st.error(resultado["msg"])

# --- CARREGA DADOS (PÓS CLONAGEM) ---
df = carregar_dados()

# Sincroniza filtros com o estado do clone
lista_juizes = ["Todos"] + list(df["Juiz"].unique())
index_juiz = 0

# Se tiver um juiz ativo na sessão, garante que ele está selecionado na lista
if st.session_state["juiz_ativo"] in lista_juizes:
    index_juiz = lista_juizes.index(st.session_state["juiz_ativo"])

# --- TABS DE NAVEGAÇÃO ---
tab1, tab2 = st.tabs(["📊 Dashboard & Dossiê", "📝 Analisador de Petição"])

# ===================================================
# ABA 1: DASHBOARD & DOSSIÊ DO JUIZ
# ===================================================

with tab1:
    st.sidebar.header("🔍 Filtros")
    juiz_selecionado = st.sidebar.selectbox(
        "Juiz Selecionado", lista_juizes, index=index_juiz
    )

    # Se o usuário mudar o selectbox, atualizamos a sessão
    if juiz_selecionado != "Todos":
        st.session_state["juiz_ativo"] = juiz_selecionado

    dados_juiz = (
        df[df["Juiz"] == juiz_selecionado] if juiz_selecionado != "Todos" else df
    )

    # KPIs
    col_kpi1, col_kpi2 = st.columns(2)
    col_kpi1.metric("Volume Analisado", len(dados_juiz))
    col_kpi2.metric("Última Atualização", "Agora")

    # Gráficos
    if not dados_juiz.empty and juiz_selecionado != "Todos":
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            fig = px.pie(dados_juiz, names="Tema", title="Distribuição de Temas")
            st.plotly_chart(fig, use_container_width=True)
        with col_g2:
            st.subheader("Últimas Decisões Coletadas")
            st.dataframe(
                dados_juiz[["Tema", "Resultado/Risco"]].head(10),
                use_container_width=True,
            )

        st.divider()

        # --- NOVA FUNCIONALIDADE: DOSSIÊ DO JUIZ (Tab 1) ---
        st.subheader("🧠 Dossiê Decisório (IA Generativa)")
        st.info(
            "A IA analisará os padrões dos processos coletados para gerar um perfil comportamental detalhado."
        )

        api_key_dash = GROQ_API_KEY
        if not api_key_dash:
            api_key_dash = st.text_input("Groq API Key", type="password", key="k1")

        if st.button("Gerar Dossiê do Magistrado", type="primary"):
            if not api_key_dash:
                st.error("Falta API Key.")
            else:
                try:
                    client = Groq(api_key=api_key_dash)

                    # Prepara contexto
                    lista_txt = ""
                    for i, row in dados_juiz.head(50).iterrows():
                        lista_txt += (
                            f"- Tema '{row['Tema']}', Risco: {row['Resultado/Risco']}\n"
                        )

                    prompt_dossie = f"""
                    ATUE COMO JURIMETRISTA. Crie um Perfil do juiz: {juiz_selecionado}.
                    DADOS: {lista_txt}
                    SAÍDA: Perfil comportamental, principais focos, tendência (rígido/garantista).
                    """

                    modelos = _discover_groq_models(client)
                    mod = modelos[0] if modelos else "llama-3.3-70b-versatile"

                    with st.spinner("Escrevendo Dossiê..."):
                        resp = client.chat.completions.create(
                            messages=[{"role": "user", "content": prompt_dossie}],
                            model=mod,
                            temperature=0.4,
                        )
                        dossie = resp.choices[0].message.content

                        # SALVA NA SESSÃO PARA USAR NA ABA 2
                        st.session_state["dossie_ia"] = dossie
                        st.success("✅ Dossiê gerado e salvo na memória!")
                        st.markdown(dossie)
                except Exception as e:
                    st.error(f"Erro: {e}")

    elif juiz_selecionado == "Todos":
        st.dataframe(dados_juiz.head(10), use_container_width=True)

# === ABA 2: CONSULTOR ===
with tab2:
    if juiz_selecionado == "Todos" or len(dados_juiz) < 5:
        st.warning("🔒 Clone um juiz primeiro.")
        st.info(
            "Para liberar esta aba, clone um Juiz com histórico suficiente (mínimo 5 sentenças) na área de Setup."
        )

        st.markdown(
            """
            <style>
                div[data-testid="stFileUploader"] { pointer-events: none; opacity: 0.5; }
            </style>
        """,
            unsafe_allow_html=True,
        )
        st.file_uploader("Carregar Petição (Bloqueado)", disabled=True)

    else:
        st.header(f"Simulador: {juiz_selecionado}")
        modelo_ia = carregar_modelo_ia()
        temas_juiz = dados_juiz["Tema"].value_counts().head(10).index.tolist()

        # Mostra se temos um dossiê carregado
        if st.session_state.get("dossie_ia"):
            st.info(
                "💡 Dossiê Comportamental carregado da Aba 1. A IA usará essas informações."
            )

        arquivo = st.file_uploader("Sua Petição (PDF)", type="pdf")
        if arquivo:
            leitor = PdfReader(arquivo)
            texto_peticao = "".join([p.extract_text() for p in leitor.pages])[:6000]

            # Vetorização
            with st.spinner("Calculando aderência vetorial..."):
                v_pet = modelo_ia.encode(texto_peticao, convert_to_tensor=True)
                v_juiz = modelo_ia.encode(temas_juiz, convert_to_tensor=True)
                scores = util.cos_sim(v_pet, v_juiz)
                best_score = float(scores.max()) * 100
                tema_match = temas_juiz[np.argmax(scores.cpu().numpy())]

            c1, c2 = st.columns([1, 2])
            c1.metric("Aderência", f"{best_score:.1f}%")
            c2.success(f"Tema Conectado: {tema_match}")

            st.divider()
            st.subheader("Consultor Jurídico IA")

            # 1. Definição da Chave (usa api_key_2)
            api_key_2 = GROQ_API_KEY
            if not api_key_2:
                api_key_2 = st.text_input("Groq API Key", type="password", key="k2")

            if st.button("Gerar Parecer Estratégico", type="primary"):
                # 2. Verificação Corrigida (usa api_key_2)
                if not api_key_2:
                    st.error("Falta API Key.")
                else:
                    try:
                        client = Groq(api_key=api_key_2)

                        # INJEÇÃO DE CONTEXTO (DOSSIÊ DA ABA 1)
                        contexto_extra = ""
                        if st.session_state.get("dossie_ia"):
                            contexto_extra = f"""
                            ⚠️ INFORMAÇÃO PRIVILEGIADA (DOSSIÊ JÁ GERADO):
                            Abaixo está o perfil comportamental deste juiz, gerado previamente.
                            Use-o para refinar suas sugestões:
                            ---
                            {st.session_state['dossie_ia']}
                            ---
                            """

                        prompt_sistema = f"""
                        Você é um Consultor Jurídico Especialista em Processo Civil Brasileiro, de conhecimento jurídico avançado que atua como SIMULADOR DECISÓRIO, utilizando um PERFIL ESTATÍSTICO DE JUIZ previamente definido
                        
                        CONTEXTO:
                        Juiz: {juiz_selecionado}
                        Tema do Processo: {tema_match}
                        - Estilo: Focado em dados estatísticos e jurisprudência consolidada.
                        
                        {contexto_extra}
                        
                        TINSTRUÇÕES:
                        1. LEITURA CRÍTICA DA PETIÇÃO
                        Analise:
                        - Estrutura lógica
                        - Clareza dos pedidos
                        - Qualidade da fundamentação jurídica
                        - Aderência ao perfil decisório do juiz
                        - Uso (ou ausência) das normas e precedentes preferidos pelo juiz

                        2. ANÁLISE SOB A ÓTICA DO JUIZ CLONADO
                        Simule como o juiz estatístico tende a:
                        - Receber os argumentos apresentados
                        - Valorizar ou desconsiderar provas
                        - Enquadrar juridicamente os pedidos
                        - Aplicar normas e precedentes

                        3. PROBABILIDADE ESTATÍSTICA DE DESFECHO
                        Com base nos dados:
                        - Probabilidade estimada de:
                          • Procedência
                          • Parcial procedência
                          • Improcedência
                        - Probabilidade de acolhimento de preliminares
                        - Risco de indeferimento liminar
                        (Use percentuais e justificativas)

                        4. FUNDAMENTAÇÃO PROVÁVEL DA SENTENÇA
                        Liste:
                        - Artigos de lei mais prováveis de serem citados
                        - Jurisprudências estatisticamente inclinadas a serem usadas
                        - Teses que tendem a ser acolhidas
                        - Teses que tendem a ser rejeitadas

                        5. SUGESTÕES DE MELHORIA DA PETIÇÃO
                        Indique:
                        - O que reforçar para alinhar ao perfil do juiz
                        - Argumentos que devem ser reescritos
                        - Jurisprudências mais adequadas para substituir ou incluir
                        - Ajustes de linguagem (ex: mais técnica, mais objetiva, mais principiológica)

                        6. ALERTA ÉTICO
                        Inclua:
                        “Esta análise é uma simulação estatística baseada em padrões decisórios anteriores, não garantindo o resultado do processo.”
                        
                        SAÍDA FINAL:
                        - Diagnóstico jurídico estratégico
                        - Tabela de riscos
                        - Sugestões práticas e acionáveis
                        - Resumo executivo para o advogado
                        
                        PETIÇÃO: {texto_peticao}
                        """

                        # Detecção de modelo
                        modelos_disponiveis = _discover_groq_models(client)
                        mod = (
                            modelos_disponiveis[0]
                            if modelos_disponiveis
                            else "llama-3.3-70b-versatile"
                        )

                        with st.spinner("Simulando julgamento..."):
                            resp = client.chat.completions.create(
                                messages=[{"role": "user", "content": prompt_sistema}],
                                model=mod,
                                temperature=0.3,
                            )
                            st.markdown(resp.choices[0].message.content)
                    except Exception as e:
                        st.error(f"Erro: {e}")
