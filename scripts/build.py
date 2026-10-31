"""Reuse Femora's upstream extractor and package its output. Python 3.11+."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = {
    '01_api_model.md': ('api', r'^## (model-[\w-]+)\s*$'),
    '02_api_other.md': ('api', r'^## (femora-[\w-]+)\s*$'),
    '03_concepts.md': ('concepts', r'^<!-- concept: ([\w-]+).*?-->\s*$'),
    '04_examples.md': ('examples', r'^<!-- example: ([\w-]+).*?-->\s*$'),
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def git(source: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(source), *args], text=True).strip()


def split_references(bundle: Path, skill: Path) -> list[dict]:
    """Preserve every section byte-for-byte; fail on missing or duplicate topics."""
    records = []
    seen = set()
    for filename, (category, pattern) in SECTIONS.items():
        # Examples may be absent only when the upstream manifest omits them.
        if filename == '04_examples.md' and not (bundle / filename).exists():
            continue
        raw = (bundle / filename).read_text(encoding='utf-8')
        matches = list(re.finditer(pattern, raw, re.M))
        if not matches:
            raise ValueError(f'No topic boundaries found in {filename}')
        preamble = raw[:matches[0].start()]
        provenance = '\n'.join(line for line in preamble.splitlines() if line.startswith('>'))
        chunks = []
        for i, match in enumerate(matches):
            slug = match.group(1)
            relative = f'references/{category}/{slug}.md'
            if relative in seen:
                raise ValueError(f'Duplicate topic: {relative}')
            seen.add(relative)
            body = raw[match.start():matches[i + 1].start() if i + 1 < len(matches) else len(raw)]
            chunks.append(body)
            header = f'# Femora reference: {slug}\n\n{provenance}\n\n'
            target = skill / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(header + body, encoding='utf-8')
            if target.read_text(encoding='utf-8')[len(header):] != body:
                raise ValueError(f'Topic changed while splitting: {slug}')
            heading = re.search(r'^#{1,2} (.+)$', body, re.M)
            records.append({'path': relative, 'category': category,
                            'title': heading.group(1) if heading else slug,
                            'source': filename, 'section_sha256': digest(body.encode())})
        if ''.join(chunks) != raw[matches[0].start():]:
            raise ValueError(f'Content loss splitting {filename}')
    return records


def make_skill(bundle: Path, skill: Path, provenance: dict) -> None:
    upstream = (bundle / 'SKILL.md').read_text(encoding='utf-8')
    front = re.match(r'\A---\n(.*?)\n---\n', upstream, re.S)
    rules = re.search(r'^## Rules\s*\n(.*?)(?=^## Build order\s*$)', upstream, re.M | re.S)
    if not front or not rules:
        raise ValueError('Upstream skill format changed; review extraction before continuing')
    records = split_references(bundle, skill)
    text = (ROOT / 'templates/routing.md').read_text(encoding='utf-8')
    text = text.replace('{{RULES}}', rules.group(1).strip())
    (skill / 'SKILL.md').write_text(front.group(0) + '\n' + text, encoding='utf-8')
    index = '# Femora reference index\n\nRead only relevant topics. Verify calls against API signatures; use concepts for ordering and examples for workflows.\n\n'
    for category in ('api', 'concepts', 'examples'):
        index += f'## {category.title()}\n\n'
        for record in records:
            if record['category'] == category:
                target = record['path'].removeprefix('references/')
                index += f'- [{record["title"]}]({target})\n'
        index += '\n'
    (skill / 'references/index.md').write_text(index, encoding='utf-8')
    write_json(skill / 'references/provenance.json', {**provenance, 'topics': records})
    validate_skill(skill)


def validate_skill(skill: Path) -> None:
    text = (skill / 'SKILL.md').read_text(encoding='utf-8')
    if not re.match(r'\A---\nname: femora\ndescription: .+\n---\n', text):
        raise ValueError('Invalid skill frontmatter')
    if len(text.encode()) > 20000 or '{{RULES}}' in text:
        raise ValueError('Skill entry point too large or contains template placeholders')
    # Validate navigation only; upstream prose may deliberately link to remote docs.
    for path in (skill / 'SKILL.md', skill / 'references/index.md'):
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            resolved = (path.parent / target).resolve()
            if not resolved.is_relative_to(skill.resolve()) or not resolved.is_file():
                raise ValueError(f'Broken/escaping navigation: {target}')
    for path in skill.rglob('*'):
        if path.is_symlink() or (path.is_file() and path.stat().st_size > 1024 * 1024):
            raise ValueError(f'Invalid skill resource: {path}')
    # Guard against a section-format change silently dropping core functionality.
    for name in ('model-core', 'model-material', 'model-meshpart', 'model-assembler', 'femora-jobs', 'femora-results'):
        if not (skill / f'references/api/{name}.md').is_file():
            raise ValueError(f'Missing required API group: {name}')


def zip_directory(directory: Path, archive: Path, prefix: str = '') -> None:
    """Stable ordering, timestamps, and modes make identical inputs reproducible."""
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
        for path in sorted(directory.rglob('*')):
            if path.is_file():
                info = zipfile.ZipInfo(prefix + path.relative_to(directory).as_posix(), (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                output.writestr(info, path.read_bytes())
    with zipfile.ZipFile(archive) as output:
        if output.testzip() is not None:
            raise ValueError(f'Corrupt ZIP: {archive}')


def package(bundle: Path, output: Path, provenance: dict, version: str) -> None:
    shared = output / 'shared/femora'
    shared.mkdir(parents=True)
    make_skill(bundle, shared, provenance)
    archives = output / 'dist'
    archives.mkdir()
    for platform in ('chatgpt', 'claude-code'):
        target = output / 'packages' / platform
        shutil.copytree(shared, target / 'skills/femora')
        manifest = json.loads((ROOT / f'platforms/{platform}/plugin.json').read_text())
        manifest['version'] = version
        manifest_path = target / ('plugin.json' if platform == 'chatgpt' else '.claude-plugin/plugin.json')
        if platform == 'chatgpt':
            interface = manifest['extensions']['com.openai']['interface']
            if len(interface['shortDescription']) > 30:
                raise ValueError('ChatGPT subtitle exceeds 30 characters')
            for prompt in interface['defaultPrompt']:
                if not prompt.strip() or len(prompt) > 128:
                    raise ValueError('Invalid starter prompt')
        write_json(manifest_path, manifest)
        zip_directory(target, archives / f'femora-{platform}-{version}.zip')
    zip_directory(shared, archives / f'femora-skill-{version}.zip', 'femora/')
    files = {p.relative_to(output).as_posix(): digest(p.read_bytes()) for p in sorted(output.rglob('*')) if p.is_file()}
    write_json(output / 'build-manifest.json', {**provenance, 'package_version': version, 'files': files})


def verify_bundle(bundle: Path) -> None:
    manifest = json.loads((bundle / 'bundle_manifest.json').read_text(encoding='utf-8'))
    for name, record in manifest['files'].items():
        if Path(name).name != name:
            raise ValueError('Unsafe upstream manifest path')
        data = (bundle / name).read_bytes()
        if digest(data)[:16] != record['sha256'] or len(data) != record['bytes']:
            raise ValueError(f'Upstream hash mismatch: {name}')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path, help='Clean Femora checkout with dependencies installed')
    args = parser.parse_args()
    config = json.loads((ROOT / 'source.json').read_text())
    source = args.source.resolve()
    generator = source / config['generator']
    if digest(generator.read_bytes()) != config['generator_sha256']:
        raise ValueError('Upstream generator changed. Review it, then update source.json generator_sha256.')
    if git(source, 'status', '--porcelain', '--untracked-files=normal', '--', 'src', 'agent/build_knowledge.py', 'website/docs', 'website/mkdocs.yml', 'examples'):
        raise ValueError('Femora input files must be clean and committed')
    output = ROOT / 'build'
    # Only this fixed, generated directory may be removed.
    if output.is_symlink():
        raise ValueError('Refusing symlinked build directory')
    if output.exists():
        shutil.rmtree(output)
    output.mkdir()
    bundle = output / 'upstream-bundle'
    subprocess.run([sys.executable, '-I', str(generator), '--force', '--out', str(bundle)], cwd=source, check=True)
    verify_bundle(bundle)
    provenance = {'source_repository': config['repository'], 'source_commit': git(source, 'rev-parse', 'HEAD'),
                  'generator_sha256': config['generator_sha256'],
                  'upstream_manifest_sha256': digest((bundle / 'bundle_manifest.json').read_bytes()),
                  'python_version': sys.version.split()[0]}
    package(bundle, output, provenance, config['package_version'])
    print(f'Built packages in {output / "dist"}')


if __name__ == '__main__':
    main()
