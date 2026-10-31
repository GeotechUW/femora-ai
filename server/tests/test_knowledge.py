import hashlib
import json
import unittest

from server.knowledge import Knowledge


def fixture():
    content = '# API\n\n### `model.material.nd.elastic_isotropic`\n```\nmodel.material.nd.elastic_isotropic(E=None, nu=None, rho=None)\n```\nElastic material.\n'
    return json.dumps({'schema_version': 1, 'source_commit': 'a' * 40,
                       'documents': [{'path': 'references/api/model-material.md', 'content': content,
                                      'sha256': hashlib.sha256(content.encode()).hexdigest()}]}).encode()


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.knowledge = Knowledge(fixture())

    def test_exact_lookup_and_absent_api(self):
        self.assertTrue(self.knowledge.lookup('model.material.nd.elastic_isotropic')['found'])
        self.assertFalse(self.knowledge.lookup('model.material.nd.magic_soil')['found'])
        self.assertFalse(self.knowledge.lookup('elastic_isotropic')['found'])

    def test_search_filters_and_pagination(self):
        result = self.knowledge.search('elastic_isotropic', 'api')
        path = result['results'][0]['reference']
        first = self.knowledge.read(path, max_chars=20)
        second = self.knowledge.read(path, offset=first['next_offset'], max_chars=20)
        self.assertEqual(first['content'] + second['content'], self.knowledge.documents[path]['content'][:40])
        self.assertEqual(self.knowledge.search('elastic', 'examples')['results'], [])

    def test_rejects_paths_urls_and_unbounded_arguments(self):
        for ref in ['../../etc/passwd', 'https://example.com/', '/etc/passwd']:
            with self.assertRaises(ValueError):
                self.knowledge.read(ref)
        for query, category, limit in [('', 'all', 5), ('x'*257, 'all', 5), ('x','invalid',5), ('x','all',100)]:
            with self.assertRaises(ValueError):
                self.knowledge.search(query, category, limit)
        with self.assertRaises(ValueError):
            self.knowledge.read('references/api/model-material.md', max_chars=100000)

    def test_rejects_corrupted_or_duplicate_documents(self):
        data = json.loads(fixture())
        data['documents'][0]['content'] += 'tamper'
        with self.assertRaises(ValueError):
            Knowledge(json.dumps(data).encode())
        data = json.loads(fixture())
        data['documents'].append(data['documents'][0])
        with self.assertRaises(ValueError):
            Knowledge(json.dumps(data).encode())


if __name__ == '__main__':
    unittest.main()
