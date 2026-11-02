"""Segunda fase: acrescenta o conector da bateria (JST-XH) e o furo para os fios,
roteia com o Freerouting, enche o plano de GND, corre o DRC e exporta os gerbers.

Tem de correr com o Python do KiCad (10.x):

    "%LOCALAPPDATA%\\Programs\\KiCad\\10.0\\bin\\python.exe" finalizar_pcb.py <freerouting.jar>

Lê e reescreve corne-x.kicad_pcb (gerado por gerar_pcb.py).
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import zipfile

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, 'corne-x.kicad_pcb')
BUILD = os.path.join(HERE, 'build')
KICAD = os.path.dirname(os.path.dirname(sys.executable))
LIB = glob.glob(os.path.join(KICAD, 'share', 'kicad', 'footprints'))[0]
CLI = os.path.join(KICAD, 'bin', 'kicad-cli.exe')

# Posições (mm) no espaço que ficou livre debaixo do XIAO, onde estava o TRRS
XH_PIN1 = (204.5, 130.5)
HOLE = (213.5, 131.0)


def mm(x, y):
    return pcbnew.VECTOR2I_MM(x, y)


def net(board, name):
    n = board.FindNet(name)
    if n is None:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
    return n


def add_footprint(board, lib, name, ref, pos, nets=None):
    fp = pcbnew.FootprintLoad(os.path.join(LIB, lib + '.pretty'), name)
    fp.SetReference(ref)
    fp.SetPosition(mm(*pos))
    for pad in fp.Pads():
        if nets and pad.GetNumber() in nets:
            pad.SetNet(net(board, nets[pad.GetNumber()]))
    board.Add(fp)
    return fp


def set_rules(board):
    """Regras de desenho dentro das capacidades normais da JLCPCB/PCBWay (2 camadas)."""
    ds = board.GetDesignSettings()
    nc = ds.m_NetSettings.GetDefaultNetclass()
    nc.SetClearance(pcbnew.FromMM(0.2))
    nc.SetTrackWidth(pcbnew.FromMM(0.25))
    nc.SetViaDiameter(pcbnew.FromMM(0.6))
    nc.SetViaDrill(pcbnew.FromMM(0.3))
    ds.m_CopperEdgeClearance = pcbnew.FromMM(0.2)
    ds.m_HoleClearance = pcbnew.FromMM(0.2)
    ds.m_TrackMinWidth = pcbnew.FromMM(0.127)  # o Freerouting estreita algumas pistas junto aos pads


# Exceções só para a geometria interna dos footprints herdados do dust (o dust foi
# fabricado e montado com eles); pistas e zonas continuam sujeitas às regras normais.
DRU = """(version 1)
(rule "Kailh X + diodo: furos e pads do proprio footprint"
  (condition "(A.memberOfFootprint('S*') || A.memberOfFootprint('D*')) && (B.memberOfFootprint('S*') || B.memberOfFootprint('D*'))")
  (constraint hole_clearance (min 0.1mm))
  (constraint edge_clearance (min 0.1mm)))
"""
# o díodo fica de propósito entre os pinos do switch; a biblioteca do autor não está instalada
IGNORE = ('pth_inside_courtyard', 'lib_footprint_issues')


def project_rules():
    with open(PCB.replace('.kicad_pcb', '.kicad_dru'), 'w', encoding='utf8') as f:
        f.write(DRU)
    pro_path = PCB.replace('.kicad_pcb', '.kicad_pro')
    pro = json.load(open(pro_path, encoding='utf8'))
    sev = pro.setdefault('board', {}).setdefault('design_settings', {}).setdefault('rule_severities', {})
    for k in IGNORE:
        sev[k] = 'ignore'
    with open(pro_path, 'w', encoding='utf8') as f:
        json.dump(pro, f, indent=2)


def gnd_zones(board):
    box = board.GetBoardEdgesBoundingBox()
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(net(board, 'GND'))
        z.SetLocalClearance(pcbnew.FromMM(0.3))
        z.SetMinThickness(pcbnew.FromMM(0.25))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        o = z.Outline()
        o.NewOutline()
        for x, y in ((box.GetLeft(), box.GetTop()), (box.GetRight(), box.GetTop()),
                     (box.GetRight(), box.GetBottom()), (box.GetLeft(), box.GetBottom())):
            o.Append(x, y)
        board.Add(z)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def java():
    # o Freerouting 2.5 precisa do Java 25+; preferir o Temurin ao java do PATH
    found = next(iter(sorted(glob.glob(r'C:\Program Files\Eclipse Adoptium\jre-2[5-9]*\bin\java.exe'))), None)
    found = found or shutil.which('java')
    if not found:
        sys.exit('java não encontrado')
    return found


def main(jar):
    os.makedirs(BUILD, exist_ok=True)
    board = pcbnew.LoadBoard(PCB)
    set_rules(board)

    # conector da bateria (furos passantes: serve nas duas faces da placa reversível)
    add_footprint(board, 'Connector_JST', 'JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical', 'J1', XH_PIN1,
                  {'1': 'BAT', '2': 'BAT-'})
    # furo não metalizado para passar os fios da bateria (que fica por baixo da placa)
    add_footprint(board, 'MountingHole', 'MountingHole_3.2mm_M3', 'H1', HOLE)
    pcbnew.SaveBoard(PCB, board)

    # ---- autorouting
    dsn, ses = os.path.join(BUILD, 'corne-x.dsn'), os.path.join(BUILD, 'corne-x.ses')
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        sys.exit('falha a exportar o DSN')
    subprocess.run([java(), '-jar', jar, '-de', dsn, '-do', ses, '-mp', '100',
                    '--gui.enabled=false'], check=True)
    board = pcbnew.LoadBoard(PCB)
    if not pcbnew.ImportSpecctraSES(board, ses):
        sys.exit('falha a importar o SES')
    gnd_zones(board)
    pcbnew.SaveBoard(PCB, board)
    project_rules()

    # ---- DRC
    report = os.path.join(BUILD, 'drc.json')
    subprocess.run([CLI, 'pcb', 'drc', '--format', 'json', '--units', 'mm',
                    '--all-track-errors', '-o', report, PCB], check=False)
    drc = json.load(open(report, encoding='utf8'))
    print_drc(drc)

    # ---- gerbers + furação
    gdir = os.path.join(BUILD, 'gerbers')
    shutil.rmtree(gdir, ignore_errors=True)
    os.makedirs(gdir)
    layers = 'F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts'
    subprocess.run([CLI, 'pcb', 'export', 'gerbers', '--layers', layers, '--no-protel-ext', '-o', gdir + os.sep, PCB],
                   check=True)
    subprocess.run([CLI, 'pcb', 'export', 'drill', '--format', 'excellon', '--excellon-separate-th',
                    '--generate-map', '--map-format', 'gerberx2', '-o', gdir + os.sep, PCB], check=True)
    with zipfile.ZipFile(os.path.join(HERE, 'corne-x-gerbers.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(gdir)):
            z.write(os.path.join(gdir, f), f)
    print('gerbers:', ', '.join(sorted(os.listdir(gdir))))


def print_drc(drc):
    from collections import Counter
    for key in ('violations', 'unconnected_items', 'schematic_parity'):
        items = drc.get(key, [])
        c = Counter((v['severity'], v['type']) for v in items)
        print(f'{key}: {len(items)}')
        for (sev, typ), n in c.most_common():
            print(f'   {sev:8} {typ:32} {n}')


if __name__ == '__main__':
    main(sys.argv[1])
