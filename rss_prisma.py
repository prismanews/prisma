import feedparser
import re
import html
import random
from datetime import datetime
from collections import Counter
import numpy as np

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# ---------------- CONFIG ----------------

UMBRAL_CLUSTER = 0.60
MAX_NOTICIAS_FEED = 10

modelo = SentenceTransformer('all-MiniLM-L6-v2')


# ---------------- FEEDS ----------------

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
    "Xataka": "https://www.xataka.com/feed.xml",
    "Genbeta": "https://www.genbeta.com/feed.xml",
    "AS": "https://as.com/rss/tags/ultimas_noticias.xml",
    "Marca": "https://e00-marca.uecdn.es/rss/portada.xml",
}


# ---------------- LIMPIEZA TEXTO ----------------

stopwords = {
    "el","la","los","las","de","del","en","para","por","con",
    "sin","un","una","unos","unas","al","a","y","o","que",
    "se","su","sus","ante","como","más","menos",
    "cuales","quien","donde","cuando","porque",
    "sobre","tras","este","esta","estos","estas",
    "algunos","segun","entre","tambien"
}


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


# ---------------- RECOGER NOTICIAS ----------------

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

    except Exception:
        continue


# ---------------- DEDUPLICADO ----------------

vistos = set()
noticias = [
    n for n in noticias
    if not (clave := re.sub(r'\W+', '', n["titulo"].lower())) in vistos
    and not vistos.add(clave)
]


# ---------------- EMBEDDINGS ----------------

titulos = [n["titulo"] for n in noticias]
embeddings = modelo.encode(titulos)


# ---------------- CLUSTERING MEJORADO ----------------

grupos = []

for i in range(len(noticias)):

    if not grupos:
        grupos.append([i])
        continue

    mejor_grupo = None
    mejor_score = 0

    for grupo in grupos:
        centroide = np.mean(embeddings[grupo], axis=0)

        score = cosine_similarity(
            [embeddings[i]],
            [centroide]
        )[0][0]

        if score > mejor_score:
            mejor_score = score
            mejor_grupo = grupo

    if mejor_score > UMBRAL_CLUSTER:
        mejor_grupo.append(i)
    else:
        grupos.append([i])

grupos.sort(key=len, reverse=True)


# ---------------- TITULAR IA EDITORIAL ----------------

def titular_prisma(indices):

    palabras = []
    for i in indices:
        palabras += limpiar(noticias[i]["titulo"])

    comunes = Counter(palabras).most_common(3)

    if not comunes:
        return "Actualidad destacada"

    tema = ", ".join(p for p, _ in comunes)

    prefijos = [
        "🧭 Claves informativas:",
        "📊 En el foco:",
        "📰 Lo que domina hoy:",
        "🔥 Tema principal:",
        "📡 Actualidad destacada:",
        "✨ Radar informativo:"
    ]

    return f"{random.choice(prefijos)} {tema.capitalize()}"


# ---------------- RESUMEN IA ----------------

def resumen_ia(indices):

    palabras = []
    for i in indices:
        palabras += limpiar(noticias[i]["titulo"])

    comunes = Counter(palabras).most_common(3)

    if not comunes:
        return ""

    tema = ", ".join(p for p, _ in comunes)

    return f"""
    <div class="resumen">
    🧠 <b>Lectura IA:</b> Cobertura centrada en
    <b>{tema}</b>.
    </div>
    """


# ---------------- HTML ----------------

cachebuster = datetime.now().timestamp()
medios_unicos = len(set(n["medio"] for n in noticias))

html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">

<title>Prisma · Más contexto menos ruido</title>
<meta name="description" content="Prisma agrupa titulares de múltiples medios para entender la actualidad sin ruido.">

<meta name="viewport" content="width=device-width, initial-scale=1">

<link rel="icon" href="Logo.PNG">
<link rel="apple-touch-icon" href="Logo.PNG">
<link rel="stylesheet" href="prisma.css?v={cachebuster}">

<meta name="theme-color" content="#ffffff">

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
{datetime.now().strftime("%d/%m %H:%M")}
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

print("PRISMA generado 🚀")
