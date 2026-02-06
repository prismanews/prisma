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
    return [p for p in palabras if p not in stopwords and len(p) > 3]

def similares(t1, t2):
    p1 = set(limpiar(t1))
    p2 = set(limpiar(t2))
    return len(p1 & p2) >= 2

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
    Coinciden varios medios en el hecho principal,
    aunque cambian el enfoque editorial y los matices.
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
        if similares(noticia["titulo"], grupo[0]["titulo"]):
            grupo.append(noticia)
            colocado = True
            break
    if not colocado:
        grupos.append([noticia])

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

<header>
<h1>PRISMA</h1>
<p>Misma noticia, distintos ángulos</p>
<p>Actualizado: {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
</header>

<div class="container">
"""

for grupo in grupos:
    html += "<div class='card'>"

    html += f"<h2>{titular_general(grupo)}</h2>"

    if len(grupo) > 1:
        html += resumen_ia(grupo)

    for n in grupo:
        html += f"""
        <p><span class="medio">{n['medio']}</span>:
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
