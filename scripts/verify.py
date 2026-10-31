"""Check the recorded files and archive contents of a generated build."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def verify(output: Path) -> None:
    manifest = json.loads((output / 'build-manifest.json').read_text())
    for name, expected in manifest['files'].items():
        path = (output / name).resolve()
        if not path.is_relative_to(output.resolve()) or not path.is_file():
            raise ValueError(f'Missing or escaping build file: {name}')
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Checksum mismatch: {name}')
    archives = sorted((output / 'dist').glob('*.zip'))
    if len(archives) != 3:
        raise ValueError('Expected three platform archives')
    for archive in archives:
        with zipfile.ZipFile(archive) as z:
            if z.testzip() is not None:
                raise ValueError(f'Invalid ZIP: {archive}')
            for name in z.namelist():
                if name.startswith('/') or '..' in Path(name).parts:
                    raise ValueError(f'Unsafe archive path: {name}')
            skills = [name for name in z.namelist() if name.endswith('/SKILL.md')]
            if len(skills) != 1:
                raise ValueError(f'Expected one skill in {archive}')
    print('Verified build checksums and all three archives.')


if __name__ == '__main__':
    verify(ROOT / 'build')
