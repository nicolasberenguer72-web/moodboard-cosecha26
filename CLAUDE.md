# Moodboard La Cosecha 26 — manual de operación

Repo compartido Nicolás ↔ Gaspar. Cada uno trabaja con su Claude Code; el tablón
público se sirve en **https://moodboard-cosecha26.vercel.app** y se actualiza al
hacer push a `main` (integración GitHub→Vercel).

## Qué es cada cosa

- `fotos/<familia>/` — las fotos del moodboard, una carpeta por familia estética
  (01_corte_y_jardin … 16_congo_portobelo). Nombres descriptivos en kebab-case;
  prefijo `fav_` = aportación directa de Nicolás/Gaspar.
- `tablon_estado.json` — orden del tablón y flags por foto: `port` (favorita
  histórica), `fav` (aportada a mano), `real` (lleva marco de subasta) + `png`.
- `enmarcadas_sin_fondo/` — composiciones foto+marco (PNG con alfa). Son las
  piezas grandes del tablón.
- `marcos_fuente/` — fotos de catálogo de los marcos en bruto, con prefijo de
  procedencia (ansorena__, segre__, sothebys__, bada__, anticstore__, nbn__).
- `marcos_procedencia.json` — qué lote de qué casa es cada marco, con medidas.
- `moodboard_cosecha26.html` — el tablón compilado (autocontenido, NO editar a
  mano: se regenera).
- `_tools/` — las herramientas. `plantilla_tablon.html` es la única fuente de
  verdad del diseño.
- `criba_*.json`, `favoritos_*.json`, `pendientes_enmarcar.json` — histórico de
  decisiones y cola de favoritos esperando marco.

## Operaciones

**Añadir fotos** (las que Gaspar/Nicolás bajen con título descriptivo):
```bash
cp ~/Downloads/"mi foto barroca.jpg" "fotos/07_glam_electrico/fav_mi-foto-barroca.jpg"
python3 _tools/rebuild_tablon.py     # la detecta y la mete repartida
```
Formatos webp/avif: convertir antes con `sips -s format jpeg archivo --out salida.jpg`.

**Quitar fotos / marcar favoritos**: en el tablón web, hover → ✕ (fuera) o
★ (favorito nuevo). Al terminar, el botón flotante ⤓ exporta `marcas_moodboard.json`.
```bash
python3 _tools/aplicar_marcas.py ~/Downloads/marcas_moodboard.json
python3 _tools/rebuild_tablon.py
```

**Enmarcar un favorito** (protocolo marcos reales):
1. Mira su ratio en `pendientes_enmarcar.json` (alto/ancho de la foto).
2. Busca un marco de subasta/anticuario cuya LUZ (hueco interior, no medidas
   totales) tenga ese ratio ±6%. Girar un marco 90º vale SOLO si no tiene
   copete/crestería/lazo. `from enmarcar_real import medir_luz` mide el ratio
   directamente sobre la foto del marco si el catálogo no da medidas.
3. REGLA DURA de resolución: marco ≥1400px y foto a su máxima resolución
   encontrable. En plataformas Labelgrup (Ansorena/Alcalá) el original está en
   la URL de imagen quitando `/thumbs/<n>/`; Segre tope 600px (evitar);
   Sotheby's sirve 4096. Desconfía de archivos <100KB.
4. Componer y revisar SIEMPRE el resultado a ojo antes de publicar:
```python
import sys; sys.path.insert(0, "_tools")
from enmarcar_real import componer
componer("marcos_fuente/xxx.jpg", "fotos/fam/foto.jpg",
         "enmarcadas_sin_fondo/real_nombre.png", max_w=2400)
# marcos macizos: solid=True (preserva brillos). Espejos moteados/forros:
# interior_rect=(x0,y0,x1,y1) en fracciones. Elipse: interior_manual=(cx,cy,rx,ry).
```
5. En `tablon_estado.json` pon a esa foto `"real": true, "png": "real_nombre.png"`,
   añade el marco bruto a `marcos_fuente/` y su ficha a `marcos_procedencia.json`.
6. `python3 _tools/rebuild_tablon.py`

**Desplegar** (tras cualquier cambio):
```bash
git add -A && git commit -m "descripción corta" && git push
```
El push publica solo (Vercel). Sin acceso a Vercel no hay problema: el push basta.

## Reglas de la casa

- El tablón no lleva ni una palabra visible: solo fotos, ✕ y ★ en hover.
- Sin marcas de agua (Getty/Alamy/Bridgeman) salvo decisión explícita.
- Nada de reducir resolución en pasos intermedios; la única compresión es la
  final del rebuild. Verifica nitidez al 100% antes de publicar una enmarcada.
- Los sujetos siempre DETRÁS de la luz del marco, centrados en el hueco.
- Estética de referencia: exceso barroco transversal (horror vacui), personas
  con carisma antes que objetos o arquitectura vacía.
- Cambios gordos (quitar familias, rehacer marcos de otro) → consultar al otro
  socio por WhatsApp antes.
