"""Verify live listing pages, then write their URLs into a separate submission copy.

Usage: python scripts/verify_listing.py --base-url https://host/path/
Run build.py first. This does not publish or alter installed plugins.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from build import zip_directory

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True)
    args = parser.parse_args()
    base = args.base_url.rstrip('/') + '/'
    parsed = urlparse(base)
    if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Use the actual public HTTPS site root without credentials or query parameters')
    fields = {'websiteURL': ('', 'Femora for ChatGPT'), 'supportURL': ('support/', 'Femora Plugin Support'),
              'privacyPolicyURL': ('privacy/', 'Femora Plugin Privacy Policy'),
              'termsOfServiceURL': ('terms/', 'Femora Plugin Terms')}
    verified = {}
    for field, (suffix, heading) in fields.items():
        url = base + suffix
        with urlopen(Request(url, headers={'User-Agent': 'Femora-listing-check'}), timeout=30) as response:
            text = response.read().decode('utf-8')
            final = response.geturl()
            if urlparse(final).scheme != 'https':
                raise ValueError(f'Non-HTTPS redirect for {url}')
        if heading not in text or 'Amin Pakzad' not in text:
            raise ValueError(f'Wrong page or sign-in wall: {url}')
        if field == 'supportURL' and 'https://github.com/GeotechUW/femora-ai/issues' not in text:
            raise ValueError('Support page does not contain the expected contact route')
        verified[field] = final
    output = ROOT / 'build/submission'
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(ROOT / 'build/packages/chatgpt', output)
    path = output / 'plugin.json'
    manifest = json.loads(path.read_text())
    interface = manifest['extensions']['com.openai']['interface']
    interface.update(verified)
    for field in ('logo', 'composerIcon'):
        if not (output / interface[field]).is_file():
            raise ValueError('Missing icon')
    path.write_text(json.dumps(manifest, indent=2) + '\n')
    archive = ROOT / 'build' / f'femora-chatgpt-submission-{manifest["version"]}.zip'
    zip_directory(output, archive)
    (ROOT / 'build/listing-verification.json').write_text(json.dumps({'urls': verified, 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}, indent=2)+'\n')
    print(f'Prepared {archive}. Publisher verification, platform checks, and attestations remain separate.')


if __name__ == '__main__':
    main()
