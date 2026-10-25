"""逐讲小实验：调用模型组件，返回便于检查的数值字典。

核心算法在 tiny_lm/；这里准备小输入、改变一个条件，再保存前后结果。
hand_calc 表示固定参数的手算例，teaching_run 表示实际训练或已存训练记录，
mechanism_check 表示检查计算路径。第09讲会训练字符基线；第17/19讲在这里
只读原记录，重新训练由对应入口转给 tiny_lm.train。
"""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path

from tiny_lm.trace import export_trace, parameter_digest
from tiny_lm.teaching import add_observation_arguments, observe_lesson

ROOT = Path(__file__).resolve().parents[1]
FIRST = ROOT / 'artifacts/first_run'  # 已保存的原实验，独立于读者的新训练输出。


def read_record(name):
    """读取一份已保存的JSON记录；读取记录不会把其中的参数加载进模型。"""
    return json.loads((FIRST / f'{name}.json').read_text(encoding='utf-8'))


def lesson02():
    """一份两项输入产生两个输出，再把同一层用于两份样本。"""
    from tiny_lm.scalar import linear
    x, w, b = [2, 1], [[1, 2], [3, 4]], [1, -1]
    batch = [x, [0, 1]]  # 每一行是一个样本，权重w和偏置b在样本之间共用。
    return {'kind': 'hand_calc', 'x': x, 'W': w, 'b': b,
            'products': [[a*v for a,v in zip(x,row)] for row in w],
            'output': linear(x, w, b), 'batch': batch,
            'batch_output': [linear(sample,w,b) for sample in batch]}


def lesson03():
    """手工指定两个ReLU分支，逐个验证四条XOR规则；不训练参数。"""
    from tiny_lm.manual_mlp import forward
    params = {'W1': [[1, -1], [-1, 1]], 'b1': [0, 0],
              'W2': [[1, 1]], 'b2': [0]}
    rows = []
    for x1,x2 in [(0,0),(0,1),(1,0),(1,1)]:
        # 调用正文对应的网络，修改其激活规则后，本实验也会反映这次改动。
        prediction, cache = forward([x1, x2], params)
        rows.append({'x':[x1,x2], 'h':cache['h'], 'y':prediction, 'target':int(x1!=x2)})
    return {'kind': 'hand_calc', 'rows': rows}


def lesson04():
    """固定输入x=2和目标6，只改变一个权重w，比较不同学习率。"""
    x,w,target = 2.,1.,6.
    loss = lambda value:(value*x-target)**2
    gradient = 2*(w*x-target)*x  # 平方误差的变化率，再乘预测对w的变化率x。
    return {'kind':'hand_calc','x':x,'w':w,'target':target,'prediction':w*x,
            'loss':loss(w),'gradient':gradient,
            'perturbation':{'w':1.1,'loss':loss(1.1)},
            'updates':[{'lr':lr,'w':w-lr*gradient,'prediction':(w-lr*gradient)*x,
                        'loss':loss(w-lr*gradient)} for lr in [.1,.3]],
            'curve':[{'w':v/20,'loss':loss(v/20)} for v in range(-10,131)]}


def lesson05():
    """对2→2→1网络核对全部梯度，再统一更新，返回两次前向的结果。"""
    from tiny_lm.manual_mlp import hand_example, forward, backward, step
    x,target,params = [1.,2.],1.,hand_example()
    prediction,cache = forward(x,params)
    gradients = backward(cache,target,params)
    # 独立复制用于存放差分结果，避免覆盖手写反向传播的梯度。
    eps=1e-6; numeric=deepcopy(gradients);errors=[]
    for name,values in params.items():
        for i,value in enumerate(values):
            # 权重是二维列表，偏置是一维列表；两种情况最终都定位到一个数。
            columns = range(len(value)) if isinstance(value,list) else [None]
            for j in columns:
                row = values[i] if j is not None else values
                index = j if j is not None else i
                original = row[index]
                row[index] = original+eps; plus=(forward(x,params)[0]-target)**2
                row[index] = original-eps; minus=(forward(x,params)[0]-target)**2
                row[index] = original  # 每个参数试改完立即恢复，下一项仍在同一初值处检查。
                estimate=(plus-minus)/(2*eps)
                if j is not None:numeric[name][i][j]=estimate;truth=gradients[name][i][j]
                else:numeric[name][i]=estimate;truth=gradients[name][i]
                errors.append(abs(estimate-truth))
    # 所有梯度核对完，再更新参数副本；旧前向与旧参数仍保留供比较。
    updated=deepcopy(params);step(updated,gradients,.01)
    after,cache_after=forward(x,updated)
    return {'kind':'hand_calc','x':x,'target':target,'params':params,'cache':cache,
            'prediction':prediction,'loss':(prediction-target)**2,'gradients':gradients,
            'numeric_gradients':numeric,'max_difference':max(errors),'lr':.01,
            'updated_params':updated,'updated_cache':cache_after,
            'updated_prediction':after,'updated_loss':(after-target)**2}


