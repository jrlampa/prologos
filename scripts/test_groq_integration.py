import os
from dotenv import load_dotenv

load_dotenv()

from pypdf import PdfReader
from sentence_transformers import SentenceTransformer, util
import numpy as np

# Try to import DB models; if unavailable, we'll use fallback themes
try:
    from database_models import SessionLocal, Decisao, Juiz
except Exception:
    SessionLocal = None
    Decisao = None
    Juiz = None

# Groq client
try:
    from groq import Groq
except Exception:
    Groq = None


def _discover_groq_models(client, prefer_prefixes=("llama3", "llama")):
    """Discover candidate models via the Groq client; return empty list on failure.

    If SDK listing doesn't work, attempts a direct request to the Groq REST endpoint
    (https://api.groq.com/v1/models) using the GROQ_API_KEY environment variable.
    """
    try:
        models = []
        # Try SDK listing
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
            except Exception:
                pass
        elif hasattr(client, "list_models"):
            try:
                resp = client.list_models()
                for m in resp:
                    name = (
                        m.get("name")
                        if isinstance(m, dict)
                        else getattr(m, "name", None)
                    )
                    if name:
                        models.append(name)
            except Exception:
                pass

        # Try REST endpoint if SDK didn't return models
        if not models:
            try:
                import json
                import urllib.request
                import urllib.error

                api_key = GROQ_API_KEY or os.getenv("GROQ_API_KEY")
                if api_key:
                    url = "https://api.groq.com/v1/models"
                    req = urllib.request.Request(
                        url, headers={"Authorization": f"Bearer {api_key}"}
                    )
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = json.load(resp)
                        candidates_list = None
                        if isinstance(data, dict):
                            candidates_list = (
                                data.get("data") or data.get("models") or data
                            )
                        elif isinstance(data, list):
                            candidates_list = data

                        if candidates_list:
                            for m in candidates_list:
                                if isinstance(m, dict):
                                    name = m.get("name")
                                else:
                                    name = getattr(m, "name", None)
                                if name:
                                    models.append(name)
            except Exception:
                pass

        candidates = [
            m for m in models if any(m.startswith(p) for p in prefer_prefixes)
        ]

        def _score(name):
            s = 0
            if "13" in name:
                s += 10
            if "8192" in name:
                s += 5
            if "8b" in name:
                s += 3
            return s

        candidates = sorted(set(candidates), key=_score, reverse=True)
        return list(candidates)
    except Exception:
        return []


def _verify_candidate_models(client, candidate_models, probe_message=None):
    results = []
    probe_system = "You are a short-response verifier. Reply with 'ok'."
    probe_user = "Ping"
    for m in candidate_models:
        try:
            resp = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": probe_system},
                    {"role": "user", "content": probe_user},
                ],
                model=m,
                temperature=0.0,
                max_tokens=1,
            )
            results.append({"model": m, "ok": True, "error": None})
        except Exception as exc:
            msg = str(exc)
            lm = msg.lower()
            if "decommission" in lm or "model_decommissioned" in lm:
                err_type = "decommissioned"
            elif "not found" in lm or "model_not_found" in lm or "does not exist" in lm:
                err_type = "not_found"
            elif "unauthor" in lm or "401" in lm or "forbidden" in lm or "403" in lm:
                err_type = "unauthorized"
            else:
                err_type = "other"
            results.append({"model": m, "ok": False, "error": f"{err_type}: {msg}"})
    return results


# Load model
modelo_ia = SentenceTransformer("all-MiniLM-L6-v2")

# Read PDF
pdf_path = os.path.join(os.path.dirname(__file__), "..", "peticao_teste.pdf")
pdf_path = os.path.abspath(pdf_path)
print("PDF path:", pdf_path)
reader = PdfReader(pdf_path)
texto = ""
for p in reader.pages:
    t = p.extract_text()
    if t:
        texto += t + "\n"

texto_analise = texto[:5000]
print("Texto extraído (preview):", texto_analise[:300].replace("\n", " "), "...")

