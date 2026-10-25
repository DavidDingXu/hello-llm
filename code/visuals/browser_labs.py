"""前五讲的浏览器练习；运算实现直接取自 tiny_lm，不另存一套算法。"""
import html
import json
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]
MODULES = ('__init__.py', 'scalar.py', 'manual_mlp.py')
# 放在相关推导与示例之后；标题变化时构建失败，避免实验悄悄跑到文章开头。
BEFORE_SECTIONS = {
    '01': ('一个结果，能不能再交给同一个函数？', 'Can one result be passed to the same function again?'),
    '02': ('再来一份输入，参数要不要复制？', 'Does another input sample require another copy of the parameters?'),
    '03': ('两道改数题', 'Two exercises with changed numbers'),
    '04': ('再加一个偏置，这个办法还能用吗？', 'Does the method still work if we add a bias?'),
    '05': ('试改刚才那个权重，核对 −8', 'Perturb that weight to check −8'),
}
LABS = {
    '01': {
        'hint': ('把 x2 从 1 改成 2，输出会从 4 变成多少？', 'Change x2 from 1 to 2. What happens to the output of 4?'),
        'controls': [('x2', '第二个输入', 'Second input', 1, -10, 10, 1), ('bias', '偏置', 'Bias', -1, -20, 20, 1)],
        'code': '''from tiny_lm.scalar import forward, neuron

x2 = 1
bias = -1
inputs = [2, x2]
weights = [1, 3]

print("weighted sum =", forward(inputs, weights, bias))
print("output =", neuron(inputs, weights, bias))
''',
    },
    '02': {
        'hint': ('改一个输入，观察两个输出分别变化多少。', 'Change one input and compare both outputs.'),
        'controls': [('x1', '第一个输入', 'First input', 2, -10, 10, 1), ('x2', '第二个输入', 'Second input', 1, -10, 10, 1)],
        'code': '''from tiny_lm.scalar import linear

x1 = 2
x2 = 1
weights = [[1, 2], [3, 4]]
biases = [1, -1]

print("outputs =", linear([x1, x2], weights, biases))
''',
    },
    '03': {
        'hint': ('关掉隐藏层的 ReLU，再看四组 XOR 输入的结果。', 'Turn off the hidden ReLU and compare all four XOR inputs.'),
        'controls': [('use_relu', '隐藏层激活', 'Hidden activation', True)],
        'code': '''from tiny_lm.scalar import linear, relu

use_relu = True
weights1 = [[1, -1], [-1, 1]]
weights2 = [[1, 1]]

for inputs in ([0, 0], [0, 1], [1, 0], [1, 1]):
    hidden = linear(inputs, weights1, [0, 0])
    if use_relu:
        hidden = [relu(value) for value in hidden]
    output = linear(hidden, weights2, [0])[0]
    print(inputs, "->", output)
''',
    },
    '04': {
        'hint': ('先运行一步，再把学习率从 0.1 改成 0.3；误差还会下降吗？', 'Run one step, then change the learning rate from 0.1 to 0.3. Does the loss still fall?'),
        'controls': [('learning_rate', '学习率', 'Learning rate', 0.1, 0.001, 1, 0.001), ('steps', '更新步数', 'Update steps', 1, 1, 100, 1)],
        'code': '''learning_rate = 0.1
steps = 1
x, target, weight = 2.0, 6.0, 1.0

print(f"start: weight={weight:.4f}, loss={(weight*x-target)**2:.4f}")
for step in range(steps):
    prediction = weight * x
    gradient = 2 * (prediction - target) * x
    weight -= learning_rate * gradient
    loss = (weight * x - target) ** 2
    print(f"step {step+1}: weight={weight:.4f}, loss={loss:.4f}")
''',
    },
    '05': {
        'hint': ('从正文的参数出发，先更新一步，再试着连续更新 10 步。', 'Start with the chapter’s parameters. Update once, then try ten steps.'),
        'controls': [('learning_rate', '学习率', 'Learning rate', 0.01, 0.001, 0.5, 0.001), ('steps', '更新步数', 'Update steps', 1, 1, 100, 1)],
        'code': '''from tiny_lm.manual_mlp import hand_example, forward, backward, step

learning_rate = 0.01
steps = 1
inputs, target = [1.0, 2.0], 1.0
params = hand_example()

prediction, _ = forward(inputs, params)
print(f"start: prediction={prediction:.4f}, loss={(prediction-target)**2:.4f}")
for index in range(steps):
    prediction, cache = forward(inputs, params)
    gradients = backward(cache, target, params)
    step(params, gradients, learning_rate)
    prediction, _ = forward(inputs, params)
    print(f"step {index+1}: prediction={prediction:.4f}, loss={(prediction-target)**2:.4f}")
print("parameters =", params)
''',
    },
}


