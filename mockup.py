"""Mockup do teclado montado (as duas metades, vista de cima), a partir de corne-x.kicad_pcb.

    python mockup.py   ->  mockup.svg
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gerar_pcb import HERE, find, layout, parse  # noqa: E402

GAP = 46.0  # distância entre as metades (mm)
LEGENDS = {
    'L': [['Tab', 'Q', 'W', 'E', 'R', 'T'], ['Ctrl', 'A', 'S', 'D', 'F', 'G'],
          ['Shift', 'Z', 'X', 'C', 'V', 'B'], ['', '', '', 'GUI', 'Lower', 'Space']],
    'R': [['Bksp', 'P', 'O', 'I', 'U', 'Y'], ["'", ';', 'L', 'K', 'J', 'H'],
          ['Esc', '/', '.', ',', 'M', 'N'], ['', '', '', 'Alt', 'Raise', 'Enter']],
}
ROW_INDEX = {'r3': 0, 'r2': 1, 'r1': 2, 'r0': 3}


def board_data():
    b = parse(open(os.path.join(HERE, 'corne-x.kicad_pcb'), encoding='utf8').read())
    # encadeia os segmentos do contorno (o KiCad pode guardá-los por outra ordem)
    nxt = {}
    for g in find(b, 'gr_line'):
        if find(g, 'layer')[0][1] == '"Edge.Cuts"':
            a, z = (tuple(round(float(v), 3) for v in find(g, k)[0][1:3]) for k in ('start', 'end'))
            nxt.setdefault(a, []).append(z)
            nxt.setdefault(z, []).append(a)
    ring, prev = [next(iter(nxt))], None
    while True:
        cur = ring[-1]
        step = next(p for p in nxt[cur] if p != prev)
        if step == ring[0]:
            break
        prev = cur
        ring.append(step)
    parts = {}
    for fp in find(b, 'footprint'):
        if find(fp, 'layer')[0][1] != '"F.Cu"':
            continue
        # KiCad 6 usa fp_text reference; o KiCad 9 usa property "Reference"
        ref = [c[2] for c in find(fp, 'fp_text') if c[1] == 'reference']
        ref += [c[2] for c in find(fp, 'property') if c[1] == '"Reference"']
        ref = ref[0].strip('"')
        at = find(fp, 'at')[0]
        parts[ref or 'BAT-'] = (float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0)
    return ring, parts


def keycap(x, y, a, label, kind):
    fill = {'alpha': 'url(#capA)', 'mod': 'url(#capM)', 'thumb': 'url(#capT)'}[kind]
    ink = '#f7f3ea' if kind == 'thumb' else '#2b2b2b'
    size = 3.4 if len(label) <= 1 else 2.3
    return f'''<g transform="translate({x:.3f} {y:.3f}) rotate({-a:.2f})">
  <rect x="-8.75" y="-8.25" width="17.5" height="16.5" rx="2.2" fill="#000" opacity=".35" filter="url(#soft)" transform="translate(.6 1.1)"/>
  <rect x="-8.75" y="-8.25" width="17.5" height="16.5" rx="2.2" fill="{fill}" stroke="#00000055" stroke-width=".25"/>
  <rect x="-7.6" y="-7.5" width="15.2" height="14.2" rx="1.6" fill="#ffffff" opacity=".10"/>
  <text x="0" y="{size * .35:.2f}" font-size="{size}" fill="{ink}" text-anchor="middle" font-weight="600">{label}</text>
</g>'''


def xiao(x, y):
    pads = ''.join(
        f'<rect x="{sx:.2f}" y="{-7.62 + i * 2.54 - .7:.2f}" width="1.6" height="1.4" rx=".3" fill="url(#gold)"/>'
        f'<circle cx="{sx + (.0 if sx < 0 else 1.6):.2f}" cy="{-7.62 + i * 2.54:.2f}" r=".5" fill="#151515"/>'
        for i in range(7) for sx in (-8.9, 7.3))
    return f'''<g transform="translate({x:.3f} {y:.3f})">
  <rect x="-8.9" y="-10.5" width="17.8" height="21" rx="1.2" fill="#000" opacity=".5" filter="url(#soft)" transform="translate(.5 1)"/>
  <rect x="-8.9" y="-10.5" width="17.8" height="21" rx="1.2" fill="#1d1f22" stroke="#3a3d42" stroke-width=".2"/>
  {pads}
  <rect x="-4.5" y="-12.1" width="9" height="5.6" rx="1.3" fill="url(#steel)" stroke="#777" stroke-width=".15"/>
  <rect x="-3.4" y="-11.5" width="6.8" height="1.6" rx=".8" fill="#2a2a2a"/>
  <rect x="-6.3" y="-3.6" width="12.6" height="11.6" rx=".5" fill="url(#steel)" stroke="#8a8a8a" stroke-width=".15"/>
  <rect x="-5.6" y="-2.9" width="11.2" height="10.2" rx=".3" fill="none" stroke="#ffffff88" stroke-width=".15"/>
  <text x="0" y="2" font-size="1.25" fill="#555" text-anchor="middle" font-weight="600">nRF52840</text>
  <text x="0" y="3.7" font-size=".9" fill="#666" text-anchor="middle">Seeed Studio</text>
  <rect x="5" y="-6.2" width="1.8" height="1.4" rx=".3" fill="#d9d9d9"/><circle cx="5.9" cy="-5.5" r=".4" fill="#999"/>
  <rect x="-1.5" y="-5.6" width="1" height=".7" fill="#7cfc9a"/><rect x=".5" y="-5.6" width="1" height=".7" fill="#ff6b6b"/>
  <rect x="-7.2" y="-6.4" width="2.4" height="2" rx=".3" fill="#2a2a2a"/>
  <text x="0" y="9.6" font-size="1.4" fill="#cfcfcf" text-anchor="middle" font-weight="700">XIAO</text>
</g>'''


def hole(x, y):
    # furo não metalizado de 3,2 mm: vê-se a mesa através dele
    return (f'<circle cx="{x:.3f}" cy="{y:.3f}" r="1.6" fill="#a9a196" stroke="#2a1745" stroke-width=".35"/>'
            f'<circle cx="{x + .25:.3f}" cy="{y + .3:.3f}" r="1.2" fill="#8f877c"/>')


def slide_switch(x, y):
    return f'''<g transform="translate({x:.3f} {y:.3f})">
  <rect x="-2" y="-3.8" width="4" height="7.6" rx=".4" fill="url(#steel)" stroke="#666" stroke-width=".15"/>
  <rect x="1.4" y="-1.8" width="1.8" height="1.6" rx=".3" fill="#1a1a1a"/>
</g>'''


def xh(x, y, hx, hy):
    """JST-XH vertical com a ficha da bateria encaixada; (x, y) é o pino 1, (hx, hy) o furo dos fios."""
    return f'''<g>
  <rect x="{x - 2.45:.3f}" y="{y - 2.35:.3f}" width="7.4" height="5.75" rx=".4" fill="#000" opacity=".4" filter="url(#soft)" transform="translate(.4 .8)"/>
  <rect x="{x - 2.45:.3f}" y="{y - 2.35:.3f}" width="7.4" height="5.75" rx=".4" fill="#f3efe4" stroke="#b9b2a2" stroke-width=".15"/>
  <rect x="{x - 1.6:.3f}" y="{y - 1.5:.3f}" width="5.7" height="3.6" rx=".3" fill="#e4ddcc"/>
  <path d="M{x:.3f} {y:.3f} C {x + 1:.3f} {y + 5:.3f}, {hx - 3:.3f} {hy + 3:.3f}, {hx - .4:.3f} {hy:.3f}" stroke="#c62828" stroke-width=".7" fill="none" stroke-linecap="round"/>
  <path d="M{x + 2.5:.3f} {y:.3f} C {x + 3.5:.3f} {y + 4:.3f}, {hx - 2:.3f} {hy + 2:.3f}, {hx + .4:.3f} {hy:.3f}" stroke="#1b1b1b" stroke-width=".7" fill="none" stroke-linecap="round"/>
  <circle cx="{x:.3f}" cy="{y:.3f}" r=".55" fill="url(#gold)"/><circle cx="{x + 2.5:.3f}" cy="{y:.3f}" r=".55" fill="url(#gold)"/>
</g>'''


def half(side, ring, parts, keys, mirror_x):
    def X(x):
        return mirror_x - x if side == 'R' else x

    def A(a):
        return -a if side == 'R' else a

    pts = ' '.join(f'{X(x):.3f},{y:.3f}' for x, y in ring)
    out = [f'<polygon points="{pts}" fill="#000" opacity=".55" filter="url(#shadow)" transform="translate(1.5 3)"/>',
           f'<polygon points="{pts}" fill="url(#pcb)" stroke="#c9a227" stroke-width=".35"/>',
           f'<polygon points="{pts}" fill="none" stroke="#ffffff22" stroke-width=".2" transform="translate(-.15 -.15)"/>']
    # parafusos/furos decorativos e silkscreen
    xx, xy, _ = parts['XIAO1']
    out.append(f'<text x="{X(xx):.2f}" y="{xy + 24.5:.2f}" font-size="2" fill="#efe6ff" text-anchor="middle" '
               f'font-weight="700" letter-spacing=".4">corne-x</text>')
    out.append(xiao(X(xx), xy))
    jx, jy, _ = parts['J1']
    hx, hy, _ = parts['H1']
    out.append(hole(X(hx), hy))
    out.append(xh(X(jx) - (2.5 if side == 'R' else 0), jy, X(hx), hy))
    sx, sy, _ = parts['PWR1']
    out.append(slide_switch(X(sx), sy) if side == 'L'
               else f'<g transform="translate({X(sx):.3f} 0) scale(-1 1)">{slide_switch(0, sy)}</g>')
    for k in keys:
        label = LEGENDS[side][ROW_INDEX[k['row']]][k['col']]
        kind = 'thumb' if k['row'] == 'r0' else ('mod' if k['col'] == 0 else 'alpha')
        out.append(keycap(X(k['x']), k['y'], A(k['a']), label, kind))
    return '\n'.join(out)


def main():
    ring, parts = board_data()
    keys = layout()
    minx = min(x for x, _ in ring)
    maxx = max(x for x, _ in ring)
    miny = min(y for _, y in ring)
    maxy = max(y for _, y in ring)
    mirror = 2 * maxx + GAP  # a metade direita é a mesma PCB virada ao contrário
    left = half('L', ring, parts, keys, mirror)
    right = half('R', ring, parts, keys, mirror)
    w = (mirror - minx) - minx
    m = 14
    vx, vy, vw, vh = minx - m, miny - 22, w + 2 * m, (maxy - miny) + 22 + 20
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vx:.2f} {vy:.2f} {vw:.2f} {vh:.2f}"
     width="{vw * 6.2:.0f}" height="{vh * 6.2:.0f}" font-family="Segoe UI, Helvetica, Arial, sans-serif">
<defs>
  <linearGradient id="desk" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#d9d4cc"/><stop offset="1" stop-color="#b9b2a7"/></linearGradient>
  <linearGradient id="pcb" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5a2f91"/><stop offset="1" stop-color="#3d1d68"/></linearGradient>
  <linearGradient id="capA" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fbf8f1"/><stop offset="1" stop-color="#e3ddcf"/></linearGradient>
  <linearGradient id="capM" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#b9bcc2"/><stop offset="1" stop-color="#9497a0"/></linearGradient>
  <linearGradient id="capT" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e8743b"/><stop offset="1" stop-color="#c4551f"/></linearGradient>
  <linearGradient id="gold" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f5d77a"/><stop offset="1" stop-color="#b8902c"/></linearGradient>
  <linearGradient id="steel" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f2f2f2"/><stop offset=".5" stop-color="#b5b5b5"/><stop offset="1" stop-color="#8c8c8c"/></linearGradient>
  <filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation=".5"/></filter>
  <filter id="shadow" x="-10%" y="-10%" width="120%" height="130%"><feGaussianBlur stdDeviation="1.6"/></filter>
</defs>
<rect x="{vx:.2f}" y="{vy:.2f}" width="{vw:.2f}" height="{vh:.2f}" fill="url(#desk)"/>
{left}
{right}
<text x="{vx + 8:.2f}" y="{vy + vh - 7:.2f}" font-size="4" fill="#3b3631" font-weight="700">corne-x</text>
<text x="{vx + 31:.2f}" y="{vy + vh - 7:.2f}" font-size="2.6" fill="#5b554d">42 teclas · Kailh X (PG1425) · Seeed XIAO nRF52840 (BLE, sem fios) · bateria LiPo por baixo · PCB reversível · mockup ilustrativo</text>
</svg>'''
    with open(os.path.join(HERE, 'mockup.svg'), 'w', encoding='utf8') as f:
        f.write(svg)
    print('mockup.svg', f'{vw * 6.2:.0f}x{vh * 6.2:.0f}px')


if __name__ == '__main__':
    main()
