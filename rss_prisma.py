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


# ---------- REFERENCIAS SESGO IA ----------

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


# ---------- FEEDS PORTADA (España / español) ----------

feeds_es = {
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
    "Jacobin": "https://jacobin.com/feed"
}

feeds_internacionales = {

    # 🇬🇧 Inglés
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "CNN World": "http://rss.cnn.com/rss/edition_world.rss",
    "Reuters": "https://www.reutersagency.com/feed/?best-topics=world",
    "NYTimes": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "Guardian": "https://www.theguardian.com/world/rss",
    "Bloomberg": "https://feeds.bloomberg.com/markets/news.rss",
    "Financial Times": "https://www.ft.com/world?format=rss",

    # 🇫🇷 Francés
    "Le Monde": "https://www.lemonde.fr/rss/une.xml",
    "France24 FR": "https://www.france24.com/fr/rss",
    "Le Figaro": "https://www.lefigaro.fr/rss/figaro_actualites.xml",

    # 🇩🇪 Alemán
    "Der Spiegel": "https://www.spiegel.de/international/index.rss",
    "Die Welt": "https://www.welt.de/feeds/latest.rss",

    # 🇮🇹 Italiano
    "Corriere": "https://xml2.corriereobjects.it/rss/homepage.xml",
    "La Repubblica": "https://www.repubblica.it/rss/homepage/rss2.0.xml",

    # 🇵🇹 Portugués
    "Publico PT": "https://www.publico.pt/rss",
    "Folha Brasil": "https://feeds.folha.uol.com.br/emcimadahora/rss091.xml",

    # 🇪🇺 Europa general
    "Politico EU": "https://www.politico.eu/feed/",
    "Euronews": "https://www.euronews.com/rss?level=theme&name=news",
     "OpenDemocracy": "https://www.opendemocracy.net/en/rss.xml",
    
    # 🌏 Asia
    "SCMP Hong Kong": "https://www.scmp.com/rss/91/feed",
    "Japan Times": "https://www.japantimes.co.jp/feed/",
    "China Daily": "http://www.chinadaily.com.cn/rss/world_rss.xml",

    # 🌎 América Latina internacional
    "Clarin": "https://www.clarin.com/rss/lo-ultimo/",
    "El Tiempo CO": "https://www.eltiempo.com/rss/colombia.xml",
    "Granma": "http://www.granma.cu/feed",
    "Cubadebate": "http://www.cubadebate.cu/feed/",
    "Prensa Latina": "https://www.prensa-latina.cu/feed/"la
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


# ---------- RECOGER NOTICIAS PORTADA ----------

noticias = []

for medio, url in feeds_es.items():
    feed = feedparser.parse(url)

    if feed.bozo:
        continue

    for entry in feed.entries[:MAX_NOTICIAS_FEED]:
        if "title" in entry and "link" in entry:
            noticias.append({
                "medio": medio,
                "titulo": limpiar_html(entry.title),
                "link": entry.link.strip()
            })


# 👉 quitar duplicados exactos por URL
noticias = list({n["link"]: n for n in noticias}.values())

print("Noticias portada:", len(noticias))


# ---------- EMBEDDINGS ----------

titulos = [n["titulo"] for n in noticias]
embeddings = modelo.encode(titulos, batch_size=32) if titulos else np.array([])


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

if not grupos:
    grupos = [[i] for i in range(len(noticias))]

grupos.sort(key=len, reverse=True)


# ---------- TITULAR IA ----------

def titular_prisma(indices):

    palabras = []
    for i in indices:
        palabras += limpiar(noticias[i]["titulo"])

    comunes = [p for p, _ in Counter(palabras).most_common(5)]
    blacklist = {"gobierno","españa","hoy","última","últimas"}

    comunes = [p for p in comunes if p not in blacklist][:3]

    tema = ", ".join(comunes)

    prefijos = [
        "🧭 Claves informativas:",
        "📊 En el foco:",
        "📰 Lo que domina hoy:",
        "🔥 Tema principal:"
    ]

    return f"{random.choice(prefijos)} {tema.capitalize()}"


def resumen_prisma(indices):

    palabras = []
    for i in indices:
        palabras += limpiar(noticias[i]["titulo"])

    comunes = [p for p, _ in Counter(palabras).most_common(6)]

    blacklist = {
        "gobierno","españa","última","hoy",
        "según","dice","años","parte"
    }

    comunes = [p for p in comunes if p not in blacklist][:2]

    if not comunes:
        return ""

    tema = " y ".join(comunes)

    frases = [
        f"Panorama informativo centrado en <b>{tema}</b>.",
        f"Las noticias destacan especialmente <b>{tema}</b>.",
        f"El foco mediático gira en torno a <b>{tema}</b>."
    ]

    return f"""
<p class="resumen">
🧠 <b>Resumen IA:</b> {random.choice(frases)}
</p>
"""


# ---------- FEEDS INTERNACIONALES → ESPAÑA ----------

KEYWORDS_ESPANA = [
    "españa","spain","espagne","spanien","spagna",
    "spanish","español","madrid","barcelona",
    "catalonia","andalusia","valencia","canary",
    "spaniard","spaniards"
]

noticias_espana = []

for medio, url in feeds_internacionales.items():
    feed = feedparser.parse(url)

    if feed.bozo:
        continue

    for entry in feed.entries[:10]:
        if "title" in entry:
            titulo = limpiar_html(entry.title)

            if any(k in titulo.lower() for k in KEYWORDS_ESPANA):
                noticias_espana.append({
                    "medio": medio,
                    "titulo": titulo,
                    "link": entry.link
                })


# 👉 ordenar por relevancia simple
noticias_espana.sort(key=lambda x: len(x["titulo"]), reverse=True)


# ---------- FECHAS ----------

fecha = datetime.now()
fecha_legible = fecha.strftime("%d/%m %H:%M")
fecha_iso = fecha.isoformat()
cachebuster = fecha.timestamp()
medios_unicos = len(set(n["medio"] for n in noticias))


# ---------- HTML PORTADA ----------

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Prisma | Comparador IA noticias</title>
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
<a href="espana.html">España en el mundo</a>
<a href="mailto:ovalero@gmail.com">Contacto</a>
</nav>
</header>

<div class="container">
"""

for i, grupo in enumerate(grupos, 1):

    clase = "card portada" if i == 1 else "card"

    html += f"""
<div class="{clase}">
<h2>{titular_prisma(grupo)}</h2>
{resumen_prisma(grupo)}
"""

    for idx in grupo[:6]:
        n = noticias[idx]
        html += f"""
<p><strong>{n['medio']}:</strong>
<a href="{n['link']}" target="_blank" rel="noopener noreferrer">
{n['titulo']}
</a></p>
"""

    html += "</div>"

html += "</div></body></html>"

with open("index.html","w",encoding="utf-8") as f:
    f.write(html)


# ---------- HTML ESPAÑA EN EL MUNDO ----------

html_espana = f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>España en el mundo | Prisma</title>
<link rel="stylesheet" href="prisma.css?v={cachebuster}">
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>

<header class="header">
<div class="logo">
<img src="Logo.PNG" class="logo-img">
<a href="index.html" class="logo-link">PRISMA</a>
</div>

<nav class="nav">
<a href="index.html">Inicio</a>
<a href="sobre.html">Sobre Prisma</a>
<a href="espana.html">España en el mundo</a>
<a href="mailto:ovalero@gmail.com">Contacto</a>
</nav>
</header>

<div class="container">
<div class="card portada">
<h2>🌍 España en el mundo</h2>
"""

for n in noticias_espana[:40]:
    html_espana += f"""
<p><strong>{n['medio']}:</strong>
<a href="{n['link']}" target="_blank" rel="noopener noreferrer">
{n['titulo']}
</a></p>
"""

html_espana += "</div></div></body></html>"

with open("espana.html","w",encoding="utf-8") as f:
    f.write(html_espana)


print("PRISMA OPTIMIZADO GENERADO 🚀")
