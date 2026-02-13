# -*- coding: utf-8 -*-

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

UMBRAL_CLUSTER = 0.63
UMBRAL_DUPLICADO = 0.87
MAX_NOTICIAS_FEED = 8

modelo = SentenceTransformer("all-MiniLM-L6-v2")


# ---------- REFERENCIAS SESGO ----------

referencias_politicas = {
    "progresista": modelo.encode([
        "derechos sociales igualdad feminismo politicas publicas diversidad justicia social bienestar",
        "progresismo cambio climatico politicas sociales regulacion inclusion servicios publicos"
    ]),
    "conservador": modelo.encode([
        "seguridad fronteras defensa tradicion economia mercado estabilidad control migratorio",
        "valores tradicionales seguridad nacional impuestos bajos orden liberalismo economico"
    ])
}


# ---------- FEEDS ----------

feeds = {
    "El Pais": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
    "El Mundo": "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",
    "ABC": "https://www.abc.es/rss/feeds/abcPortada.xml",
    "La Vanguardia": "https://www.lavanguardia.com/rss/home.xml",
    "20 Minutos": "https://www.20minutos.es/rss/",
    "eldiario.es": "https://www.eldiario.es/rss/",
    "Europa Press": "https://www.europapress.es/rss/rss.aspx",
    "El Espanol": "https://www.elespanol.com/rss/",
    "RTVE": "https://www.rtve.es/rss/",
    "BBC Mundo": "https://feeds.bbci.co.uk/mundo/rss.xml",
    "France24": "https://www.france24.com/es/rss",
    "DW": "https://rss.dw.com/xml/rss-es-all",
    "El Confidencial": "https://www.elconfidencial.com/rss/",
    "Publico": "https://www.publico.es/rss/",
    "HuffPost": "https://www.huffingtonpost.es/feeds/index.xml",
    "CNN Espanol": "https://cnnespanol.cnn.com/feed/",
    "NYTimes": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "Reuters": "https://www.reutersagency.com/feed/?best-topics=general-news",
    "Guardian": "https://www.theguardian.com/world/rss",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "Xataka": "https://www.xataka.com/feedburner.xml",
    "Genbeta": "https://www.genbeta.com/feedburner.xml"
}


# ---------- LIMPIEZA ----------

stopwords = {
    "el","la","los","las","de","del","en","para","por","con",
    "sin","un","una","unos","unas","al","a","y","o","que",
    "se","su","sus","ante","como","mas","menos","tras"
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
        print("Error feed", medio, e)

print("Noticias recogidas:", len(noticias))


# ---------- EMBEDDINGS ----------

titulos = [n["titulo"] for n in noticias]

if titulos:
    embeddings = modelo.encode(titulos, batch_size=32)
else:
    embeddings = np.array([])


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


if not grupos or all(len(g) < 2 for g in grupos):
    grupos = [[i] for i in range(len(noticias))]
else:
    grupos = [g for g in grupos if len(g) >= 2]

grupos.sort(key=len, reverse=True)


# ---------- SESGO ----------

def sesgo_politico(indices):

    textos = [noticias[i]["titulo"] for i in indices]
    emb = modelo.encode(textos, batch_size=16)
    centroide = np.mean(emb, axis=0).reshape(1, -1)

    prog = cosine_similarity(centroide, referencias_politicas["progresista"]).mean()
    cons = cosine_similarity(centroide, referencias_politicas["conservador"]).mean()

    if abs(prog - cons) < 0.015:
        texto = "Cobertura equilibrada"
    elif prog > cons:
        texto = "Enfoque algo progresista"
    else:
        texto = "Enfoque algo conservador"

    return f'<div class="sesgo">Sesgo IA: {texto}</div>'


# ---------- TITULAR IA ----------

def titular_prisma(indices):

    palabras = []
    for i in indices:
        palabras += limpiar(noticias[i]["titulo"])

    comunes = Counter(palabras).most_common(3)
    tema = ", ".join(p for p, _ in comunes)

    prefijos = [
        "Claves informativas:",
        "Tema principal:",
        "En el foco:",
        "Lo destacado:"
    ]

    return f"{random.choice(prefijos)} {tema.capitalize()}"


# ---------- FECHA ----------

fecha = datetime.now()
fecha_legible = fecha.strftime("%d/%m %H:%M")
fecha_iso = fecha.isoformat()
cachebuster = fecha.timestamp()
medios_unicos = len(set(n["medio"] for n in noticias))


# ---------- HTML ----------

html_out = f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Prisma noticias IA</title>

<meta name="description"
content="Comparador inteligente de noticias. Analiza multiples medios para ofrecer contexto.">

<link rel="stylesheet" href="prisma.css?v={cachebuster}">
<meta name="viewport" content="width=device-width, initial-scale=1">

</head>
<body>

<header class="header">
<h1>PRISMA</h1>
<p>Mas contexto menos ruido</p>
<p>{medios_unicos} medios analizados</p>
<p>Actualizado: {fecha_legible}</p>
</header>

<div class="container">
"""


for i, grupo in enumerate(grupos, 1):

    clase = "card portada" if i == 1 else "card"

    html_out += f'<div class="{clase}">'
    html_out += f"<h2>{titular_prisma(grupo)}</h2>"
    html_out += sesgo_politico(grupo)

    for idx in grupo[:6]:
        n = noticias[idx]
        html_out += f'<p><b>{n["medio"]}:</b> <a href="{n["link"]}" target="_blank">{n["titulo"]}</a></p>'

    html_out += "</div>"


# ---------- FOOTER SEGURO ASCII ----------

html_out += """
<footer style="text-align:center;margin:40px 0;font-size:.9em;opacity:.75">

Contacto:
<a href="mailto:contacto@prismanews.com">
contacto@prismanews.com
</a><br>

Comparador automatico de noticias con IA - Actualizacion continua

</footer>
"""

html_out += "</div></body></html>"


with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_out)


# ---------- SITEMAP ----------

with open("sitemap.xml", "w", encoding="utf-8") as f:
    f.write("""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://prismanews.github.io/prisma/</loc></url>
</urlset>""")


# ---------- ROBOTS ----------

with open("robots.txt", "w", encoding="utf-8") as f:
    f.write("""User-agent: *
Allow: /

Sitemap: https://prismanews.github.io/prisma/sitemap.xml
""")


print("PRISMA generado OK")
