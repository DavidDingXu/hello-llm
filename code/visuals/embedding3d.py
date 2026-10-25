"""Build lesson 07's offline Embedding inspector from its existing hand calculation."""
from pathlib import Path
import subprocess


def build():
    directory = Path(__file__).resolve().with_name('tensor3d')
    subprocess.run(['node', str(directory / 'embedding-build.mjs')], cwd=directory, check=True)


if __name__ == '__main__':
    build()
