"""Gera uma PCB reversível no formato Corne (3x6 + 3 polegares) usando
os footprints da PCB do dust (Kailh X / PG1425, XIAO reversível, interruptor
de energia). Versão sem fios (XIAO BLE): o conector JST-XH da bateria e o furo
para os fios são acrescentados depois por finalizar_pcb.py. Uso:

    python gerar_pcb.py <caminho/para/dust.kicad_pcb>

Saídas (na pasta deste script): corne-x.kicad_pcb e preview.svg
"""
import copy
import math
import os
import re
import sys
import uuid

from shapely import affinity
from shapely.geometry import MultiPoint, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp import dumps, find, parse  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

# Espaçamento usado no dust para os Kailh X (mm)
SX, SY = 18.0, 17.0
# Stagger das colunas do Corne (crkbd), em unidades, para baixo a partir da coluna mais alta.
# c0 = pinky externo ... c5 = indicador interno
STAGGER_U = [0.375, 0.375, 0.125, 0.0, 0.125, 0.25]
X0, Y0 = 100.0, 100.0
ROWS = ['r3', 'r2', 'r1']  # topo, home, baixo (r0 = polegares), como no dust
CAP = (17.5, 16.5)  # tamanho do keycap Kailh X (para checagem de colisão)
DIODE_DY = 4.75  # posição do díodo em relação ao centro da tecla (igual ao dust)

# XIAO: pino do dust -> pino desta placa (D0..D5 = colunas, D6 = tx, D7..D10 = linhas)
XIAO_NETS = {'c4': 'c5', 'c3': 'c4', 'c2': 'c3', 'c1': 'c2', 'c0': 'c1', 'D5': 'c0'}


def rot(x, y, a):
    """Roda (x, y) pelo ângulo a do KiCad (graus, anti-horário no ecrã, y para baixo)."""
    r = math.radians(a)
    return x * math.cos(r) + y * math.sin(r), -x * math.sin(r) + y * math.cos(r)


def fmt(v):
    s = f'{v:.6f}'.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


# ---------------------------------------------------------------- layout

def layout():
    keys = []
    for c in range(6):
        x = X0 + c * SX
        for r, row in enumerate(ROWS):
            y = Y0 + STAGGER_U[c] * SY + r * SY
            keys.append(dict(x=x, y=y, a=0.0, col=c, row=row))

    def bottom(c):
        return next(k for k in keys if k['col'] == c and k['row'] == 'r1')

    # Polegares: o primeiro debaixo do indicador, os outros abrem em leque (0°, -15°, -30°),
    # cada um a rodar a partir do canto inferior direito do anterior.
    b4 = bottom(4)
    t = dict(x=b4['x'], y=b4['y'] + SY + 1.0, a=0.0)
    thumbs = [t]
    for a in (-15.0, -30.0):
        px, py = rot(SX / 2, SY / 2, t['a'])
        cx, cy = rot(-SX / 2, SY / 2, a)
        gx, gy = rot(0.5, 0, a)
        t = dict(x=t['x'] + px - cx + gx, y=t['y'] + py - cy + gy, a=a)
        thumbs.append(t)
    for i, t in enumerate(thumbs):
        keys.append(dict(t, col=3 + i, row='r0'))
    return keys


# ---------------------------------------------------------------- footprints

class Board:
    def __init__(self, dust):
        self.dust = dust
        self.nets = ['']
        self.footprints = []

    def net(self, name):
        if name not in self.nets:
            self.nets.append(name)
        return ['net', str(self.nets.index(name)), f'"{name}"']

    def place(self, tpl, x, y, a=None, ref=None, netmap=lambda pad, old: old):
        fp = copy.deepcopy(tpl)
        at = find(fp, 'at')[0]
        a0 = float(at[3]) if len(at) > 3 else 0.0
        a = a0 if a is None else a
        d = a - a0
        fp[fp.index(at)] = ['at', fmt(x), fmt(y)] + ([fmt(a)] if a else [])
        for child in fp:
            if not (isinstance(child, list) and child[0] in ('pad', 'fp_text')):
                continue
            cat = find(child, 'at')[0]
            ang = ((float(cat[3]) if len(cat) > 3 else 0.0) + d) % 360
            child[child.index(cat)] = cat[:3] + ([fmt(ang)] if ang else [])
            if child[0] == 'fp_text' and child[1] == 'reference' and ref:
                child[2] = f'"{ref}"'
            if child[0] == 'pad':
                n = find(child, 'net')
                if n:
                    new = netmap(child[1].strip('"'), n[0][2].strip('"'))
                    child[child.index(n[0])] = self.net(new)
        self.footprints.append(fp)
        return fp


def templates(dust):
    def ref(fp):
        r = [c for c in find(fp, 'fp_text') if c[1] == 'reference']
        return r[0][2].strip('"') if r else ''

    fps = find(dust, 'footprint')
    by_ref = {(ref(f), find(f, 'layer')[0][1]): f for f in fps}
    return dict(
        switch=by_ref[('S1', '"F.Cu"')],
        diode=by_ref[('D1', '"F.Cu"')],
        # bloco de eletrónica (XIAO e interruptor de energia), frente e verso
        cluster=[f for f in fps if ref(f) in ('XIAO1', 'T1')],
    )


