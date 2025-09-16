from sentence_transformers import SentenceTransformer, util
import requests
from xml.etree import ElementTree
import json
import os

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
    model = SentenceTransformer('all-MiniLM-L6-v2')
    pergunta_embedding = model.encode(pergunta)

    # Construir lista de possíveis respostas do banco
    candidatos = []
    referencias = {}
    for tema, areas in knowledge_base.items():
        for area, info in areas.items():
            texto = info.get("definicao", "") if area == "definicao" else " ".join(info.get("direitos", []))
            candidatos.append(texto)
            referencias[texto] = (tema, area)

    # Calcular similaridade semântica
    candidato_embeddings = model.encode(candidatos)
    import numpy as np
    similaridades = util.cos_sim(pergunta_embedding, candidato_embeddings)[0]
    idx_max = int(np.argmax(similaridades))
    texto_selecionado = candidatos[idx_max]
    tema, area = referencias[texto_selecionado]

    # Montar resposta
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

    # Buscar artigos se solicitado
    if incluir_artigos:
        query_artigos = "ADHD AND workplace" if tema == "TDAH" else "narcissistic abuse psychological violence"
        artigos = buscar_artigos_com_cache(query_artigos)
        resposta += "**Referências científicas recentes:**\n" + "\n".join(artigos)

    return resposta

# ===== Teste =====
if __name__ == "__main__":
    perguntas = [
        "Quais são meus direitos no trabalho com TDAH?",
        "Sofro abuso psicológico de um narcisista, o que a lei diz?",
        "Como posso lidar com TDAH no emprego e quero artigos científicos?",
        "Preciso de informações e referências sobre abuso psicológico"
    ]

    for p in perguntas:
        print("❓", p)
        print(responder_avancado(p))
        print("="*80)
