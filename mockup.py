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
    ring = []
    for g in find(b, 'gr_line'):
        if find(g, 'layer')[0][1] == '"Edge.Cuts"':
            ring.append(tuple(map(float, find(g, 'start')[0][1:3])))
    parts = {}
    for fp in find(b, 'footprint'):
        if find(fp, 'layer')[0][1] != '"F.Cu"':
            continue
        ref = [c for c in find(fp, 'fp_text') if c[1] == 'reference'][0][2].strip('"')
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
  <rect x="-3.5" y="-2.5" width="7" height="7" rx=".4" fill="#2c2c2e" stroke="#4a4a4e" stroke-width=".15"/>
  <circle cx="-2.6" cy="-1.6" r=".35" fill="#666"/>
  <text x="0" y="1.6" font-size="1.1" fill="#9a9a9a" text-anchor="middle">RP2040</text>
  <rect x="-3" y="5.6" width="4" height="2.8" rx=".3" fill="#2a2a2a"/>
  <rect x="-6.6" y="-5.6" width="2" height="1.6" rx=".3" fill="#d9d9d9"/><circle cx="-5.6" cy="-4.8" r=".45" fill="#999"/>
  <rect x="4.6" y="-5.6" width="2" height="1.6" rx=".3" fill="#d9d9d9"/><circle cx="5.6" cy="-4.8" r=".45" fill="#999"/>
  <rect x="-1.5" y="-5.3" width="1" height=".7" fill="#7cfc9a"/><rect x=".5" y="-5.3" width="1" height=".7" fill="#ff6b6b"/>
  <text x="0" y="9.6" font-size="1.4" fill="#cfcfcf" text-anchor="middle" font-weight="700">XIAO</text>
</g>'''


def trrs(x, y):
    # PJ-320A deitado; a abertura para o cabo aponta para a borda de fora
    return f'''<g transform="translate({x:.3f} {y:.3f})">
  <rect x="-6" y="-3" width="12" height="6" rx=".6" fill="#000" opacity=".45" filter="url(#soft)" transform="translate(.4 .8)"/>
  <rect x="-6" y="-3" width="11" height="6" rx=".6" fill="#202020" stroke="#444" stroke-width=".15"/>
  <rect x="5" y="-2.5" width="2.2" height="5" rx=".5" fill="#2a2a2a"/>
  <circle cx="6.6" cy="0" r="1.6" fill="url(#steel)"/><circle cx="6.6" cy="0" r=".9" fill="#111"/>
</g>'''


def slide_switch(x, y):
    return f'''<g transform="translate({x:.3f} {y:.3f})">
  <rect x="-2" y="-3.8" width="4" height="7.6" rx=".4" fill="url(#steel)" stroke="#666" stroke-width=".15"/>
  <rect x="1.4" y="-1.8" width="1.8" height="1.6" rx=".3" fill="#1a1a1a"/>
</g>'''


def jst(x, y):
    return f'''<g transform="translate({x:.3f} {y:.3f})">
  <rect x="-3" y="-2.6" width="6" height="4.2" rx=".4" fill="#f1ede2" stroke="#bbb" stroke-width=".15"/>
  <rect x="-1.4" y="-1.8" width="2.8" height="2.2" fill="#d9d3c3"/>
  <path d="M-.5 -2.6 C -.5 -6, -1 -9, 1 -12" stroke="#d33" stroke-width=".5" fill="none"/>
  <path d="M .5 -2.6 C .5 -6, 0 -9, 2 -12" stroke="#222" stroke-width=".5" fill="none"/>
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
    out.append(trrs(X(jx), jy) if side == 'L'
               else f'<g transform="translate({X(jx):.3f} 0) scale(-1 1)">{trrs(0, jy)}</g>')
    bx, by, _ = parts['BT1']
    out.append(jst(X(bx), by))
    sx, sy, _ = parts['SW1']
    out.append(slide_switch(X(sx), sy) if side == 'L'
               else f'<g transform="translate({X(sx):.3f} 0) scale(-1 1)">{slide_switch(0, sy)}</g>')
    for k in keys:
        label = LEGENDS[side][ROW_INDEX[k['row']]][k['col']]
        kind = 'thumb' if k['row'] == 'r0' else ('mod' if k['col'] == 0 else 'alpha')
        out.append(keycap(X(k['x']), k['y'], A(k['a']), label, kind))
    return '\n'.join(out), X(jx)


def main():
    ring, parts = board_data()
    keys = layout()
    minx = min(x for x, _ in ring)
    maxx = max(x for x, _ in ring)
    miny = min(y for _, y in ring)
    maxy = max(y for _, y in ring)
    mirror = 2 * maxx + GAP  # a metade direita é a mesma PCB virada ao contrário
    left, jl = half('L', ring, parts, keys, mirror)
    right, jr = half('R', ring, parts, keys, mirror)
    jy = parts['J1'][1]
    w = (mirror - minx) - minx
    m = 14
    vx, vy, vw, vh = minx - m, miny - 22, w + 2 * m, (maxy - miny) + 22 + 20
    usb_x, usb_top = parts['XIAO1'][0], parts['XIAO1'][1] - 12.1
    cable = (f'<path d="M{jl + 7.2:.2f} {jy:.2f} C {jl + 22:.2f} {jy:.2f}, {jl + 14:.2f} {jy + 26:.2f}, '
             f'{(jl + jr) / 2:.2f} {jy + 26:.2f} S {jr - 22:.2f} {jy:.2f}, {jr - 7.2:.2f} {jy:.2f}" '
             f'stroke="#111" stroke-width="2.4" fill="none" stroke-linecap="round"/>'
             f'<path d="M{jl + 7.2:.2f} {jy:.2f} C {jl + 22:.2f} {jy:.2f}, {jl + 14:.2f} {jy + 26:.2f}, '
             f'{(jl + jr) / 2:.2f} {jy + 26:.2f} S {jr - 22:.2f} {jy:.2f}, {jr - 7.2:.2f} {jy:.2f}" '
             f'stroke="#555" stroke-width=".6" fill="none" transform="translate(-.4 -.5)"/>'
             f'<rect x="{jl + 7:.2f}" y="{jy - 1.6:.2f}" width="6" height="3.2" rx=".8" fill="#2b2b2b"/>'
             f'<rect x="{jr - 13:.2f}" y="{jy - 1.6:.2f}" width="6" height="3.2" rx=".8" fill="#2b2b2b"/>'
             f'<path d="M{usb_x:.2f} {usb_top - 4:.2f} C {usb_x:.2f} {usb_top - 16:.2f}, {usb_x + 40:.2f} '
             f'{usb_top - 10:.2f}, {usb_x + 60:.2f} {vy:.2f}" stroke="#111" stroke-width="2.6" fill="none"/>'
             f'<rect x="{usb_x - 3.5:.2f}" y="{usb_top - 6.5:.2f}" width="7" height="7" rx="1.2" fill="#2b2b2b"/>')
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
{cable}
<text x="{vx + 8:.2f}" y="{vy + vh - 7:.2f}" font-size="4" fill="#3b3631" font-weight="700">corne-x</text>
<text x="{vx + 31:.2f}" y="{vy + vh - 7:.2f}" font-size="2.6" fill="#5b554d">42 teclas · Kailh X (PG1425) · Seeed XIAO RP2040 · PCB reversível · mockup ilustrativo</text>
</svg>'''
    with open(os.path.join(HERE, 'mockup.svg'), 'w', encoding='utf8') as f:
        f.write(svg)
    print('mockup.svg', f'{vw * 6.2:.0f}x{vh * 6.2:.0f}px')


if __name__ == '__main__':
    main()
