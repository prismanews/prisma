import feedparser
import re
import html
import random
from datetime import datetime
from collections import Counter
import numpy as np

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# ---------- CONFIG ----------

UMBRAL_CLUSTER = 0.56
UMBRAL_DUPLICADO = 0.88
MAX_NOTICIAS_FEED = 12

modelo = SentenceTransformer("all-MiniLM-L6-v2")


# ---------- FEEDS ----------

feeds = {
    "El País": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
    "El Mundo": "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",
    "ABC": "https://www.abc.es/rss/feeds/abcPortada.xml",
    "La Vanguardia": "https://www.lavanguardia.com/rss/home.xml",
    "20 Minutos": "https://www.20minutos.es/rss/",
    "eldiario.es": "https://www.eldiario.es/rss/",
    "Europa Press": "https://www.europapress.es/rss/rss.aspx",
    "El Español": "https://www.elespanol.com/rss/",
    "RTVE": "https://www.rtve.es/rss/",
    "BBC Mundo": "https://feeds.bbci.co.uk/mundo/rss.xml",
    "France24 Español": "https://www.france24.com/es/rss",
    "DW Español": "https://rss.dw.com/xml/rss-es-all",
    "El Confidencial": "https://www.elconfidencial.com/rss/",
    "Público": "https://www.publico.es/rss/",
    "OKDiario": "https://okdiario.com/feed/",
    "HuffPost": "https://www.huffingtonpost.es/feeds/index.xml",
    "CNN Español": "https://cnnespanol.cnn.com/feed/",
    "NYTimes": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"
}


# ---------- STOPWORDS ----------

stopwords = {
    "el","la","los","las","de","del","en","para","por","con",
    "sin","un","una","unos","unas","al","a","y","o","que",
    "se","su","sus","ante","como","más","menos","tras",
    "dice","segun","hoy","pais","gobierno"
}


# ---------- SESGO POLÍTICO MEJORADO ----------

progresista = {
    "derechos","igualdad","social","diversidad",
    "clima","publico","feminismo"
}

conservador = {
    "seguridad","frontera","impuestos","defensa",
    "control","tradicion","orden"
}


def sesgo_politico(indices):

    palabras = []
    for i in indices:
        palabras += limpiar(noticias[i]["titulo"])

    izq = sum(1 for p in palabras if p in progresista)
    der = sum(1 for p in palabras if p in conservador)

    # NUEVO equilibrio más realista
    if abs(izq - der) <= 1:
        texto = "Cobertura bastante equilibrada"
    elif izq > der:
        texto = "Enfoque ligeramente progresista"
    else:
        texto = "Enfoque ligeramente conservador"

    return f"""
<div class="sesgo">
⚖️ <b>Sesgo IA:</b> {texto}
</div>
"""


# ---------- LIMPIEZA ----------

def limpiar_html(texto):
    texto = html.unescape(texto)
    texto = re.sub(r'<.*?>', '', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()


def limpiar(texto):
    texto = texto.lower()
    texto = re.sub(r'[^\w\s]', '', texto)
    palabras = texto.split()
    return [p for p in palabras if p not in stopwords and len(p) > 3]


# ---------- RECOGER NOTICIAS ----------

noticias = []

for medio, url in feeds.items():
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:MAX_NOTICIAS_FEED]:
            if "title" in entry and "link" in entry:
                noticias.append({
                    "medio": medio,
                    "titulo": limpiar_html(entry.title),
                    "link": entry.link.strip()
                })
    except:
        continue


# ---------- EMBEDDINGS CON SEGURIDAD ----------

titulos = [n["titulo"] for n in noticias]

try:
    embeddings = modelo.encode(titulos)
except Exception as e:
    print("Error embeddings:", e)
    embeddings = np.random.rand(len(titulos), 384)


# ---------- DEDUPLICADO ----------

filtradas = []
emb_filtrados = []

