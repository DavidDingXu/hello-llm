const lab = document.querySelector('.training-lab');
if (lab && location.protocol !== 'file:' && typeof Worker !== 'undefined') {
  const english = document.documentElement.lang === 'en';
  const t = (zh,en) => english ? en : zh;
  const presets = JSON.parse(lab.dataset.presets), counts = JSON.parse(lab.dataset.counts);
  const mode = lab.querySelector('#training-mode'), steps = lab.querySelector('#training-steps');
  const rate = lab.querySelector('#training-lr'), sftSteps = lab.querySelector('#training-sft-steps');
  const sftRate = lab.querySelector('#training-sft-lr');
  const start = lab.querySelector('.training-start'), stop = lab.querySelector('.training-stop');
  const reset = lab.querySelector('.training-reset'), download = lab.querySelector('.training-download');
  const status = lab.querySelector('.training-status'), progress = lab.querySelector('.training-progress');
  const results = lab.querySelector('.training-results'), tabs = lab.querySelector('.training-chart-tabs');
  const chart = lab.querySelector('.training-chart'), metrics = lab.querySelector('.training-metrics');
  const generations = lab.querySelector('.training-generations'), observation = lab.querySelector('.training-observation');
  const extraGenerations = lab.querySelector('.training-extra-generations');
  const comparison = lab.querySelector('.training-comparison');
  const answerScores = lab.querySelector('.training-answer-scores');
  let worker, epoch = 0, timer, busy = false, history = {}, snapshots = {}, report = null;
  let lastCompleted = null, previous = null;
  let selectedStage, currentStage, currentOptions;
  const stageName = stage => ({quick:t('快速实验','Quick experiment'),pretrain:t('预训练','Pretraining'),sft:t('问答微调','Fine-tuning')})[stage];
  const formatLoss = value => value > 0 && value < 0.0001 ? value.toExponential(2) : value.toFixed(4);
  const score = answers => `${answers.filter(answer=>answer.exact_match).length} / ${answers.length}`;
  const probeNames = [t('熟悉的续写','A familiar continuation'),t('微调用的问法','A fine-tuning question'),
    t('未训练的问法','An unseen question'),t('另一种旧续写','Another familiar continuation')];
  const question=lab.querySelector('.training-question'), defaultQuestion=question.textContent;
  const questions={
    pretrain:t('先预测：训练集和验证集的损失会一起变好吗？观察两条曲线从哪里开始分开。','Predict first: will training and validation loss improve together? Look for where the curves diverge.'),
    sft:t('先微调，再降低学习率重跑。对照留出问答与旧续写，解释改善与代价。','Fine-tune, then reduce the learning rate and run again. Compare held-out answers with familiar continuations to explain the trade-off.'),
    pipeline:t('从随机初值开始，连续完成预训练与微调。对照同一组输入，解释每个阶段学到了什么。','Start from random weights and run pretraining followed by fine-tuning. Compare the same inputs and explain what each stage changes.'),
    quick:t('只用四条样本，先检验模型能不能学会它们。训练损失下降时，留出题也会变好吗？','Use four samples to check whether the model can learn them. As training loss falls, do held-out examples improve too?'),
  };

  function settings() {
    return {mode:mode.value,steps:Number(steps.value),learningRate:Number(rate.value),
      sftSteps:Number(sftSteps.value),sftLearningRate:Number(sftRate.value)};
  }
  function describeRecipe() {
    const selected = mode.value, base = presets[selected === 'pipeline' ? 'pretrain' : selected];
    const custom = Number(steps.value) !== base.steps || Number(rate.value) !== base.learning_rate
      || (selected === 'pipeline' && (Number(sftSteps.value) !== presets.sft.steps || Number(sftRate.value) !== presets.sft.learning_rate));
    const label = custom ? t('已调整参数。','Custom parameters. ') : t('课程配置。','Course settings. ');
    const descriptions = {
      pretrain: t(`${counts.pretrain_train} 条训练 / ${counts.pretrain_val} 条验证 · 每批 ${base.batch_size} 条 · ${steps.value} 步`, `${counts.pretrain_train} training / ${counts.pretrain_val} validation samples · batch ${base.batch_size} · ${steps.value} steps`),
      sft: t(`从正文预训练权重开始 · ${counts.sft_train} 条训练 / ${counts.sft_val} 条验证 · 每批 ${base.batch_size} 条 · ${steps.value} 步`, `Starts from the course's pretrained weights · ${counts.sft_train} training / ${counts.sft_val} validation samples · batch ${base.batch_size} · ${steps.value} steps`),
      pipeline: t(`同一个模型先预训练 ${steps.value} 步，再微调 ${sftSteps.value} 步；两阶段使用各自完整数据。`, `Pretrain the same model for ${steps.value} steps, then fine-tune for ${sftSteps.value}. Both stages use their full datasets.`),
      quick: t(`4 条训练 / 4 条验证 · 每批 4 条 · ${steps.value} 步`, `4 training / 4 validation samples · batch 4 · ${steps.value} steps`),
    };
    lab.querySelector('.training-recipe').textContent = (selected === 'quick' ? t('快速实验。','Quick experiment. ') : label) + descriptions[selected];
  }
  function preset() {
    const isSft = mode.value === 'sft', isPipeline = mode.value === 'pipeline';
    const base = presets[isPipeline ? 'pretrain' : mode.value];
    steps.value = base.steps; rate.value = base.learning_rate;
    sftSteps.value = presets.sft.steps; sftRate.value = presets.sft.learning_rate;
    question.textContent=mode.value===lab.dataset.defaultMode?defaultQuestion:questions[mode.value];
    lab.querySelectorAll('.pipeline-field').forEach(field => field.hidden = !isPipeline);
    lab.querySelector('.primary-steps-label').textContent = isPipeline ? t('预训练步数','Pretraining steps') : t('训练步数','Training steps');
    lab.querySelector('.primary-lr-label').textContent = isPipeline ? t('预训练学习率','Pretraining learning rate') : t('学习率','Learning rate');
    describeRecipe();
  }
  function setBusy(value) {
    busy = value; start.disabled = value; stop.disabled = !value;
    lab.querySelectorAll('select,input').forEach(field => field.disabled = value);
    download.disabled = value || !report; lab.setAttribute('aria-busy', String(value));
  }
  function finish(message) { clearTimeout(timer); setBusy(false); status.textContent = message; }
  function terminate(message) {
    epoch++; worker?.terminate(); worker = null;
    finish(message);
  }
  function clearResults() {
    history = {}; snapshots = {}; report = null; selectedStage = currentStage = null;
    results.hidden = true; progress.hidden = true; progress.value = 0;
    chart.replaceChildren(); tabs.replaceChildren(); generations.replaceChildren(); extraGenerations.replaceChildren(); observation.textContent = '';
    comparison.hidden = true; comparison.open = false;
    answerScores.hidden = true; answerScores.textContent = '';
    download.disabled = true;
  }
  mode.addEventListener('change', () => { preset(); clearResults(); status.textContent = t('点击开始，用所选配置重新训练。','Start a new run with the selected settings.'); });
  [steps,rate,sftSteps,sftRate].forEach(field => field.addEventListener('input', describeRecipe));
  reset.disabled = false;
  reset.addEventListener('click', () => {
    terminate(t('已重置。下一次训练从该实验的初始权重开始。','Reset. The next run starts from this experiment’s initial weights.'));
    preset(); clearResults();
  });
  stop.addEventListener('click', () => terminate(t('已停止，已显示的结果保留。再次开始会重新训练。','Stopped. The displayed results remain. Start again for a new run.')));

  function svgElement(name, attributes, text) {
    const node = document.createElementNS('http://www.w3.org/2000/svg', name);
    Object.entries(attributes).forEach(([key,value]) => node.setAttribute(key,String(value)));
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function drawChart() {
    const points = history[selectedStage] || [];
    if (!points.length) return;
    chart.replaceChildren();
    const left=44, top=12, width=458, height=176;
    const maximum = Math.max(0.2, ...points.flatMap(p => [p.train_loss,p.val_loss])) * 1.08;
    const totalSteps = selectedStage === 'sft' && currentOptions.mode === 'pipeline' ? currentOptions.sftSteps : currentOptions.steps;
    for (let tick=0; tick<=4; tick++) {
      const y = top + tick * height / 4, value = maximum * (1-tick/4);
      chart.append(svgElement('line',{x1:left,y1:y,x2:left+width,y2:y,class:'training-grid'}));
      chart.append(svgElement('text',{x:left-7,y:y+4,'text-anchor':'end',class:'training-tick'},value.toFixed(1)));
    }
    const stepTicks = Math.min(4, totalSteps);
    for (let tick=0; tick<=stepTicks; tick++) {
      const step = Math.round(totalSteps*tick/stepTicks);
      chart.append(svgElement('text',{x:left+step/totalSteps*width,y:211,'text-anchor':'middle',class:'training-tick'},step));
    }
    for (const [key,style] of [['train_loss','training-line'],['val_loss','validation-line']]) {
      const path = points.map((p,i) => `${i?'L':'M'}${left+p.step/totalSteps*width},${top+height-p[key]/maximum*height}`).join(' ');
      chart.append(svgElement('path',{d:path,class:style,fill:'none','stroke-width':2.5}));
      const last = points.at(-1);
      chart.append(svgElement('circle',{cx:left+last.step/totalSteps*width,cy:top+height-last[key]/maximum*height,r:3,class:style}));
    }
    const last=points.at(-1);
    metrics.textContent = t(`第 ${last.step} 步 · ${formatLoss(last.train_loss)} / ${formatLoss(last.val_loss)}`,`Step ${last.step} · ${formatLoss(last.train_loss)} / ${formatLoss(last.val_loss)}`);
    chart.setAttribute('aria-label',t(`${stageName(selectedStage)}第 ${last.step} 步，训练损失 ${formatLoss(last.train_loss)}，验证损失 ${formatLoss(last.val_loss)}`,`${stageName(selectedStage)}, step ${last.step}. Training loss ${formatLoss(last.train_loss)}, validation loss ${formatLoss(last.val_loss)}.`));
    tabs.querySelectorAll('button').forEach(button => button.setAttribute('aria-pressed',String(button.dataset.stage===selectedStage)));
  }
  function addStage(stage) {
    if (history[stage]) return;
    history[stage]=[];
    const button=document.createElement('button');button.type='button';button.dataset.stage=stage;
    button.textContent=stageName(stage);button.addEventListener('click',()=>{selectedStage=stage;drawChart();});
    tabs.append(button);
  }
  function showGenerations() {
    generations.replaceChildren(); extraGenerations.replaceChildren();
    for(let index=0;index<4;index++) {
      const card=document.createElement('div');card.className='generation-example';
      const title=document.createElement('h4');title.textContent=probeNames[index];
      const prompt=document.createElement('p');prompt.className='generation-prompt';prompt.textContent=snapshots.initial?.[index].prompt || '';
      card.append(title,prompt);
      for(const [stage,values] of Object.entries(snapshots)) {
        const label=document.createElement('span');label.className='generation-label';
        label.textContent=stage==='initial'?t('训练前','Before training'):stageName(stage)+t('后',' result');
        const value=document.createElement('p');value.className='generation-text';value.textContent=values[index].text || t('（直接结束）','(Ended immediately)');
        if (values[index].stop !== 'eos') {
          const limit = document.createElement('small');limit.textContent=t('（达到生成长度上限）',' (Generation length limit reached)');value.append(limit);
        }
        card.append(label,value);
      }
      (index < 2 ? generations : extraGenerations).append(card);
    }
  }
  function showComparison() {
    if (!previous || previous.mode !== report.mode) return;
    const table=document.createElement('table'), head=document.createElement('thead'), body=document.createElement('tbody');
    const header=document.createElement('tr');
    for (const label of [t('对照项','Measure'),t('上一次','Previous'),t('这一次','Current')]) {
      const cell=document.createElement('th');cell.textContent=label;header.append(cell);
    }
    head.append(header);table.append(head,body);
    const row=(label,oldValue,newValue)=>{
      const line=document.createElement('tr');
      for(const value of [label,oldValue,newValue]) {const cell=document.createElement('td');cell.textContent=value;line.append(cell);}
      body.append(line);
    };
    for (const recipe of report.recipes) {
      const stage=recipe.stage, oldRecipe=previous.recipes.find(item=>item.stage===stage);
      const oldPoint=previous.history[stage].at(-1), point=report.history[stage].at(-1);
      row(stageName(stage)+t(' · 步数 / 学习率',' · steps / learning rate'), `${oldRecipe.steps} / ${oldRecipe.learning_rate}`,`${recipe.steps} / ${recipe.learning_rate}`);
      row(stageName(stage)+t(' · 训练 / 验证损失',' · training / validation loss'),`${formatLoss(oldPoint.train_loss)} / ${formatLoss(oldPoint.val_loss)}`,`${formatLoss(point.train_loss)} / ${formatLoss(point.val_loss)}`);
    }
    const finalStage=report.recipes.at(-1).stage;
    if (report.answers && previous.answers) {
      row(t('训练问法 · 完整答对','Training questions · exact answers'),score(previous.answers.sft_train),score(report.answers.sft_train));
      row(t('留出问法 · 完整答对','Held-out questions · exact answers'),score(previous.answers.sft_val),score(report.answers.sft_val));
    }
    report.generations[finalStage].forEach((output,index)=>row(probeNames[index],previous.generations[finalStage][index].text,output.text));
    comparison.querySelector('div').replaceChildren(table);comparison.hidden=false;comparison.open=true;
  }
  function showObservation() {
    if (history.sft?.length) {
      observation.textContent=t('展开“再检查”，对照未训练的问法与另一种旧续写。问答变好时，原有续写是否都保持不变？','Expand “Check more” to compare an unseen question and another familiar continuation. Did better answers preserve every old continuation?');
    } else {
      const points=history[currentStage] || [], first=points[0], last=points.at(-1);
      if(first && last && last.step>0) observation.textContent=last.val_loss>first.val_loss
        ?t('训练集上的进步没有自动带来验证集上的进步。结合两条曲线，解释正文中的差异。','Improvement on training data did not automatically improve validation performance. Use both curves to explain the difference.')
        :t('先看两条曲线，再看生成结果：一次损失下降，是否已经足以说明模型学会了新问法？','Compare both curves with the generated text. Does a lower loss already demonstrate that the model learned a new phrasing?');
    }
  }
  download.addEventListener('click', () => {
    if(!report)return;
    const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)+'\n'],{type:'application/json'}));
    const link=document.createElement('a');link.href=url;link.download='hello-llm-training-'+report.mode+'.json';link.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  start.addEventListener('click', () => {
    if(busy)return;
    for(const field of lab.querySelectorAll('input')) {
      if(!field.closest('[hidden]') && !field.checkValidity()) {
        lab.querySelector('.training-settings').open=true;
        status.textContent=t('请填写有效的步数和学习率，再开始训练。','Enter a valid step count and learning rate before starting.');
        field.reportValidity();field.focus();return;
      }
    }
    previous=lastCompleted;clearResults();currentOptions=settings();setBusy(true);progress.hidden=false;
    status.textContent=t('正在准备训练环境，首次加载需要联网…','Preparing the training environment. The first load requires a connection…');
    const id=++epoch;
    timer=setTimeout(()=>terminate(t('加载超时，请检查网络后重试。','Loading timed out. Check your connection and retry.')),45000);
    try {
      worker ||= new Worker(new URL('./training-worker.mjs',import.meta.url),{type:'module'});
      worker.onerror=()=>{if(id===epoch)terminate(t('训练环境未能启动，请检查网络后重试。','The training environment could not start. Check your connection and retry.'));};
      worker.onmessage=({data})=>{
        if(data.id!==epoch)return;
        if(data.type==='ready') {
          clearTimeout(timer);timer=setTimeout(()=>terminate(t('已达到本次运行的 5 分钟上限。结果保留，可减少步数后重试。','Stopped after the 5-minute limit. Results remain; reduce the step count and retry.')),300000);
          status.textContent=t('正在计算初始结果…','Calculating the initial results…');
        } else if(data.type==='initial') {
          snapshots.initial=data.generations;results.hidden=false;showGenerations();
        } else if(data.type==='stage') {
          currentStage=selectedStage=data.stage;addStage(data.stage);progress.value=0;progress.max=data.steps;
          status.textContent=stageName(data.stage)+t('：正在检查训练与验证数据…',': evaluating training and validation data…');
        } else if(data.type==='snapshot') {
          history[data.stage].push(data.point);snapshots[data.stage]=data.generations;
          results.hidden=false;drawChart();showGenerations();showObservation();
        } else if(data.type==='progress') {
          progress.value=data.step;status.textContent=stageName(data.stage)+` · ${data.step} / ${data.steps}`;
        } else if(data.type==='checking') {
          status.textContent=t('正在逐题检查训练问法与留出问法…','Checking exact answers to training and held-out questions…');
        } else if(data.type==='answers') {
          answerScores.textContent=t(`完整答对：训练问法 ${score(data.answers.sft_train)} · 留出问法 ${score(data.answers.sft_val)}`,`Exact answers: training questions ${score(data.answers.sft_train)} · held-out questions ${score(data.answers.sft_val)}`);
          answerScores.hidden=false;
        } else if(data.type==='complete') {
          report=data.report;progress.value=progress.max;showComparison();lastCompleted=report;
          finish(t('训练完成。现在比较曲线和两种输出，再改一个变量重跑。','Training complete. Compare the curves and both outputs, then change one variable and run again.'));
        } else if(data.type==='error') {
          const message=data.error.includes('NON_FINITE')?t('数值无法继续计算，请降低学习率后重新训练。','The values became non-finite. Reduce the learning rate and retry.')
            :data.error.includes('INVALID_OPTIONS')?t('请检查步数和学习率范围。','Check the step count and learning-rate range.')
            :data.error.includes('ASSET_MISMATCH')?t('训练资源版本不一致，请刷新页面后重试。','Training assets have different versions. Refresh the page and retry.')
            :t('实验未能完成。请检查网络后重试；已显示的结果保留。','The experiment could not finish. Check your connection and retry; displayed results remain.');
          terminate(message);
        }
      };
      worker.postMessage({type:'start',id,options:currentOptions});
    } catch(_) {terminate(t('此浏览器无法启动训练，请使用新版浏览器重试。','This browser could not start training. Try a current browser.'));}
  });
  addEventListener('pagehide',()=>terminate(busy
    ?t('已离开实验，本次训练停止。可以重新开始。','Training stopped when you left the page. You can start a new run.')
    :status.textContent));
  preset();setBusy(false);
}