def lesson06(steps=500):
    """核对第05讲单步，再实际训练XOR指定次数，不读取旧训练结果。"""
    import torch
    from tiny_lm.tensor_mlp import TensorMLP, train_xor
    from tiny_lm.manual_mlp import hand_example
    torch.set_num_threads(1)
    model=TensorMLP(hand_example()); x=torch.tensor([[1.,2.]])
    loss=(model(x)-1).square().mean();loss.backward()  # backward只填梯度，不改参数。
    gradients={n:p.grad.tolist() for n,p in model.named_parameters()}
    # 手工执行一次SGD更新；no_grad避免把参数更新本身记进求导图。
    with torch.no_grad():
        for p in model.parameters():p-=.01*p.grad
    return {'kind':'autograd_check','input_shape':list(x.shape),'loss_before':loss.item(),
            'gradients':gradients,'prediction_after':model(x).item(),
            'xor':train_xor(steps=steps),'xor_source':'tiny_lm.tensor_mlp.train_xor'}


def lesson07():
    """分开观察真实字符编号与4×2玩具表；同一行被查两次会收到两份梯度。"""
    import torch
    from tiny_lm.tokenizer import CharTokenizer
    tok=CharTokenizer.for_course(); text='小丁喜欢苹果。'
    table=torch.tensor([[1.,0.],[0.,1.],[1.,1.],[-1.,2.]],requires_grad=True)
    # ids是行号，不参与求导；参与求导的是被选中的表内数值。
    ids=torch.tensor([2,1,2]); selected=table[ids];selected.sum().backward()
    return {'kind':'hand_calc','text':text,'tokens':list(text),'ids':tok.encode(text),
            'vocab_size':tok.vocab_size,'vocab':tok.itos,'toy_table':table.detach(),
            'toy_ids':ids,'toy_selected':selected,'toy_gradient':table.grad}


def lesson08():
    """比较三项分数的Softmax：统一平移不变，只改一个候选则整行概率改变。"""
    import torch
    scores=torch.tensor([0.,1.,2.],dtype=torch.float64)
    p=torch.softmax(scores,dim=-1)
    shifted=torch.softmax(scores+1000,dim=-1)  # 稳定实现先消去共同偏移，不直接计算exp(1000)。
    variant=torch.softmax(torch.tensor([0.,1.,3.],dtype=torch.float64),dim=-1)
    return {'kind':'hand_calc','logits':scores,'exp':scores.exp(),'probabilities':p,
            'shifted_scores':scores+1000,'shifted_probabilities':shifted,
            'variant_logits':[0,1,3],'variant_probabilities':variant}


