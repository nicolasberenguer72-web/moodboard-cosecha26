#!/usr/bin/env python3
"""Regenera el moodboard desde fotos/ + tablon_estado.json.

Genera DOS páginas y una carpeta de imágenes:
  index.html   -> pública: solo fotos, scroll y zoom. Sin controles.
  editor.html  -> privada: con ✕, ★ y exportador (para Nicolás y Gaspar).
  img/         -> las fotos como archivos sueltos (carga progresiva, CDN).

- El orden del tablón = orden de tablon_estado.json.
- Fotos nuevas en fotos/ que no estén en el estado se añaden repartidas.
- Entradas cuyo archivo ya no exista se eliminan del estado.
- Piezas real=true usan su PNG de enmarcadas_sin_fondo/ (webp, 1200px, span 6).
- Resto: webp hasta 820px; span: portada 4 / fav 3 / normal 2, cap por resolución.

Uso:  python3 _tools/rebuild_tablon.py
"""
import hashlib, json, os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "_tools"))
from PIL import Image

FOTOS = os.path.join(BASE, "fotos")
ENM = os.path.join(BASE, "enmarcadas_sin_fondo")
IMG = os.path.join(BASE, "img")

estado = json.load(open(os.path.join(BASE, "tablon_estado.json")))
existentes = set()
for fam in sorted(os.listdir(FOTOS)):
    d = os.path.join(FOTOS, fam)
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.lower().endswith((".jpg", ".png")):
                existentes.add((fam, f))

en_estado = {(e["fam"], e["file"]) for e in estado}
antes = len(estado)
estado = [e for e in estado if (e["fam"], e["file"]) in existentes]
if len(estado) != antes:
    print(f"eliminadas del estado (archivo ausente): {antes - len(estado)}")
nuevas = sorted(existentes - en_estado)
for i, (fam, f) in enumerate(nuevas):
    pos = (i + 1) * len(estado) // (len(nuevas) + 1)
    estado.insert(pos, {"fam": fam, "file": f, "port": False,
                        "fav": f.startswith(("fav_", "v5_", "v6_", "v7_")), "real": False})
    print("nueva en tablón:", fam, f)

os.makedirs(IMG, exist_ok=True)
vivos = set()
items = []
for e in estado:
    slug = re.sub(r"[^a-z0-9]+", "-", (e["fam"] + "-" + os.path.splitext(e["file"])[0]).lower()).strip("-")[:70]
    nombre = slug + ".webp"
    destino = os.path.join(IMG, nombre)
    vivos.add(nombre)

    if e.get("real") and e.get("png") and os.path.exists(os.path.join(ENM, e["png"])):
        origen = os.path.join(ENM, e["png"])
        im = Image.open(origen).convert("RGBA")
        im.thumbnail((1200, 3000))
        calidad, span = 72, 6
    else:
        origen = os.path.join(FOTOS, e["fam"], e["file"])
        im = Image.open(origen).convert("RGB")
        W = im.width
        span = 4 if e.get("port") else (3 if e.get("fav") else 2)
        if not e.get("port") and W >= 1600: span += 1
        span = max(2, min(span, max(2, W // 230), 5))
        im.thumbnail((min(W, 820), 3200))
        calidad = 62

    # solo reescribe si el origen cambió (rebuilds rápidos, caché de CDN estable)
    firma = hashlib.md5(open(origen, "rb").read()).hexdigest()[:10]
    marca = destino + ".md5"
    if not (os.path.exists(destino) and os.path.exists(marca)
            and open(marca).read().strip() == firma):
        im.save(destino, "WEBP", quality=calidad, method=6)
        open(marca, "w").write(firma)

    with Image.open(destino) as chk:
        w, h = chk.size
    items.append({"fam": e["fam"], "file": e["file"], "w": w, "h": h,
                  "span": span, "port": e.get("port", False), "fav": e.get("fav", False),
                  "real": e.get("real", False), "src": "img/" + nombre})

# limpia imágenes de fotos que ya no están
huerfanas = 0
for f in os.listdir(IMG):
    base_f = f[:-4] if f.endswith(".md5") else f
    if base_f not in vivos:
        os.remove(os.path.join(IMG, f)); huerfanas += 1

datos = json.dumps(items)
for plantilla, salida in [("plantilla_publica.html", "index.html"),
                          ("plantilla_tablon.html", "editor.html")]:
    p = os.path.join(BASE, "_tools", plantilla)
    if not os.path.exists(p):
        continue
    open(os.path.join(BASE, salida), "w").write(open(p).read().replace("__DATA__", datos))

json.dump(estado, open(os.path.join(BASE, "tablon_estado.json"), "w"), indent=1, ensure_ascii=False)
peso_img = sum(os.path.getsize(os.path.join(IMG, f)) for f in os.listdir(IMG) if f.endswith(".webp"))
print(f"tablón regenerado: {len(items)} fotos | {sum(1 for i in items if i['real'])} enmarcadas")
print(f"  index.html {os.path.getsize(os.path.join(BASE,'index.html'))//1024} KB · "
      f"editor.html {os.path.getsize(os.path.join(BASE,'editor.html'))//1024} KB · "
      f"img/ {peso_img/1e6:.1f} MB en {len(vivos)} archivos" + (f" · {huerfanas} huérfanas borradas" if huerfanas else ""))
