#!/usr/bin/env python3
"""Regenera moodboard_cosecha26.html desde fotos/ + tablon_estado.json + plantilla.

- El orden del tablón = orden de tablon_estado.json.
- Fotos nuevas en fotos/ que no estén en el estado se añaden repartidas.
- Entradas cuyo archivo ya no exista se eliminan del estado.
- Piezas real=true usan su PNG de enmarcadas_sin_fondo/ (webp q72, 1200px, span 6).
- Resto: jpeg q55 hasta 820px; span: portada 4 / fav 3 / normal 2, con cap por resolución.

Uso:  python3 _tools/rebuild_tablon.py
"""
import base64, io, json, os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "_tools"))
from PIL import Image

FOTOS = os.path.join(BASE, "fotos")
ENM = os.path.join(BASE, "enmarcadas_sin_fondo")

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

items = []
for e in estado:
    if e.get("real") and e.get("png") and os.path.exists(os.path.join(ENM, e["png"])):
        im = Image.open(os.path.join(ENM, e["png"])).convert("RGBA")
        im.thumbnail((1200, 3000))
        buf = io.BytesIO(); im.save(buf, "WEBP", quality=72, method=6)
        src = "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()
        span = 6
    else:
        p = os.path.join(FOTOS, e["fam"], e["file"])
        im = Image.open(p).convert("RGB")
        W, H = im.size
        span = 4 if e.get("port") else (3 if e.get("fav") else 2)
        if not e.get("port") and W >= 1600: span += 1
        span = max(2, min(span, max(2, W // 230), 5))
        tw = min(W, span * 200, 820)
        im.thumbnail((tw, tw * 4))
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=55, optimize=True)
        src = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    items.append({"fam": e["fam"], "file": e["file"], "w": im.width, "h": im.height,
                  "span": span, "port": e.get("port", False), "fav": e.get("fav", False),
                  "real": e.get("real", False), "src": src})

plantilla = open(os.path.join(BASE, "_tools", "plantilla_tablon.html")).read()
html = plantilla.replace("__DATA__", json.dumps(items))
out = os.path.join(BASE, "moodboard_cosecha26.html")
open(out, "w").write(html)
open(os.path.join(BASE, "index.html"), "w").write(html)  # raiz para Vercel
json.dump(estado, open(os.path.join(BASE, "tablon_estado.json"), "w"), indent=1, ensure_ascii=False)
print(f"tablón regenerado: {len(items)} fotos | {sum(1 for i in items if i['real'])} enmarcadas | "
      f"{round(os.path.getsize(out)/1e6, 2)} MB")