def footprint_hull(fp):
    """Envolvente aproximada (pads + linhas) de um footprint, em coordenadas da placa."""
    at = find(fp, 'at')[0]
    x, y, a = float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0
    pts = []
    for c in fp:
        if not isinstance(c, list):
            continue
        if c[0] == 'pad':
            px, py = map(float, find(c, 'at')[0][1:3])
            sw, sh = map(float, find(c, 'size')[0][1:3])
            r = max(sw, sh) / 2
            pts += [(px - r, py - r), (px + r, py + r), (px - r, py + r), (px + r, py - r)]
        elif c[0] in ('fp_line',) and find(c, 'layer')[0][1] not in ('"Dwgs.User"', '"Cmts.User"'):
            for k in ('start', 'end'):
                pts.append(tuple(map(float, find(c, k)[0][1:3])))
    world = [(x + dx, y + dy) for dx, dy in (rot(px, py, a) for px, py in pts)]
    return MultiPoint(world).convex_hull


def cell(k, w=SX, h=SY):
    return affinity.translate(affinity.rotate(box(-w / 2, -h / 2, w / 2, h / 2), -k['a']), k['x'], k['y'])


# ---------------------------------------------------------------- main

def main(dust_path):
    dust = parse(open(dust_path, encoding='utf8').read())
    tpl = templates(dust)
    board = Board(dust)
    keys = layout()

    for i, k in enumerate(keys, 1):
        name = f"k_c{k['col']}_{k['row']}"
        k['net'] = name
        board.place(tpl['switch'], k['x'], k['y'], k['a'], f'S{i}',
                    lambda pad, old, k=k: f"c{k['col']}" if pad == '1' else k['net'])
        dx, dy = rot(0, DIODE_DY, k['a'])
        board.place(tpl['diode'], k['x'] + dx, k['y'] + dy, 180 + k['a'], f'D{i}',
                    lambda pad, old, k=k: k['row'] if pad == '1' else k['net'])

    # Bloco de eletrónica: mesma posição relativa à coluna interna que no dust
    inner_top = next(k for k in keys if k['col'] == 5 and k['row'] == 'r3')
    ox, oy = inner_top['x'] - 237.83833, inner_top['y'] - 98.948154
    refs = {'T1': 'PWR1'}
    for f in tpl['cluster']:
        at = find(f, 'at')[0]
        r = [c for c in find(f, 'fp_text') if c[1] == 'reference']
        old = r[0][2].strip('"') if r else ''
        board.place(f, float(at[1]) + ox, float(at[2]) + oy, None, refs.get(old),
                    lambda pad, net: XIAO_NETS.get(net, net) if old == 'XIAO1' else net)
        if old == 'T1' and find(f, 'layer')[0][1] == '"B.Cu"':
            # as duas cópias do interruptor (frente/verso) partilham os furos: só a da frente os leva
            fp = board.footprints[-1]
            fp[:] = [c for c in fp if not (isinstance(c, list) and c[0] == 'pad' and c[2] == 'np_thru_hole')]
    cluster_area = box(inner_top['x'] + SX / 2, inner_top['y'] - 2.25,
                       inner_top['x'] + 32.0, inner_top['y'] + 40.2)

    # ---- contorno: união das células das teclas + bloco, fechada e com cantos arredondados
    # (o invólucro convexo bloco+último polegar evita um entalhe entre os dois)
    shape = unary_union([cell(k) for k in keys] + [cluster_area,
                                                   unary_union([cluster_area, cell(keys[-1])]).convex_hull])
    shape = shape.buffer(8, join_style='round').buffer(-8, join_style='round')
    shape = shape.buffer(-1.5, join_style='round').buffer(1.5, join_style='round').simplify(0.02)
    assert shape.geom_type == 'Polygon', shape.geom_type

    # ---- verificações
    problems = []
    caps = [cell(k, *CAP) for k in keys]
    for i in range(len(caps)):
        for j in range(i + 1, len(caps)):
            if caps[i].intersection(caps[j]).area > 0.01:
                problems.append(f'keycaps S{i + 1} e S{j + 1} sobrepõem-se')
    edge = shape.buffer(0.01)
    for fp in board.footprints:
        h = footprint_hull(fp)
        r = [c for c in find(fp, 'fp_text') if c[1] == 'reference'][0][2]
        # o USB-C do XIAO fica 0,37 mm fora da borda de propósito (como no dust)
        if not (shape.buffer(0.5) if r == '"XIAO1"' else edge).contains(h):
            problems.append(f'{r} sai fora do contorno ({h.difference(edge).area:.2f} mm²)')
        if not r.startswith(('"S', '"D')):
            for i, cap in enumerate(caps):
                if cap.intersection(h).area > 0.5:
                    problems.append(f'{r} fica debaixo do keycap S{i + 1}')

    # ---- escrever o .kicad_pcb
    gr = []
    ring = list(shape.exterior.coords)
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        gr.append(['gr_line', ['start', fmt(x1), fmt(y1)], ['end', fmt(x2), fmt(y2)],
                   ['layer', '"Edge.Cuts"'], ['width', '0.15'], ['tstamp', 'X']])
    tx, ty = inner_top['x'] + 20.5, inner_top['y'] + 37.0
    for layer, extra in (('"F.SilkS"', []), ('"B.SilkS"', [['justify', 'mirror']])):
        gr.append(['gr_text', '"corne-x"', ['at', fmt(tx), fmt(ty)], ['layer', layer], ['tstamp', 'X'],
                   ['effects', ['font', ['size', '1.5', '1.5'], ['thickness', '0.2']]] + extra])

    setup = copy.deepcopy(find(dust, 'setup')[0])
    pp = find(setup, 'pcbplotparams')[0]
    pp[:] = [c for c in pp if not (isinstance(c, list) and c[0] == 'outputdirectory')]
    body = [
        ['general', ['thickness', '1.6']], ['paper', '"A3"'],
        ['title_block', ['title', '"corne-x"'], ['rev', '"v0.1"'], ['company', '"baseado no dust (Jason Hazel)"']],
        find(dust, 'layers')[0], setup,
    ] + [['net', str(i), f'"{n}"'] for i, n in enumerate(board.nets)] + board.footprints + gr
    out = '(kicad_pcb (version 20211014) (generator pcbnew)\n'
    out += '\n'.join('  ' + dumps(b, 1) for b in body) + '\n)\n'
    out = re.sub(r'\(tstamp [^)\s]+\)', lambda m: f'(tstamp {uuid.uuid4()})', out)
    with open(os.path.join(HERE, 'corne-x.kicad_pcb'), 'w', encoding='utf8', newline='\n') as f:
        f.write(out)

    write_preview(shape, keys, board, caps)

    w, h = shape.bounds[2] - shape.bounds[0], shape.bounds[3] - shape.bounds[1]
    print(f'{len(keys)} teclas, {len(board.footprints)} footprints, {len(board.nets) - 1} nets, '
          f'placa {w:.1f} x {h:.1f} mm, {len(ring) - 1} segmentos de contorno')
    print('\n'.join(problems) or 'sem colisões; tudo dentro do contorno')
    return not problems


