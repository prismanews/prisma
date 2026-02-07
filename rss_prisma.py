import feedparser
import re
from datetime import datetime
from collections import Counter

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# ---------------- CONFIG ----------------

UMBRAL_CLUSTER = 0.68
MAX_NOTICIAS_FEED = 5

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

# ---------------- LIMPIAR TEXTO ----------------

stopwords = {
    "el","la","los","las","de","del","en","para","por","con",
    "sin","un","una","unos","unas","al","a","y","o","que",
    "se","su","sus","ante","como","más","menos"
}

stopwords.update({
    "cuales","quien","donde","cuando","porque",
    "sobre","tras","este","esta","estos","estas",
    "algunos","segun","entre","tambien"
})

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
                    "titulo": entry.title.strip(),
                    "link": entry.link.strip()
                })

    except Exception:
        continue


# ---------------- ELIMINAR DUPLICADOS ----------------

vistos = set()
noticias_filtradas = []

for n in noticias:
    clave = re.sub(r'\W+', '', n["titulo"].lower())
    if clave not in vistos:
        vistos.add(clave)
        noticias_filtradas.append(n)

noticias = noticias_filtradas


# ---------------- EMBEDDINGS ----------------

titulos = [n["titulo"] for n in noticias]
embeddings = modelo.encode(titulos)


# ---------------- CLUSTERING IA ----------------

grupos = []

for i, noticia in enumerate(noticias):

    if not grupos:
        grupos.append([i])
        continue

    mejor_grupo = None
    mejor_score = 0

    for grupo in grupos:
        score = cosine_similarity(
            [embeddings[i]],
            [embeddings[grupo[0]]]
        )[0][0]

        if score > mejor_score:
            mejor_score = score
            mejor_grupo = grupo

    if mejor_score > UMBRAL_CLUSTER:
        mejor_grupo.append(i)
    else:
        grupos.append([i])

grupos.sort(key=len, reverse=True)


# ---------------- MÉTRICAS ----------------

max_medios = max(len(g) for g in grupos)
medios_unicos = len(set(n["medio"] for n in noticias))


# ---------------- IA EXTRA ----------------

def tema_dominante(indices):
    palabras = []
    for i in indices:
        palabras += limpiar(noticias[i]["titulo"])

    comunes = Counter(palabras).most_common(2)
    return " / ".join(p for p, _ in comunes)


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


def titular_representativo(indices):
    centro = embeddings[indices].mean(axis=0)
    scores = cosine_similarity([centro], embeddings[indices])[0]
    return noticias[indices[scores.argmax()]]["titulo"]


# ---------------- HTML MODERNO ----------------

html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Prisma</title>
<link rel="stylesheet" href="prisma.css">
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>

<header class="header">
<div class="logo">
<img src="Logo.PNG" class="logo-img" alt="Prisma logo">
<span>PRISMA</span>
</div>

<p class="tagline">Más contexto · menos ruido</p>

<div class="stats">
📰 {medios_unicos} medios analizados ·
{datetime.now().strftime("%d/%m %H:%M")}
</div>
</header>

<nav class="menu">
<a href="index.html">Inicio</a>
<a href="sobre.html">Sobre Prisma</a>
</nav>

<div class="container">
"""


for i, grupo in enumerate(grupos, 1):

    num = len(grupo)
    tema = tema_dominante(grupo)

    consenso = (
    "🔥 Consenso total" if num >= 5 else
    "🟡 Cobertura amplia" if num >= 3 else
    "⚪ Tema emergente"
)

    html += f"""
    <div class="card">

    <div class="meta">
      <span>{consenso}</span>
      <span>#{i}</span>
    </div>

    <h2>{titular_representativo(grupo)}</h2>

    <div class="tema">🧭 {tema}</div>
    """

    if num > 1:
        html += resumen_ia(grupo)

    for idx in grupo:
        n = noticias[idx]
        html += f"""
        <p>
        <strong class="medio">{n['medio']}:</strong>
        <a href="{n['link']}" target="_blank">
        {n['titulo']}
        </a>
        </p>
        """

    html += """
    <button class="share"
    onclick="navigator.share?.({title:'Prisma',
    url:window.location.href})">
    Compartir
    </button>

    </div>
    """


html += "</div></body></html>"


with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("PRISMA generado correctamente 🚀")