for i, emb in enumerate(embeddings):

    if not emb_filtrados:
        filtradas.append(noticias[i])
        emb_filtrados.append(emb)
        continue

    similitudes = cosine_similarity([emb], emb_filtrados)[0]

    if max(similitudes) < UMBRAL_DUPLICADO:
        filtradas.append(noticias[i])
        emb_filtrados.append(emb)

noticias = filtradas
embeddings = np.array(emb_filtrados)


# ---------- CLUSTERING ----------

grupos = []

for i, emb in enumerate(embeddings):

    mejor_grupo = None
    mejor_score = 0

    for grupo in grupos:
        centroide = np.mean(embeddings[grupo], axis=0)
        score = cosine_similarity([emb], [centroide])[0][0]

        if score > mejor_score:
            mejor_score = score
            mejor_grupo = grupo

    if mejor_score > UMBRAL_CLUSTER:
        mejor_grupo.append(i)
    else:
        grupos.append([i])

grupos.sort(key=len, reverse=True)

# NUEVO filtro anti-clusters raros
grupos = [g for g in grupos if len(g) > 0]


# ---------- TITULAR IA ----------

def titular_prisma(indices):
    palabras = []
    for i in indices:
        palabras += limpiar(noticias[i]["titulo"])

    comunes = Counter(palabras).most_common(3)

    prefijos = [
        "🧭 Claves informativas:",
        "📊 En el foco:",
        "📰 Lo que domina hoy:",
        "🔥 Tema principal:",
        "📡 Actualidad destacada:",
        "✨ Radar informativo:"
    ]

    tema = ", ".join(p for p, _ in comunes)
    return f"{random.choice(prefijos)} {tema.capitalize()}"


def resumen_ia(indices):
    palabras = []
    for i in indices:
        palabras += limpiar(noticias[i]["titulo"])

    comunes = Counter(palabras).most_common(3)
    tema = ", ".join(p for p, _ in comunes)

    return f"""
<div class="resumen">
🧠 <b>Lectura IA:</b> Cobertura centrada en
<b>{tema}</b>.
</div>
"""


# ---------- GENERAR HTML ----------

fecha = datetime.now()
fecha_legible = fecha.strftime("%d/%m %H:%M")
fecha_iso = fecha.isoformat()
cachebuster = fecha.timestamp()
medios_unicos = len(set(n["medio"] for n in noticias))

html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Prisma | Comparador IA de noticias</title>
<link rel="stylesheet" href="prisma.css?v={cachebuster}">
</head>
<body>

<header class="header">
<div class="logo">
<img src="Logo.PNG" class="logo-img">
<a href="index.html" class="logo-link">PRISMA</a>
</div>

<p class="tagline">Más contexto · menos ruido</p>

<div class="stats">
📰 {medios_unicos} medios analizados ·
<time datetime="{fecha_iso}">Actualizado: {fecha_legible}</time>
</div>

<nav class="nav">
<a href="index.html">Inicio</a>
<a href="sobre.html">Sobre Prisma</a>
</nav>

</header>

<div class="container">
"""


for i, grupo in enumerate(grupos, 1):

    consenso = (
        "🔥 Consenso alto" if len(grupo) >= 4 else
        "🟡 Cobertura amplia" if len(grupo) >= 2 else
        "⚪ Tema emergente"
    )

    html += f"""
<div class="card">
<div class="meta">
<span>{consenso}</span>
<span>#{i}</span>
</div>

<h2>{titular_prisma(grupo)}</h2>
"""

    if len(grupo) > 1:
        html += resumen_ia(grupo)
        html += sesgo_politico(grupo)

    for idx in grupo:
        n = noticias[idx]
        html += f"""
<p>
<strong class="medio">{n['medio']}:</strong>
<a href="{n['link']}" target="_blank">{n['titulo']}</a>
</p>
"""

    html += """
<button class="share"
onclick="navigator.share?.({title:'Prisma',url:window.location.href})">
Compartir
</button>
</div>
"""


html += "</div></body></html>"

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("PRISMA definitivo generado 🚀")
