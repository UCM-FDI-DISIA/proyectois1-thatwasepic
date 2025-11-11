from bs4 import BeautifulSoup
from markdown import markdown

# Usa el renderer estándar de markdown con extensiones útiles
def markdown_renderer(text):
    return markdown(
        text,
        extensions=[
            'fenced_code',    # bloques de código
            'tables',         # tablas
            'toc',            # genera IDs en los encabezados + tabla de contenidos
            'attr_list',      # permite {#id .clase}
            'codehilite'      # resaltado de sintaxis
        ]
    )

def get_headings(html):
    """Extrae los encabezados <h1>-<h3> del HTML y genera estructura jerárquica."""
    soup = BeautifulSoup(html, "html.parser")
    headings = []
    stack = []

    for tag in soup.find_all(["h1", "h2", "h3"]):
        item = {
            "text": tag.get_text(strip=True),
            "link": tag.get("id") or "",
            "level": int(tag.name[1]),
            "children": []
        }

        # Estructura jerárquica
        while stack and stack[-1]["level"] >= item["level"]:
            stack.pop()
        if stack:
            stack[-1]["children"].append(item)
        else:
            headings.append(item)
        stack.append(item)

    return headings
