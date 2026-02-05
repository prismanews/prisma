import feedparser
import re
from datetime import datetime

# ---------- FEEDS ----------
feeds = {
    "El País": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
    "El Mundo": "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",
    "ABC": "https://www.abc.es/rss/feeds/abcPortada.xml",
    "La Vanguardia": "https://www.lavanguardia.com/rss/home.xml",
    "20 Minutos": "https://www.20minutos.es/rss/",
    "eldiario.es": "https://www.eldiario.es/rss/",
    "El Confidencial": "https://www.elconfidencial.com/rss/",
    "Público": "https://www.publico.es/rss/",
    "La Razón": "https://www.larazon.es/rss/",
    "OK Diario": "https://okdiario.com/feed/",
    "Libertad Digital": "https://www.libertaddigital.com/rss/portada.xml"
}

# ---------- STOPWORDS ----------
stopwords = {
    "el","la","los","las","de","del","en","para","por",
    "con","sin","un","una","unos","unas","al","a",
    "y","o","que","se","su","sus"
}

def limpiar(texto):
    texto = texto.lower()
    texto = re.sub(r'[^\w\s]', '', texto)
    palabras = texto.split()
    return set(p for p in palabras if p not in stopwords and len(p) > 3)

def similares(t1, t2):
    p1 = limpiar(t1)
    p2 = limpiar(t2)
    if not p1 or not p2:
        return False
    inter = len(p1 & p2)
    return inter >= 2

# ---------- LEER NOTICIAS ----------
noticias = []

for medio, url in feeds.items():
    try:
        feed = feedparser.parse(url)
        if feed.entries:
            n = feed.entries[0]
            noticias.append({
                "medio": medio,
                "titulo": n.title,
                "link": n.link
            })
    except:
        pass

# ---------- AGRUPAR ----------
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

# ---------- GENERAR HTML ----------
html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Prisma</title>
<link rel="stylesheet" href="prisma.css">
</head>
<body>
<header>
<h1>PRISMA</h1>
<p>La misma noticia observada desde distintos ángulos</p>
<p>Actualizado: {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
</header>

<div class="container">
"""

for grupo in grupos:
    html += "<div class='card'>"

    if len(grupo) > 1:
        html += "<h2>Comparativa de medios</h2>"
    else:
        html += "<h2>Otros titulares</h2>"

    for n in grupo:
        html += f"""
        <p><strong>{n['medio']}:</strong>
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

print("Página generada correctamente")
