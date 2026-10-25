"""可选扩展实验：固定公开权重的真实前向与 KV cache 记录。无需远程代码。"""
import argparse
import hashlib
import platform
from pathlib import Path
import tempfile
import time

import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.models.qwen3.modeling_qwen3 import apply_rotary_pos_emb
from tiny_lm.trace import export_trace

MODEL = 'Qwen/Qwen3-0.6B'
REVISION = 'c1899de289a04d12100db370d81485cdf75e47ca'


def tensor_record(value):
    value = value.detach().cpu()
    return {'shape':list(value.shape), 'first_values':value.flatten()[:16].tolist(),
            'rms':value.float().square().mean().sqrt().item()}


def digest(model):
    h=hashlib.sha256()
    for name,p in model.named_parameters():
        h.update(name.encode());h.update(p.detach().contiguous().cpu().numpy().tobytes())
    return h.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--use-downloaded',action='store_true',help='使用download_reference.py已校验的临时目录')
    parser.add_argument('--local-model',type=Path,help='已校验的本地 safetensors 目录')
    parser.add_argument('--out',type=Path,default=Path('artifacts/reference/qwen3_trace.json'))
    parser.add_argument('--cache-dir',type=Path,default=Path(tempfile.gettempdir())/'llm-column-reference-cache')
    args=parser.parse_args()
    if args.use_downloaded:args.local_model=Path(tempfile.gettempdir())/'llm-column-reference-model'
    torch.set_num_threads(2);torch.manual_seed(42)
    started=time.perf_counter()
    print('加载官方固定权重（首次下载约 1.5 GB）…',flush=True)
    source=str(args.local_model) if args.local_model else MODEL
    kwargs={'local_files_only':True} if args.local_model else {'revision':REVISION,'cache_dir':args.cache_dir}
    tokenizer=AutoTokenizer.from_pretrained(source,**kwargs)
    model=AutoModelForCausalLM.from_pretrained(source,**kwargs,
                                              dtype=torch.float32,attn_implementation='eager').eval()
    model.requires_grad_(False)
    messages=[{'role':'user','content':'天空是什么颜色？'}]
    rendered=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)
    ids=tokenizer(rendered,return_tensors='pt').input_ids
    if ids.shape[1]>32:raise ValueError('观察输入超过约定的32 token')
    print(f'加载完成，输入 {ids.shape[1]} tokens，记录前向…',flush=True)
    captured={};phase='prefill';hooks=[]
    first=model.model.layers[0]
    def capture(name):
        def hook(module,inputs,output):
            value=output[0] if isinstance(output,tuple) else output
            captured.setdefault(phase,{})[name]=value.detach().cpu()
        return hook
    def pre_attention(module,inputs,kwargs):
        cos,sin=kwargs['position_embeddings']
        captured.setdefault(phase,{})['cos']=cos.detach().cpu()
        captured[phase]['sin']=sin.detach().cpu()
    hooks.append(first.self_attn.register_forward_pre_hook(pre_attention,with_kwargs=True))
    for name,module in [('input_norm',first.input_layernorm),('q_projection',first.self_attn.q_proj),
                        ('q_norm',first.self_attn.q_norm),('k_projection',first.self_attn.k_proj),
                        ('k_norm',first.self_attn.k_norm),('v_projection',first.self_attn.v_proj),
                        ('attention_output',first.self_attn),('ffn_gate',first.mlp.gate_proj),
                        ('ffn_up',first.mlp.up_proj),('ffn_output',first.mlp)]:
        hooks.append(module.register_forward_hook(capture(name)))
    before=digest(model);runs=[];generated=[];cache=None;current=ids
    with torch.no_grad():
        for step in range(4):
            phase='prefill' if step==0 else f'decode{step}'
            outputs=model(input_ids=current,past_key_values=cache,use_cache=True,
                          output_attentions=True,output_hidden_states=True,return_dict=True)
            cache=outputs.past_key_values
            logits=outputs.logits[0,-1].float();probability=logits.softmax(-1);top=probability.topk(5)
            next_id=logits.argmax().item();generated.append(next_id)
            detail=captured[phase]
            q=detail['q_norm'].transpose(1,2);k=detail['k_norm'].transpose(1,2)
            rq,rk=apply_rotary_pos_emb(q,k,detail['cos'],detail['sin'])
            runs.append({'phase':phase,'input_ids':current.tolist(),'input_shape':list(current.shape),
                         'logits_shape':list(outputs.logits.shape),
                         'hidden_states':[tensor_record(x) for x in outputs.hidden_states],
                         'first_layer':{name:tensor_record(value) for name,value in detail.items()},
                         'q_after_rope':tensor_record(rq),'k_after_rope':tensor_record(rk),
                         'attention_shape':list(outputs.attentions[0].shape),
                         'attention_head0':outputs.attentions[0][0,0],
                         'cache_key_shape':list(cache.layers[0].keys.shape),
                         'cache_value_shape':list(cache.layers[0].values.shape),
                         'selected_id':next_id,'selected_token':tokenizer.decode([next_id]),
                         'top':[{'id':i,'token':tokenizer.decode([i]),'p':p} for i,p in zip(top.indices.tolist(),top.values.tolist())]})
            current=torch.tensor([[next_id]])
        phase='uncached_check'
        full=torch.cat([ids,torch.tensor([generated[:-1]])],dim=1)
        uncached=model(input_ids=full,use_cache=False,return_dict=True).logits[0,-1]
        max_error=(uncached-outputs.logits[0,-1]).abs().max().item()
    for hook in hooks:hook.remove()
    after=digest(model)
    result={'kind':'public_reference_run','model':MODEL,'revision':('09b42cad3d112e832108974449ccb5e8e0f5b5d1' if args.use_downloaded else REVISION),
            'source':(f'https://modelscope.cn/models/{MODEL}' if args.use_downloaded else f'https://huggingface.co/{MODEL}/tree/{REVISION}'),
            'weight_reference_revision':REVISION,
            'download_manifest':'download_manifest.json' if args.local_model else None,
            'local_source_used':bool(args.local_model),
            'environment':{'python':platform.python_version(),'torch':torch.__version__,
                           'transformers':transformers.__version__,'device':'cpu','dtype':'float32',
                           'threads':torch.get_num_threads(),'attention_implementation':'eager'},
            'config':{**model.config.to_dict(),'_name_or_path':MODEL},'parameter_count':sum(p.numel() for p in model.parameters()),
            'prompt':messages[0]['content'],'rendered_prompt':rendered,
            'input_ids':ids.tolist(),'tokens':tokenizer.convert_ids_to_tokens(ids[0].tolist()),
            'runs':runs,'generated_ids':generated,'generated_text':tokenizer.decode(generated),
            'parameter_sha256_before':before,'parameter_sha256_after':after,'weights_unchanged':before==after,
            'cached_vs_uncached_max_logit_difference':max_error,
            'seconds_from_loading_to_export':time.perf_counter()-started}
    export_trace(args.out,result)
    print(f'完成：{args.out}，输出 {result["generated_text"]!r}，cache差值 {max_error:.3g}',flush=True)


if __name__=='__main__':main()
