import feedparser
import re
import html
import random
from datetime import datetime
from collections import Counter
import numpy as np

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# ---------- CONFIG PRO ----------

UMBRAL_CLUSTER = 0.63
UMBRAL_DUPLICADO = 0.87
MAX_NOTICIAS_FEED = 8

modelo = SentenceTransformer("all-MiniLM-L6-v2")


# ---------- REFERENCIAS NLP SESGO ----------

referencias_politicas = {
    "progresista": modelo.encode([
        "derechos sociales igualdad feminismo políticas públicas diversidad justicia social",
        "progresismo cambio climático políticas sociales regulación bienestar"
    ]),
    "conservador": modelo.encode([
        "seguridad fronteras defensa tradición economía mercado estabilidad control migratorio",
        "valores tradicionales seguridad nacional impuestos bajos orden"
    ])
}


# ---------- FEEDS ----------
feeds = {
    # (tu lista completa intacta)
}


# ---------- LIMPIEZA ----------

stopwords = {
    "el","la","los","las","de","del","en","para","por","con",
    "sin","un","una","unos","unas","al","a","y","o","que",
    "se","su","sus","ante","como","más","menos","tras"
}


def limpiar_html(texto):
    texto = html.unescape(texto)
    texto = re.sub(r'<.*?>', '', texto)
    return re.sub(r'\s+', ' ', texto).strip()


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
    except Exception as e:
        print(f"Error feed {medio}: {e}")


# ---------- EMBEDDINGS (más eficiente) ----------

titulos = [n["titulo"] for n in noticias]
embeddings = modelo.encode(titulos, batch_size=32)


# ---------- DEDUPLICADO SEMÁNTICO ----------

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


# ---------- CLUSTERING IA ----------

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


grupos = [g for g in grupos if len(g) >= 2]
grupos.sort(key=len, reverse=True)


# ---------- SESGO NLP ----------

def sesgo_politico(indices):

    textos = [noticias[i]["titulo"] for i in indices]
    emb = modelo.encode(textos, batch_size=16)
    centroide = np.mean(emb, axis=0).reshape(1, -1)

    prog = cosine_similarity(
        centroide,
        referencias_politicas["progresista"]
    ).mean()

    cons = cosine_similarity(
        centroide,
        referencias_politicas["conservador"]
    ).mean()

    if abs(prog - cons) < 0.02:
        texto = "Cobertura bastante equilibrada"
    elif prog > cons:
        texto = "Enfoque algo progresista"
    else:
        texto = "Enfoque algo conservador"

    return f"""
<div class="sesgo">
⚖️ <b>Sesgo IA:</b> {texto}
</div>
"""


# ---------- TITULAR IA ----------

def titular_prisma(indices):

    palabras = []
    for i in indices:
        palabras += limpiar(noticias[i]["titulo"])

    comunes = Counter(palabras).most_common(3)
    tema = ", ".join(p for p, _ in comunes)

    prefijos = [
        "🧭 Claves informativas:",
        "📊 En el foco:",
        "📰 Lo que domina hoy:",
        "🔥 Tema principal:"
    ]

    return f"{random.choice(prefijos)} {tema.capitalize()}"


# ---------- SEO + FECHA ----------

fecha = datetime.now()
fecha_legible = fecha.strftime("%d/%m %H:%M")
fecha_iso = fecha.isoformat()
cachebuster = fecha.timestamp()
medios_unicos = len(set(n["medio"] for n in noticias))


# ---------- HTML ----------

html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">

<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-9WZC3GQSN8"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
gtag('config', 'G-9WZC3GQSN8');
</script>

<title>Prisma | Comparador IA de noticias</title>

<meta name="description"
content="Comparador inteligente de noticias. Analiza múltiples medios para ofrecer contexto y reducir ruido informativo.">

<meta name="robots" content="index, follow">
<link rel="canonical" href="https://prismanews.github.io/prisma/">
<!-- Open Graph -->
<meta property="og:title" content="Prisma noticias IA">
<meta property="og:description" content="Comparador inteligente de noticias con IA">
<meta property="og:image" content="Logo.PNG">
<meta property="og:type" content="website">

<link rel="stylesheet" href="prisma.css?v={cachebuster}">
<meta name="viewport" content="width=device-width, initial-scale=1">

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

    html += f"""
<div class="card">
<h2>{titular_prisma(grupo)}</h2>
{sesgo_politico(grupo)}
"""

    # 👉 LIMITAMOS A 6 TITULARES POR CLUSTER
    for idx in grupo[:6]:
        n = noticias[idx]
        html += f"""
<p>
<strong>{n['medio']}:</strong>
<a href="{n['link']}" target="_blank">{n['titulo']}</a>
</p>
"""

    html += "</div>"


html += "</div></body></html>"

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)


# ---------- SITEMAP ----------

sitemap = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://prismanews.github.io/prisma/</loc></url>
</urlset>
"""

with open("sitemap.xml", "w", encoding="utf-8") as f:
    f.write(sitemap)


# ---------- ROBOTS ----------

robots = """User-agent: *
Allow: /

Sitemap: https://prismanews.github.io/sitemap.xml
"""

with open("robots.txt", "w", encoding="utf-8") as f:
    f.write(robots)


print("PRISMA NLP PRO generado 🚀")
