from flask import Flask, request, render_template_string
from sentence_transformers import SentenceTransformer, util
import requests
from xml.etree import ElementTree
import json
import os
import numpy as np

# ========= SEU CÓDIGO A PARTIR DAQUI ========

CACHE_FILE = "pubmed_cache.json"

# ===== Carregar/Salvar Cache =====
def carregar_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

# ===== Banco de conhecimento expandido =====
knowledge_base = {
    "TDAH": {
        "definicao": "O TDAH é um transtorno do neurodesenvolvimento que afeta atenção, impulsividade e organização.",
        "trabalho": {
            "direitos": [
                "Proteção contra discriminação no emprego.",
                "Adaptações razoáveis: prazos flexíveis, ambiente silencioso, intervalos breves."
            ],
            "status": "O TDAH ainda não é considerado deficiência pela Lei de Cotas.",
            "projetos": [
                "PL 479/2025 – classificar TDAH como deficiência.",
                "PL 2630/2021 – Política Nacional do TDAH."
            ],
            "como_acessar": [
                "Negociar adaptações com laudo médico.",
                "Acionar MPT/Defensoria em caso de discriminação."
            ]
        },
        "educacao": {
            "direitos": [
                "Tempo extra em provas com laudo médico.",
                "Sala separada em exames.",
                "Planos pedagógicos individualizados (PEI)."
            ]
        },
        "saude": {
            "direitos": [
                "Atendimento multiprofissional (psiquiatria, psicologia, neurologia).",
                "Medicamentos pelo SUS (metilfenidato, lisdexanfetamina)."
            ]
        }
    },
    "vitimas_narcisistas": {
        "definicao": "O abuso narcisista é manipulação, gaslighting, humilhações e controle psicológico.",
        "juridico": {
            "direitos": [
                "Lei Maria da Penha: violência psicológica é crime.",
                "Código Penal: ameaça, injúria, difamação, stalking.",
                "Medidas protetivas: afastamento do agressor, proibição de contato."
            ],
            "como_acessar": [
                "Registrar boletim de ocorrência.",
                "Solicitar medida protetiva (juiz decide em até 48h).",
                "Acionar Defensoria Pública."
            ]
        },
        "saude": {
            "direitos": [
                "Atendimento psicológico gratuito pelo SUS.",
                "Encaminhamento para CAPS e grupos de apoio."
            ]
        }
    }
}

# Carregando o modelo de IA uma única vez, fora das funções
model = SentenceTransformer('all-MiniLM-L6-v2')

# ===== Função para buscar artigos com cache =====
def buscar_artigos_com_cache(query, max_results=3):
    cache = carregar_cache()
    if query in cache:
        return cache[query]
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    search_url = f"{base_url}esearch.fcgi?db=pubmed&term={query}&retmax={max_results}&retmode=json"
    search_resp = requests.get(search_url).json()
    ids = search_resp.get("esearchresult", {}).get("idlist", [])
    artigos = []
    if ids:
        fetch_url = f"{base_url}efetch.fcgi?db=pubmed&id={','.join(ids)}&retmode=xml"
        fetch_resp = requests.get(fetch_url)
        root = ElementTree.fromstring(fetch_resp.content)
        for article in root.findall(".//PubmedArticle"):
            titulo = article.findtext(".//ArticleTitle", default="Sem título")
            journal = article.findtext(".//Title", default="Sem periódico")
            ano = article.findtext(".//PubDate/Year", default="Sem ano")
            doi = article.findtext(".//ArticleId[@IdType='doi']", default="Sem DOI")
            artigos.append(f"- {titulo} ({ano}) - {journal}. DOI: {doi}")
    if artigos:
        cache[query] = artigos
        salvar_cache(cache)
        return artigos
    else:
        return ["Não encontrei artigos recentes sobre este tema."]

