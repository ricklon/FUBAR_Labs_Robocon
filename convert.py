"""Convert an unpacked .pptx into a single self-contained HTML slide deck.

Usage:
    mkdir -p build && unzip -o FUBAR_Labs_Robocon_presentation.pptx -d build/pptx
    python convert.py build/pptx FUBAR_Labs_Robocon_presentation.html

Images are inlined as data URIs; hand-built slides listed in EXTRA_SLIDES are
spliced in from slides/. Requires lxml.
"""
import base64, html, os, re, sys
from lxml import etree

SRC = sys.argv[1]
OUT = sys.argv[2]
NS = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
EMU = 9525  # EMU per CSS px at 96 dpi
A = '{%s}' % NS['a']


def px(v):
    return round(int(v) / EMU, 3)


def color(el):
    """Return css color for an element containing a color child (srgbClr)."""
    c = el.find('a:srgbClr', NS)
    if c is None:
        return None
    hexv = c.get('val')
    al = c.find('a:alpha', NS)
    if al is None:
        return '#' + hexv
    r, g, b = (int(hexv[i:i + 2], 16) for i in (0, 2, 4))
    return f'rgba({r},{g},{b},{int(al.get("val")) / 100000:.3f})'


def fill_css(parent):
    sf = parent.find('a:solidFill', NS)
    if sf is not None:
        return f'background:{color(sf)};'
    gf = parent.find('a:gradFill', NS)
    if gf is not None:
        stops = [f'{color(gs)} {int(gs.get("pos")) / 1000:g}%' for gs in gf.findall('a:gsLst/a:gs', NS)]
        lin = gf.find('a:lin', NS)
        ang = int(lin.get('ang')) / 60000 if lin is not None else 0
        # OOXML 0deg = left->right; CSS 90deg = left->right
        return f'background:linear-gradient({ang + 90:g}deg,{",".join(stops)});'
    return ''


def line_css(sppr):
    ln = sppr.find('a:ln', NS)
    if ln is None or ln.find('a:solidFill', NS) is None:
        return ''
    w = px(ln.get('w', '12700'))
    dash = ln.find('a:prstDash', NS)
    style = 'dashed' if dash is not None and 'dash' in dash.get('val', '').lower() else 'solid'
    # PowerPoint centers strokes on the shape edge
    return f'outline:{w}px {style} {color(ln.find("a:solidFill", NS))};outline-offset:{-w / 2:.3f}px;'


def geom(sppr):
    g = sppr.find('a:prstGeom', NS)
    return 'border-radius:50%;' if g is not None and g.get('prst') == 'ellipse' else ''


def xfrm(sppr):
    x = sppr.find('a:xfrm', NS)
    off, ext = x.find('a:off', NS), x.find('a:ext', NS)
    return px(off.get('x')), px(off.get('y')), px(ext.get('cx')), px(ext.get('cy'))


def font_stack(name):
    fallback = {'Barlow Condensed': "'Barlow Condensed','Arial Narrow',sans-serif",
                'Barlow': "'Barlow',Arial,sans-serif"}
    return fallback.get(name, f"'{name}',Arial,sans-serif")


def run_css(rpr):
    s = ''
    if rpr is None:
        return s
    if rpr.get('sz'):
        s += f'font-size:{int(rpr.get("sz")) / 100 * 4 / 3:.2f}px;'
    s += f'font-weight:{700 if rpr.get("b") == "1" else 400};'
    if rpr.get('i') == '1':
        s += 'font-style:italic;'
    if rpr.get('u') and rpr.get('u') != 'none':
        s += 'text-decoration:underline;'
    if rpr.get('spc'):
        s += f'letter-spacing:{int(rpr.get("spc")) / 100 * 4 / 3:.2f}px;'
    sf = rpr.find('a:solidFill', NS)
    if sf is not None:
        s += f'color:{color(sf)};'
    lat = rpr.find('a:latin', NS)
    if lat is not None and lat.get('typeface'):
        s += f'font-family:{font_stack(lat.get("typeface"))};'
    return s


def text_html(txbody):
    bp = txbody.find('a:bodyPr', NS)
    ins = {k: px(bp.get(k, d)) for k, d in
           (('lIns', 91440), ('tIns', 45720), ('rIns', 91440), ('bIns', 45720))}
    anchor = {'t': 'flex-start', 'ctr': 'center', 'b': 'flex-end'}[bp.get('anchor', 't')]
    wrap = bp.get('wrap') != 'none'
    paras = []
    for p in txbody.findall('a:p', NS):
        ppr = p.find('a:pPr', NS)
        algn = {'l': 'left', 'ctr': 'center', 'r': 'right', 'just': 'justify'}.get(
            ppr.get('algn') if ppr is not None else 'l', 'left')
        lh = 1.2
        if ppr is not None:
            sp = ppr.find('a:lnSpc/a:spcPct', NS)
            if sp is not None:
                lh = 1.2 * int(sp.get('val')) / 100000
        runs = []
        for r in p:
            if r.tag == A + 'r':
                runs.append(f'<span style="{run_css(r.find("a:rPr", NS))}">'
                            f'{html.escape(r.findtext("a:t", "", NS))}</span>')
            elif r.tag == A + 'br':
                runs.append('<br>')
        if not runs:  # empty paragraph keeps its height
            runs.append(f'<span style="{run_css(p.find("a:endParaRPr", NS))}">&#8203;</span>')
        paras.append(f'<p style="text-align:{algn};line-height:{lh:.3f}">{"".join(runs)}</p>')
    return (f'<div class="tx" style="padding:{ins["tIns"]}px {ins["rIns"]}px {ins["bIns"]}px {ins["lIns"]}px;'
            f'justify-content:{anchor};{"" if wrap else "white-space:nowrap;"}">{"".join(paras)}</div>')


