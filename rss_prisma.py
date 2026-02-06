import feedparser
import re
from datetime import datetime
from collections import Counter

feeds = {
    "El País": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
    "El Mundo": "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",
    "ABC": "https://www.abc.es/rss/feeds/abcPortada.xml",
    "La Vanguardia": "https://www.lavanguardia.com/rss/home.xml",
    "20 Minutos": "https://www.20minutos.es/rss/",
    "eldiario.es": "https://www.eldiario.es/rss/",
    "El Confidencial": "https://www.elconfidencial.com/rss/",
    "Público": "https://www.publico.es/rss/",
    "OK Diario": "https://okdiario.com/feed/",
    "Libertad Digital": "https://www.libertaddigital.com/rss/",
    "Europa Press": "https://www.europapress.es/rss/rss.aspx",
    "La Sexta": "https://www.lasexta.com/rss.xml",
    "La Razón": "https://www.larazon.es/rss/",
    "El Español": "https://www.elespanol.com/rss/",
    "RTVE": "https://www.rtve.es/rss/",
    "Expansión": "https://e00-expansion.uecdn.es/rss/portada.xml",
    "Cinco Días": "https://cincodias.elpais.com/seccion/rss/portada/",
    
    # Regional / prensa general
    "La Voz de Galicia": "https://www.lavozdegalicia.es/rss/portada.xml",
    "El Periódico de Extremadura": "https://www.elperiodicoextremadura.com/rss/portada.xml",
    "La Nueva España": "https://www.lne.es/rss/portada.xml",
    "Heraldo de Aragón": "https://www.heraldo.es/rss/portada/",
    "El Periódico de Catalunya": "https://www.elperiodico.com/es/rss/rss_portada.xml",
    "Levante EMV": "https://www.levante-emv.com/rss/portada.xml",
    "Diario de Sevilla": "https://www.diariodesevilla.es/rss/",
    "Diario de Cádiz": "https://www.diariodecadiz.es/rss/",
    "El Periódico de Aragón": "https://www.elperiodicodearagon.com/rss/portada.xml",

    # Deportes
    "AS": "https://as.com/rss/tags/ultimas_noticias.xml",
    "Marca": "https://e00-marca.uecdn.es/rss/portada.xml",
}

stopwords = {
    "el","la","los","las","de","del","en","para","por","con",
    "sin","un","una","unos","unas","al","a","y","o","que",
    "se","su","sus","ante","como","más","menos"
}

def limpiar(texto):
    texto = texto.lower()
    texto = re.sub(r'[^\w\s]', '', texto)
    palabras = texto.split()
    resultado = []

    for p in palabras:
        if p.endswith("s"):
            p = p[:-1]
        if p not in stopwords and len(p) > 3:
            resultado.append(p)

    return resultado

def similares(t1, t2):
    p1 = limpiar(t1)
    p2 = limpiar(t2)

    if not p1 or not p2:
        return False

    # frecuencia de palabras
    c1 = Counter(p1)
    c2 = Counter(p2)

    # producto escalar (cosine simplificado)
    comunes = set(c1) & set(c2)
    num = sum(c1[w] * c2[w] for w in comunes)

    # norma de cada vector
    den1 = sum(v*v for v in c1.values()) ** 0.5
    den2 = sum(v*v for v in c2.values()) ** 0.5

    if not den1 or not den2:
        return False

    similitud = num / (den1 * den2)

    return similitud >= 0.20

def titular_general(grupo):
    return max(grupo, key=lambda n: len(n["titulo"]))["titulo"]

def resumen_ia(grupo):
    palabras = []

    for n in grupo:
        palabras += limpiar(n["titulo"])

    comunes = [p for p, _ in Counter(palabras).most_common(3)]

    if not comunes:
        return ""

    tema = ", ".join(comunes)

    return f"""
    <div class="resumen">
    <strong>Lectura IA:</strong>
    La noticia gira en torno a <b>{tema}</b>.
   </div>
    """

# recoger noticias
noticias = []

for medio, url in feeds.items():
    try:
        feed = feedparser.parse(url)
        if feed.entries:
            noticias.append({
                "medio": medio,
                "titulo": feed.entries[0].title,
                "link": feed.entries[0].link
            })
    except:
        pass

# agrupar noticias similares
grupos = []

for noticia in noticias:
    colocado = False
    for grupo in grupos:
        if any(similares(noticia["titulo"], n["titulo"]) for n in grupo):
            grupo.append(noticia)
            colocado = True
            break
    if not colocado:
        grupos.append([noticia])

# ordenar por impacto (más medios primero)
grupos.sort(key=len, reverse=True)

max_medios = max(len(g) for g in grupos)

total_medios = sum(len(g) for g in grupos)

# HTML
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

<header class="cabecera">
        <h1><img src="Logo.PNG" class="logo-inline"> PRISMA</h1>
        <p>Más contexto, menos ruido. La actualidad sin sesgos</p>
        <p>Actualizado: {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
        <div class="contador">📰 {total_medios} medios analizados hoy</div>
</header>

<div class="container">
"""

for i, grupo in enumerate(grupos, 1):
    html += "<div class='card'>"
    if len(grupo) > 1:
        html += f"<div class='ranking'>#{i} noticia del día</div>"

    if len(grupo) == max_medios and len(grupo) > 1:
        html += "<div class='trending'>🔥 Trending</div>"
        
    # Indicador consenso
    num = len(grupo)

    if num >= 4:
        consenso = "🟢 Consenso alto"
    elif num >= 2:
        consenso = "🟡 Cobertura variada"
    else:
        consenso = "🔴 Solo un medio"

    html += f"<div class='consenso'>{consenso} — {num} medios</div>"

    html += f"<div class='impacto'>{len(grupo)} medios hablan de esto</div>"
    
    html += f"<h2>{titular_general(grupo)}</h2>"

    html += f"<div class='impacto'>{len(grupo)} medios hablan de esto</div>"
    
    if len(grupo) > 1:
        html += resumen_ia(grupo)

    for n in grupo:
        html += f"""
        <p><strong class="medio">{n['medio']}:</strong>
        <a href="{n['link']}" target="_blank">{n['titulo']}</a></p>
        """

    html += "</div>"

html += """
</div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Página generada con análisis IA")
