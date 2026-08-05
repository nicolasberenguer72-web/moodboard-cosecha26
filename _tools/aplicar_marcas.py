#!/usr/bin/env python3
"""Aplica un JSON de marcas exportado desde el tablón (botón flotante ⤓).

Estados soportados:
- "fuera"           -> borra la foto del repo y del estado
- "favorito_nuevo"  -> marca fav=true y lo apunta en pendientes_enmarcar.json
                       con el ratio de luz que habría que buscar

Uso:  python3 _tools/aplicar_marcas.py <marcas.json>
Después ejecuta rebuild_tablon.py y despliega.
"""
import json, os, sys
from PIL import Image

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
marcas = json.load(open(sys.argv[1]))
estado = json.load(open(os.path.join(BASE, "tablon_estado.json")))
por_key = {(e["fam"], e["file"]): e for e in estado}

pend_path = os.path.join(BASE, "pendientes_enmarcar.json")
pendientes = json.load(open(pend_path)) if os.path.exists(pend_path) else []

borradas, favs = 0, 0
for it in marcas.get("items", []):
    key = (it["familia"], it["archivo"])
    if it["estado"] == "fuera":
        p = os.path.join(BASE, "fotos", *key)
        if os.path.exists(p):
            os.remove(p); borradas += 1
        if key in por_key:
            estado.remove(por_key[key])
    elif it["estado"] == "favorito_nuevo":
        e = por_key.get(key)
        if e and not e.get("real"):
            e["fav"] = True; favs += 1
            p = os.path.join(BASE, "fotos", *key)
            if os.path.exists(p):
                im = Image.open(p)
                r = im.height / im.width
                pendientes.append({"familia": key[0], "archivo": key[1],
                                   "ratio_foto": round(r, 3),
                                   "buscar_luz": f"vertical ~{r:.2f} o girable ~{1/r:.2f} (sin copete)",
                                   "resolucion_foto": list(im.size)})

json.dump(estado, open(os.path.join(BASE, "tablon_estado.json"), "w"), indent=1, ensure_ascii=False)
json.dump(pendientes, open(pend_path, "w"), indent=1, ensure_ascii=False)
print(f"borradas: {borradas} | favoritos nuevos: {favs} | pendientes de marco: {len(pendientes)}")
print("Ahora: python3 _tools/rebuild_tablon.py  y despliega (ver CLAUDE.md)")