def rels_for(path):
    rp = os.path.join(os.path.dirname(path), '_rels', os.path.basename(path) + '.rels')
    tree = etree.parse(rp)
    return {r.get('Id'): os.path.normpath(os.path.join(os.path.dirname(path), r.get('Target')))
            for r in tree.getroot()}


def data_uri(path):
    ext = os.path.splitext(path)[1][1:].lower()
    mime = {'jpg': 'jpeg', 'svg': 'svg+xml'}.get(ext, ext)
    with open(path, 'rb') as f:
        return f'data:image/{mime};base64,' + base64.b64encode(f.read()).decode()


def shape_html(el, rels):
    tag = etree.QName(el).localname
    if tag == 'sp':
        sppr = el.find('p:spPr', NS)
        x, y, w, h = xfrm(sppr)
        style = f'left:{x}px;top:{y}px;width:{w}px;height:{h}px;{fill_css(sppr)}{line_css(sppr)}{geom(sppr)}'
        tb = el.find('p:txBody', NS)
        inner = text_html(tb) if tb is not None else ''
        return f'<div class="sh" style="{style}">{inner}</div>'
    if tag == 'pic':
        sppr = el.find('p:spPr', NS)
        x, y, w, h = xfrm(sppr)
        bf = el.find('p:blipFill', NS)
        src = data_uri(rels[bf.find('a:blip', NS).get('{%s}embed' % NS['r'])])
        sr = bf.find('a:srcRect', NS)
        l, t, r, b = ((int(sr.get(k, 0)) / 100000 if sr is not None else 0) for k in 'ltrb')
        iw, ih = w / (1 - l - r), h / (1 - t - b)
        alt = html.escape(el.find('p:nvPicPr/p:cNvPr', NS).get('descr', ''))
        return (f'<div class="sh" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;overflow:hidden;{geom(sppr)}">'
                f'<img alt="{alt}" src="{src}" style="position:absolute;left:{-l * iw:.2f}px;top:{-t * ih:.2f}px;'
                f'width:{iw:.2f}px;height:{ih:.2f}px"></div>')
    if tag == 'grpSp':
        return ''.join(shape_html(c, rels) for c in el if etree.QName(c).localname in ('sp', 'pic', 'grpSp'))
    return ''


root = SRC
pres = etree.parse(f'{root}/ppt/presentation.xml').getroot()
sz = pres.find('p:sldSz', NS)
SW, SH = px(sz.get('cx')), px(sz.get('cy'))
prels = rels_for(f'{root}/ppt/presentation.xml')
slides = []
for sid in pres.findall('p:sldIdLst/p:sldId', NS):
    path = prels[sid.get('{%s}id' % NS['r'])]
    rels = rels_for(path)
    s = etree.parse(path).getroot()
    bgpr = s.find('p:cSld/p:bg/p:bgPr', NS)
    bg = fill_css(bgpr) if bgpr is not None else 'background:#fff;'
    tree = s.find('p:cSld/p:spTree', NS)
    body = ''.join(shape_html(c, rels) for c in tree if etree.QName(c).localname in ('sp', 'pic', 'grpSp'))
    notes = ''
    for rid, target in rels.items():
        if 'notesSlide' in target:
            n = etree.parse(target).getroot()
            for sp in n.iter('{%s}sp' % NS['p']):
                ph = sp.find('.//p:nvPr/p:ph', NS)
                if ph is not None and ph.get('type') == 'body':
                    notes = '\n'.join(''.join(t.text or '' for t in p.iter(A + 't'))
                                      for p in sp.findall('.//a:p', NS)).strip()
    slides.append((bg, body, notes))

# Hand-built slides that are not in the pptx: (insert after slide N, fragment, background, notes).
# Relative image srcs in a fragment are inlined so the deck stays one self-contained file.
EXTRA_SLIDES = [
    (1, 'slides/giveaway.html', 'background:#FFF200;',
     'Prize giveaway at the FUBAR Labs booth: FUBAR Puzzle and Dummy 13 kit. Free to play.'),
]
here = os.path.dirname(os.path.abspath(__file__))
for after, frag, bg, notes in sorted(EXTRA_SLIDES, reverse=True):
    path = os.path.join(here, frag)
    body = re.sub(r'src="(?!data:)([^"]+)"',
                  lambda m: f'src="{data_uri(os.path.join(os.path.dirname(path), m.group(1)))}"',
                  open(path).read())
    slides.insert(after, (bg, body, notes))

