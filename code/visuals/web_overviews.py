"""连续计算图的网页横向概览；完整数值图仍通过原图入口提供。"""
from pathlib import Path
from html import escape
import json
from build_reading import COLUMN

# 这里只概括结构，数值与分支细节保留在原始教学图中。
FLOWS={
'02':('向量与矩阵：一份输入，多项输出',[('输入 x','同一向量进入两组计算'),('权重矩阵 W','每一行对应一项输出'),('逐项乘加','对应位置相乘，再求和'),('加上偏置 b','每项输出有自己的偏置'),('得到向量 y','y = x @ W.T + b')]),
'03':('多层与非线性：从线性组合到分段变换',[('输入','把同一问题交给网络'),('第一层乘加','计算隐藏层的加权和'),('非线性激活','ReLU 保留正值、截去负值'),('下一层乘加','组合已经改变的表示'),('输出','用目标检查表达能力')]),
'04':('从预测到损失：一次可核对的计算',[('输入与参数','输入 x，当前权重 w'),('计算预测','使用当前参数前向计算'),('对照目标','预测值 − 目标值'),('计算损失','将差值平方'),('准备更新','根据梯度与学习率调整 w')]),
'05':('反向传播：先算前向，再分配梯度',[('前向计算','参数固定，记录中间数值'),('损失','从最终错误开始回传'),('局部梯度','沿反向路径使用链式法则'),('分支合流','同一参数的贡献相加'),('统一更新','梯度就绪后再改参数')]),
'06':('训练循环：把一次更新反复执行',[('取出样本','输入与目标保持对应'),('前向与损失','预测后按目标评分'),('清除旧梯度','避免无意累积旧贡献'),('反向传播','为本轮参数计算梯度'),('参数更新','下一轮用新参数重新预测')]),
'10':('单头注意力：先匹配，再读取',[('输入表示','每个位置都有向量'),('生成 Q、K、V','投影表参与训练'),('匹配分数','Q @ K.T，再缩放'),('Softmax','每行得到一套读取比例'),('汇总 V','按比例加权得到读出向量')]),
'11':('因果注意力：先屏蔽未来，再归一化',[('Q、K','计算位置之间的匹配分数'),('因果掩码','当前行只允许读取前文'),('屏蔽未来','不允许位置置为负无穷'),('Softmax','对可见位置重新分配比例'),('汇总 V','未来位置不参与读出')]),
'15':('模型块：子层计算与残差通路',[('输入 x','保留原始信息通路'),('归一化 → 注意力','先控制幅度，再读取前文'),('第一次残差','将注意力结果加回原通路'),('归一化 → 前馈','在每个位置进行门控加工'),('第二次残差','得到下一模型块的输入')]),
'16':('完整前向：从字符编号到候选分数',[('字符编号','按词表编码，保留顺序'),('Embedding','查出每个字符的向量'),('模型块','注意力、前馈与残差'),('末端归一化','整理最终位置表示'),('词表投影','每个候选字符得到分数')]),
'17':('预训练：用下一字符目标调整参数',[('语料与划分','训练数据与留出数据分开'),('输入和标签','标签比输入错开一个位置'),('前向与损失','给每个位置的正确字符评分'),('反向与更新','按训练目标改变参数'),('评价与保存','检查留出结果，保存快照')]),
'18':('生成循环：权重不变，前缀逐次增长',[('当前前缀','从提示文字开始'),('执行前向','只取最后位置的候选分数'),('选择一个字符','按既定生成策略选择'),('追加到前缀','新的前文进入下一次计算'),('停止条件','选到 EOS 或达到长度上限')]),
'19':('问答微调：只对答案计分',[('问题与答案','放进同一因果序列'),('错位标签','对齐每个下一字符目标'),('选择监督位置','问题不直接计入答案损失'),('反向传播','梯度可经过提示上下文'),('评价取舍','同时检查问答和旧续写')]),
'20':('完整实验：每一步都保留可追溯记录',[('数据与词表','形成可重用的数据快照'),('随机初始化','保存起始模型配置和权重'),('预训练','学习续写，记录训练与评价'),('生成与微调','比较不同阶段的真实行为'),('重载与迁移','重新加载并检验独立数据')])}
EN={
'02':('Vectors and matrices',[('Input x','One vector, multiple outputs'),('Weights W','One row per output'),('Multiply and sum','Match corresponding coordinates'),('Add bias b','One bias for each output'),('Output y','y = x @ W.T + b')]),
'03':('Layers and nonlinearity',[('Input','The same problem enters the network'),('First linear layer','Compute weighted sums'),('Activation','ReLU keeps positive values'),('Next linear layer','Combine the transformed features'),('Output','Compare with the target')]),
'04':('From prediction to loss',[('Input and weight','Input x and current weight w'),('Prediction','Compute with current parameters'),('Target difference','Prediction minus target'),('Loss','Square the difference'),('Update','Use gradient and learning rate')]),
'05':('Backpropagation',[('Forward pass','Keep parameters fixed'),('Loss','Start from the final error'),('Local derivatives','Apply the chain rule in reverse'),('Merge branches','Add contributions to one parameter'),('Update together','Change parameters after gradients')]),
'06':('The training loop',[('Batch','Keep inputs and targets aligned'),('Forward and loss','Predict, then score'),('Clear gradients','Remove previous contributions'),('Backward','Compute this iteration’s gradients'),('Update','Predict again with new parameters')]),
'10':('Single-head attention',[('Input features','One vector at each position'),('Q, K and V','Learned projections'),('Scores','Q @ K.T, then scale'),('Softmax','A distribution for each row'),('Weighted V','Combine the values')]),
'11':('Causal attention',[('Q and K','Compute matching scores'),('Causal mask','Limit each row’s visible positions'),('Hide the future','Set future scores to −infinity'),('Softmax','Normalize allowed positions'),('Weighted V','Future values contribute nothing')]),
'15':('A model block',[('Input x','Keep the residual path'),('Norm → attention','Normalize, then read context'),('First residual','Add to the original path'),('Norm → feed-forward','Transform each position'),('Second residual','Pass the result to the next block')]),
'16':('The complete forward pass',[('Character IDs','Encode in vocabulary order'),('Embedding','Look up each character vector'),('Model blocks','Attention, feed-forward, residuals'),('Final normalization','Normalize the representation'),('Vocabulary projection','Score every candidate character')]),
'17':('Pretraining',[('Data split','Separate training and held-out data'),('Inputs and labels','Shift targets by one position'),('Forward and loss','Score the correct next character'),('Backward and update','Change parameters'),('Evaluate and save','Keep metrics and checkpoints')]),
'18':('The generation loop',[('Current prefix','Start from the prompt'),('Forward pass','Read scores at the last position'),('Choose a character','Use the selected generation policy'),('Append','Feed the new prefix back in'),('Stop','EOS or the length limit')]),
'19':('Answer-only fine-tuning',[('Question and answer','One causal sequence'),('Shifted labels','Align next-character targets'),('Supervised positions','Score only answer positions'),('Backward pass','Gradients can pass through context'),('Evaluate trade-offs','Check answers and old continuations')]),
'20':('A reproducible experiment',[('Data and vocabulary','Save a reusable data snapshot'),('Initialization','Save configuration and weights'),('Pretraining','Record learning and evaluation'),('Generate and fine-tune','Compare observed behavior'),('Reload and transfer','Verify with independent data')])}