# ===== Função avançada para responder =====
def responder_avancado(pergunta: str, incluir_artigos=True) -> str:
    pergunta_embedding = model.encode(pergunta)
    candidatos = []
    referencias = {}
    for tema, areas in knowledge_base.items():
        for area, info in areas.items():
            texto = info.get("definicao", "") if area == "definicao" else " ".join(info.get("direitos", []))
            candidatos.append(texto)
            referencias[texto] = (tema, area)
    candidato_embeddings = model.encode(candidatos)
    similaridades = util.cos_sim(pergunta_embedding, candidato_embeddings)[0]
    idx_max = int(np.argmax(similaridades))
    texto_selecionado = candidatos[idx_max]
    tema, area = referencias[texto_selecionado]
    dados = knowledge_base[tema]
    info = dados.get(area, {})
    resposta = f"📌 Tema: {tema}\n\n{dados.get('definicao','')}\n\n"
    if "direitos" in info:
        resposta += "**Direitos garantidos:**\n- " + "\n- ".join(info["direitos"]) + "\n\n"
    if "status" in info:
        resposta += f"**Status atual:** {info['status']}\n\n"
    if "projetos" in info:
        resposta += "**Projetos em tramitação:**\n- " + "\n- ".join(info["projetos"]) + "\n\n"
    if "como_acessar" in info:
        resposta += "**Como acessar:**\n- " + "\n- ".join(info["como_acessar"]) + "\n\n"
    if incluir_artigos:
        query_artigos = "ADHD AND workplace" if tema == "TDAH" else "narcissistic abuse psychological violence"
        artigos = buscar_artigos_com_cache(query_artigos)
        resposta += "**Referências científicas recentes:**\n" + "\n".join(artigos)
    return resposta

# ========= FIM DO SEU CÓDIGO ========

# Inicializa o Flask
app = Flask(__name__)

# O HTML para a página do seu chat
html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Assistência IA da Prof. Cláudia Pinheiro</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
        body {
            font-family: 'Poppins', sans-serif;
            background-color: #f0f2f5;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
        }
        .container {
            background-color: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 500px;
            display: flex;
            flex-direction: column;
            height: 80vh; /* Altura do contêiner */
        }
        h1 {
            color: #2c3e50;
            font-weight: 600;
            text-align: center;
            margin-top: 0;
            margin-bottom: 20px;
        }
        .chat-container {
            flex-grow: 1;
            overflow-y: auto;
            padding: 10px;
            border: 1px solid #bdc3c7;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            flex-direction: column;
        }
        .message {
            margin-bottom: 10px;
            padding: 10px 15px;
            border-radius: 20px;
            max-width: 70%;
        }
        .user-message {
            background-color: #2980b9;
            color: white;
            align-self: flex-end;
            text-align: right;
            border-bottom-right-radius: 5px;
        }
        .ai-message {
            background-color: #ecf0f1;
            color: black;
            align-self: flex-start;
            text-align: left;
            border-bottom-left-radius: 5px;
        }
        form {
            display: flex;
            gap: 10px;
        }
        input[type="text"] {
            flex-grow: 1;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #bdc3c7;
            font-family: 'Poppins', sans-serif;
        }
        button {
            padding: 12px 20px;
            border: none;
            border-radius: 8px;
            background-color: #2980b9;
            color: white;
            font-weight: 600;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        button:hover {
            background-color: #2471a5;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Assistência IA da Prof. Cláudia Pinheiro</h1>
        <div class="chat-container">
            {% if resposta %}
            <div class="message ai-message">
                <p>{{ resposta | replace('\n', '<br>') | safe }}</p>
            </div>
            {% endif %}
        </div>
        <form method="post">
            <input type="text" name="pergunta" placeholder="Digite sua mensagem...">
            <button type="submit">Enviar</button>
        </form>
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        pergunta = request.form["pergunta"]
        resposta = responder_avancado(pergunta)
        return render_template_string(html_template, resposta=resposta)
    return render_template_string(html_template)