title = 'FUBAR Labs Robocon'
out = [f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barlow:ital,wght@0,400;0,700;1,400;1,700&family=Barlow+Condensed:ital,wght@0,400;0,700;1,400;1,700&display=swap" rel="stylesheet">
<style>
:root{{--page:#1a1a1a;--muted:#9a9a9a;--sw:{SW};--sh:{SH}}}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{background:var(--page);color:#eee;font-family:Arial,sans-serif}}
#deck{{display:flex;flex-direction:column;align-items:center;gap:24px;padding:24px 16px}}
.frame{{width:100%;max-width:1600px;aspect-ratio:{SW}/{SH};position:relative;overflow:hidden;box-shadow:0 8px 30px rgba(0,0,0,.5)}}
.slide{{position:absolute;left:0;top:0;width:{SW}px;height:{SH}px;transform-origin:0 0}}
.sh{{position:absolute}}
.tx{{position:absolute;inset:0;display:flex;flex-direction:column;overflow:visible}}
.tx p{{margin:0}}
.notes{{width:100%;max-width:1600px;font-size:14px;line-height:1.5;color:var(--muted);white-space:pre-wrap;display:none}}
body.show-notes .notes{{display:block}}
body.present #deck{{padding:0;gap:0;height:100vh;justify-content:center}}
body.present .frame{{display:none;max-width:none;box-shadow:none;width:min(100vw,calc(100vh*{SW}/{SH}))}}
body.present .frame.cur{{display:block}}
body.present .notes{{display:none!important}}
#hint{{position:fixed;right:12px;bottom:10px;font-size:12px;color:var(--muted);background:rgba(0,0,0,.55);padding:6px 10px;border-radius:6px}}
body.present #hint{{display:none}}
body.kiosk,body.kiosk *{{cursor:none}}
body.kiosk{{background:#000;overflow:hidden}}
</style></head><body>
<div id="deck">''']
for i, (bg, body, notes) in enumerate(slides, 1):
    out.append(f'<section class="frame" id="s{i}" aria-label="Slide {i}"><div class="slide" style="{bg}">{body}</div></section>')
    out.append(f'<div class="notes"><b>Slide {i} notes:</b> {html.escape(notes)}</div>')
out.append('''</div>
<div id="hint">P / F: present &nbsp;·&nbsp; ←/→: navigate &nbsp;·&nbsp; A: autoplay &nbsp;·&nbsp; N: notes</div>
<script>
const frames=[...document.querySelectorAll('.frame')];let cur=0;
function fit(){frames.forEach(f=>{const s=f.firstElementChild;s.style.transform='scale('+(f.clientWidth/parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--sw')))+')'})}
function show(i){cur=Math.max(0,Math.min(frames.length-1,i));frames.forEach((f,j)=>f.classList.toggle('cur',j===cur));
  if(!document.body.classList.contains('present'))frames[cur].scrollIntoView({behavior:'smooth',block:'center'});fit()}
function present(on){document.body.classList.toggle('present',on);
  try{on?document.documentElement.requestFullscreen?.():document.fullscreenElement&&document.exitFullscreen()}catch(e){}
  show(cur)}
// ?kiosk starts presenting, loops, hides the cursor; ?interval=N sets seconds per slide (default 10)
const qs=new URLSearchParams(location.search);const kiosk=qs.has('kiosk');
const interval=Math.max(1,parseFloat(qs.get('interval'))||10)*1000;let timer=null;
function autoplay(on){clearInterval(timer);timer=on?setInterval(()=>show((cur+1)%frames.length),interval):null}
if(kiosk){document.body.classList.add('present','kiosk');autoplay(true)}
document.addEventListener('keydown',e=>{const k=e.key;
  if(kiosk)return;
  if(k==='a')autoplay(!timer);
  else if(k==='p'||k==='f'||k==='F5')present(!document.body.classList.contains('present'));
  else if(k==='Escape')present(false);
  else if(k==='n')document.body.classList.toggle('show-notes');
  else if(['ArrowRight','ArrowDown','PageDown',' '].includes(k)){e.preventDefault();show(cur+1)}
  else if(['ArrowLeft','ArrowUp','PageUp'].includes(k)){e.preventDefault();show(cur-1)}});
document.addEventListener('click',e=>{if(!kiosk&&document.body.classList.contains('present'))show(cur+(e.clientX<innerWidth/3?-1:1))});
document.addEventListener('fullscreenchange',()=>{if(!kiosk&&!document.fullscreenElement)document.body.classList.remove('present');fit()});
new ResizeObserver(fit).observe(document.body);document.fonts?.ready.then(fit);fit();
</script></body></html>''')
open(OUT, 'w').write('\n'.join(out))
print('wrote', OUT, len(slides), 'slides', SW, 'x', SH)