def draw(title,items,english):
    width,height=1540,470
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="{escape(title)}" data-web-layout="overview"><rect width="100%" height="100%" fill="white"/><g font-family="Arial,PingFang SC,Microsoft YaHei,sans-serif">'
    svg+=f'<text x="36" y="68" font-size="38" font-weight="600" fill="#222A35">{escape(title)}</text>'
    svg+=f'<text x="36" y="116" font-size="25" fill="#606C7B">{"Structure overview · Open the original figure for numerical details" if english else "结构概览 · 点击图片可查看完整数值与分支细节"}</text>'
    for i,(heading,caption) in enumerate(items):
        x=36+i*300;color=('#3267A4','#8056A5','#8056A5','#187B79','#187B79')[i]
        svg+=f'<rect x="{x}" y="178" width="268" height="180" rx="12" fill="#F4F6F9" stroke="#DDE2E8"/><text x="{x+20}" y="219" font-size="24" fill="{color}">{i+1:02d}</text>'
        # 文本由编辑定义，不截断；英文按词折行，中文按字折行。
        import textwrap
        hs=textwrap.wrap(heading,21 if english else 10)
        cs=textwrap.wrap(caption,27 if english else 12)
        for j,line in enumerate(hs):svg+=f'<text x="{x+20}" y="{258+j*29}" font-size="25" font-weight="600" fill="#222A35">{escape(line)}</text>'
        for j,line in enumerate(cs):svg+=f'<text x="{x+20}" y="{305+j*27}" font-size="22" fill="#606C7B">{escape(line)}</text>'
        if i<4:svg+=f'<path d="M{x+275} 270h18l-5-5m5 5-5 5" fill="none" stroke="#8F9BA8" stroke-width="2"/>'
    svg+=f'<text x="36" y="428" font-size="24" fill="#606C7B">{"Read left to right; repeat the loop where the text specifies." if english else "从左向右读计算顺序；需要循环的部分按正文说明返回起点。"}</text></g></svg>'
    return svg

