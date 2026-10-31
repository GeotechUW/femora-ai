"""Bounded, hash-checked reference retrieval; no user code execution."""
import hashlib
import json
import re

MAX_BYTES = 8 * 1024 * 1024


class Knowledge:
    def __init__(self, raw: bytes):
        if len(raw) > MAX_BYTES:
            raise ValueError('Knowledge snapshot exceeds size limit')
        data = json.loads(raw)
        if data.get('schema_version') != 1 or not re.fullmatch(r'[0-9a-f]{40}', data.get('source_commit', '')):
            raise ValueError('Invalid knowledge schema or source commit')
        self.commit = data['source_commit']
        self.documents = {}
        self.api = {}
        for doc in data['documents']:
            path, content = doc['path'], doc['content']
            if not re.fullmatch(r'references/(api|concepts|examples)/[\w-]+\.md', path) or path in self.documents:
                raise ValueError('Invalid or duplicate document path')
            if len(content) > 1024 * 1024 or hashlib.sha256(content.encode()).hexdigest() != doc['sha256']:
                raise ValueError('Reference hash mismatch')
            self.documents[path] = doc
            if path.startswith('references/api/'):
                matches = list(re.finditer(r'^### `([^`]+)`\s*$', content, re.M))
                for i, match in enumerate(matches):
                    symbol = match.group(1)
                    if symbol in self.api:
                        raise ValueError('Duplicate API symbol')
                    self.api[symbol] = {'reference': path, 'content': content[match.start():matches[i+1].start() if i+1 < len(matches) else len(content)].strip()}
        if not self.documents or not self.api:
            raise ValueError('Empty reference or API index')

    def search(self, query: str, category: str = 'all', limit: int = 5) -> dict:
        if not query.strip() or len(query) > 256 or category not in {'all', 'api', 'concepts', 'examples'} or not 1 <= limit <= 10:
            raise ValueError('Use a query of 1–256 characters, a supported category, and limit 1–10')
        terms = set(re.findall(r'[a-z0-9_]+', query.lower()))
        if not terms:
            raise ValueError('Query needs at least one word')
        ranked = []
        for path, doc in self.documents.items():
            if category != 'all' and path.split('/')[1] != category:
                continue
            text = doc['content'].lower()
            hits = [term for term in terms if term in text]
            if not hits:
                continue
            score = len(hits) + sum(4 for term in hits if term in path) + (10 if query.lower() in text else 0)
            start = max(0, min(text.find(term) for term in hits) - 100)
            ranked.append((score, path, doc['content'][start:start + 700]))
        ranked.sort(key=lambda row: (-row[0], row[1]))
        return {'source_commit': self.commit, 'results': [{'reference': p, 'excerpt': e} for _, p, e in ranked[:limit]]}

    def lookup(self, symbol: str) -> dict:
        if not symbol or len(symbol) > 256:
            raise ValueError('API symbol must contain 1–256 characters')
        match = self.api.get(symbol)
        if match is None:
            return {'source_commit': self.commit, 'found': False, 'symbol': symbol, 'message': 'No exact documented API match. Do not invent this callable.'}
        content = match['content']
        return {'source_commit': self.commit, 'found': True, 'symbol': symbol, 'reference': match['reference'],
                'content': content[:16000], 'truncated': len(content) > 16000}

    def read(self, reference: str, offset: int = 0, max_chars: int = 12000) -> dict:
        # Exact index lookup never interprets a user argument as a filesystem path or URL.
        if reference not in self.documents:
            raise ValueError('Unknown reference; use search_femora first')
        if offset < 0 or not 1 <= max_chars <= 16000:
            raise ValueError('Use a nonnegative offset and max_chars between 1 and 16000')
        text = self.documents[reference]['content']
        end = min(len(text), offset + max_chars)
        return {'source_commit': self.commit, 'reference': reference, 'content': text[offset:end],
                'next_offset': end if end < len(text) else None, 'total_chars': len(text)}
