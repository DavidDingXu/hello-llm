"""白底教材图的可编辑 SVG 基础；图中数值从逐讲 JSON 读取。"""
from html import escape
import json
from pathlib import Path

COLUMN = Path(__file__).resolve().parents[2]
CODE = COLUMN / 'code'
C = {'ink':'#222A35','muted':'#606C7B','input':'#3267A4','param':'#8056A5',
     'output':'#187B79','grad':'#B14C70','line':'#C5CDD7','light':'#F4F6F9'}
FONT = "'Hiragino Sans GB','PingFang SC','Microsoft YaHei',Arial,sans-serif"


def read(n):
    return json.loads((CODE/f'artifacts/lessons/l{n:02d}.json').read_text(encoding='utf-8'))


def text(x,y,value,size=34,color='ink',anchor='start',weight=400):
    color=C.get(color,color)
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">{escape(str(value))}</text>'


def lines(x,y,values,size=34,gap=49,color='ink',anchor='start'):
    return ''.join(text(x,y+i*gap,v,size,color,anchor) for i,v in enumerate(values))


def rect(x,y,w,h,fill='light',stroke=None,r=12):
    stroke=C.get(stroke,stroke) if stroke else 'none'
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{C.get(fill,fill)}" stroke="{stroke}" stroke-width="2"/>'


def arrow(x1,y1,x2,y2,color='line',width=3):
    c=C.get(color,color)
    return f'<path d="M{x1} {y1} L{x2} {y2}" fill="none" stroke="{c}" stroke-width="{width}" marker-end="url(#a-{color if color in C else "line"})"/>'


def line(x1,y1,x2,y2,color='line',width=2,dash=None):
    return f'<path d="M{x1} {y1} L{x2} {y2}" fill="none" stroke="{C.get(color,color)}" stroke-width="{width}"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>'


def circle(x,y,r,value=None,color='input',size=34):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="white" stroke="{C.get(color,color)}" stroke-width="3"/>'+ (text(x,y+size*.34,value,size,color,'middle') if value is not None else '')


def box(x,y,w,h,label,color='input',size=34):
    return rect(x,y,w,h,'#FFFFFF',color)+text(x+w/2,y+h/2+size*.34,label,size,color,'middle')


def matrix(x,y,values,label='',cell_w=112,cell_h=66,colors=None,fmt=None,size=32):
    s=text(x,y-24,label,34) if label else ''
    for r,row in enumerate(values):
        for c,value in enumerate(row):
            cell_color = colors[r][c] if colors else 'light'
            s+=rect(x+c*cell_w,y+r*cell_h,cell_w-5,cell_h-5,cell_color,r=4)
            rendered=fmt(value) if fmt else str(value)
            s+=text(x+(c+.5)*cell_w-2,y+(r+.5)*cell_h+size*.31-2,rendered,size,'ink','middle')
    return s


def phase(number,markup):
    return f'<g data-phase="{number}">{markup}</g>'


def svg(title,subtitle,content,height=1050):
    markers=''.join(f'<marker id="a-{key}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 Z" fill="{color}"/></marker>' for key,color in C.items())
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="{int(height*1.5)}" viewBox="0 0 720 {height}" role="img" aria-label="{escape(title)}">'
            f'<defs>{markers}</defs><rect width="720" height="{height}" fill="white"/>'
            f'<g font-family="{FONT}" font-variant-numeric="tabular-nums">'
            +text(36,60,title,40,'ink',weight=600)
            +text(36,110,subtitle,30,'muted')+content+'</g></svg>')


def save(folder,name,markup):
    directory=COLUMN/'chapters'/folder/'images';directory.mkdir(parents=True,exist_ok=True)
    (directory/(name+'.svg')).write_text(markup,encoding='utf-8')
    print(folder,name)


def fmt(value):
    if isinstance(value,float):
        if abs(value)>0 and abs(value)<.0001:return f'{value:.1e}'
        return f'{value:.3f}'.rstrip('0').rstrip('.')
    return str(value)