if __name__=='__main__':
    for key,(title,items) in FLOWS.items():
        folder=next((COLUMN/'chapters').glob(key+'-*'))
        name='03-全流程.svg' if key=='20' else '01-机制.svg'
        for language in ('zh','en'):
            base=folder/'images' if language=='zh' else folder/'images/en'
            if not (base/name).exists():continue
            out=base/'web'/name;out.parent.mkdir(exist_ok=True)
            if out.exists() and 'data-web-layout="two-panels"' in out.read_text(encoding='utf-8'):continue
            t,rows=(title,items) if language=='zh' else EN[key]
            out.write_text(draw(t,rows,language=='en'),encoding='utf-8')
    print('已构建 13 组中英网页结构概览；数值详图保留原图。')

    # 第2章的两条数值路径完整横排，避免概览遮掉正文正在引用的乘加细节。
    d=json.loads((COLUMN/'code/artifacts/lessons/l02.json').read_text(encoding='utf-8'))
    folder=next((COLUMN/'chapters').glob('02-*'))
    for english in (False,True):
        title='One weight row produces one output' if english else '一行权重，算出一项输出'
        svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="1504" height="650" viewBox="0 0 1504 650" role="img" aria-label="{title}" data-web-layout="reconstructed"><rect width="100%" height="100%" fill="white"/><g font-family="Arial,PingFang SC,Microsoft YaHei,sans-serif"><text x="36" y="65" font-size="38" font-weight="600" fill="#222A35">{title}</text>'
        subtitle='Both rows read the same input; neither output feeds the other.' if english else '两行参数读取同一输入；两个输出之间没有计算依赖。'
        svg+=f'<text x="36" y="113" font-size="27" fill="#606C7B">{subtitle}</text>'
        for i in range(2):
            top=166+i*214
            cells=[('Input x' if english else '同一输入 x',str(d['x'])),(f'Weight row {i+1}' if english else f'W 第 {i+1} 行',str(d['W'][i])),('Products' if english else '对应位置相乘',str(d['products'][i])),('Sum' if english else '乘积求和',f'{sum(d["products"][i]):g}'),('Bias → output' if english else '加偏置 → 输出',f'{sum(d["products"][i]):g} + ({d["b"][i]:g}) = {d["output"][i]:g}')]
            for j,(label,value) in enumerate(cells):
                x=36+j*296;color=('#3267A4','#8056A5','#222A35','#222A35','#187B79')[j]
                svg+=f'<rect x="{x}" y="{top}" width="258" height="164" rx="10" fill="#F4F6F9"/><text x="{x+20}" y="{top+45}" font-size="28" fill="{color}">{escape(label)}</text><text x="{x+20}" y="{top+111}" font-size="34" font-weight="600" fill="{color}">{escape(value)}</text>'
                if j<4:svg+=f'<path d="M{x+265} {top+84}h22l-6-6m6 6-6 6" fill="none" stroke="#8F9BA8" stroke-width="2"/>'
        svg+=f'<text x="36" y="620" font-size="27" fill="#187B79">{"Outputs side by side: " if english else "并排组成输出向量："}{escape(str(d["output"]))}</text></g></svg>'
        base=folder/'images'/('en' if english else '')/'web';(base/'01-机制.svg').write_text(svg,encoding='utf-8')
