# corne-x

PCB reversível no formato **Corne** (3×6 + 3 polegares por metade, 42 teclas) com os mesmos
componentes do [dust](https://github.com/hazels-garage/dust): switches Kailh X (PG1425),
díodos 1N4148 SOD-123, Seeed XIAO (RP2040 ou BLE), jack TRRS e bateria opcional.

![mockup](mockup.png)

## Ficheiros
| Ficheiro | O que é |
|---|---|
| `corne-x.kicad_pcb` | PCB para o KiCad 6+ (posicionada e com nets, **ainda sem pistas**) |
| `gerar_pcb.py` | Gerador: `python gerar_pcb.py <dust.kicad_pcb>` (precisa de `pip install shapely`) |
| `mockup.py` / `mockup.svg` / `mockup.png` | Render ilustrativo das duas metades montadas |
| `preview.svg` | Vista técnica: posições, colunas e linhas da matriz |

## Matriz e pinos do XIAO
| Pino | Função | Pino | Função |
|---|---|---|---|
| D0 | c5 (indicador interno) | D6 | `tx` (dados entre metades, via TRRS) |
| D1 | c4 (indicador) | D7 | r0 (polegares) |
| D2 | c3 (médio) | D8 | r1 (fila de baixo) |
| D3 | c2 (anelar) | D9 | r2 (fila home) |
| D4 | c1 (mindinho) | D10 | r3 (fila de cima) |
| D5 | c0 (mindinho externo) | 5V / GND | RAW / GND do TRRS |

Díodos com o cátodo (pad 1) na linha → `DIODE_DIRECTION = COL2ROW` no QMK.
Os polegares estão nas colunas c3, c4 e c5 da linha r0. A metade direita é a mesma PCB virada.

## Antes de fabricar
1. Abrir no KiCad, rotear as pistas (à mão ou com o Freerouting) e encher as zonas.
2. Correr o DRC e rever o contorno.
3. Adaptar o firmware do dust (QMK/ZMK) a 6 colunas + o pinout acima.

## Créditos
Footprints e bloco de eletrónica retirados do dust, de Jason Hazel (CC BY 4.0).
Layout baseado no Corne (crkbd), de foostan (MIT).
