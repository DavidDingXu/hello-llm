"""从 Qwen 官方 ModelScope 仓库取同一权重；逐文件核对 SHA256。"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import tempfile
import urllib.request

REVISION='09b42cad3d112e832108974449ccb5e8e0f5b5d1'
WEIGHT_SHA='f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b'
DESTINATION=Path(tempfile.gettempdir())/'llm-column-reference-model'
NAMES={'config.json','generation_config.json','tokenizer.json','tokenizer_config.json',
       'vocab.json','merges.txt','model.safetensors'}


def main():
    url=f'https://modelscope.cn/api/v1/models/Qwen/Qwen3-0.6B/repo/files?Revision={REVISION}&Recursive=true'
    with urllib.request.urlopen(url,timeout=30) as response:data=json.load(response)
    files=[x for x in data['Data']['Files'] if x['Name'] in NAMES]
    assert len(files)==len(NAMES)
    assert next(x for x in files if x['Name']=='model.safetensors')['Sha256']==WEIGHT_SHA
    DESTINATION.mkdir(parents=True,exist_ok=True)
    def download(item):
        target=DESTINATION/item['Name'];expected=item['Sha256']
        if target.exists():
            with target.open('rb') as stream:existing=hashlib.file_digest(stream,'sha256').hexdigest()
            if existing==expected:return {'name':item['Name'],'sha256':existing,'bytes':target.stat().st_size}
        source=f'https://modelscope.cn/models/Qwen/Qwen3-0.6B/resolve/{REVISION}/{item["Name"]}'
        temporary=target.with_suffix(target.suffix+'.partial');h=hashlib.sha256();count=0;reported=0
        print('下载：'+item['Name'],flush=True)
        with urllib.request.urlopen(source,timeout=60) as response, temporary.open('wb') as stream:
            while chunk:=response.read(2*1024*1024):
                stream.write(chunk);h.update(chunk);count+=len(chunk)
                if count-reported>=128*1024*1024:
                    print(f'{item["Name"]}: {count/1024**2:.0f} MiB',flush=True);reported=count
        if h.hexdigest()!=expected or count!=item['Size']:raise ValueError('文件校验失败：'+item['Name'])
        temporary.replace(target)
        return {'name':item['Name'],'sha256':h.hexdigest(),'bytes':count,'source':source}
    with ThreadPoolExecutor(max_workers=3) as pool:manifest=list(pool.map(download,files))
    out=Path('artifacts/reference/download_manifest.json');out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({'model':'Qwen/Qwen3-0.6B','repository':'ModelScope/Qwen/Qwen3-0.6B',
      'revision':REVISION,'weight_matches_huggingface_revision':'c1899de289a04d12100db370d81485cdf75e47ca',
      'weight_sha256':WEIGHT_SHA,'files':manifest},ensure_ascii=False,indent=2),encoding='utf-8')
    print('已校验：'+str(DESTINATION),flush=True)

if __name__=='__main__':main()
