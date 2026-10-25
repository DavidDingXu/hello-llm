"""从唯一的 Markdown 正文生成本地学习站；--check 检查页面与搜索索引是否过期。"""
import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import struct
from urllib.parse import quote, unquote, urlsplit, urlunsplit, urlencode
import markdown
from markdown.extensions.toc import slugify_unicode
try:
    from browser_labs import render_lab, module_bundle, BEFORE_SECTIONS
    from training_lab import render_training_lab, PLACEMENTS as TRAINING_PLACEMENTS
    from export_browser_training import check_assets as check_training_assets
except ModuleNotFoundError:
    from visuals.browser_labs import render_lab, module_bundle, BEFORE_SECTIONS
    from visuals.training_lab import render_training_lab, PLACEMENTS as TRAINING_PLACEMENTS
    from visuals.export_browser_training import check_assets as check_training_assets

COLUMN = Path(__file__).resolve().parents[2]
ASSETS = Path(__file__).with_name('reading_site')
BRAND = 'Hello LLM'
TITLE = '手写小模型，看懂大模型'
RELEASE_FILE = ASSETS / 'release.json'
RELEASE = json.loads(RELEASE_FILE.read_text(encoding='utf-8')) if RELEASE_FILE.exists() else {'version': '0.1.0-rc.1'}
BOOK_STEM = 'hello-llm-v' + RELEASE['version'] + '-zh-CN'
BOOK_DIR = 'dist/v' + RELEASE['version']
STAGES = (
    (1, 6, '让数值网络学起来', '从一个输出开始，看到错误怎样改变参数。', '完成第一次学习闭环'),
    (7, 9, '把文字接进来', '把文字变成输入、概率和训练题。', '训练第一个字符预测模型'),
    (10, 16, '读取前文，组装模型', '补上上下文和顺序，把组件接成完整网络。', '看清完整模型的一次前向计算'),
    (17, 20, '预训练、生成与微调', '让同一个模型学会续写，再尝试回答问题。', '复现训练，并用独立数据检验理解'),
)
DEMO_NAMES = {
    'walkthrough.html': '逐步演示', 'lab3d.html': '三维损失曲面',
    'training-replay.html': '训练全过程回放', 'model-inspector.html': '模型解剖台',
}
THREE_DEMOS = {
    '04': ('三维损失曲面', '3D loss surface', '调整参数和学习率，沿真实损失曲面查看更新路径。', 'Change parameters and learning rate; inspect the update path on the loss surface.'),
    '07': ('三维 Embedding 查表', '3D embedding lookup', '选中一个编号，追踪参数表的一行怎样进入批次张量。', 'Select a token ID and follow its embedding row into a batch tensor.'),
    '12': ('三维张量实验', '3D tensor lab', '跟住一个数字，查看拆头、交换轴与合头后的索引。', 'Follow one number through splitting, transposing, and merging heads.'),
    '13': ('三维 RoPE 实验', '3D RoPE lab', '并排观察二维坐标对，比较位置与相对角度对点积的影响。', 'Inspect coordinate pairs and compare how relative positions change dot products.'),
    '16': ('三维模型解剖台', '3D model inspector', '跟随一个字，逐层查看真实表示、注意力和候选分数。', 'Follow one token through real representations, attention and candidate scores.'),
}
ICONS = {
    'arrow': '<path d="M5 12h14M13 6l6 6-6 6"/>',
    'back': '<path d="M19 12H5m6-6-6 6 6 6"/>',
    'search': '<circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 4.5 4.5"/>',
    'menu': '<path d="M4 6h16M4 12h16M4 18h16"/>',
    'close': '<path d="m6 6 12 12M18 6 6 18"/>',
    'external': '<path d="M14 4h6v6m0-6-9 9M10 4H4v16h16v-6"/>',
    'check': '<path d="m5 12 4 4L19 6"/>',
    'focus': '<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/>',
    'code': '<path d="m8 7-5 5 5 5m8-10 5 5-5 5M14 4l-4 16"/>',
    'book': '<path d="M12 5c-3-2-6-2-9-1v15c3-1 6-1 9 1 3-2 6-2 9-1V4c-3-1-6-1-9 1Zm0 0v15"/>',
    'play': '<path d="m9 5 11 7-11 7Z"/>',
    'sun': '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
    'moon': '<path d="M20.5 14.5A9 9 0 0 1 9.5 3.5a9 9 0 1 0 11 11Z"/>',
}


