"""Generate lesson 16's offline 3D inspector from the existing verified saved trace."""
import json
from pathlib import Path
import subprocess
import tempfile

from model_xray import load_data


def build():
    directory = Path(__file__).resolve().with_name('tensor3d')
    # Keep the sole editable data source in artifacts; this is a disposable build handoff.
    with tempfile.TemporaryDirectory(prefix='hello-llm-model3d-') as temporary:
        payload = Path(temporary) / 'saved-forward.json'
        payload.write_text(json.dumps(load_data(), ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        subprocess.run(['node', str(directory / 'xray-build.mjs'), str(payload)], cwd=directory, check=True)


if __name__ == '__main__':
    build()
