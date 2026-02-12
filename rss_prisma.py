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


# ---------- REFERENCIAS NLP SESGO (mejoradas) ----------

referencias_politicas = {
    "progresista": modelo.encode([
        "derechos sociales igualdad feminismo políticas públicas diversidad justicia social bienestar",
        "progresismo cambio climático políticas sociales regulación inclusión servicios públicos"
    ]),
    "conservador": modelo.encode([
        "seguridad fronteras defensa tradición economía mercado estabilidad control migratorio",
        "valores tradicionales seguridad nacional impuestos bajos orden liberalismo económico"
    ])
}


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
    "HuffPost": "https://www.huffingtonpost.es/feeds/index.xml",
    "CNN Español": "https://cnnespanol.cnn.com/feed/",
    "NYTimes World": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "La Voz de Galicia": "https://www.lavozdegalicia.es/rss/portada.xml",
    "El Correo": "https://www.elcorreo.com/rss/portada.xml",
    "Diario Sur": "https://www.diariosur.es/rss/portada.xml",
    "Levante": "https://www.levante-emv.com/rss/portada.xml",
    "Heraldo": "https://www.heraldo.es/rss/portada/",
    "Xataka": "https://www.xataka.com/feedburner.xml",
    "Genbeta": "https://www.genbeta.com/feedburner.xml",
    "Trendencias": "https://www.trendencias.com/feedburner.xml",
    "Verne": "https://feeds.elpais.com/mrss-s/pages/ep/site/verne.elpais.com/portada",
    "Yorokobu": "https://www.yorokobu.es/feed/",
    "The Guardian": "https://www.theguardian.com/world/rss",
    "Reuters": "https://www.reutersagency.com/feed/?best-topics=general-news",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "El Periódico": "https://www.elperiodico.com/es/rss/rss_portada.xml",
    "Diario Vasco": "https://www.diariovasco.com/rss/portada.xml",
    "Información Alicante": "https://www.informacion.es/rss/portada.xml",
    "Hipertextual": "https://hipertextual.com/feed",
    "Microsiervos": "https://www.microsiervos.com/index.xml",
    "Applesfera": "https://www.applesfera.com/feedburner.xml",
    "Expansión": "https://e00-expansion.uecdn.es/rss/portada.xml",
    "Cinco Días": "https://cincodias.elpais.com/seccion/rss/portada/",
    "Nature News": "https://www.nature.com/nature.rss",
    "Scientific American": "https://rss.sciam.com/ScientificAmerican-Global",
    "Infolibre": "https://www.infolibre.es/rss",
    "El Salto": "https://www.elsaltodiario.com/rss",
    "CTXT": "https://ctxt.es/es/feed/",
    "Jacobin": "https://jacobin.com/feed",
    "Politico EU": "https://www.politico.eu/feed/",
    "OpenDemocracy": "https://www.opendemocracy.net/en/rss.xml"
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

print("Noticias recogidas:", len(noticias))


# ---------- EMBEDDINGS ----------

titulos = [n["titulo"] for n in noticias]

if not titulos:
    print("⚠️ No hay titulares.")
    embeddings = np.array([])
else:
    embeddings = modelo.encode(titulos, batch_size=32)


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


# ---------- CLUSTERING PRO (NO PÁGINA VACÍA) ----------

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


# 👉 FIX PROFESIONAL:
# evita página vacía si no hay clusters claros
if not grupos or all(len(g) < 2 for g in grupos):
    grupos = [[i] for i in range(len(noticias))]
else:
    grupos = [g for g in grupos if len(g) >= 2]

grupos.sort(key=len, reverse=True)


# ---------- SESGO NLP MEJORADO ----------

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

    # ajuste fino NLP
    if abs(prog - cons) < 0.015:
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

<!-- SEO extra -->
<meta name="theme-color" content="#ffffff">
<meta name="author" content="Prisma News">

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

    for idx in grupo[:6]:
        n = noticias[idx]
        html += f"""
<p>
<strong>{n['medio']}:</strong>
<a href="{n['link']}" target="_blank">{n['titulo']}</a>
</p>
"""

    html += "</div>"


# 👉 Truco tráfico joven (SEO + UX)
html += """
<footer style="text-align:center;opacity:.7;margin:40px 0;font-size:.9em">
Comparador automático de noticias con IA · Actualización continua
</footer>
"""

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
