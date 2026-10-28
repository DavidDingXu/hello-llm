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
  const editedResults = lab.querySelector('.training-edited');
  let worker, epoch = 0, timer, busy = false, history = {}, snapshots = {}, report = null;
  let lastCompleted = null, previous = null;
  let selectedStage, currentStage, currentOptions;
  const stageName = stage => ({quick:t('快速实验','Quick experiment'),pretrain:t('预训练','Pretraining'),sft:t('问答微调','Fine-tuning')})[stage];
  const formatLoss = value => value > 0 && value < 0.0001 ? value.toExponential(2) : value.toFixed(4);
  const score = answers => `${answers.filter(answer=>answer.exact_match).length} / ${answers.length}`;
  const probeNames = [t('熟悉的续写','A familiar continuation'),t('微调用的问法','A fine-tuning question'),
    t('未训练的问法','An unseen question'),t('另一种旧续写','Another familiar continuation')];
  const sampleEditor = lab.querySelector('.sample-editor');
  const sampleGroup = lab.querySelector('#sample-group'), sampleRecord = lab.querySelector('#sample-record');
  const sampleFields = Object.fromEntries(['text','prompt','answer'].map(key => [key,lab.querySelector('#sample-'+key)]));
  const sampleStatus = lab.querySelector('.sample-editor-status'), sampleNote = lab.querySelector('.sample-change-note');
  const sampleRestore = lab.querySelector('.sample-restore'), sampleRetry = lab.querySelector('.sample-retry');
  let sampleData, originalSamples, draftSamples, sampleHelpers, sampleLoading;
  const groupNames = {
    pretrain_train:t('预训练短句 · 可修改','Pretraining sentences · editable'),
    sft_train:t('微调问答 · 可修改','Fine-tuning examples · editable'),
    pretrain_val:t('预训练验证题 · 只读','Pretraining validation · read-only'),
    sft_val:t('问答验证题 · 只读','Question validation · read-only'),
  };
  function activeGroups() {
    return mode.value==='pipeline'?['pretrain_train','sft_train','pretrain_val','sft_val']
      :mode.value==='sft'?['sft_train','sft_val']:['pretrain_train','pretrain_val'];
  }
  function visibleSamples(group) {
    const rows=draftSamples?.[group] || [];
    return mode.value==='quick'?rows.slice(0,4):rows;
  }
  function sampleEdits() {
    if(!draftSamples)return [];
    return activeGroups().filter(group=>group.endsWith('_train')).flatMap(group=>
      visibleSamples(group).filter(row=>JSON.stringify(row)!==JSON.stringify(originalSamples[group].find(old=>old.record_id===row.record_id)))
        .map(row=>({group,...row})));
  }
  function sampleMessage(issue) {
    const position=(originalSamples?.[issue.group] || []).findIndex(row=>row.record_id===issue.record_id)+1;
    const prefix=position?t(`第 ${position} 条样本：`,`Example ${position}: `):'';
    const messages={
      UNKNOWN_CHARACTER:t(`模型还不认识 ${issue.characters?.join('、')}。请换成下方词表中的字。`,`The model does not know ${issue.characters?.join(', ')}. Use the available characters below.`),
      TOO_LONG:t(`超过 ${issue.limit} 个字符，请缩短问题或答案。`,`More than ${issue.limit} characters. Shorten the prompt or answer.`),
      EMPTY_SAMPLE:t('短句、问题和答案都不能留空。','The sentence, prompt, and answer must not be empty.'),
      VALIDATION_OVERLAP:t('这条内容属于验证题，请保留它用于检查，不要加入训练。','This is a validation example. Keep it for evaluation instead of adding it to training.'),
      READ_ONLY_GROUP:t('验证题不能修改。','Validation examples are read-only.'),
      INVALID_SAMPLE:t('这条样本无法使用，请恢复课程样本后再试。','This example cannot be used. Restore the course examples and retry.'),
    };
    return prefix+(messages[issue.code] || messages.INVALID_SAMPLE);
  }
  function updateDataNotice() {
    const quick=mode.value==='quick', pre=mode.value!=='sft', sft=['sft','pipeline'].includes(mode.value);
    const descriptions=[];
    if(pre)descriptions.push(t(`${quick?4:counts.pretrain_train} 条训练短句、${quick?4:counts.pretrain_val} 条验证短句`,`${quick?4:counts.pretrain_train} training sentences and ${quick?4:counts.pretrain_val} validation sentences`));
    if(sft)descriptions.push(t(`${counts.sft_train} 条训练问答、${counts.sft_val} 条验证问答`,`${counts.sft_train} training question–answer examples and ${counts.sft_val} validation questions`));
    lab.querySelector('.training-data-summary').textContent=t('课程已提供：','Included: ')+descriptions.join(t('；','; '))+t('。验证题不参与参数更新。','. Validation examples do not update parameters.');
    lab.querySelector('[data-preview="pretrain"]').hidden=!pre;
    lab.querySelector('[data-preview="sft"]').hidden=!sft;
    if(draftSamples){
      lab.querySelector('[data-preview="pretrain"] p').textContent=draftSamples.pretrain_train[0].text;
      const row=draftSamples.sft_train[0];lab.querySelector('[data-preview="sft"] p').textContent=row.prompt+row.answer;
    }
    const changed=sampleEdits().length;
    sampleNote.textContent=changed?t(`已修改 ${changed} 条训练样本，其他样本保持原样。验证题仍按课程原答案检查；若改变了人物与水果的关系，原答案可能不再适用。`,`Edited ${changed} training examples. The others are unchanged. Validation still uses the course answers; they may no longer apply if you change the facts.`)
      :t('可以直接训练，也可以展开样本改一条试试。','Train as provided, or open the examples and edit one.');
    if(changed&&report&&!busy)sampleNote.textContent+=t(' 修改不会立即改变下面的回答，需要重新训练。',' The answers below will change only after you train again.');
  }
  function showSample() {
    if(!draftSamples)return;
    const group=sampleGroup.value, row=visibleSamples(group).find(item=>item.record_id===sampleRecord.value);
    if(!row)return;
    const sft=group.startsWith('sft'), readOnly=group.endsWith('_val');
    for(const [key,field] of Object.entries(sampleFields)){
      field.closest('label').hidden=sft?key==='text':key!=='text';
      field.value=row[key] || '';field.readOnly=readOnly;field.disabled=busy;
    }
    sampleStatus.classList.remove('sample-error');
    sampleStatus.textContent=readOnly?t('这是验证题，只用来检查效果，不参与训练。','This example is for evaluation only. It does not take part in training.')
      :t('修改后点击“开始训练”，模型才会学习这次改动。','After editing, select “Start training” to teach the model the change.');
  }
  function listSamples() {
    sampleRecord.replaceChildren();
    for(const [index,row] of visibleSamples(sampleGroup.value).entries()){
      const option=document.createElement('option');option.value=row.record_id;
      option.textContent=`${index+1} / ${visibleSamples(sampleGroup.value).length} · ${(row.text || row.prompt).replaceAll('\n',' ').slice(0,32)}`;
      sampleRecord.append(option);
    }
    showSample();
  }
  function listGroups() {
    const previousGroup=sampleGroup.value;sampleGroup.replaceChildren();
    for(const key of activeGroups()){
      const option=document.createElement('option');option.value=key;option.textContent=groupNames[key];sampleGroup.append(option);
    }
    if(activeGroups().includes(previousGroup))sampleGroup.value=previousGroup;
    listSamples();updateDataNotice();
  }
  async function loadSamples() {
    if(draftSamples)return;
    if(sampleLoading)return sampleLoading;
    sampleStatus.textContent=t('正在读取样本…','Loading examples…');sampleRetry.hidden=true;
    sampleLoading=(async()=>{
      const controller=new AbortController(), timeout=setTimeout(()=>controller.abort(),15000);
      try{
        const [helpers,response]=await Promise.all([
          import(new URL('./training-engine.mjs'+new URL(import.meta.url).search,import.meta.url)),
          fetch(new URL('./training/data.json',import.meta.url),{signal:controller.signal})]);
        if(!response.ok)throw new Error('LOAD_FAILED');
        sampleData=await response.json();sampleHelpers=helpers;originalSamples=helpers.readableSamples(sampleData);
        draftSamples=structuredClone(originalSamples);
        lab.querySelector('.sample-vocab p').textContent=sampleData.tokens.slice(4).map(char=>char==='\n'?t('〔换行〕','[newline]'):char).join(' ');
        listGroups();setBusy(busy);
      }catch(_){sampleStatus.textContent=t('样本暂时没读到。检查网络后，点击“重新读取”。','Examples could not load. Check your connection and select “Retry loading”.');sampleRetry.hidden=false;}
      finally{clearTimeout(timeout);sampleLoading=null;}
    })();
    return sampleLoading;
  }
  sampleEditor.addEventListener('toggle',()=>{if(sampleEditor.open)loadSamples()});
  sampleRetry.addEventListener('click',loadSamples);
  sampleGroup.addEventListener('change',listSamples);sampleRecord.addEventListener('change',showSample);
  for(const [key,field] of Object.entries(sampleFields))field.addEventListener('input',()=>{
    if(!draftSamples || sampleGroup.value.endsWith('_val'))return;
    const row=draftSamples[sampleGroup.value].find(item=>item.record_id===sampleRecord.value);row[key]=field.value;
    updateDataNotice();sampleStatus.classList.remove('sample-error');
    try{sampleHelpers.applySampleEdits(sampleData,sampleEdits(),32);sampleStatus.textContent=t('修改已记下。点击“开始训练”使用这些样本。','Edits are ready. Select “Start training” to use them.');}
    catch(error){sampleStatus.textContent=sampleMessage(error.sampleError || {});sampleStatus.classList.add('sample-error');}
  });
  sampleRestore.addEventListener('click',()=>{
    if(busy||!originalSamples)return;
    draftSamples=structuredClone(originalSamples);listGroups();clearResults();
    sampleStatus.textContent=t('已恢复课程样本。','Course examples restored.');
  });

  const question=lab.querySelector('.training-question'), defaultQuestion=question.textContent;
  const questions={
    pretrain:t('先预测：训练集和验证集的损失会一起变好吗？观察两条曲线从哪里开始分开。','Predict first: will training and validation loss improve together? Look for where the curves diverge.'),
    sft:t('先微调，再降低学习率重跑。对照留出问答与旧续写，解释改善与代价。','Fine-tune, then reduce the learning rate and run again. Compare held-out answers with familiar continuations to explain the trade-off.'),
    pipeline:t('先用课程样本跑一次，再改一条短句或答案，看看同样的问题会得到什么回答。','Run the course examples first, then edit a sentence or answer and check the same prompts again.'),
    quick:t('只用四条样本，先检验模型能不能学会它们。训练损失下降时，留出题也会变好吗？','Use four samples to check whether the model can learn them. As training loss falls, do held-out examples improve too?'),
  };

  function settings() {
    return {mode:mode.value,steps:Number(steps.value),learningRate:Number(rate.value),
      sftSteps:Number(sftSteps.value),sftLearningRate:Number(sftRate.value),sampleEdits:sampleEdits()};
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
    describeRecipe();updateDataNotice();if(draftSamples)listGroups();
  }
  function setBusy(value) {
    busy = value; start.disabled = value; stop.disabled = !value;
    lab.querySelectorAll('select,input,textarea').forEach(field => field.disabled = value);
    sampleEditor.querySelectorAll('select,textarea').forEach(field=>field.disabled=value||!draftSamples);
    sampleRestore.disabled=value||!draftSamples;
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
    editedResults.hidden = true; editedResults.open = false;
    editedResults.querySelector('.training-edited-generations').replaceChildren();
    download.disabled = true;
    updateDataNotice();
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
    metrics.textContent = t(`第 ${last.step} 步 · 训练损失 ${formatLoss(last.train_loss)} · 验证损失 ${formatLoss(last.val_loss)}`,`Step ${last.step} · Training loss ${formatLoss(last.train_loss)} · Validation loss ${formatLoss(last.val_loss)}`);
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
    row(t('修改的训练样本','Edited training examples'),previous.data?.modified || 0,report.data?.modified || 0);
    const finalStage=report.recipes.at(-1).stage;
    if (report.answers && previous.answers) {
      row(t('训练问法 · 完整答对','Training questions · exact answers'),score(previous.answers.sft_train),score(report.answers.sft_train));
      row(t('留出问法 · 完整答对','Held-out questions · exact answers'),score(previous.answers.sft_val),score(report.answers.sft_val));
    }
    report.generations[finalStage].forEach((output,index)=>row(probeNames[index],previous.generations[finalStage][index].text,output.text));
    comparison.querySelector('div').replaceChildren(table);comparison.hidden=false;comparison.open=true;
  }
  function showEditedExamples(examples) {
    const container=editedResults.querySelector('.training-edited-generations');container.replaceChildren();
    for(const example of examples){
      const card=document.createElement('div');card.className='generation-example';
      const title=document.createElement('h4');title.textContent=stageName(example.stage);card.append(title);
      for(const [label,text] of [[t('给模型的输入','Model input'),example.prompt || t('（从句首开始）','(From the start)')],
        [t('样本中的接续','Expected continuation'),example.expected],[t('模型实际生成','Model output'),example.actual || t('（直接结束）','(Ended immediately)')]]){
        const heading=document.createElement('span');heading.className='generation-label';heading.textContent=label;
        const value=document.createElement('p');value.className='generation-text';value.textContent=text;card.append(heading,value);
      }
      if(example.stop!=='eos'){
        const limit=document.createElement('small');limit.textContent=t('达到生成长度上限，尚未生成结束标记。','Generation limit reached before the end marker.');card.append(limit);
      }
      container.append(card);
    }
    editedResults.hidden=false;editedResults.open=true;
  }
  function showObservation() {
    if (history.sft?.length) {
      observation.textContent=t('展开“再检查”，对照未训练的问法与另一种旧续写。问答变好时，原有续写是否都保持不变？','Expand “Check more” to compare an unseen question and another familiar continuation. Did better answers preserve every old continuation?');
    } else {
      const points=history[currentStage] || [], first=points[0], last=points.at(-1);
      if(first && last && last.step>0) observation.textContent=last.val_loss>first.val_loss
        ?t('这次验证损失比训练前更高。看看模型是否只接好了熟悉的句子。','Validation loss is higher than before training. Check whether the model only improved on familiar sentences.')
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
    if(sampleData){
      try{sampleHelpers.applySampleEdits(sampleData,sampleEdits(),32);}
      catch(error){
        const issue=error.sampleError || {};sampleEditor.open=true;
        if(activeGroups().includes(issue.group)){sampleGroup.value=issue.group;listSamples();sampleRecord.value=issue.record_id;showSample();}
        sampleStatus.textContent=sampleMessage(issue);sampleStatus.classList.add('sample-error');status.textContent=sampleStatus.textContent;
        (sampleFields[issue.field] || Object.values(sampleFields).find(field=>!field.closest('label').hidden))?.focus();return;
      }
    }
    previous=lastCompleted;clearResults();currentOptions=settings();setBusy(true);progress.hidden=false;
    status.textContent=t('正在准备训练环境，首次加载需要联网…','Preparing the training environment. The first load requires a connection…');
    const id=++epoch;
    timer=setTimeout(()=>terminate(t('加载超时，请检查网络后重试。','Loading timed out. Check your connection and retry.')),45000);
    try {
      worker ||= new Worker(new URL('./training-worker.mjs'+new URL(import.meta.url).search,import.meta.url),{type:'module'});
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
        } else if(data.type==='edited') {
          showEditedExamples(data.examples);
        } else if(data.type==='complete') {
          report=data.report;progress.value=progress.max;showComparison();lastCompleted=report;
          finish(t('训练完成。下面是同一组输入在训练前后的回答。','Training complete. Compare the answers to the same prompts below.'));
        } else if(data.type==='error') {
          const message=data.sampleError?sampleMessage(data.sampleError):data.error.includes('NON_FINITE')?t('数值无法继续计算，请降低学习率后重新训练。','The values became non-finite. Reduce the learning rate and retry.')
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
