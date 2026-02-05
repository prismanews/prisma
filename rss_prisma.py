import feedparser
from datetime import datetime
from collections import defaultdict

# =========================
# FUENTES RSS
# =========================
feeds = {
    "El País": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
    "El Mundo": "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",
    "ABC": "https://www.abc.es/rss/feeds/abcPortada.xml",
    "La Vanguardia": "https://www.lavanguardia.com/rss/home.xml",
    "El Confidencial": "https://www.elconfidencial.com/rss/",
    "20 Minutos": "https://www.20minutos.es/rss/",
}

# =========================
# CLASIFICACIÓN DE TEMAS
# =========================
TEMAS = {
    "Reforma fiscal": ["reforma", "fiscal", "impuestos", "hacienda"],
    "Tipos del BCE": ["bce", "tipos", "interés", "europeo"],
    "Gobierno y política": ["gobierno", "psoe", "pp", "congreso", "senado"],
    "Economía": ["inflación", "economía", "crecimiento", "déficit"],
}

# =========================
# AGRUPADOR
# =========================
comparativas = defaultdict(list)

def detectar_tema(titulo):
    t = titulo.lower()
    for tema, claves in TEMAS.items():
        if any(c in t for c in claves):
            return tema
    return "Otros"

# =========================
# LECTURA RSS
# =========================
for medio, url in feeds.items():
    feed = feedparser.parse(url)
    if not feed.entries:
        continue

    noticia = feed.entries[0]
    titulo = noticia.title
    link = noticia.link
    tema = detectar_tema(titulo)

    comparativas[tema].append((medio, titulo, link))

# =========================
# GENERAR HTML
# =========================
fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

html = f"""<!DOCTYPE html>
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
  <p class="fecha">Actualizado: {fecha}</p>
</header>

<main>
"""

for tema, items in comparativas.items():
    if len(items) < 2:
        continue  # Solo comparativas reales

    html += f"""
<section class="tema">
  <h2>{tema}</h2>
  <div class="comparativa">
"""

    for medio, titulo, link in items:
        html += f"""
    <div class="card">
      <strong>{medio}</strong>
      <p>{titulo}</p>
      <a href="{link}" target="_blank">Leer noticia →</a>
    </div>
"""

    html += """
  </div>
</section>
"""

html += """
</main>
</body>
</html>
"""

# =========================
# ESCRIBIR ARCHIVO
# =========================
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Página generada correctamente")
