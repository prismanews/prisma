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


# ---------- REFERENCIAS NLP SESGO (MEJORADAS PRO) ----------

referencias_politicas = {
    "progresista": modelo.encode([
        # español
        "derechos sociales igualdad feminismo justicia social diversidad políticas públicas bienestar",
        "progresismo cambio climático políticas sociales regulación inclusión servicios públicos",

        # inglés
        "social justice equality progressive politics climate action diversity welfare public services",
        "left wing policies regulation social rights inclusion government intervention",

        # internacional neutro
        "environmental protection social equality human rights public healthcare welfare state"
    ]),

    "conservador": modelo.encode([
        # español
        "seguridad fronteras defensa tradición economía mercado estabilidad control migratorio",
        "valores tradicionales seguridad nacional impuestos bajos orden liberalismo económico",

        # inglés
        "border security national defense free market traditional values low taxes immigration control",
        "conservative policies economic freedom national identity law and order",

        # internacional neutro
        "fiscal responsibility strong military traditional culture business friendly policies"
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

    # 🌏 Asia
    "SCMP Hong Kong": "https://www.scmp.com/rss/91/feed",
    "Japan Times": "https://www.japantimes.co.jp/feed/",
    "China Daily": "http://www.chinadaily.com.cn/rss/world_rss.xml",

    # 🌎 América Latina internacional
    "Clarin": "https://www.clarin.com/rss/lo-ultimo/",
    "El Tiempo CO": "https://www.eltiempo.com/rss/colombia.xml",
    "Granma": "http://www.granma.cu/feed",
    "Cubadebate": "http://www.cubadebate.cu/feed/",
    "Prensa Latina": "https://www.prensa-latina.cu/feed/"
}

KEYWORDS_ESPANA = [

    # ----- País básico (multilenguaje) -----
    "españa","espana","spain",
    "espagne","spanien","spagna","espanya",
    "西班牙","スペイン","스페인",

    # gentilicios
    "spanish","español","spaniard","spaniards",
    "espagnol","espagnols",
    "spanisch",
    "spagnolo","spagnoli",
    "espanhol","espanhóis",

    # ----- Ciudades internacionales -----
    "madrid","barcelona","valencia","sevilla","seville",
    "bilbao","zaragoza","malaga","málaga",
    "granada","ibiza","mallorca","majorca",

    # ----- Regiones / territorios -----
    "catalonia","cataluña","catalunya",
    "basque country","pais vasco",
    "andalusia","andalucía",
    "galicia",
    "balearic islands","canary islands",
    "islas canarias",

    # ----- Política española internacional -----
    "spanish government","gobierno español",
    "gobierno de españa",
    "pedro sanchez","sánchez","feijoo",
    "vox spain","psoe","pp spain",

    # francés / alemán política frecuente
    "gouvernement espagnol",
    "regierung spanien",

    # italiano / portugués política
    "governo spagnolo",
    "governo espanhol",

    # ----- Economía / turismo -----
    "spanish economy","economía española",
    "economia spagnola","economia espanhola",
    "spanische wirtschaft",

    "tourism spain","turismo españa",
    "turismo spagna","turismo espanhol",

    "housing spain","crisis vivienda españa",

    # ----- Cultura / deporte -----
    "la liga",
    "real madrid","fc barcelona",
    "spanish football",
    "fútbol español",

    # ----- Geopolítica / ubicación -----
    "iberian peninsula","península ibérica",
    "iberia",
    "southern europe",
    "mediterranean spain",
    "spain eu","spanish presidency eu",
    "nato spain"
]
# ---------- LIMPIEZA ----------

stopwords = {
    # artículos / básicos español
    "el","la","los","las","un","una","unos","unas",
    "de","del","al","a","en","por","para","con","sin",
    "sobre","entre","hasta","desde",

    # conjunciones / conectores
    "y","o","e","ni","que","como","pero","aunque",
    "porque","ya","también","solo",

    # posesivos / pronombres
    "su","sus","se","lo","le","les","esto","esta",
    "estos","estas","ese","esa","esos","esas",

    # tiempo típico noticias
    "hoy","ayer","mañana","tras","antes","después",
    "última","últimas","último","últimos",

    # palabras periodísticas vacías
    "dice","según","afirma","asegura","explica",
    "parte","caso","forma","vez","años",

    # inglés frecuente en feeds
    "the","a","an","of","to","in","on","for","with",
    "and","or","but","from","by","about","as",
    "after","before","over","under",

    # prensa internacional típica
    "says","said","report","reports","new","latest",
    "update","breaking","news"
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
        feed = feedparser.parse(url, request_headers={'User-Agent': 'Mozilla/5.0'})
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

# ---------- INTERNACIONAL ESPAÑA (solo nueva página) ----------

noticias_espana = []

for medio, url in feeds_internacionales.items():
    try:
        feed = feedparser.parse(url, request_headers={'User-Agent': 'Mozilla/5.0'})
        if feed.bozo:
            continue

        for entry in feed.entries[:16]:

            # evita feeds rotos o incompletos
            if "title" not in entry or "link" not in entry:
                continue

            titulo = limpiar_html(entry.title)

            if any(k in titulo.lower() for k in KEYWORDS_ESPANA):
                noticias_espana.append({
                    "medio": medio,
                    "titulo": titulo,
                    "link": entry.link
                })

    except Exception:
        pass

# quitar duplicados internacionales
noticias_espana = list({n["link"]: n for n in noticias_espana}.values())
noticias_espana.sort(key=lambda x: len(x["titulo"]), reverse=True)

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

    comunes = [p for p, _ in Counter(palabras).most_common(5)]

    # elimina palabras muy genéricas
    blacklist = {"gobierno", "españa", "hoy", "última", "últimas"}
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
        "gobierno","españa","última","hoy","tras",
        "según","dice","años","parte"
    }

    comunes = [p for p in comunes if p not in blacklist][:2]

    if not comunes:
        return ""

    tema = " y ".join(comunes)

    return f"""
<p class="resumen">
🧠 <b>Resumen IA:</b>
La actualidad informativa se centra en <b>{tema}</b>.
</p>
"""
    
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

<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="googlebot" content="index, follow">
<link rel="canonical" href="https://prismanews.github.io/prisma/">

<!-- Open Graph -->
<meta property="og:title" content="Prisma noticias IA">
<meta property="og:description" content="Comparador inteligente de noticias con IA">
<meta property="og:image" content="Logo.PNG">
<meta property="og:type" content="website">
<meta property="og:url" content="https://prismanews.github.io/prisma/">
<meta http-equiv="content-language" content="es">

<!-- SEO extra -->
<meta name="theme-color" content="#ffffff">
<meta name="author" content="Prisma News">

<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">

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

<p class="gancho">
Comparador inteligente de medios · Detecta sesgos · Entiende la actualidad mejor
</p>

<p style="font-size:14px;color:#666;margin-top:6px;">
Análisis automático de titulares de más de 25 medios para detectar tendencias informativas y comparar enfoques editoriales.
</p>

<div class="stats">
📰 {medios_unicos} medios analizados ·
<time datetime="{fecha_iso}">Actualizado: {fecha_legible}</time>
</div>

<nav class="nav">
<a href="index.html?v={cachebuster}">Inicio</a>
<a href="sobre.html">Sobre Prisma</a>
<a href="espana.html?v={cachebuster}">España en el mundo</a>
<a href="mailto:ovalero@gmail.com?subject=Contacto%20Prisma">
Contacto
</a>
</nav>
</header>

<div class="container">
"""

for i, grupo in enumerate(grupos, 1):

    clase = "card"
    if i == 1:
        clase = "card portada"
    html += f"""
<div class="{clase}">

<h2>{titular_prisma(grupo)}</h2>
{resumen_prisma(grupo)}
{sesgo_politico(grupo)} 
"""

    for idx in grupo[:6]:
        n = noticias[idx]
        html += f"""
<p>
<strong>{n['medio']}:</strong>
<a href="{n['link']}" target="_blank" rel="noopener noreferrer">{n['titulo']}</a>
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
<url><loc>https://prismanews.github.io/prisma/espana.html</loc></url>
</urlset>
"""

with open("sitemap.xml", "w", encoding="utf-8") as f:
    f.write(sitemap)

# ---------- HTML ESPAÑA EN EL MUNDO ----------

html_espana = f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="robots" content="index, follow">
<meta name="googlebot" content="index, follow">
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
<a href="mailto:ovalero@gmail.com?subject=Contacto%20Prisma">
Contacto
</a>
</nav>
</header>

<div class="container">
<div class="card portada">
<h2>🌍 España en el mundo</h2>
<p>Visión de la prensa internacional sobre España.</p>
"""

for n in noticias_espana[:40]:
    html_espana += f"""
<p>
<strong>{n['medio']}:</strong>
<a href="{n['link']}" target="_blank" rel="noopener noreferrer">
{n['titulo']}
</a>
</p>
"""

html_espana += "</div></div></body></html>"

with open("espana.html", "w", encoding="utf-8") as f:
    f.write(html_espana)

# ---------- ROBOTS ----------

robots = """User-agent: *
Allow: /

Sitemap: https://prismanews.github.io/prisma/sitemap.xml
"""

with open("robots.txt", "w", encoding="utf-8") as f:
    f.write(robots)


print("PRISMA NLP PRO generado 🚀")