def lesson09(steps=1000):
    """训练只读当前字符的基线，记录训练/留出损失，再验证它读不到人名。"""
    import torch
    from tiny_lm.baseline import CharBaseline
    from tiny_lm.tokenizer import CharTokenizer
    from tiny_lm.data import build_records, make_pretrain_batch
    from tiny_lm.losses import token_loss
    torch.set_num_threads(1);torch.manual_seed(42)
    tok=CharTokenizer.for_course();groups=build_records()
    # x、y都为[样本数,32]；y比原文错开一位，填充目标为-100。
    x,y=make_pretrain_batch(groups['pretrain_train'],tok)
    vx,vy=make_pretrain_batch(groups['pretrain_val'],tok)
    model=CharBaseline(tok.vocab_size,16);optimizer=torch.optim.SGD(model.parameters(),lr=.1)
    history=[]
    # 第0次记录初值，第steps次记录最后一次更新后的结果，因此多检查一轮。
    for step in range(steps+1):
        scores=model(x);loss=token_loss(scores,y)
        if step%50==0 or step==steps:
            with torch.no_grad():val=token_loss(model(vx),vy).item()  # 留出题只评分，不用于更新。
            history.append({'step':step,'train_loss':loss.item(),'val_loss':val})
        if step==steps:break
        optimizer.zero_grad();loss.backward();optimizer.step()  # 清旧梯度→求本次梯度→更新。
    small_text='苹果。';sx,sy=make_pretrain_batch([{'text':small_text}],tok,max_len=6)
    prompt1,prompt2='小丁喜欢','小周喜欢'
    # 两个前缀最后都为“欢”。若没有跨位置读取，最后一行概率会完全相同。
    with torch.no_grad():
        p1=model(torch.tensor([tok.encode(prompt1)]))[0,-1].softmax(-1)
        p2=model(torch.tensor([tok.encode(prompt2)]))[0,-1].softmax(-1)
    top=torch.topk(p1,5)
    return {'kind':'teaching_run','seed':42,'steps':steps,'lr':.1,'width':16,
            'optimizer':'SGD','batch_size':len(x),'history':history,
            'shift_example':{'text':small_text,'x':sx,'y':sy,
                             'x_tokens':[tok.itos[i] for i in sx[0]],
                             'y_tokens':[tok.itos[i] if i>=0 else '忽略' for i in sy[0]]},
            'loss_example':{'logits':[0,math.log(2),math.log(3)],'probs':[1/6,2/6,3/6],
                            'target':2,'loss':math.log(2)},
            'same_last_token':{'prompts':[prompt1,prompt2],'max_probability_difference':(p1-p2).abs().max().item(),
                               'top':[{'token':tok.itos[i],'p':p} for i,p in zip(top.indices.tolist(),top.values.tolist())]}}


def attention_example(causal=False):
    """固定3位置×2维的Q/K/V；causal决定是否只允许读取当前及更早位置。"""
    import torch
    from tiny_lm.attention import attention_2d
    q=torch.tensor([[1.,0.],[0.,1.],[1.,1.]],dtype=torch.float64)
    v=torch.tensor([[1.,0.],[0.,2.],[1.,2.]],dtype=torch.float64)
    output,trace=attention_2d(q,q,v,causal=causal)  # 此算例特意令K=Q，便于逐项手算。
    return {'kind':'hand_calc','q':q,'k':q,'v':v,'raw_dot':q@q.T,'output':output,**trace}


def lesson10():
    """只改V，检查读取比例不变但加权汇总的内容发生变化。"""
    import torch
    from tiny_lm.attention import attention_2d
    result=attention_example()
    variant_v=torch.tensor([[1.,0.],[0.,2.],[3.,2.]],dtype=torch.float64)
    output,trace=attention_2d(result['q'],result['k'],variant_v)
    return {**result,'variant_v':variant_v,'variant_output':output,
            'weights_unchanged':torch.equal(result['weights'],trace['weights'])}


def lesson11():
    """只改最后位置；有因果限制时，前两个位置的输出应保持不变。"""
    import torch
    from tiny_lm.attention import attention_2d
    result=attention_example(True)
    # clone保留原始输入；最后位置同时作为查询和键，V也做相同位置的干预。
    changed_q=result['q'].clone();changed_q[-1]=torch.tensor([4.,0.])
    changed_v=result['v'].clone();changed_v[-1]=torch.tensor([4.,0.])
    output,_=attention_2d(changed_q,changed_q,changed_v,causal=True)
    return {**result,'changed_last_qk':changed_q,'changed_last_v':changed_v,
            'changed_output':output,'prefix_max_difference':(output[:2]-result['output'][:2]).abs().max().item(),
            'unmasked_weights':attention_example(False)['weights'],
            'unmasked_changed_output':attention_2d(changed_q,changed_q,changed_v,causal=False)[0],
            'unmasked_output':attention_example(False)['output']}


