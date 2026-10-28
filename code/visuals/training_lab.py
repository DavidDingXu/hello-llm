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


def render_samples(mode, english):
    def t(zh, en): return en if english else zh
    data = json.loads((Path(__file__).with_name('reading_site') / 'training/data.json').read_text(encoding='utf-8'))
    sentence = ''.join(data['tokens'][i] for i in data['groups']['pretrain_train'][0]['ids'] if i >= 4)
    answer = data['groups']['sft_train'][0]
    groups = data['groups']
    descriptions = []
    if mode != 'sft':
        descriptions.append(t(f"{len(groups['pretrain_train'])} 条训练短句、{len(groups['pretrain_val'])} 条验证短句",
                              f"{len(groups['pretrain_train'])} training sentences and {len(groups['pretrain_val'])} validation sentences"))
    if mode in ('sft', 'pipeline'):
        descriptions.append(t(f"{len(groups['sft_train'])} 条训练问答、{len(groups['sft_val'])} 条验证问答",
                              f"{len(groups['sft_train'])} training question–answer examples and {len(groups['sft_val'])} validation questions"))
    summary = t('课程已提供：', 'Included: ') + t('；', '; ').join(descriptions) + t('。验证题不参与参数更新。', '. Validation examples do not update parameters.')
    return f'''<section class="training-samples" aria-labelledby="training-samples-title">
<h4 id="training-samples-title">{t('模型要学哪些内容？', 'What will the model learn from?')}</h4>
<p class="training-data-summary">{html.escape(summary)}</p>
<div class="sample-previews"><div data-preview="pretrain" {'hidden' if mode == 'sft' else ''}><span>{t('预训练短句，例如：', 'A pretraining sentence:')}</span><p>{html.escape(sentence)}</p></div>
<div data-preview="sft" {'hidden' if mode not in ('sft','pipeline') else ''}><span>{t('微调问答，例如：', 'A fine-tuning example:')}</span><p>{html.escape(answer['prompt'] + answer['answer'])}</p></div></div>
<details class="sample-editor"><summary>{t('查看全部样本，或改一条试试', 'Browse the samples or edit one')}</summary>
<p class="sample-help">{t('可以修改现有训练样本；验证题只用于检查效果，不能在这里改。修改只用于本页实验，刷新页面会恢复课程样本。', 'You can edit existing training examples. Validation questions are read-only and used only for evaluation. Edits apply to this page; reloading restores the course examples.')}</p>
<div class="sample-selects"><label for="sample-group">{t('数据组', 'Dataset')}<select id="sample-group" disabled></select></label><label for="sample-record">{t('选择一条', 'Choose an example')}<select id="sample-record" disabled></select></label></div>
<label class="sample-text-field" for="sample-text">{t('短句', 'Sentence')}<textarea id="sample-text" rows="2" disabled spellcheck="false"></textarea></label>
<label class="sample-prompt-field" for="sample-prompt" hidden>{t('问题（保留“问：”和“答：”格式）', 'Prompt (keep the 问： and 答： format)')}<textarea id="sample-prompt" rows="2" disabled spellcheck="false"></textarea></label>
<label class="sample-answer-field" for="sample-answer" hidden>{t('期望回答', 'Expected answer')}<textarea id="sample-answer" rows="2" disabled spellcheck="false"></textarea></label>
<p class="sample-editor-status" role="status">{t('展开后读取课程样本。', 'Open this section to load the course examples.')}</p>
<p class="sample-help">{t('每条最多 31 个字符，问题与答案合计。一次只改一条，先猜结果再训练；其他样本仍会影响模型的回答。', 'Each example allows up to 31 characters, counting prompt and answer together. Edit one example, predict the outcome, then train. The other examples still influence the answer.')}</p>
<details class="sample-vocab"><summary>{t('查看可用的字和标点', 'Available characters and punctuation')}</summary><p></p></details>
<div class="sample-tools"><button class="button sample-restore" type="button" disabled>{t('恢复课程样本', 'Restore course examples')}</button><button class="button sample-retry" type="button" hidden>{t('重新读取', 'Retry loading')}</button></div>
</details><p class="sample-change-note" role="status"></p>
</section>'''


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
        '20': ('先用课程样本跑一次，再改一条短句或答案，看看同样的问题会得到什么回答。完整流程从随机参数开始，依次进行预训练和问答微调。',
               'Run the course examples first. Then edit a sentence or answer and check the same prompts again. The full pipeline starts from random weights, pretrains, then fine-tunes on questions and answers.'),
    }[number]
    options = [('pretrain','预训练 · 学习短句','Pretraining · learn from sentences'),
               ('sft','问答微调 · 学习回答','Fine-tuning · learn to answer'),
               ('pipeline','完整流程 · 预训练 → 微调','Full pipeline · pretrain → fine-tune'),
               ('quick','快速实验 · 4 条样本','Quick experiment · 4 samples')]
    selects = ''.join(f'<option value="{key}" {"selected" if key == mode else ""}>{t(zh,en)}</option>' for key,zh,en in options)
    return f'''<section class="training-lab" id="training-lab" data-default-mode="{mode}" data-presets="{html.escape(json.dumps(presets))}" data-counts="{html.escape(json.dumps(counts))}" aria-labelledby="training-lab-title">
<div class="lab-heading"><span>{t('浏览器实验', 'BROWSER EXPERIMENT')}</span><h3 id="training-lab-title">{t('用这些样本训练模型', 'Train a model with these examples')}</h3></div>
<p class="training-question">{html.escape(task[int(english)])}</p>
<label class="training-mode-label" for="training-mode">{t('实验', 'Experiment')}<select id="training-mode">{selects}</select></label>
<p class="training-recipe" id="training-recipe"></p>
{render_samples(mode, english)}
<details class="training-settings"><summary>{t('调整训练参数', 'Adjust training parameters')}</summary><div class="training-fields">
<label><span class="primary-steps-label">{t('训练步数', 'Training steps')}</span><input id="training-steps" type="number" min="1" max="1000" step="1" value="{primary['steps']}" required></label>
<label><span class="primary-lr-label">{t('学习率', 'Learning rate')}</span><input id="training-lr" type="number" min="0.000001" max="0.1" step="any" value="{primary['learning_rate']}" required></label>
<label class="pipeline-field" {'hidden' if mode != 'pipeline' else ''}>{t('微调步数', 'Fine-tuning steps')}<input id="training-sft-steps" type="number" min="1" max="1000" step="1" value="{presets['sft']['steps']}" required></label>
<label class="pipeline-field" {'hidden' if mode != 'pipeline' else ''}>{t('微调学习率', 'Fine-tuning learning rate')}<input id="training-sft-lr" type="number" min="0.000001" max="0.1" step="any" value="{presets['sft']['learning_rate']}" required></label>
</div><p class="training-change-note">{t('步数是参数更新的次数，学习率决定每次更新的幅度。第一次用默认值即可；之后一次只改一项，方便比较结果。', 'Steps count parameter updates; the learning rate controls the size of each update. Start with the defaults, then change one setting at a time.')}</p></details>
<div class="training-actions"><button class="button primary training-start" type="button" disabled>{t('开始训练', 'Start training')}</button><button class="button training-stop" type="button" disabled>{t('停止', 'Stop')}</button><button class="button training-reset" type="button" disabled>{t('重置参数与结果', 'Reset settings and results')}</button><button class="button training-download" type="button" disabled>{t('下载实验记录', 'Download results')}</button></div>
<p class="training-status" role="status">{t('选择实验，点击开始训练。', 'Choose an experiment and start training.')}</p>
<progress class="training-progress" value="0" max="100" aria-label="{t('训练进度', 'Training progress')}" hidden></progress>
<div class="training-results" hidden><h4>{t('训练前后的回答', 'Answers before and after training')}</h4><p class="training-answer-scores" hidden></p><div class="training-generations"></div>
<details class="training-edited" hidden><summary>{t('你改过的样本（训练题）', 'Your edited examples (training data)')}</summary><p class="training-change-note">{t('每个阶段最多展示前三条修改。这里检查的是训练题，答对还不代表能处理新问法。', 'Shows up to three edits per stage. These are training examples; matching them does not establish performance on new questions.')}</p><div class="training-edited-generations"></div></details>
<details class="training-more"><summary>{t('再检查：未训练的问法与另一种旧续写', 'Check more: an unseen question and another familiar continuation')}</summary><div class="training-extra-generations"></div></details>
<div class="training-chart-tabs" role="group" aria-label="{t('查看训练阶段', 'Choose a training stage')}"></div>
<figure class="training-plot"><svg class="training-chart" viewBox="0 0 520 230" role="img" aria-label="{t('训练与验证损失曲线', 'Training and validation loss curves')}"></svg><figcaption><span class="train-key">{t('训练集', 'Training')}</span><span class="validation-key">{t('验证集', 'Validation')}</span><span class="training-metrics"></span></figcaption></figure>
<p class="training-change-note">{t('损失越低，表示模型对这组题的预测更接近答案。验证题没有参与参数更新，要和实际生成的文字一起看。', 'Lower loss means better predictions on these examples. Validation examples do not update parameters; compare their loss with the text the model actually generates.')}</p>
<p class="training-observation"></p><details class="training-explanation"><summary>{t('实验说明', 'About this experiment')}</summary><p class="training-run-note">{t('重新训练的数值和措辞可能与正文不同，请结合曲线与输出判断。', 'A fresh training run may differ from the recorded values and wording. Compare both curves and outputs.')}</p></details>
<details class="training-comparison" hidden><summary>{t('与上一次训练比较', 'Compare with the previous run')}</summary><div></div></details></div>
<noscript>{t('启用 JavaScript 后可以在这里训练模型；配套代码也可以在本地运行。', 'Enable JavaScript to train here, or run the companion code locally.')}</noscript>
</section>'''
