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
    render_input_section(assembly, out / 'views' / 'lighting-input-section.png')


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

    backwash = s.get('emission') == 'backwash'
    rect(0, 0, width+22, host.thickness_mm, '#c99d66')
    # Section through a real end tie: the vertical legs use actual tray slots.
    for y0,y1 in ((-12,4),(6,10+width),(12+width,15+width)):
        rect(y0,-2*stock,y1,-stock,'#508fa0')
    if backwash:
        rect(8, -2*stock-thick, 8+width, -2*stock, '#f0d23c')
    else:
        rect(8, -stock, 8+width, -stock+thick, '#f0d23c')
    for record in s['retention']['envelopes'][:5]:
        _,y0,z0,_,y1,z1 = record['local_bounds_mm']
        rect(y0,z0,y1,z1,'#d2d5d8')
    if backwash:
        draw.text((35, 150), 'Strip-end tie section: LEDs face -Z, away from viewers, '
                  'onto the surface below', font=font, fill='white')
    else:
        draw.text((35, 150), 'Strip-end tie section: adjacent LED faces +Z into plywood',
                  font=font, fill='white')
    draw.text((35, 190), f'Host {host.thickness_mm:g} mm; carrier stock {stock:g} mm',
              font=font, fill='white')
    if backwash:
        draw.text((35, 225), f'Strip {width:g} x {thick:g} mm; clear throw '
                  f'{s.get("throw_mm") or 0:.0f} mm to the next surface', font=font, fill='white')
    else:
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
    draw.text((750, 585), 'Tie body <=2.5 x 1; head <=5 x 5 x 3 mm.', font=font, fill='white')
    draw.text((750, 620), f'Bolt length >= {s["bolt_length_min_mm"]:g} mm;',
              font=font, fill='white')
    draw.text((750, 655), '2 x M3 bolts/nuts; 4 washers. Round UP.', font=font, fill='white')
    if backwash:
        draw.text((35, 810), 'Tray and host hide the strip; reflected light leaves as a halo '
                  'around the host edge.', font=font, fill='white')
    else:
        draw.text((35, 810), 'Host blocks direct front view. Underside illumination may leave '
                  'front faces dark.', font=font, fill='white')
    draw.text((35, 850), 'Open ends permit oblique LED visibility. Optical/electrical/thermal '
              'and Wire/Arena: NOT RUN.', font=font, fill='#f1bf65')
    image.save(path)


def render_input_section(assembly, path):
    """Actual input stack and purchased envelope projection; board edge at Y zero."""
    anchor = assembly.lighting['input']
    inst = next(i for i in assembly.instances if i.instance_id == anchor['part_instances'][0])
    stock = assembly.definition_for(inst).thickness_mm
    host = next(i for i in assembly.instances if i.instance_id == anchor['host_instance'])
    thickness = assembly.definition_for(host).thickness_mm
    image = Image.new('RGB',(1200,780),'#12151b')
    draw = ImageDraw.Draw(image)
    title = ImageFont.load_default(size=25)
    font = ImageFont.load_default(size=20)
    draw.text((30,25),'Bottom input: exposed tie paths outside intact board',font=title,fill='white')
    draw.text((30,70),'Local Y/Z projection; purchased envelopes, not manufactured electronics.',font=font,fill='white')
    scale = min(14,330/(stock+thickness+16))
    ox,oy = 460,420

    def rect(bounds,color):
        y0,z0,y1,z1 = bounds
        draw.rectangle((ox+y0*scale,oy-z1*scale,ox+y1*scale,oy-z0*scale),fill=color,outline='white')

    rect((0,0,26,thickness),'#c99d66')
    rect((-12,-stock,16,0),'#508fa0')
    # The two ties run along X: projection shows upper/rear returns and head limits.
    for row in anchor['retention']['envelopes']:
        _,y0,z0,_,y1,z1 = row['local_bounds_mm']
        if row['kind'] == 'tie-leg':
            continue
        rect((y0,z0,y1,z1),'#596776' if row['kind']=='input-cable' else '#d2d5d8')
    draw.line((ox,170,ox,620),fill='#e4b96b',width=2)
    draw.text((35,135),'OUTSIDE board (Y<0)',font=font,fill='white')
    draw.text((640,135),'INTACT board (Y>=0)',font=font,fill='white')
    draw.text((35,590),'Slots at Y=-8/-3 mm, paired across X=-5/+5 mm; both exits exposed.',font=font,fill='white')
    draw.text((35,630),'Cable <=5 mm diameter; ties <=2.5 x 1 mm; heads <=5 x 5 x 3 mm.',font=font,fill='white')
    draw.text((35,670),'Heads on rear face. Front/rear paths and total envelope checked; no extra stock pads.',font=font,fill='white')
    draw.text((35,710),'Physical fit, optical, electrical/thermal and Wire/Arena checks NOT RUN.',font=font,fill='#f1bf65')
    image.save(path)