def lesson12():
    """先用索引检查分头/合头，再用随机投影检查多头的独立读取。"""
    import torch
    from tiny_lm.attention import split_heads,merge_heads,attention_2d
    x=torch.arange(12,dtype=torch.float64).reshape(1,3,4)  # [1个样本,3位置,4特征]，数值只充当格子标签。
    parts=split_heads(x,2);out,trace=attention_2d(parts,parts,parts,causal=True)
    torch.manual_seed(42)
    projections=[torch.nn.Linear(4,4,bias=False) for _ in range(4)]  # 三个输入投影Q/K/V，一个输出投影。
    px=x.float()
    pq,pk,pv=[split_heads(layer(px),2) for layer in projections[:3]]
    pcontext,ptrace=attention_2d(pq,pk,pv,causal=True)
    poutput=projections[3](merge_heads(pcontext))
    # 逐头循环作为参照，核对带头轴的批量计算没有串错坐标。
    independent=torch.stack([attention_2d(pq[:,i],pk[:,i],pv[:,i],causal=True)[0] for i in range(2)],dim=1)
    return {'kind':'hand_calc','x':x,'split':parts,'merged':merge_heads(parts),
            'heads_output':out,'output':merge_heads(out),'weights':trace['weights'],
            'inverse_exact':torch.equal(x,merge_heads(parts)),
            'projected_q':pq,'projected_k':pk,'projected_v':pv,
            'projected_weights':ptrace['weights'],'projected_context':pcontext,
            'projected_output':poutput,'projected_reference':independent,
            'per_head_max_difference':(pcontext-independent).abs().max().item(),
            'W_output':projections[3].weight}