def module_bundle():
    return json.dumps({name: (CODE / 'tiny_lm' / name).read_text(encoding='utf-8')
                       for name in MODULES}, ensure_ascii=False, indent=2) + '\n'


def render_lab(number, english=False):
    lab = LABS.get(number)
    if lab is None:
        return ''
    def t(zh, en): return en if english else zh
    controls = []
    for name, zh, en, value, *limits in lab['controls']:
        field_id = 'lab-' + name
        if isinstance(value, bool):
            field = f'<select id="{field_id}" data-variable="{name}"><option value="True">ReLU</option><option value="False">{t("不使用激活", "No activation")}</option></select>'
        else:
            low, high, increment = limits
            field = f'<input id="{field_id}" data-variable="{name}" type="number" value="{value}" min="{low}" max="{high}" step="{increment}" required>'
        controls.append(f'<label for="{field_id}">{en if english else zh}{field}</label>')
    return f'''<section class="python-lab" id="python-lab" aria-labelledby="python-lab-title">
<div class="lab-heading"><span>PYTHON · {t('可编辑实验', 'EDITABLE EXPERIMENT')}</span><h3 id="python-lab-title">{t('改一改，运行看看', 'Change it. Run it. See what happens.')}</h3></div>
<p class="lab-challenge">{html.escape(lab['hint'][int(english)])}</p>
<div class="lab-controls">{''.join(controls)}</div>
<details class="lab-editor"><summary>{t('修改 Python 代码', 'Edit Python code')}</summary>
<label class="lab-editor-label" for="lab-code">{t('Python 代码', 'Python code')}</label>
<p class="lab-editor-help" id="lab-code-help">{t('Tab 缩进，Shift + Tab 反缩进；按 Esc 后再按 Tab 离开代码框。Ctrl / ⌘ + Enter 运行。', 'Tab indents; Shift + Tab unindents. Press Esc then Tab to leave the editor. Ctrl / ⌘ + Enter runs the code.')}</p>
<textarea id="lab-code" class="lab-code" aria-describedby="lab-code-help" wrap="off" spellcheck="false" autocapitalize="off" autocomplete="off" autocorrect="off" rows="{min(18, lab['code'].count(chr(10)) + 1)}">{html.escape(lab['code'])}</textarea>
</details>
<div class="lab-actions"><button type="button" class="button primary lab-run" disabled>{t('运行代码', 'Run code')}</button><button type="button" class="button lab-stop" disabled>{t('停止', 'Stop')}</button><button type="button" class="button lab-reset" disabled>{t('恢复示例', 'Reset example')}</button><button type="button" class="button lab-download" disabled>{t('下载代码', 'Download code')}</button></div>
<p class="lab-status" role="status">{t('点击运行，结果显示在下面。', 'Run the code to see the result below.')}</p>
<pre class="lab-output" tabindex="0" aria-label="{t('运行输出', 'Program output')}">{t('等待运行…', 'Ready to run…')}</pre>
<noscript>{t('启用 JavaScript 后可在这里运行代码，也可以复制示例在本地执行。', 'Enable JavaScript to run here, or copy the example and run locally.')}</noscript>
</section>'''
