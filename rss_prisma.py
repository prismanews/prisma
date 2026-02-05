import feedparser
from datetime import datetime
from difflib import SequenceMatcher

feeds = {
    "El País": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
    "El Mundo": "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",
    "ABC": "https://www.abc.es/rss/feeds/abcPortada.xml",
    "La Vanguardia": "https://www.lavanguardia.com/rss/home.xml",
    "El Confidencial": "https://www.elconfidencial.com/rss/",
    "20 Minutos": "https://www.20minutos.es/rss/",
}

noticias = []

# ======================
# LEER RSS
# ======================
for medio, url in feeds.items():
    feed = feedparser.parse(url)
    if feed.entries:
        n = feed.entries[0]
        noticias.append({
            "medio": medio,
            "titulo": n.title,
            "link": n.link
        })

# ======================
# AGRUPAR POR SIMILITUD
# ======================
grupos = []

for noticia in noticias:
    colocado = False

    for grupo in grupos:
        base = grupo[0]["titulo"]

        similitud = SequenceMatcher(
            None,
            noticia["titulo"].lower(),
            base.lower()
        ).ratio()

        if similitud > 0.45:
            grupo.append(noticia)
            colocado = True
            break

    if not colocado:
        grupos.append([noticia])

# ======================
# HTML
# ======================
fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

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
<p>Actualizado: {fecha}</p>
</header>

<main>
"""

for grupo in grupos:
    if len(grupo) < 2:
        continue

    html += "<section><h2>Comparativa de medios</h2>"

    for n in grupo:
        html += f"""
        <div class="card">
        <strong>{n['medio']}</strong>
        <p>{n['titulo']}</p>
        <a href="{n['link']}">Leer noticia →</a>
        </div>
        """

    html += "</section>"

html += "</main></body></html>"

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Página generada")