# Get a judge and their top themes from DB (use fallback if DB unavailable)
if SessionLocal is not None:
    session = SessionLocal()
    juiz = session.query(Juiz).first()
    if juiz:
        juiz_nome = juiz.nome
        temas = [
            row[0]
            for row in session.query(Decisao.tema)
            .filter(Decisao.juiz_id == juiz.id)
            .limit(10)
            .all()
        ]
        temas = [t for t in temas if t]
    else:
        juiz_nome = "Juiz de Teste"
        temas = []
    session.close()
else:
    juiz_nome = "Juiz de Teste"
    temas = []

if not temas:
    temas = ["Responsabilidade Civil", "Direito do Consumidor", "Dano Moral"]

print("Juiz escolhido:", juiz_nome)
print("Temas do juiz (top):", temas[:5])

# Embeddings
vetor_pet = modelo_ia.encode(texto_analise, convert_to_tensor=True)
vetor_tem = modelo_ia.encode(temas[:5], convert_to_tensor=True)
scores = util.cos_sim(vetor_pet, vetor_tem)
score_maximo = float(scores.max()) * 100
tema_match = temas[:5][np.argmax(scores.cpu().numpy())]
score_final = min(100, score_maximo * 1.5) if score_maximo > 15 else score_maximo

print(f"Score semântico: {score_final:.2f}/100 (tema: {tema_match})")

# Prepare prompt (reuse the exact prompt from app.py)
prompt_sistema = f"""
Você é um Consultor Jurídico Especialista em Processo Civil Brasileiro, de conhecimento jurídico avançado que atua como SIMULADOR DECISÓRIO, utilizando um PERFIL ESTATÍSTICO DE JUIZ previamente definido.

PERFIL DO JUIZ:
- Nome: {juiz_nome}
- Tema Predileto/Recorrente: {tema_match}
- Estilo: Focado em dados estatísticos e jurisprudência consolidada.

INSTRUÇÕES:
1. LEITURA CRÍTICA DA PETIÇÃO
Analise:
- Estrutura lógica
- Clareza dos pedidos
- Qualidade da fundamentação jurídica
- Aderência ao perfil decisório do juiz
- Uso (ou ausência) das normas e precedentes preferidos pelo juiz

2. ENTREGA
Forneça:
- 1 Ponto Forte (máx 1 frase)
- 1 Ponto Fraco (máx 1 frase)
- Reescrita de um parágrafo da fundamentação (máx 3-6 frases)
- 1 Súmula do STJ/STF que sirva como precedente aplicável
"""

# Groq call
api_key = os.getenv("GROQ_API_KEY")
if Groq is None:
    print("Groq package not available. Skipping LLM call.")
elif not api_key:
    print("GROQ_API_KEY not found in environment. Skipping LLM call.")
else:
    client = Groq(api_key=api_key)
    print("Calling Groq...")
    messages = [
        {"role": "system", "content": prompt_sistema},
        {"role": "user", "content": f"Texto da Petição:\n{texto_analise}"},
    ]

    # Discover candidate models (or fallback to static list)
    discovered = _discover_groq_models(client)
    if discovered:
        print("Discovered models:", discovered[:10])
        candidate_models = discovered
    else:
        candidate_models = [
            "llama3-8b-8192",
            "llama3-8b",
            "llama3-13b-8192",
            "llama3-13b",
        ]

    # Verify candidates and print diagnostics
    print("\nVerification:")
    verification = _verify_candidate_models(client, candidate_models)
    for r in verification:
        print(f" - {r['model']}: {'OK' if r['ok'] else r['error']}")

    if not any(r["ok"] for r in verification):
        print("Warning: no candidate models passed verification; see details above.")

    last_exc = None
    for model_name in candidate_models:
        try:
            print(f"Trying model: {model_name}")
            chat_completion = client.chat.completions.create(
                messages=messages,
                model=model_name,
                temperature=0.5,
            )
            resposta = chat_completion.choices[0].message.content
            print("--- RSP GROQ ---")
            print(resposta)
            print("Used model:", model_name)
            break
        except Exception as exc:
            last_exc = exc
            msg = str(exc).lower()
            print("Model failed:", model_name, "-", msg)
            if "decommission" in msg or "model_decommissioned" in msg:
                print("Model decommissioned, trying next candidate...")
                continue
            else:
                continue
    else:
        print("All candidate models failed. Last error:", last_exc)
