import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('packager', Path(__file__).resolve().parents[1] / 'scripts/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class PackagerTests(unittest.TestCase):
    def fixture(self, folder):
        files = {
            '01_api_model.md': '# API\n\n## model-core\n\n### `model.test`\n```\nmodel.test(x: int = 1)\n```\n\n## model-material\nmaterial\n\n## model-meshpart\nmesh\n\n## model-assembler\nassembly\n',
            '02_api_other.md': '# Other API\n\n## femora-jobs\njobs\n\n## femora-results\nresults\n',
            '03_concepts.md': '# Concepts\n\n<!-- concept: index (index.md) -->\n# Overview\n\n```python\n# This is a code comment, not a new guide\n```\n\n<!-- concept: building-blocks (building-blocks.md) -->\n# Building Blocks\n',
            '04_examples.md': '# Examples\n\n<!-- example: soil -->\n## Soil\n\nExample text\n',
            'SKILL.md': '---\nname: femora\ndescription: Writes Femora code.\n---\n\n## Rules\n\n1. Never invent APIs.\n\n## Build order\n\nMaterial before mesh.\n',
        }
        folder.mkdir()
        for name, text in files.items():
            (folder / name).write_text(text)
        return files

    def test_preserves_signatures_and_code_comments(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            self.fixture(base / 'bundle')
            build.make_skill(base / 'bundle', base / 'skill', {'source_commit': 'a' * 40})
            self.assertIn('model.test(x: int = 1)', (base / 'skill/references/api/model-core.md').read_text())
            self.assertIn('# This is a code comment', (base / 'skill/references/concepts/index.md').read_text())
            provenance = json.loads((base / 'skill/references/provenance.json').read_text())
            self.assertEqual(len(provenance['topics']), 9)

    def test_rejects_duplicate_and_missing_topics(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            self.fixture(base / 'bundle')
            p = base / 'bundle/01_api_model.md'
            p.write_text(p.read_text() + '\n## model-core\nduplicate\n')
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                build.split_references(base / 'bundle', base / 'skill')
            p.write_text('# No recognized topic boundaries\n')
            with self.assertRaisesRegex(ValueError, 'No topic boundaries'):
                build.split_references(base / 'bundle', base / 'skill2')

    def test_packages_are_reproducible_and_platform_specific(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            self.fixture(base / 'bundle')
            provenance = {'source_commit': 'a' * 40}
            build.package(base / 'bundle', base / 'first', provenance, '1.2.0')
            build.package(base / 'bundle', base / 'second', provenance, '1.2.0')
            for archive in (base / 'first/dist').glob('*.zip'):
                self.assertEqual(archive.read_bytes(), (base / 'second/dist' / archive.name).read_bytes())
            self.assertTrue((base / 'first/packages/chatgpt/plugin.json').is_file())
            self.assertTrue((base / 'first/packages/claude-code/.claude-plugin/plugin.json').is_file())

    def test_detects_modified_upstream_bundle(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            files = self.fixture(base / 'bundle')
            manifest = {'files': {name: {'sha256': build.digest(text.encode())[:16], 'bytes': len(text.encode())} for name, text in files.items()}}
            build.write_json(base / 'bundle/bundle_manifest.json', manifest)
            build.verify_bundle(base / 'bundle')
            (base / 'bundle/01_api_model.md').write_text('altered')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                build.verify_bundle(base / 'bundle')


if __name__ == '__main__':
    unittest.main()
