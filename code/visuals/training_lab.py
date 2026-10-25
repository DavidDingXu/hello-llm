"""课程模型训练实验的网页入口；正文和离线书籍仍使用同一份讲解。"""
import html
import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def training_settings():
    folder = Path(__file__).with_name('reading_site') / 'training'
    manifest = json.loads((folder / 'model.json').read_text(encoding='utf-8'))
    data = json.loads((folder / 'data.json').read_text(encoding='utf-8'))
    return manifest['presets'], {key: len(value) for key, value in data['groups'].items()}

PLACEMENTS = {
    '17': ('自己运行这次实验', 'Run the Experiment Yourself'),
    '19': ('查看与重跑', 'Inspect or Rerun'),
    '20': ('再把一次计算拆开', 'Unpack a Single Computation Again'),
}


def render_training_lab(number, english=False):
    if number not in PLACEMENTS:
        return ''
    def t(zh,en): return en if english else zh
    mode = {'17':'pretrain','19':'sft','20':'pipeline'}[number]
    presets, counts = training_settings()
    primary = presets['sft' if mode == 'sft' else 'pretrain']
    task = {
        '17': ('先预测：训练到 1000 步，训练集和验证集的损失都会变好吗？观察两条曲线从哪里开始分开。',
               'Predict first: after 1,000 steps, will both training and validation loss improve? Look for where the curves diverge.'),
        '19': ('微调后，问题回答和旧续写会一起变好吗？先看默认结果，再降低学习率重跑，比较两种能力的变化。',
               'Does fine-tuning improve both answers and familiar continuations? Run the default, then reduce the learning rate and compare.'),
        '20': ('从随机初值开始，连续完成预训练与微调。对照同一组输入，解释模型在两个阶段分别学到了什么。',
               'Start from random weights and run pretraining followed by fine-tuning. Compare the same inputs and explain what each stage changes.'),
    }[number]
    options = [('pretrain','预训练 · 全部数据','Pretraining · full dataset'),
               ('sft','问答微调 · 全部数据','Fine-tuning · full dataset'),
               ('pipeline','完整流程 · 预训练 → 微调','Full pipeline · pretrain → fine-tune'),
               ('quick','快速实验 · 4 条样本','Quick experiment · 4 samples')]
    selects = ''.join(f'<option value="{key}" {"selected" if key == mode else ""}>{t(zh,en)}</option>' for key,zh,en in options)
    return f'''<section class="training-lab" id="training-lab" data-default-mode="{mode}" data-presets="{html.escape(json.dumps(presets))}" data-counts="{html.escape(json.dumps(counts))}" aria-labelledby="training-lab-title">
<div class="lab-heading"><span>{t('动手验证 · 真实训练', 'TEST THE IDEA · REAL TRAINING')}</span><h3 id="training-lab-title">{t('就在这里，把模型训练一遍', 'Train the model right here')}</h3></div>
<p class="training-question">{html.escape(task[int(english)])}</p>
<label class="training-mode-label" for="training-mode">{t('实验', 'Experiment')}<select id="training-mode">{selects}</select></label>
<p class="training-recipe" id="training-recipe"></p>
<details class="training-settings"><summary>{t('调整训练参数', 'Adjust training parameters')}</summary><div class="training-fields">
<label><span class="primary-steps-label">{t('训练步数', 'Training steps')}</span><input id="training-steps" type="number" min="1" max="1000" step="1" value="{primary['steps']}" required></label>
<label><span class="primary-lr-label">{t('学习率', 'Learning rate')}</span><input id="training-lr" type="number" min="0.000001" max="0.1" step="any" value="{primary['learning_rate']}" required></label>
<label class="pipeline-field" {'hidden' if mode != 'pipeline' else ''}>{t('微调步数', 'Fine-tuning steps')}<input id="training-sft-steps" type="number" min="1" max="1000" step="1" value="{presets['sft']['steps']}" required></label>
<label class="pipeline-field" {'hidden' if mode != 'pipeline' else ''}>{t('微调学习率', 'Fine-tuning learning rate')}<input id="training-sft-lr" type="number" min="0.000001" max="0.1" step="any" value="{presets['sft']['learning_rate']}" required></label>
</div><p class="training-change-note">{t('先只改一个变量，再与默认结果比较。', 'Change one variable at a time and compare with the default run.')}</p></details>
<div class="training-actions"><button class="button primary training-start" type="button" disabled>{t('开始训练', 'Start training')}</button><button class="button training-stop" type="button" disabled>{t('停止', 'Stop')}</button><button class="button training-reset" type="button" disabled>{t('重置', 'Reset')}</button><button class="button training-download" type="button" disabled>{t('下载实验记录', 'Download results')}</button></div>
<p class="training-status" role="status">{t('选择实验，点击开始训练。', 'Choose an experiment and start training.')}</p>
<progress class="training-progress" value="0" max="100" aria-label="{t('训练进度', 'Training progress')}" hidden></progress>
<div class="training-results" hidden><div class="training-chart-tabs" role="group" aria-label="{t('查看训练阶段', 'Choose a training stage')}"></div>
<figure class="training-plot"><svg class="training-chart" viewBox="0 0 520 230" role="img" aria-label="{t('训练与验证损失曲线', 'Training and validation loss curves')}"></svg><figcaption><span class="train-key">{t('训练集', 'Training')}</span><span class="validation-key">{t('验证集', 'Validation')}</span><span class="training-metrics"></span></figcaption></figure>
<p class="training-answer-scores" hidden></p><div class="training-generations"></div>
<details class="training-more"><summary>{t('再检查：未训练的问法与另一种旧续写', 'Check more: an unseen question and another familiar continuation')}</summary><div class="training-extra-generations"></div></details>
<p class="training-observation"></p><details class="training-explanation"><summary>{t('实验说明', 'About this experiment')}</summary><p class="training-run-note">{t('重新训练的数值和措辞可能与正文不同，请结合曲线与输出判断。', 'A fresh training run may differ from the recorded values and wording. Compare both curves and outputs.')}</p></details>
<details class="training-comparison" hidden><summary>{t('与上一次训练比较', 'Compare with the previous run')}</summary><div></div></details></div>
<noscript>{t('启用 JavaScript 后可以在这里训练模型；配套代码也可以在本地运行。', 'Enable JavaScript to train here, or run the companion code locally.')}</noscript>
</section>'''
