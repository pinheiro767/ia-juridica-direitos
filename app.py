from flask import Flask, request, render_template_string, session
import requests
from xml.etree import ElementTree
import os
import random

# ===== Banco de conhecimento resumido (já existente) =====
knowledge_base = {
    "TDAH": {
        "definicao": "O TDAH é um transtorno do neurodesenvolvimento que afeta atenção, impulsividade e organização.",
        "trabalho": {
            "status": "O TDAH ainda não é considerado deficiência pela Lei de Cotas.",
            "direitos": [
                "Proteção contra discriminação no emprego.",
                "Adaptações razoáveis: prazos flexíveis, ambiente silencioso, intervalos breves."
            ],
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
        "definicao": "O abuso narcisista é manipulação, gaslighting, humilhações e controle psicológico. Enquadra-se como violência psicológica.",
        "juridico": {
            "direitos": [
                "Lei Maria da Penha: violência psicológica é crime.",
                "Código Penal: ameaça, injúria, difamação, stalking.",
                "Medidas protetivas: afastamento do agressor, proibição de contato."
            ],
            "como_acessar": [
                "Registrar boletim de ocorrência (delegacia ou online).",
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


# ===== Função para buscar artigos no PubMed =====
def listar_artigos(query, max_results=3):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    
    # Passo 1: Buscar IDs
    search_url = f"{base_url}esearch.fcgi?db=pubmed&term={query}&retmax={max_results}&retmode=json"
    search_resp = requests.get(search_url).json()
    ids = search_resp.get("esearchresult", {}).get("idlist", [])
    
    artigos = []
    
    # Passo 2: Obter detalhes
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
        return "📚 Artigos científicos recentes:\n\n" + "\n".join(artigos)
    else:
        return "Não encontrei artigos recentes sobre este tema."


# ===== Função para responder com base no JSON =====
def responder(pergunta: str) -> str:
    pergunta_lower = pergunta.lower()

    # Detectar intenção de buscar artigos
    if "artigo" in pergunta_lower or "científico" in pergunta_lower or "pubmed" in pergunta_lower:
        if "tdah" in pergunta_lower:
            return listar_artigos("ADHD AND workplace")
        elif "narcis" in pergunta_lower or "abuso" in pergunta_lower:
            return listar_artigos("narcissistic abuse psychological violence")
        else:
            return "Posso buscar artigos científicos sobre TDAH ou abuso narcisista. Qual você prefere?"

    # Identificar tema
    if "tdah" in pergunta_lower:
        tema = "TDAH"
    elif "narcis" in pergunta_lower or "abuso" in pergunta_lower or "psicológic" in pergunta_lower:
        tema = "vitimas_narcisistas"
    else:
        return "Não encontrei informações específicas para essa pergunta."

    dados = knowledge_base[tema]

    # Identificar área
    if any(word in pergunta_lower for word in ["trabalho", "emprego", "empresa"]):
        area = "trabalho"
    elif any(word in pergunta_lower for word in ["lei", "crime", "violência", "protetiva", "polícia"]):
        area = "juridico"
    else:
        area = None

    resposta = f"📌 Tema: {tema}\n\n{dados['definicao']}\n\n"

    if area and area in dados:
        info = dados[area]
        resposta += f"**Direitos garantidos:**\n- " + "\n- ".join(info.get("direitos", [])) + "\n\n"
        if "status" in info:
            resposta += f"**Status atual:** {info['status']}\n\n"
        if "projetos" in info:
            resposta += "**Projetos em tramitação:**\n- " + "\n- ".join(info["projetos"]) + "\n\n"
        if "como_acessar" in info:
            resposta += "**Como acessar:**\n- " + "\n- ".join(info["como_acessar"])
    else:
        resposta += "Posso detalhar nas áreas de saúde, educação, trabalho ou jurídico. Qual delas você gostaria?"

    return resposta


# ========= FIM DO SEU CÓDIGO ========

# Inicializa o Flask e a chave secreta para a sessão
app = Flask(__name__)
app.secret_key = os.urandom(24) # Chave aleatória para segurança da sessão

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
            {% for msg in conversa %}
            <div class="message {% if msg.role == 'user' %}user-message{% else %}ai-message{% endif %}">
                <p>{{ msg.text | replace('\n', '<br>') | safe }}</p>
            </div>
            {% endfor %}
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
    if 'conversa' not in session:
        session['conversa'] = [
            {'role': 'ai', 'text': 'AVISO LEGAL: Sou um assistente de informação sobre direitos, não um advogado. Procure sempre um profissional jurídico para orientação formal.\n\nOlá! Bem-vindo(a) ao Módulo V do curso IA e o Sistema Nervoso. Posso te ajudar com dúvidas sobre direitos de TDAH e vítimas de abuso narcisista.'}
        ]
        
    if request.method == "POST":
        pergunta_usuario = request.form["pergunta"]
        session['conversa'].append({'role': 'user', 'text': pergunta_usuario})
        
        resposta_ia = responder(pergunta_usuario)
        session['conversa'].append({'role': 'ai', 'text': resposta_ia})
        
    return render_template_string(html_template, conversa=session.get('conversa', []))