def write_preview(shape, keys, board, caps):
    minx, miny, maxx, maxy = shape.bounds
    m = 6
    vb = f'{minx - m:.2f} {miny - m:.2f} {maxx - minx + 2 * m:.2f} {maxy - miny + 2 * m:.2f}'
    pts = ' '.join(f'{x:.2f},{y:.2f}' for x, y in shape.exterior.coords)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" width="{(maxx - minx + 2 * m) * 6:.0f}" '
         f'font-family="sans-serif">',
         f'<rect x="{minx - m}" y="{miny - m}" width="100%" height="100%" fill="#fff"/>',
         f'<polygon points="{pts}" fill="#4b2a7a" stroke="#c9b6ff" stroke-width="0.3"/>']
    for fp in board.footprints:
        r = [c for c in find(fp, 'fp_text') if c[1] == 'reference'][0][2].strip('"')
        if re.fullmatch(r'[SD]\d+', r) or find(fp, 'layer')[0][1] != '"F.Cu"':
            continue
        h = footprint_hull(fp)
        hp = ' '.join(f'{x:.2f},{y:.2f}' for x, y in h.exterior.coords) if h.geom_type == 'Polygon' else ''
        cx, cy = h.centroid.x, h.centroid.y
        s.append(f'<polygon points="{hp}" fill="#2d6a4f" fill-opacity="0.8" stroke="#95d5b2" stroke-width="0.25"/>')
        s.append(f'<text x="{cx:.2f}" y="{cy:.2f}" font-size="2" fill="#fff" text-anchor="middle">{r or "BAT-"}</text>')
    for i, (k, cap) in enumerate(zip(keys, caps), 1):
        cp = ' '.join(f'{x:.2f},{y:.2f}' for x, y in cap.exterior.coords)
        s.append(f'<polygon points="{cp}" fill="#f4f1ea" stroke="#333" stroke-width="0.25" rx="1"/>')
        s.append(f'<text x="{k["x"]:.2f}" y="{k["y"] - 1:.2f}" font-size="2.6" text-anchor="middle" '
                 f'transform="rotate({-k["a"]} {k["x"]:.2f} {k["y"]:.2f})">S{i}</text>')
        s.append(f'<text x="{k["x"]:.2f}" y="{k["y"] + 3:.2f}" font-size="2" fill="#666" text-anchor="middle" '
                 f'transform="rotate({-k["a"]} {k["x"]:.2f} {k["y"]:.2f})">c{k["col"]} · {k["row"]}</text>')
    s.append('</svg>')
    with open(os.path.join(HERE, 'preview.svg'), 'w', encoding='utf8') as f:
        f.write('\n'.join(s))


if __name__ == '__main__':
    sys.exit(0 if main(sys.argv[1]) else 1)
