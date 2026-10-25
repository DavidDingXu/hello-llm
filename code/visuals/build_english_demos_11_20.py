"""Build English demo pages from Chinese originals without changing experiment data.

Only HTML text/accessibility labels and JavaScript string/template text are
translated. JavaScript identifiers, operators, event hooks, JSON traces, and
Chinese token strings are retained. Animated SVGs come from images/en/.
"""
from __future__ import annotations

import json
import re
from html import escape
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEXT = json.loads(Path(__file__).with_name('english_demos_11_20_text.json').read_text(encoding='utf-8'))
PATTERN = re.compile('|'.join(re.escape(k) for k in sorted(TEXT, key=len, reverse=True)))
PAGES = {11:'walkthrough',12:'walkthrough',13:'walkthrough',16:'model-inspector',18:'walkthrough',19:'walkthrough',20:'training-replay'}


def translate(text):
    return PATTERN.sub(lambda m: TEXT[m.group()], text)


def literal_spans(code):
    """Yield only string/template payload spans; expressions and comments stay code.

    This small lexer handles the literals used by these fixed demo sources,
    including nested template expressions and regexes passed to replace().
    """
    spans=[]
    n=len(code)

    def string(i):
        quote=code[i]; start=i+1; i=start
        while i<n:
            if code[i]=='\\': i+=2; continue
            if code[i]==quote:
                spans.append((start,i,quote)); return i+1
            i+=1
        raise ValueError('Unclosed JavaScript string')

    def template(i):
        i+=1; start=i
        while i<n:
            if code[i]=='\\': i+=2; continue
            if code[i]=='`':
                spans.append((start,i,'`')); return i+1
            if code.startswith('${',i):
                spans.append((start,i,'`'))
                i=walk(i+2,True); start=i; continue
            i+=1
        raise ValueError('Unclosed JavaScript template')

    def regex(i):
        i+=1; in_class=False
        while i<n:
            if code[i]=='\\': i+=2; continue
            if code[i]=='[': in_class=True
            elif code[i]==']': in_class=False
            elif code[i]=='/' and not in_class:
                i+=1
                while i<n and code[i].isalpha(): i+=1
                return i
            i+=1
        raise ValueError('Unclosed JavaScript regex')

    def walk(i, interpolation=False):
        depth=0
        while i<n:
            if code.startswith('//',i):
                end=code.find('\n',i); i=n if end<0 else end+1; continue
            if code.startswith('/*',i):
                end=code.find('*/',i+2)
                if end<0: raise ValueError('Unclosed JavaScript comment')
                i=end+2; continue
            c=code[i]
            if c in "'\"": i=string(i); continue
            if c=='`': i=template(i); continue
            if c=='/' and code[:i].rstrip().endswith(('(', '=', ',', ':', '[', '=>')):
                i=regex(i); continue
            if interpolation and c=='{': depth+=1
            if interpolation and c=='}':
                if depth==0: return i+1
                depth-=1
            i+=1
        if interpolation: raise ValueError('Unclosed template expression')
        return i

    walk(0)
    return sorted(spans)


def translate_js(code):
    # Training replay embeds a large JSON object in JavaScript. Keep it byte-for-byte.
    data_span=None
    match=re.search(r'\bconst DATA\s*=\s*',code)
    if match:
        _,length=json.JSONDecoder().raw_decode(code[match.end():])
        data_span=(match.end(),match.end()+length)
    parts=[]; cursor=0
    for start,end,quote in literal_spans(code):
        if data_span and start>=data_span[0] and end<=data_span[1]: continue
        raw=code[start:end]; translated=translate(raw)
        if translated!=raw:
            # Mappings contain presentation text only. Escape any newly inserted
            # delimiter without touching original escapes or ${expressions}.
            translated=translated.replace(quote,'\\'+quote)
            if quote=='`': translated=translated.replace('${','\\${')
            parts.extend([code[cursor:start],translated]); cursor=end
    parts.append(code[cursor:]); result=''.join(parts)
    if data_span:
        match2=re.search(r'\bconst DATA\s*=\s*',result)
        _,length2=json.JSONDecoder().raw_decode(result[match2.end():])
        assert code[data_span[0]:data_span[1]]==result[match2.end():match2.end()+length2]
    return result


class EnglishHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False); self.parts=[]; self.raw_tag=None
    def handle_starttag(self,tag,attrs):
        raw=self.get_starttag_text()
        for key,value in attrs:
            if value is None: continue
            new=value
            if key=='lang': new='en'
            elif key in ('aria-label','title','alt'): new=translate(value)
            elif key in ('href','src'):
                if value=='index.html': new='index.en.html'
                elif value.startswith('images/'): new=value.replace('images/','images/en/',1)
            if new!=value:
                raw=re.sub(r'('+re.escape(key)+r'\s*=\s*)([\'\"])(.*?)\2',lambda m:m[1]+m[2]+escape(new,quote=True)+m[2],raw,count=1)
        self.parts.append(raw)
        if tag in ('script','style'): self.raw_tag=tag
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
    def handle_endtag(self,tag):
        self.parts.append('</'+tag+'>')
        if tag==self.raw_tag:self.raw_tag=None
    def handle_data(self,data): self.parts.append(data if self.raw_tag else translate(data))
    def handle_entityref(self,name): self.parts.append('&'+name+';')
    def handle_charref(self,name): self.parts.append('&#'+name+';')
    def handle_decl(self,decl): self.parts.append('<!'+decl+'>')
    def handle_comment(self,text): self.parts.append('<!--'+text+'-->')


def build_page(source):
    original=source.read_text(encoding='utf-8')
    def script(match):
        attrs,body=match.group(1),match.group(2)
        if 'application/json' not in attrs:
            return '<script'+attrs+'>'+translate_js(body)+'</script>'
        data=json.loads(body)
        if 'frames' not in data:
            return match.group(0)
        for frame in data['frames']:
            english_figure=frame['figure'].replace('/images/','/images/en/')
            svg=(ROOT/english_figure).read_text(encoding='utf-8')
            original_phases=re.findall(r'data-phase=[\'\"](\d+)[\'\"]',frame['markup'])
            assert re.findall(r'data-phase=[\'\"](\d+)[\'\"]',svg)==original_phases,english_figure
            frame['figure']=english_figure
            frame['markup']=svg
            frame['caption']=translate(frame['caption'])
        data['labels']=[translate(x) for x in data['labels']]
        encoded=json.dumps(data,ensure_ascii=False).replace('</','<\\/')
        return '<script'+attrs+'>'+encoded+'</script>'
    rendered=re.sub(r'<script([^>]*)>(.*?)</script>',script,original,flags=re.S)
    parser=EnglishHTML();parser.feed(rendered);result=''.join(parser.parts)
    target=source.with_name(source.stem+'.en.html')
    target.write_text(result,encoding='utf-8')
    # All behavior hooks must retain their original identities and ordering.
    assert re.findall(r'\b(?:id|class)="[^"]*"',re.sub(r'<script.*?</script>','',original,flags=re.S))==re.findall(r'\b(?:id|class)="[^"]*"',re.sub(r'<script.*?</script>','',result,flags=re.S))
    return target


def main():
    for number,name in PAGES.items():
        source=next((ROOT/'chapters').glob(f'{number:02}-*/{name}.html'))
        print(build_page(source).relative_to(ROOT))


if __name__=='__main__': main()
