"""Lighting sidecars and dimensioned local manufacturing evidence (not ray tracing)."""
from importlib import resources
import json

from PIL import Image, ImageDraw, ImageFont


def export_lighting(assembly, out):
    light = assembly.lighting
    for filename, data in [('lighting-routing.json', light), ('lighting-bom.json', light['bom'])]:
        (out / filename).write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
    (out / 'lighting-instructions.md').write_text(
        resources.files('parametric_deco.resources').joinpath('lighting-instructions.md').read_text())
    render_section(assembly, out / 'views' / 'lighting-section.png')


def render_section(assembly, path):
    """Scale actual tray/strip/host cross sections and cut contours from first clamp."""
    light = assembly.lighting
    s = light['segments'][0]
    by_id = {i.instance_id: i for i in assembly.instances}
    tray = assembly.definition_for(by_id[s['part_instances'][0]])
    host = assembly.definition_for(by_id[s['host_instance']])
    stock = tray.thickness_mm
    width = light['config']['strip_width_mm']
    thick = light['config']['strip_thickness_mm']
    image = Image.new('RGB', (1300, 940), '#12151b')
    draw = ImageDraw.Draw(image)
    title = ImageFont.load_default(size=26)
    font = ImageFont.load_default(size=19)
    draw.text((30, 20), 'Concealed LED clamp: actual dimensions / local section', font=title,
              fill='white')
    draw.text((30, 60), s['segment_id']+' on '+s['host_instance'], font=font, fill='white')
    draw.text((30, 90), 'Geometry evidence only. No simulated illumination. Physical fit NOT RUN.',
              font=font, fill='#f1bf65')
    # Side section through the strip, looking along the strip length. Y horizontal, Z up.
    scale = min(14, 470/(width+35), 260/(4*stock+host.thickness_mm))
    ox, oy = 230, 340

    def rect(y0, z0, y1, z1, color):
        draw.rectangle((ox+y0*scale, oy-z1*scale, ox+y1*scale, oy-z0*scale), fill=color,
                       outline='white')

    rect(0, 0, width+22, host.thickness_mm, '#c99d66')
    rect(-12, -2*stock, width+15, -stock, '#508fa0')
    rect(8, -stock, 8+width, -stock+thick, '#f0d23c')
    tie = [(5, -2*stock-.8), (5, -stock+thick+.8),
           (11+width, -stock+thick+.8), (11+width, -2*stock-.8),
           (5, -2*stock-.8)]
    draw.line([(ox+y*scale, oy-z*scale) for y, z in tie], fill='#eee9da', width=3)
    start = (ox+(8+width/2)*scale, oy+(stock-thick)*scale)
    end = (start[0], oy)
    draw.line((start, end), fill='#f0d23c', width=3)
    draw.polygon((end, (end[0]-5, end[1]+8), (end[0]+5, end[1]+8)), fill='#f0d23c')
    draw.text((35, 150), 'Mid-span section: strip faces +Z into plywood underside',
              font=font, fill='white')
    draw.text((35, 190), f'Host {host.thickness_mm:g} mm; carrier stock {stock:g} mm',
              font=font, fill='white')
    draw.text((35, 225), f'Strip {width:g} x {thick:g} mm; unobstructed gap '
              f'{s["emitter_to_host_mm"]:g} mm', font=font, fill='white')
    draw.text((35, 480), 'End section: bolt outside host; pads bear on host underside',
              font=font, fill='white')
    oy = 680
    scale *= .75
    rect(0, 0, width+22, host.thickness_mm, '#c99d66')
    rect(-12, -2*stock, width+15, -stock, '#508fa0')
    rect(-12, -stock, width+15, 0, '#467891')
    rect(-12, host.thickness_mm, width+15, host.thickness_mm+stock, '#508fa0')
    rect(-7.5, -2*stock-3, -4.5, -2*stock+s['bolt_envelopes'][0]['length_mm'], '#b0b5bb')
    # Actual tray cut outline at right, including holes/slots.
    minx, miny, maxx, maxy = tray.polygon.bounds
    sc = min(480/(maxx-minx), 320/(maxy-miny))

    def points(ring):
        return [(760+(x-minx)*sc, 200+(maxy-y)*sc) for x, y in ring]

    draw.polygon(points(tray.outer), fill='#508fa0', outline='white')
    for hole in tray.holes:
        draw.polygon(points(hole), fill='#12151b', outline='white')
    draw.text((750, 150), 'Actual tray cut contour and tie slots', font=font, fill='white')
    draw.text((750, 550), 'Two end ties wrap over strip via paired slots.', font=font, fill='white')
    draw.text((750, 585), '2 x M3 bolts + locking nuts; 4 washers.', font=font, fill='white')
    draw.text((750, 620), f'Bolt length >= {s["bolt_length_min_mm"]:g} mm;',
              font=font, fill='white')
    draw.text((750, 655), 'round UP to available length (see BOM).', font=font, fill='white')
    draw.text((35, 810), 'Host blocks direct front view. Underside illumination may leave front '
              'faces dark.', font=font, fill='white')
    draw.text((35, 850), 'Open ends permit oblique LED visibility. Optical/electrical/thermal '
              'and Wire/Arena: NOT RUN.', font=font, fill='#f1bf65')
    image.save(path)