def icon(name):
    return ('<svg class="icon" width="20" height="20" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="1.7" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            + ICONS[name] + '</svg>')


def article_paths():
    metadata = json.loads((ASSETS / 'course.zh.json').read_text(encoding='utf-8'))
    return [COLUMN / row['source'] for row in metadata['articles']]


def without_repository_navigation(source):
    """GitHub uses Markdown navigation; web and book layouts provide their own."""
    return re.sub(r'\n<!-- chapter-navigation:start -->.*?<!-- chapter-navigation:end -->\s*$', '', source, flags=re.S)


def render_article(source, source_path=None):
    """正文与定位目录在同一次转换中产生；仅处理正文，不加入站点导航。"""
    source = without_repository_navigation(source)
    document = markdown.Markdown(
        extensions=['fenced_code', 'tables', 'sane_lists', 'md_in_html', 'toc'],
        extension_configs={'toc': {'toc_depth': '2-2', 'slugify': slugify_unicode}})
    body = document.convert(source)
    body = body.replace('<table>', '<div class="table-scroll"><table>').replace('</table>', '</table></div>')
    if source_path is not None:
        first_image = True

        def reserve_image_space(match):
            nonlocal first_image
            tag = match.group(0)
            src = re.search(r'\bsrc="([^"]+)"', tag)
            if not src:
                return tag
            url = urlsplit(html.unescape(src.group(1)))
            if url.scheme or url.netloc:
                return tag
            path = (source_path.parent / unquote(url.path)).resolve()
            if not path.is_file():
                return tag
            with path.open('rb') as image_file:
                header = image_file.read(24)
            if header.startswith(b'\x89PNG\r\n\x1a\n') and len(header) >= 24:
                width, height = struct.unpack('>II', header[16:24])
            elif header[:6] in (b'GIF87a', b'GIF89a') and len(header) >= 10:
                width, height = struct.unpack('<HH', header[6:10])
            else:
                return tag
            # 先预留正确比例，后续图片按需载入；跳到段落时不会被迟到的图推走。
            attributes = f' width="{width}" height="{height}" loading="{"eager" if first_image else "lazy"}" decoding="async"'
            first_image = False
            return (tag[:-2] + attributes + ' />') if tag.endswith('/>') else (tag[:-1] + attributes + '>')

        body = re.sub(r'<img\b[^>]*>', reserve_image_space, body)
        body = web_figures(body, source_path)
    if source_path is not None:
        body = inline_experiments(body, source_path)
    return body, document.toc if document.toc_tokens else ''


def web_figures(body, source_path):
    """桌面横向、手机单列；矢量内容与原文技术信息保持一致。"""
    def picture(match):
        tag = match.group(0)
        src_match = re.search(r'src="([^"]+)"', tag)
        if not src_match:
            return tag
        src = html.unescape(src_match[1])
        url = urlsplit(src)
        if url.scheme or url.netloc:
            return tag
        image_path = source_path.parent / unquote(url.path)
        english = source_path.name.endswith('.en.md')
        vector_path = image_path.with_suffix('.svg')
        if image_path.suffix in {'.png', '.jpg'} and vector_path.is_file():
            vector_src = str(Path(src).with_suffix('.svg')).replace('\\', '/')
            tag = tag.replace('src="' + html.escape(src) + '"', 'src="' + html.escape(vector_src) + '"', 1)
            src = vector_src
        if image_path.suffix == '.gif':
            label = 'Watch the animated walkthrough' if english else '展开观看动态过程'
            return f'<details class="motion-figure"><summary>{label}</summary>{tag}</details>'
        wide = image_path.parent / 'web' / (image_path.stem + '.svg')
        if not wide.is_file():
            return tag
        markup = wide.read_text(encoding='utf-8')
        if 'data-web-layout="overview"' in markup:
            tag = tag.replace('<img', '<img data-full-figure="' + html.escape(src) + '"', 1)
        viewbox = re.search(r'viewBox="([^"]+)"', markup)
        _, _, width, height = viewbox[1].split()
        import os
        relative = Path(os.path.relpath(wide, source_path.parent)).as_posix()
        return (f'<picture class="wide-figure"><source media="(min-width: 1280px)" '
                f'srcset="{html.escape(relative)}" width="{width}" height="{height}">{tag}</picture>')
    body = re.sub(r'<img\b[^>]*>', picture, body)
    return re.sub(r'<p>(<details class="motion-figure".*?</details>)</p>', r'\1', body, flags=re.S)


def inline_experiments(body, source_path):
    """在第一次提到实验的讲解段后加入可展开实验；原 Markdown 保持平台通用。"""
    english = source_path.name.endswith('.en.md')
    number = source_path.parent.name[:2]
    for name, label in DEMO_NAMES.items():
        filename = name.replace('.html', '.en.html') if english else name
        if not (source_path.parent / filename).is_file():
            continue
        tail = {'walkthrough.html': '', 'lab3d.html': 'surface.html',
                'model-inspector.html': 'model.html', 'training-replay.html': 'training.html'}[name]
        if english:
            label = {'walkthrough.html': 'Step-by-step experiment', 'lab3d.html': 'Loss surface',
                     'model-inspector.html': 'Model X-ray', 'training-replay.html': 'Training replay'}[name]
        heading = 'Try it here' if english else '动手实验'
        hints = {
            'walkthrough.html': ('逐步核对计算过程，随时前进或后退。', 'Step through the calculation, forwards or backwards.'),
            'lab3d.html': ('调整参数，比较更新前后的损失。', 'Change parameters and compare the loss before and after an update.'),
            'training-replay.html': ('沿已有训练记录，查看每一步的变化。', 'Inspect each step of a recorded training run.'),
            'model-inspector.html': ('查看真实张量，追踪模型的一次前向计算。', 'Inspect real tensors throughout one forward pass.'),
        }
        hint = hints[name][int(english)]
        if name == 'lab3d.html' and number in THREE_DEMOS:
            info = THREE_DEMOS[number]
            label, hint = info[int(english)], info[2 + int(english)]
        standalone = 'Open in a new tab' if english else '在新标签页打开'
        expand = 'Expand workspace' if english else '展开大窗口'
        close = 'Return to reading' if english else '返回阅读'
        card = (f'<details class="inline-experiment"><summary><span>{heading} · {label}</span><small>{hint}</small></summary>'
                f'<p><a href="{filename}" class="js-experiment inline-expand">{expand} ↗</a> · '
                f'<a href="{filename}" target="_blank" rel="noopener">{standalone} ↗</a></p>'
                f'<dialog class="inline-workspace experiment-viewer" aria-label="{label}"><header><strong>{label}</strong><div>'
                f'<a href="{filename}" target="_blank" rel="noopener">{standalone} {icon("external")}</a>'
                f'<button class="button inline-close" type="button" aria-label="{close}">{close} {icon("close")}</button></div></header>'
                f'<iframe data-src="{filename}" title="{label}" loading="lazy"></iframe></dialog></details>')
        pattern = r'<p>[^<]*(?:(?!</p>).)*?href="(?:[^" ]*/demos/' + re.escape(number) + '/' + re.escape(tail) + r'|[^" ]*' + re.escape(filename) + r')"(?:(?!</p>).)*?</p>'
        match = re.search(pattern, body, re.S)
        if match:
            body = body[:match.end()] + card + body[match.end():]
        else:
            # 每讲有演示时必须能在正文发现；无既有引用时放在导读之后。
            first_section = re.search(r'<h2\b', body)
            at = first_section.start() if first_section else len(body)
            body = body[:at] + card + body[at:]
    lab = render_lab(source_path.parent.name[:2], english)
    if lab:
        next_heading = BEFORE_SECTIONS[source_path.parent.name[:2]][int(english)]
        section = re.search(r'<h2\b[^>]*>' + re.escape(html.escape(next_heading)) + r'</h2>', body)
        if section is None:
            raise ValueError('可编辑实验缺少对应的讲解段落：' + str(source_path))
        at = section.start()
        body = body[:at] + lab + body[at:]
    training = render_training_lab(source_path.parent.name[:2], english)
    if training:
        next_heading = TRAINING_PLACEMENTS[source_path.parent.name[:2]][int(english)]
        section = re.search(r'<h2\b[^>]*>' + re.escape(html.escape(next_heading)) + r'</h2>', body)
        if section is None:
            raise ValueError('网页训练实验缺少对应讲解段落：' + str(source_path))
        body = body[:section.start()] + training + body[section.start():]
    return body


def render_body(source, source_path=None):
    return render_article(source, source_path)[0]


def source_digest(source):
    return hashlib.sha256(source.encode('utf-8')).hexdigest()


def localize_ui(document, language, article_body=None):
    """只翻译站点界面节点；正文（尤其代码和中文实验字串）逐字保留。"""
    if language != 'en':
        return document
    labels = json.loads((ASSETS / 'ui.en.json').read_text(encoding='utf-8'))
    ordered = sorted(labels, key=len, reverse=True)

    def translate(value):
        value = re.sub(r'中文 · v([^ ]+)', r'Chinese · v\1', value)
        value = re.sub(r'建议预留 (\d+) 分钟', r'Allow about \1 minutes', value)
        value = re.sub(r'展开其余 (\d+) 个实验', r'Show the other \1 experiments', value)
        value = re.sub(r'(\d+) 个交互实验', r'\1 interactive experiments', value)
        value = re.sub(r'(\d+) 个逐步演示', r'\1 step-by-step demos', value)
        if value == '。':
            return '.'
        for key in ordered:
            value = value.replace(key, labels[key])
        return value

    if article_body is not None:
        document = document.replace('<article id="article-body">' + article_body + '</article>',
                                    '<article id="article-body">__ARTICLE_SOURCE__</article>', 1)

    class InterfaceTranslator(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.output = []
            self.raw = False

        def handle_starttag(self, tag, attrs):
            raw = self.get_starttag_text()
            for name, value in attrs:
                if name in ('aria-label', 'placeholder', 'title', 'alt') and value:
                    raw = raw.replace(name + '="' + html.escape(value, quote=True) + '"',
                                      name + '="' + html.escape(translate(value), quote=True) + '"')
            self.output.append(raw)
            if tag in ('script', 'style'):
                self.raw = True

        def handle_endtag(self, tag):
            self.output.append('</' + tag + '>')
            if tag in ('script', 'style'):
                self.raw = False

        def handle_data(self, value):
            self.output.append(value if self.raw else translate(value))

        def handle_entityref(self, name):
            self.output.append('&' + name + ';')

        def handle_charref(self, name):
            self.output.append('&#' + name + ';')

        def handle_decl(self, declaration):
            self.output.append('<!' + declaration + '>')

        def handle_comment(self, value):
            self.output.append('<!--' + value + '-->')

    parser = InterfaceTranslator()
    parser.feed(document)
    result = ''.join(parser.output)
    return result.replace('__ARTICLE_SOURCE__', article_body, 1) if article_body is not None else result


def build_context(paths, language='zh'):
    metadata = json.loads((ASSETS / 'course.zh.json').read_text(encoding='utf-8'))
    metadata_by_source = {row['source']: row for row in metadata['articles']}
    english = json.loads((ASSETS / 'course.en.json').read_text(encoding='utf-8'))
    english_by_id = {row['id']: row for row in english['articles']}
    video_manifest = json.loads((ASSETS / 'videos.json').read_text(encoding='utf-8'))
    videos = {row['id']: row for row in video_manifest['videos']}
    filename = 'index.en.html' if language == 'en' else 'index.html'
    records = []
    for path in paths:
        source_path = path.with_name('README.en.md') if language == 'en' else path
        source = source_path.read_text(encoding='utf-8')
        title = re.search(r'^# (.+)$', source, re.M).group(1)
        try:
            relative = path.relative_to(COLUMN).as_posix()
        except ValueError:  # 独立渲染与单元测试同样可用。
            relative = path.name
        row = metadata_by_source.get(relative, {})
        if language == 'en':
            row = {**row, **english_by_id.get(row.get('id'), {})}
        fallback_id = path.parent.name[:2] if re.match(r'\d{2}-', path.parent.name) else path.parent.name
        lesson_id = row.get('id', fallback_id)
        number = int(lesson_id) if lesson_id.isdigit() else 0
        stage = next((i for i, (start, end, *_) in enumerate(STAGES, 1) if start <= number <= end), 0)
        demos = [{'label': label, 'url': f'chapters/{path.parent.name}/{name.replace(".html", ".en.html") if language == "en" else name}'}
                 for name, label in DEMO_NAMES.items() if (path.parent / name).exists()]
        if lesson_id in THREE_DEMOS:
            for demo in demos:
                if 'lab3d' in demo['url']:
                    demo['label'] = THREE_DEMOS[lesson_id][int(language == 'en')]
        records.append({
            'id': lesson_id, 'title': title, 'topic': row.get('topic', title),
            'goal': row.get('goal', ''), 'summary': row.get('short_summary', ''),
            'minutes': row.get('suggested_reading_minutes', 0), 'stage': stage,
            'url': f'course/{lesson_id}{".en" if language == "en" else ""}.html', 'demos': demos,
            'video': videos.get(lesson_id, {'status': 'pending'}),
            'path': path, 'source': source,
        })
    asset_version = source_digest(''.join((ASSETS / name).read_text(encoding='utf-8')
                                         for name in ('site.css', 'site.js', 'ui.en.json', 'python-lab.mjs', 'python-worker.mjs', 'code-editor.mjs', 'code-editor.css', 'training-lab.mjs', 'training-worker.mjs', 'training-engine.mjs')))[:12]
    content_version = source_digest(json.dumps(metadata, ensure_ascii=False) + json.dumps(english, ensure_ascii=False)
                                    + json.dumps(video_manifest, ensure_ascii=False)
                                    + ''.join(r['source'] for r in records) + asset_version)[:12]
    return {'records': records, 'asset_version': asset_version, 'content_version': content_version,
            'language': language, 'filename': filename}


def page_header(root, context, *, article=False, alternate='index.en.html'):
    menu = (f'<button class="icon-button menu-toggle js-only" type="button" aria-label="打开课程目录" '
            f'aria-controls="course-sidebar" aria-expanded="false">{icon("menu")}</button>') if article else ''
    return f'''<a class="skip-link" href="#main-content">跳到正文</a>
<header class="site-header"><div class="header-inner">{menu}
<a class="brand" href="{root}{context['filename']}" aria-label="Hello LLM · 学习站首页">
<img src="{root}assets/brand-mark.png" alt="" width="36" height="36"><span><strong>{BRAND}</strong><small>手写小模型，看懂大模型</small></span></a>
<nav class="header-nav" aria-label="主导航"><a href="{root}{context['filename']}#curriculum">学习路径</a><a href="{root}{context['filename']}#experiments">交互实验</a><a href="https://github.com/DavidDingXu/hello-llm" target="_blank" rel="noopener">GitHub {icon('external')}</a></nav>
<div class="header-controls"><a class="language-switch" href="{alternate}" lang="{'zh-CN' if context['language'] == 'en' else 'en'}" aria-label="{'切换到中文' if context['language'] == 'en' else 'Switch to English'}">{'中文' if context['language'] == 'en' else 'EN'}</a><button class="icon-button theme-toggle js-only" type="button" aria-label="切换到深色主题" title="切换到深色主题"><span class="theme-light-icon">{icon('moon')}</span><span class="theme-dark-icon">{icon('sun')}</span></button>
<button class="search-trigger js-only" type="button" aria-label="搜索课程">{icon('search')}<span>搜索课程</span><kbd>⌘ K</kbd></button>
</div></div><div class="reading-progress" aria-hidden="true"><span id="reading-progress-bar"></span></div></header>'''


def page_head(title, context, root, digest='', url=None, description=None):
    english = context['language'] == 'en'
    site_url = 'https://daviddingxu.github.io/hello-llm/'
    canonical = site_url + quote(url if url is not None else ('index.en.html' if english else ''), safe='/')
    page_title = 'Build a Small Model, Understand Large Models' if english and not digest else title
    description = description or ('An original 20-lesson course: build and train a small language model, explore interactive diagrams and reproduce experiments on a CPU.' if english else '20讲原创语言模型教程：从一个神经元到预训练、生成与问答微调，配有交互图解、逐讲代码和可复现的CPU实验。')
    social_image = site_url + 'assets/social-preview.png'
    metadata = (f'<meta name="description" content="{html.escape(description)}">'
                f'<link rel="canonical" href="{canonical}">'
                f'<meta property="og:site_name" content="Hello LLM">'
                f'<meta property="og:title" content="{html.escape(page_title)} · Hello LLM">'
                f'<meta property="og:description" content="{html.escape(description)}">'
                f'<meta property="og:type" content="{"article" if digest else "website"}">'
                f'<meta property="og:url" content="{canonical}">'
                f'<meta property="og:image" content="{social_image}">'
                f'<meta name="twitter:card" content="summary_large_image">'
                f'<link rel="image_src" href="{root}assets/social-preview.png">')
    source_meta = f'<meta name="source-sha256" content="{digest}">' if digest else ''
    search_filename = 'search-index.en.js' if context['language'] == 'en' else 'search-index.js'
    bundled = all((COLUMN / BOOK_DIR / (BOOK_STEM + suffix)).is_file() for suffix in ('.pdf', '.epub'))
    bundle_attribute = ' data-offline-bundle="true"' if bundled else ''
    return f'''<!doctype html><html lang="{'en' if context['language'] == 'en' else 'zh-CN'}"{bundle_attribute}><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light">
{source_meta}{metadata}<title>{html.escape(page_title)} · {BRAND}</title>
<link rel="icon" href="{root}assets/favicon.png" type="image/png">
<script>try{{const theme=localStorage.getItem('haohai-tinylm-theme');document.documentElement.dataset.theme=theme==='dark'||(theme!=='light'&&matchMedia('(prefers-color-scheme:dark)').matches)?'dark':'light'}}catch(_){{document.documentElement.dataset.theme='light'}}</script>
<link rel="stylesheet" href="{root}code/visuals/reading_site/site.css?v={context['asset_version']}">
<link rel="stylesheet" href="{root}code/visuals/reading_site/code-editor.css?v={context['asset_version']}">
<script defer src="{root}code/visuals/reading_site/{search_filename}?v={context['content_version']}"></script>
<script defer src="{root}code/visuals/reading_site/site.js?v={context['asset_version']}"></script>
<script type="module" src="{root}code/visuals/reading_site/python-lab.mjs?v={context['asset_version']}"></script>
<script type="module" src="{root}code/visuals/reading_site/training-lab.mjs?v={context['asset_version']}"></script></head>'''


def dialogs():
    return f'''<dialog class="search-dialog" id="search-dialog" aria-labelledby="search-label">
<form method="dialog" class="search-heading"><label for="course-search" id="search-label">{icon('search')}搜索课程</label><button class="icon-button" aria-label="关闭搜索">{icon('close')}</button></form>
<input id="course-search" type="search" placeholder="搜索概念、代码或问题…" autocomplete="off" spellcheck="false">
<p class="search-status" id="search-status" role="status">输入关键词，搜索全部 23 篇文章。</p>
<div class="search-results" id="search-results"></div><footer>↑ ↓ 选择结果 <span>Enter 打开 · Esc 关闭</span></footer></dialog>
<dialog class="experiment-viewer" id="experiment-viewer" aria-labelledby="experiment-title"><header><strong id="experiment-title">交互实验</strong><div><a id="experiment-standalone" target="_blank" rel="noopener">独立打开 {icon('external')}</a><button class="button" id="close-experiment" type="button">返回阅读 {icon('close')}</button></div></header><iframe id="experiment-frame" title="交互实验" src="about:blank"></iframe></dialog>
<dialog class="image-viewer" id="image-viewer" aria-label="放大配图">
<header><span>查看配图</span><div class="image-actions"><button type="button" id="image-zoom-out" aria-label="缩小配图">−</button><output id="image-scale" aria-label="缩放比例">100%</output><button type="button" id="image-zoom-in" aria-label="放大配图">＋</button><button type="button" id="image-size">原尺寸</button><button type="button" id="close-image" autofocus>关闭</button></div></header>
<div class="image-canvas"><p id="image-status" role="status" hidden></p><img id="large-image" alt=""></div><footer><p id="image-description"></p><a id="original-image" target="_blank" rel="noopener">打开原图 {icon('external')}</a></footer></dialog>
<div class="toast" id="toast" role="status"></div>'''


def community(root, compact=False):
    content = f'''<div class="community-section"><div><h2>关注与交流 · 好好用 AI</h2><p>交流学习中的问题与实践心得。</p><p>代码问题和勘误，欢迎在 <a href="https://github.com/DavidDingXu/hello-llm/issues" target="_blank" rel="noopener">GitHub 提交 Issue</a>。</p></div><a class="qr-link" href="{root}code/assets/wechat-official-account.jpg" target="_blank" rel="noopener" aria-label="查看好好用 AI 公众号二维码原图"><img src="{root}code/assets/wechat-official-account.jpg" alt="好好用 AI 微信公众号二维码" width="130" height="130" loading="lazy"><p class="qr-caption">微信扫码 · 点击查看原图</p></a></div>'''
    return '<details class="community-mini"><summary>关注与交流 · 好好用 AI</summary>' + content + '</details>' if compact else content


def video_panel(row, root, language):
    video = row['video']
    if video.get('status') != 'ready':
        return ''

    audio_note = '<span class="video-language">中文讲解</span>' if language == 'en' and video.get('audio_language', 'zh-CN').startswith('zh') else ''
    seconds = round(video.get('duration_seconds', 0))
    duration = f'<span class="video-duration">{seconds // 60}:{seconds % 60:02d}</span>' if seconds else ''
    platform = ''
    bili = video.get('bilibili')
    if not bili:
        raise ValueError('已就绪的视频缺少 B 站地址')
    if bili:
        bvid = bili.get('bvid', '')
        part = bili.get('part', 1)
        if not re.fullmatch(r'BV[A-Za-z0-9]{10}', bvid) or not isinstance(part, int) or part < 1:
            raise ValueError('B站视频标识无效')
        player_url = 'https://player.bilibili.com/player.html?' + urlencode({'bvid': bvid, 'p': part, 'autoplay': 0, 'danmaku': 0})
        watch_url = f'https://www.bilibili.com/video/{bvid}/?p={part}'
        platform = (f'<div class="bilibili-embed"><iframe data-src="{html.escape(player_url)}" '
                    f'title="{html.escape(row.get("title", TITLE))} · B站视频" '
                    'allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe>'
                    f'<p class="video-actions"><a href="{html.escape(watch_url)}" target="_blank" rel="noopener">在 B 站高清观看 ↗</a></p></div>')
    return (f'<details class="lesson-video video-ready" id="lesson-video"><summary>{icon("play")}观看配套视频{duration}{audio_note}</summary>'
            + platform + '</details>')


def sidebar(context, current, root):
    def link(row):
        active = ' aria-current="page"' if row['id'] == current else ''
        label = row['topic'] if row['id'] not in ('intro', '00', 'end') else {'intro': '专栏介绍', '00': '开篇导学', 'end': '结束篇'}[row['id']]
        number = row['id'] if row['stage'] else '·'
        return (f'<a class="lesson-link" data-lesson="{html.escape(row["id"])}" href="{root}{html.escape(row["url"])}"{active}>'
                f'<span class="lesson-number">{number}</span><span>{html.escape(label)}</span><span class="lesson-state" aria-hidden="true"></span></a>')
    rows = context['records']
    body = '<div class="sidebar-guides">' + ''.join(link(r) for r in rows if r['id'] in ('intro', '00')) + '</div>'
    current_row = next((r for r in rows if r['id'] == current), {})
    for i, (start, end, title, *_) in enumerate(STAGES, 1):
        expanded = ' open' if current_row.get('stage') == i else ''
        body += (f'<details class="sidebar-stage"{expanded}><summary><span class="stage-index">第{"一二三四"[i-1]}部分</span>{title}</summary>'
                 + ''.join(link(r) for r in rows if r['stage'] == i) + '</details>')
    body += ''.join(link(r) for r in rows if r['id'] == 'end')
    return f'''<aside class="course-sidebar" id="course-sidebar" aria-label="课程目录">
<div class="sidebar-heading"><a href="{root}{context['filename']}">课程目录</a><button class="icon-button menu-close js-only" type="button" aria-label="关闭课程目录">{icon('close')}</button></div>
<nav aria-label="全部文章">{body}</nav></aside>'''


def article_links(body, source_path, context, output_url):
    """公开阅读地址独立于创作目录；保留配图、实验和代码的真实相对位置。"""
    destination = COLUMN / output_url
    articles = {}
    for row in context['records']:
        for name in ('README.md', 'README.en.md', 'index.html', 'index.en.html'):
            english = '.en.' in name
            suffix = '.en' if english or context['language'] == 'en' else ''
            articles[row['path'].with_name(name).resolve()] = COLUMN / f'course/{row["id"]}{suffix}.html'

    def address(value):
        parsed = urlsplit(html.unescape(value))
        if not parsed.path:
            return value
        if parsed.netloc == 'daviddingxu.github.io' and parsed.path.startswith('/hello-llm/'):
            target = COLUMN / unquote(parsed.path.removeprefix('/hello-llm/'))
        elif parsed.scheme or parsed.netloc or parsed.path.startswith('/'):
            return value
        else:
            target = source_path.parent / unquote(parsed.path)
        target = articles.get(target.resolve(), target.resolve())
        relative = Path(os.path.relpath(target, destination.parent)).as_posix()
        return html.escape(urlunsplit(('', '', quote(relative, safe='/'), parsed.query, parsed.fragment)), quote=True)

    def element(match):
        def attribute(item):
            field, value = item.group(1), item.group(2)
            if field == 'srcset':
                value = ', '.join(' '.join([address(parts[0]), *parts[1:]])
                                  for candidate in value.split(',') if (parts := candidate.strip().split()))
            else:
                value = address(value)
            return f'{field}="{value}"'
        return re.sub(r'\b(href|src|srcset|data-src|data-full-figure)="([^"]*)"', attribute, match.group(0))

    return re.sub(r'<(?:a|img|source|iframe)\b[^>]*>', element, body)


def legacy_article_redirect(url):
    target = '../../' + url
    return (f'<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
            f'<meta http-equiv="refresh" content="0;url={html.escape(target)}">'
            f'<title>{TITLE}</title><a href="{html.escape(target)}">继续阅读</a>'
            f'<script>location.replace({json.dumps(target)} + location.search + location.hash);</script></html>')


def build_document(path, paths=None, context=None):
    paths = paths or article_paths()
    context = context or build_context(paths)
    row = next(r for r in context['records'] if r['path'] == path)
    source = row['source']
    body, contents = render_article(source, path.with_name('README.en.md') if context['language'] == 'en' else path)
    alternate_path = path if context['language'] == 'en' else path.with_name('README.en.md')
    alternate_anchors = []
    if alternate_path.is_file():
        alternate_body = render_body(alternate_path.read_text(encoding='utf-8'))
        alternate_anchors = re.findall(r'<h2\b[^>]*\bid="([^"]+)"', alternate_body)
    body = article_links(body, path, context, row['url'])
    root = '../'
    stage_text = STAGES[row['stage'] - 1][2] if row['stage'] else '阅读之前' if row['id'] != 'end' else '回望与继续'
    experiment_links = ''.join(f'<a href="{root}{html.escape(d["url"])}">{icon("play")}<span>{html.escape(d["label"])}</span>{icon("external")}</a>' for d in row['demos'])
    resource_panel = f'<section class="lesson-experiments"><h2>动手看一看</h2>{experiment_links}</section>' if experiment_links else ''
    goal = f'<p class="lesson-goal">{html.escape(row["goal"])}</p>' if row['goal'] else ''
    minutes = f'<span>建议预留 {row["minutes"]} 分钟</span>' if row['minutes'] else ''
    toc = ('<nav class="reading-route" aria-label="本篇路线"><details open><summary>本篇路线</summary>'
           + contents + '</details></nav>') if contents else ''
    font_controls = ('<div class="font-controls js-only"><button type="button" data-font="-1" aria-label="减小正文字号">A−</button>'
                     '<span data-font-size-label>18</span><button type="button" data-font="1" aria-label="增大正文字号">A+</button></div>')
    mobile_toc = ('<div class="mobile-context"><nav class="reading-route" aria-label="本篇路线"><details><summary>本篇目录</summary>'
                  + contents + '</details></nav>' + font_controls + '</div>') if contents else ''
    index = paths.index(path)
    links = []
    for position, label, arrow in ((index - 1, '上一篇', 'back'), (index + 1, '下一篇', 'arrow')):
        if 0 <= position < len(paths):
            neighbor = context['records'][position]
            links.append(f'<a href="{root}{html.escape(neighbor["url"])}"><span>{label} {icon(arrow)}</span><strong>{html.escape(neighbor["title"])}</strong></a>')
        else:
            links.append('<span></span>')
    document = (page_head(row['title'], context, root, source_digest(source), row['url'], row['summary'])
            + f'<body class="article-page" data-root="{root}" data-page="{html.escape(row["id"])}" data-alternate-sections="{html.escape(json.dumps(alternate_anchors, ensure_ascii=False))}">'
            + page_header(root, context, article=True, alternate=f'{row["id"]}{"" if context["language"] == "en" else ".en"}.html')
            + '<div class="sidebar-scrim" hidden></div><div class="reader-layout">'
            + sidebar(context, row['id'], root)
            + f'''<main class="reader-main" id="main-content"><div class="article-context"><span>{html.escape(stage_text)}</span><div class="article-actions"><button type="button" class="copy-page-link js-only">复制链接</button><button type="button" class="focus-toggle js-only" aria-pressed="false">{icon('focus')}<span>专注阅读</span></button></div></div>
{mobile_toc}<article id="article-body">{body}</article>{video_panel(row, root, context['language'])}
{reader_feedback(row, context)}<nav class="chapter-nav" aria-label="前后篇">{''.join(links)}</nav><footer class="reader-footer">{BRAND} · {TITLE}{community(root, compact=True)}</footer></main>
<aside class="context-sidebar" aria-label="本篇辅助导航"><div class="context-inner">{toc}
<section class="reading-settings"><h2>阅读设置</h2>{font_controls}{minutes}{goal}</section>
</div></aside></div>'''
            + dialogs() + '</body></html>')
    return localize_ui(document, context['language'], body)


def model_preview(context):
    by_id = {row['id']: row for row in context['records']}
    def url(lesson):
        return html.escape(by_id[lesson]['url']) if lesson in by_id else '#curriculum'
    return f'''<div class="model-preview" aria-label="文字经过模型的路径"><div class="model-caption"><span>从文字，到下一个字</span><span class="model-label">TinyLM</span></div>
<div class="token-line" aria-label="输入：早上，小丁喜欢">{''.join('<span>'+c+'</span>' for c in '早上，小丁喜欢')}<span class="next-token">?</span></div>
<div class="model-pipeline"><a href="{url('07')}" class="pipeline-row"><span class="pipeline-dot blue"></span><span>字符变成向量<small>Embedding</small></span><span class="pipeline-lesson">07</span>{icon('arrow')}</a>
<a href="{url('16')}" class="pipeline-row middle"><span class="pipeline-dot purple"></span><span>读取前文，逐层计算<small>Transformer</small></span><span class="pipeline-lesson">10—16</span>{icon('arrow')}</a>
<a href="{url('18')}" class="pipeline-row"><span class="pipeline-dot teal"></span><span>选择下一个字<small>Softmax & sampling</small></span><span class="pipeline-lesson">18</span>{icon('arrow')}</a></div>
<div class="model-loop"><svg viewBox="0 0 50 24" aria-hidden="true"><path d="M1 1v10c0 6 4 9 10 9h34m-5-5 5 5-5 4" fill="none" stroke="currentColor" stroke-width="1.5"/></svg><span>把新字接回输入，再算一次</span></div></div>'''


def reader_feedback(record, context):
    english = context['language'] == 'en'
    page_url = 'https://daviddingxu.github.io/hello-llm/' + quote(record['url'], safe='/')
    location = f"{record['title']} · v{RELEASE['version']}\n{page_url}"
    links = []
    for template, prefix, label in [('question.yml', '[学习] ', 'Ask a question' if english else '提出学习疑问'),
                                     ('content.yml', '[勘误] ', 'Suggest a correction' if english else '反馈内容勘误')]:
        query = urlencode({'template': template, 'title': prefix + record['title'], 'location': location})
        links.append(f'<a href="https://github.com/DavidDingXu/hello-llm/issues/new?{html.escape(query)}" target="_blank" rel="noopener">{label}</a>')
    lead = 'Questions about this chapter?' if english else '这一讲有疑问？'
    return f'<div class="reader-feedback"><span>{lead}</span>{"".join(links)}</div>'


def build_index(paths, context=None):
    context = context or build_context(paths)
    records = context['records']
    by_id = {row['id']: row for row in records}
    start_url = by_id.get('00', records[0])['url']
    first_demo = by_id['01']['demos'][0]['url']
    first_python = by_id['01']['url'] + '#python-lab'
    full_training = by_id['20']['url'] + '#training-lab'
    stage_nav = ''.join(f'<a href="#stage-{i}"><span>{start:02d}—{end:02d}</span><strong>{title}</strong>{icon("arrow")}</a>' for i, (start, end, title, *_) in enumerate(STAGES, 1))
    catalog = ''
    for i, (start, end, title, description, outcome) in enumerate(STAGES, 1):
        lesson_rows = ''
        for row in (r for r in records if r['stage'] == i):
            name = re.sub(r'^\d{2}\s*[|｜]\s*', '', row['title'])
            lesson_rows += f'''<li><a class="course-row" href="{html.escape(row['url'])}" data-lesson="{row['id']}"><span class="row-number">{row['id']}</span><span class="row-content"><strong>{html.escape(name)}</strong><small>{html.escape(row['goal'])}</small></span><span class="lesson-state" aria-hidden="true"></span>{icon('arrow')}</a></li>'''
        catalog += f'''<section class="catalog-stage" id="stage-{i}"><header><span class="stage-marker">第{"一二三四"[i-1]}部分</span><div><h3>{title}</h3><p>{description}</p></div><span class="lesson-range">{start:02d}—{end:02d}</span></header><ol class="course-rows">{lesson_rows}</ol><p class="stage-outcome">{icon('check')}阶段目标：{outcome}</p></section>'''
    guides = ''.join(f'<a href="{html.escape(row["url"])}">{label}{icon("arrow")}</a>' for key, label in (('intro', '专栏介绍'), ('00', '开篇导学')) if (row := by_id.get(key)))
    ending = (f'<a href="{html.escape(by_id["end"]["url"])}">结束篇{icon("arrow")}</a>' if 'end' in by_id else '')
    before_reading = f'<section class="guide-stage"><h3>先从这里开始</h3><p>认识这门课，再给成品模型出两道题。</p><div>{guides}</div></section>'
    after_reading = f'<section class="guide-stage ending-stage"><h3>走完 20 讲之后</h3><p>回看起点，梳理你已经能解释的模型行为。</p><div>{ending}</div></section>'
    featured = []
    other_demos = []
    for row in records:
        for demo in row['demos']:
            is_model = row['id'] == '16' and ('lab3d' in demo['url'] or
                       (demo['label'] == '模型解剖台' and not any('lab3d' in d['url'] for d in row['demos'])))
            if (row['id'], demo['label']) == ('01', '逐步演示') or is_model:
                featured.append((row, demo))
            else:
                other_demos.append((row, demo))
    featured.append((by_id['20'], {'label': '训练完整小模型', 'url': full_training}))
    descriptions = {'01': '改变输入和参数，逐步核对一次神经元计算。', '16': '沿着真实张量，拆开模型的一次前向计算。', '20': '亲手训练，对照损失曲线与生成结果。'}
    demo_list = ''.join(f'''<a class="experiment-feature" href="{html.escape(demo['url'])}"><span class="experiment-number">{row['id']}</span><div><h3>{'神经元逐步演示' if row['id'] == '01' else demo['label']}</h3><p>{descriptions[row['id']]}</p><span class="text-link">打开实验 {icon('arrow')}</span></div></a>''' for row, demo in featured)
    more_demos = ''.join(f'<a href="{html.escape(demo["url"])}"><span>{row["id"]}</span>{html.escape(row["topic"])} · {html.escape(demo["label"])}{icon("arrow")}</a>' for row, demo in other_demos)
    video_cards = ''
    for key in ('intro', '01', '20'):
        row = by_id[key]
        if row['video'].get('status') != 'ready':
            continue
        seconds = round(row['video']['duration_seconds'])
        video_cards += f'<a class="video-card" href="{html.escape(row["url"])}#lesson-video"><img src="{html.escape(row["video"]["poster"])}" alt="" width="1280" height="720" loading="lazy"><span><strong>{html.escape(row["topic"])}</strong><small>{seconds // 60}:{seconds % 60:02d} · 打开本篇视频</small></span></a>'
    video_section = ('<section class="videos-section page-width" id="videos"><div class="section-heading"><div><h2>视频讲解</h2><p>从原理到源码，再到运行结果。</p></div><span class="section-count">23 支视频 · 约 110 分钟</span></div><div class="video-cards">' + video_cards + '</div></section>') if video_cards else ''
    document = (page_head(TITLE, context, './') + '<body class="home-page" data-root="./" data-page="home">'
            + page_header('./', context, alternate='index.html' if context['language'] == 'en' else 'index.en.html') + f'''<main id="main-content"><div class="hero-band"><section class="home-hero page-width"><div class="hero-copy"><p class="book-eyebrow">HELLO LLM · 免费学习 · 非商业使用</p><h1>手写小模型，<br><em>看懂大模型。</em></h1><p>从一个能手算的神经元开始，<br class="desktop-break">亲手接出能训练、能生成文字的小语言模型。</p><div class="hero-actions"><a class="button primary" id="continue-learning" href="{html.escape(start_url)}"><span>开始阅读</span>{icon('arrow')}</a><a class="button secondary" href="#downloads">下载 PDF / EPUB</a></div><p class="hero-note" id="resume-label">零基础可入门 · 20 讲 · 无需 GPU</p></div>{model_preview(context)}</section></div>
<section class="experiments-section" id="experiments"><div class="page-width"><div class="section-heading"><div><h2>让原理，在手上走一遍</h2><p>改数、写代码，再亲手训练一个模型。</p></div></div><div class="featured-experiments">{demo_list}</div><details class="more-experiments"><summary>展开其余 {len(other_demos)} 个实验</summary><div>{more_demos}</div></details></div></section>
{video_section}<section class="curriculum-section page-width" id="curriculum"><div class="section-heading"><div><h2>一步步，把模型造出来</h2><p>沿着同一个项目学习，每个阶段都有可核对的成果。</p></div></div>
<div class="curriculum-layout"><aside class="path-rail"><div class="guide-links beginning-links">{guides}</div><nav aria-label="四阶段学习路径">{stage_nav}</nav><div class="guide-links">{ending}</div></aside><div class="catalog">{before_reading}{catalog}{after_reading}</div></div></section>

<section class="downloads-section page-width" id="downloads"><h2>下载电子书</h2><p>PDF 适合打印，EPUB 适合手机和阅读器。</p><div class="download-links"><a class="button primary" href="{RELEASE["repository"]}/releases/download/v{RELEASE["version"]}/{BOOK_STEM}.pdf" data-offline-href="{BOOK_DIR}/{BOOK_STEM}.pdf" download>下载 PDF</a><a class="button secondary" href="{RELEASE["repository"]}/releases/download/v{RELEASE["version"]}/{BOOK_STEM}.epub" data-offline-href="{BOOK_DIR}/{BOOK_STEM}.epub" download>下载 EPUB</a></div><p class="download-note">中文 · v{RELEASE["version"]}</p></section></main>
<div class="page-width">{community('./')}</div><footer class="site-footer page-width"><span>{BRAND} · v{RELEASE["version"]}</span><span>从神经元到预训练、微调与文字生成</span></footer>'''
            + dialogs() + '</body></html>')
    return localize_ui(document, context['language'])


class SearchSections(HTMLParser):
    """按正文二级标题建索引；索引与可见文本一致，答案折叠内容也能检索。"""
    def __init__(self):
        super().__init__()
        self.sections = [{'anchor': '', 'heading': '', 'parts': []}]
        self.heading = False

    def handle_starttag(self, tag, attrs):
        if tag == 'h2':
            self.sections.append({'anchor': dict(attrs).get('id', ''), 'heading': '', 'parts': []})
            self.heading = True
        elif tag in ('p', 'li', 'pre', 'tr', 'h1', 'h3', 'h4', 'summary', 'br'):
            self.sections[-1]['parts'].append(' ')

    def handle_endtag(self, tag):
        if tag == 'h2':
            self.heading = False
            self.sections[-1]['parts'].append(' ')
        elif tag in ('p', 'li', 'pre', 'tr', 'h1', 'h3', 'h4', 'summary'):
            self.sections[-1]['parts'].append(' ')

    def handle_data(self, data):
        self.sections[-1]['parts'].append(data)
        if self.heading:
            self.sections[-1]['heading'] += data


def build_search_index(context):
    lessons, sections = [], []
    for row in context['records']:
        lessons.append({key: row[key] for key in ('id', 'title', 'topic', 'url', 'stage', 'demos')})
        parser = SearchSections()
        parser.feed(render_body(row['source']))
        for section in parser.sections:
            text = re.sub(r'\s+', ' ', ''.join(section['parts'])).strip()
            if text:
                sections.append({'id': row['id'], 'title': row['title'], 'topic': row['topic'],
                                 'heading': section['heading'], 'text': text,
                                 'url': row['url'] + ('#' + section['anchor'] if section['anchor'] else '')})
    labels = json.loads((ASSETS / 'ui.en.json').read_text(encoding='utf-8')) if context['language'] == 'en' else {}
    data = json.dumps({'lessons': lessons, 'sections': sections, 'labels': labels, 'language': context['language']}, ensure_ascii=False, separators=(',', ':'))
    return '// 由 build_reading.py 从正文生成，请勿手工修改。\nwindow.LEARNING_DATA = ' + data + ';\n'


def build_all(check=False):
    check_training_assets()
    paths = article_paths()
    context = build_context(paths)
    outputs = [(COLUMN / row['url'], build_document(row['path'], paths, context)) for row in context['records']]
    outputs += [(row['path'].with_name('index.html'), legacy_article_redirect(row['url'])) for row in context['records']]
    homepage = build_index(paths, context)
    outputs += [(COLUMN / 'index.html', homepage), (COLUMN / 'index.html', homepage),
                (ASSETS / 'search-index.js', build_search_index(context)),
                (ASSETS / 'python-modules.json', module_bundle()),
                (ASSETS / 'release.json', json.dumps(RELEASE, ensure_ascii=False, indent=2) + '\n')]
    if all(p.with_name('README.en.md').exists() for p in paths):
        english = build_context(paths, 'en')
        outputs += [(COLUMN / row['url'], build_document(row['path'], paths, english)) for row in english['records']]
        outputs += [(row['path'].with_name('index.en.html'), legacy_article_redirect(row['url'])) for row in english['records']]
        homepage_en = build_index(paths, english)
        outputs += [(COLUMN / 'index.en.html', homepage_en), (COLUMN / 'index.en.html', homepage_en),
                    (ASSETS / 'search-index.en.js', build_search_index(english))]
    # Experiment shells are generated here too, so rebuilding a demo cannot drop
    # the shared responsive workbench. Keep this transform strictly idempotent.
    for source in paths:
        for name in DEMO_NAMES:
            for suffix in ('', '.en'):
                demo = source.parent / name.replace('.html', suffix + '.html')
                if not demo.is_file():
                    continue
                page = re.sub(r'<!-- experiment-shell:start -->.*?<!-- experiment-shell:end -->', '',
                              demo.read_text(encoding='utf-8'), flags=re.S)
                css = ''.join(f'<link rel="stylesheet" href="../../code/visuals/reading_site/{asset}">'
                              for asset in ('experiment-ui.css', 'experiment-special.css') if (ASSETS / asset).is_file())
                js = ''.join(f'<script src="../../code/visuals/reading_site/{asset}" defer></script>'
                             for asset in ('experiment-ui.js', 'experiment-special.js') if (ASSETS / asset).is_file())
                shell = '<!-- experiment-shell:start -->' + css + js + '<!-- experiment-shell:end -->'
                # Some original demos use HTML's implicit head/body. Insert before
                # their first body content as well, rather than silently skipping them.
                boundary = re.search(r'</head\s*>|<(?:body|main)\b', page, flags=re.I)
                if not boundary:
                    raise ValueError(f'演示缺少可插入样式的位置：{demo}')
                page = page[:boundary.start()] + shell + page[boundary.start():]
                outputs.append((demo, page))
    stale = []
    for target, content in outputs:
        if not target.exists() or target.read_text(encoding='utf-8') != content:
            stale.append(target)
            if not check:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding='utf-8', newline='\n')
    return stale


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    stale = build_all(check=args.check)
    for path in stale:
        print(('过期：' if args.check else '已生成：') + str(path.relative_to(COLUMN)))
    if args.check and stale:
        raise SystemExit(1)
    print(f'{len(article_paths())} 篇阅读页与搜索索引已和 Markdown 正文核对。')
