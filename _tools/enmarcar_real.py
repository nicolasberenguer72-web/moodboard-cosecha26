"""Compositor de fotos dentro de marcos de catálogo (La Cosecha 26).

Uso típico:
    from enmarcar_real import componer
    componer("marco.jpg", "foto.jpg", "salida.png")

- Quita el fondo claro exterior (flood desde bordes + limpieza global de claros,
  salvo solid=True para marcos macizos: preserva brillos especulares).
- Detecta la luz (hueco interior) sellando calados por cierre morfológico y
  rellenando huecos; las motas de azogue se absorben como componentes pequeñas.
- interior_rect=(x0,y0,x1,y1) en fracciones fuerza la luz a mano (espejos muy
  moteados, forros pintados, rejillas). interior_manual=(cx,cy,rx,ry) = elipse.
- La foto entra en cover con recorte centrado; pre-recorta tú la foto si
  necesitas anclar el sujeto (ver CLAUDE.md).
- REGLA DURA: marco y foto SIEMPRE a máxima resolución de origen; max_w solo
  limita el lienzo final (usa 2200-2400).
"""
import numpy as np
from collections import deque
from PIL import Image, ImageFilter


def flood(ok, seeds):
    H, W = ok.shape
    vis = np.zeros((H, W), bool)
    dq = deque()
    for y, x in seeds:
        if 0 <= y < H and 0 <= x < W and ok[y, x] and not vis[y, x]:
            vis[y, x] = True; dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        if y > 0 and ok[y-1, x] and not vis[y-1, x]: vis[y-1, x] = True; dq.append((y-1, x))
        if y < H-1 and ok[y+1, x] and not vis[y+1, x]: vis[y+1, x] = True; dq.append((y+1, x))
        if x > 0 and ok[y, x-1] and not vis[y, x-1]: vis[y, x-1] = True; dq.append((y, x-1))
        if x < W-1 and ok[y, x+1] and not vis[y, x+1]: vis[y, x+1] = True; dq.append((y, x+1))
    return vis