def lesson13():
    """在固定内容上只改位置，核对RoPE保长度与相对位置的点积关系。"""
    import torch
    from tiny_lm.rope import apply_rope
    q=torch.tensor([[[[1.,0.],[1.,0.],[1.,0.]]]],dtype=torch.float64)  # [样本1,头1,位置3,头宽2]。
    k=q.clone()
    positions=torch.arange(3)
    rq,rk=apply_rope(q,k,positions)
    sq,sk=apply_rope(q,k,positions+7)  # 两侧一起平移，位置差没变，点积应相同。
    width=32;frequencies=[10000**(-2*i/width) for i in range(width//2)]
    return {'kind':'hand_calc','q':q,'k':k,'positions':positions,'rotated_q':rq,'rotated_k':rk,
            'norm_before':q.norm(dim=-1),'norm_after':rq.norm(dim=-1),
            'dots':rq@rk.transpose(-2,-1),'shifted_dots':sq@sk.transpose(-2,-1),
            'common_shift_error':((rq@rk.transpose(-2,-1))-(sq@sk.transpose(-2,-1))).abs().max().item(),
            'first_pair_pos1':[math.cos(1),math.sin(1)],'frequencies_d32':frequencies}


def lesson14():
    """用2→4→2的小向量展开SwiGLU：两路投影、SiLU、逐项乘、投影回去。"""
    import torch
    import torch.nn.functional as F
    x=torch.tensor([1.,2.],dtype=torch.float64)
    wu=torch.tensor([[1.,0.],[0.,1.],[1.,1.],[1.,-1.]],dtype=torch.float64)
    wg=torch.tensor([[-1.,0.],[0.,0.],[1.,0.],[0.,1.]],dtype=torch.float64)
    wd=torch.tensor([[1.,0.,1.,0.],[0.,1.,0.,1.]],dtype=torch.float64)
    # up与activated都是4项，*逐坐标相乘；门控数值不是概率，可以为负或超过1。
    up=x@wu.T;gate=x@wg.T;activated=F.silu(gate);product=up*activated;out=product@wd.T
    return {'kind':'hand_calc','x':x,'W_up':wu,'W_gate':wg,'W_down':wd,
            'up':up,'gate_input':gate,'gate':activated,'product':product,'output':out}


def lesson15():
    """分别看RMS归一化与残差直路；本次反向只针对x+2x的和。"""
    import torch
    from tiny_lm.layers import RMSNorm
    x=torch.tensor([3.,4.],dtype=torch.float64,requires_grad=True)
    norm=RMSNorm(2).double();value=norm(x)
    residual=x+2*x;residual.sum().backward()  # 梯度从直路和支路相加，x.grad每项为3。
    return {'kind':'hand_calc','x':x,'eps':1e-5,'rms':(x.square().mean()+1e-5).sqrt(),
            'normalized':value,'rms_after':value.square().mean().sqrt(),
            'mean_after':value.mean(),'residual_branch':2*x,'residual_output':residual,
            'input_gradient':x.grad,'identity_when_branch_zero':x+torch.zeros_like(x)}


def lesson16():
    """加载真正的预训练权重，记录同一句话的全模型前向与位置7的数值切片。"""
    import torch
    from tiny_lm.checkpoint import load_checkpoint
    from dataclasses import asdict
    model,tok,meta=load_checkpoint(FIRST/'pretrain.pt')
    text='早上，小丁喜欢红色的苹果。';ids=torch.tensor([tok.encode(text,add_bos=True)])
    with torch.no_grad():logits,trace=model(ids,return_trace=True)  # 只观察中间量，不计算梯度或更新。
    path=[('ids',list(ids.shape)),('embedding',list(trace['embedding'].shape))]
    for i,block in enumerate(trace['blocks']):path.append((f'block{i+1}',list(block['block_output'].shape)))
    path.extend([('norm',list(trace['normalized'].shape)),('logits',list(logits.shape))])
    p=logits[0,7].softmax(-1);top=torch.topk(p,5)  # 第0个样本、位置7“欢”，沿79个候选归一化。
    return {'kind':'teaching_run','stage':'pretrain','text':text,'config':asdict(model.config),
            'parameter_count':sum(p.numel() for p in model.parameters()),
            'parameter_sha256':parameter_digest(model),'shapes':path,
            'position':7,'token':tok.itos[ids[0,7].item()],
            'coordinates_first4':[{'name':'embedding','values':trace['embedding'][0,7,:4]},
                 *[{'name':f'block{i+1}','values':b['block_output'][0,7,:4]} for i,b in enumerate(trace['blocks'])],
                 {'name':'norm','values':trace['normalized'][0,7,:4]}],
            'top':[{'token':tok.itos[i],'p':p} for i,p in zip(top.indices.tolist(),top.values.tolist())],
            'trace':trace}


def lesson17():
    """--inspect使用：读取原预训练曲线；真实训练入口在tiny_lm.train。"""
    return {'kind':'teaching_run','pretrain':read_record('pretrain_log'),
            'small_batch':read_record('small_batch')}


def lesson18():
    """固定同一权重，比较贪心和两次采样，并检查生成没有改变参数。"""
    import torch
    from tiny_lm.checkpoint import load_checkpoint
    from tiny_lm.generate import generate
    torch.set_num_threads(1)
    model,tok,_=load_checkpoint(FIRST/'pretrain.pt');before=parameter_digest(model)  # 记录生成前的参数摘要。
    greedy=generate(model,tok,'早上，小丁喜欢',greedy=True)
    sampling=[generate(model,tok,'早上，小丁喜欢',temperature=.8,seed=seed) for seed in [42,43]]
    return {'kind':'teaching_run','greedy':greedy,'sampling':sampling,
            'weights_unchanged':before==parameter_digest(model),
            'parameter_sha256':before,'comparison':read_record('generation_comparison')}


def lesson19():
    """--inspect使用：读取微调结果，并展开一条问答的输入和有效目标。"""
    from tiny_lm.tokenizer import CharTokenizer
    from tiny_lm.data import make_sft_batch,build_records
    tok=CharTokenizer.for_course();row=build_records()['sft_train'][0]
    x,y=make_sft_batch([row],tok)  # x保留问题与答案；y只给答案及EOS评分，其他位置为-100。
    return {'kind':'teaching_run','sft':read_record('sft_log'),
            'comparison':read_record('generation_comparison'),
            'mask_example':{'record':row,'prefix_len':1+len(tok.encode(row['prompt'])),
                            'x':x,'y':y,'x_tokens':[tok.itos[i] for i in x[0]],
                            'y_tokens':[tok.itos[i] if i>=0 else '忽略' for i in y[0]],
                            'valid_count':(y!=-100).sum().item()}}


def lesson20():
    """用随机模型检查依赖路径与评分边界；两项实验都不执行参数更新。"""
    import torch
    from tiny_lm.tokenizer import CharTokenizer
    from tiny_lm.model import TinyLM,ModelConfig
    from tiny_lm.data import build_records,make_sft_batch
    from tiny_lm.losses import token_loss
    torch.set_num_threads(1);torch.manual_seed(42)
    tok=CharTokenizer.for_course();model=TinyLM(ModelConfig(vocab_size=tok.vocab_size)).eval()
    ids=torch.tensor([tok.encode('早上，小丁喜欢红色的苹果。',add_bos=True)])
    variant=ids.clone();variant[0,8]=tok.stoi['黄']  # 位置8原为“红”，位置0—7不允许读取它。
    with torch.no_grad():before=model(ids);after=model(variant)
    x,y=make_sft_batch([build_records()['sft_train'][0]],tok)
    # 故意漏掉首个答案标签，观察评分对象变化；输入与参数都不变。
    masked=y.clone();first=(y[0]!=-100).nonzero()[0,0].item();masked[0,first]=-100
    with torch.no_grad():scores=model(x);loss=token_loss(scores,y);wrong_loss=token_loss(scores,masked)
    return {'kind':'mechanism_check','seed':42,'ids':ids,'variant_ids':variant,
            'future_change':{'position':8,'prefix_max_difference':(before[:,:8]-after[:,:8]).abs().max().item(),
                             'suffix_max_difference':(before[:,8:]-after[:,8:]).abs().max().item()},
            'mask_boundary':{'first_answer_index':first,'valid_before':(y!=-100).sum().item(),
                             'valid_after':(masked!=-100).sum().item(),
                             'loss_before':loss.item(),'loss_after':wrong_loss.item()},
            'parameter_count':sum(p.numel() for p in model.parameters())}


def build(number,steps=None):
    """按讲次调用实验；第06/09讲可指定更新次数，否则使用各自默认值。"""
    function=globals()[f'lesson{number:02d}']
    return function(steps=steps) if number in (6,9) and steps is not None else function()


def main(number):
    """读取入口参数，把同一次计算结果打印出来并导出为JSON。"""
    parser=argparse.ArgumentParser(description=f'第 {number:02d} 讲：打印并保存可核对的实验数值')
    parser.add_argument('--out',type=Path,default=ROOT/f'artifacts/lessons/l{number:02d}.json')
    if number in (6,9):parser.add_argument('--steps',type=int,default=500 if number==6 else 1000)
    add_observation_arguments(parser)
    args=parser.parse_args()
    if getattr(args,'steps',0)<0:parser.error('更新次数不能为负数')
    with observe_lesson(number, verbose=args.verbose, step=args.step):
        result=build(number,getattr(args,'steps',None))
    export_trace(args.out,result)
    # 完整大张量只写入文件，终端保留便于核对的关键结果。
    summary={k:v for k,v in result.items() if k not in {'trace','curve','vocab','comparison','xor','pretrain','sft'}}
    if number==6:
        # 终端显示本次训练的关键节点，完整逐10步记录仍保存在JSON中。
        xor=result['xor']
        summary['xor']={'steps':xor['steps'],'final_loss':xor['final_loss'],
                        'predictions':xor['predictions'],
                        'history':[row for row in xor['history'] if row['step'] in {0,100,xor['steps']}]}
    from tiny_lm.trace import json_value
    print(json.dumps(json_value(summary),ensure_ascii=False,indent=2,allow_nan=False))
    print(f'完整数值记录：{args.out}')