def componer(frame_path, foto_path, out_path, bg_thresh=152, interior_tol=45, max_w=2200,
             interior_manual=None, interior_rect=None, grande_frac=0.01, solid=False):
    fr = Image.open(frame_path).convert("RGB")
    if fr.width > max_w:
        fr = fr.resize((max_w, round(fr.height*max_w/fr.width)), Image.LANCZOS)
    a = np.asarray(fr).astype(int)
    H, W, _ = a.shape
    lum = a.mean(axis=2)
    sat = a.max(axis=2) - a.min(axis=2)

    okbg = (lum > bg_thresh) & (sat < 52)
    ext = flood(okbg, [(2,2),(2,W-3),(H-3,2),(H-3,W-3),(2,W//2),(H-3,W//2),(H//2,2),(H//2,W-3)])
    if not solid:
        # blancos encerrados (huecos de calado): fuera tambien
        ext = ext | ((lum > 172) & (sat < 40))

    if interior_rect:
        x0, y0, x1, y1 = interior_rect
        inte = np.zeros((H, W), bool)
        inte[int(y0*H):int(y1*H), int(x0*W):int(x1*W)] = True
    elif interior_manual:
        cx, cy, rx, ry = interior_manual
        yy, xx = np.mgrid[0:H, 0:W]
        inte = (((xx - cx*W)/(rx*W))**2 + ((yy - cy*H)/(ry*H))**2) <= 1.0
    else:
        # hueco-relleno: sella calados y encuentra la luz
        body = ~okbg
        closed = np.asarray(Image.fromarray((body*255).astype(np.uint8))
                            .filter(ImageFilter.MaxFilter(15))) > 127
        out2 = flood(~closed, [(2,2),(2,W-3),(H-3,2),(H-3,W-3),(2,W//2),(H-3,W//2),(H//2,2),(H//2,W-3)])
        holes = ~closed & ~out2
        cy, cx = H//2, W//2
        if holes[cy, cx]:
            zona = flood(holes, [(cy, cx)])
            zmax = np.asarray(Image.fromarray((zona*255).astype(np.uint8))
                              .filter(ImageFilter.MaxFilter(13))) > 127
            lab = np.zeros((H, W), int); cur = 0
            for y0 in range(0, H, 6):
                for x0 in range(0, W, 6):
                    if body[y0, x0] and lab[y0, x0] == 0:
                        cur += 1
                        dq2 = deque([(y0, x0)]); lab[y0, x0] = cur
                        while dq2:
                            yq, xq = dq2.popleft()
                            for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
                                ny, nx = yq+dy, xq+dx
                                if 0 <= ny < H and 0 <= nx < W and body[ny, nx] and lab[ny, nx] == 0:
                                    lab[ny, nx] = cur; dq2.append((ny, nx))
            sizes = np.bincount(lab.ravel())
            grandes = [i for i, sz in enumerate(sizes) if i and sz > grande_frac*H*W]
            body_main = np.isin(lab, grandes)
            inte = zmax & ~body_main
        else:
            # luz oscura (trasera opaca): flood clasico por color
            c0 = a[cy-10:cy+10, cx-10:cx+10].reshape(-1, 3).mean(axis=0)
            inte = flood(np.abs(a - c0).sum(axis=2) < interior_tol*3, [(cy, cx)])
            if inte.sum() < 0.05*H*W:
                inte = flood(np.abs(a - c0).sum(axis=2) < interior_tol*4.5, [(cy, cx)])

    ys, xs = np.nonzero(inte)
    bx0, bx1, by0, by1 = xs.min(), xs.max(), ys.min(), ys.max()
    bw, bh = bx1-bx0+1, by1-by0+1

    foto = Image.open(foto_path).convert("RGB")
    fr_ratio, f_ratio = bw/bh, foto.width/foto.height
    if f_ratio > fr_ratio:
        nh, nw = bh, round(bh*f_ratio)
    else:
        nw, nh = bw, round(bw/f_ratio)
    foto_r = foto.resize((nw, nh), Image.LANCZOS)
    foto_c = foto_r.crop(((nw-bw)//2, (nh-bh)//2, (nw-bw)//2+bw, (nh-bh)//2+bh))

    m_int = Image.fromarray((inte*255).astype(np.uint8))
    er = m_int.filter(ImageFilter.MinFilter(15))
    banda = np.clip(np.asarray(m_int, int) - np.asarray(er, int), 0, 255)
    banda_img = Image.fromarray(banda.astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))
    shadow_f = 1.0 - 0.45*(np.asarray(banda_img, float)/255.0)

    canvas = np.zeros((H, W, 4), np.uint8)
    fnp = np.asarray(foto_c, float)
    sh = shadow_f[by0:by1+1, bx0:bx1+1][..., None]
    fnp = np.clip(fnp*sh, 0, 255).astype(np.uint8)
    m_in_b = (np.asarray(m_int)[by0:by1+1, bx0:bx1+1] > 127)
    region = canvas[by0:by1+1, bx0:bx1+1]
    region[m_in_b, :3] = fnp[m_in_b]
    region[m_in_b, 3] = 255

    ext = ext & ~inte
    marco_mask = ~(ext | inte)
    canvas[marco_mask, :3] = a[marco_mask]
    canvas[marco_mask, 3] = 255

    out = Image.fromarray(canvas)
    alpha = out.getchannel("A").filter(ImageFilter.GaussianBlur(0.8))
    out.putalpha(alpha)
    out.save(out_path)
    return out.size


def medir_luz(path, bg_thresh=152):
    """Devuelve el ratio alto/ancho de la luz de un marco, o None."""
    fr = Image.open(path).convert("RGB")
    sc = max(1, fr.width // 800)
    a = np.asarray(fr.resize((fr.width//sc, fr.height//sc))).astype(int)
    H, W, _ = a.shape
    lum = a.mean(axis=2); sat = a.max(axis=2) - a.min(axis=2)
    body = ~((lum > bg_thresh) & (sat < 52))
    closed = np.asarray(Image.fromarray((body*255).astype(np.uint8))
                        .filter(ImageFilter.MaxFilter(15))) > 127
    out2 = flood(~closed, [(2,2),(2,W-3),(H-3,2),(H-3,W-3)])
    holes = ~closed & ~out2
    if not holes[H//2, W//2]: return None
    zona = flood(holes, [(H//2, W//2)])
    if zona.sum() < 0.04*H*W: return None
    ys, xs = np.nonzero(zona)
    return (ys.max()-ys.min())/(xs.max()-xs.min())
