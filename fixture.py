#!/usr/bin/env python3
"""A fictional site fixture for the connected proof, not a deployed publisher."""
from __future__ import annotations

import argparse
import hashlib
from html import escape
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
COLOR = re.compile(r'#[0-9a-fA-F]{6}')
SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')


def read_state(root: Path) -> dict:
    return json.loads((root / 'state.json').read_text())


def apply_request(state: dict, request: dict) -> tuple[dict, bool]:
    """Apply a bounded, repeatable content request. Does not authenticate a user."""
    value = json.loads(json.dumps(state))
    request_id = request['request_id']
    if not SLUG.fullmatch(request_id) or len(request_id) > 80:
        raise ValueError('Request ID must be a short lowercase slug.')
    fingerprint = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
    if request_id in value['requests']:
        if value['requests'][request_id] != fingerprint:
            raise ValueError('An earlier request ID cannot approve different content.')
        return value, False
    kind = request['kind']
    if kind == 'color':
        if not COLOR.fullmatch(request['value']):
            raise ValueError('Background must be a six-digit hex color.')
        value['background'] = request['value'].lower()
    elif kind in ('blog', 'category'):
        slug = request['slug']
        if not SLUG.fullmatch(slug) or len(slug) > 80:
            raise ValueError('Page slug must be a short lowercase slug.')
        title = request['value'].strip()
        if not title or len(title) > 150:
            raise ValueError('A title of 1 to 150 characters is required.')
        collection = 'posts' if kind == 'blog' else 'categories'
        if any(item['slug'] == slug for item in value[collection]):
            raise ValueError('That page already exists. An explicit edit is required.')
        item = {'slug': slug, 'title': title}
        if kind == 'blog':
            item['text'] = request.get('text', '')[:6000]
        value[collection].append(item)
    else:
        raise ValueError('Only color, blog and category requests are supported.')
    value['requests'][request_id] = fingerprint
    return value, True


def render(state: dict, out: Path, base_path: str = '') -> dict:
    if not re.fullmatch(r'(?:/[a-zA-Z0-9_-]+)*', base_path):
        raise ValueError('Base path must contain only simple path segments.')
    if not COLOR.fullmatch(state['background']):
        raise ValueError('Invalid stored background.')
    canonical = json.dumps(state, sort_keys=True, separators=(',', ':')).encode()
    identity = hashlib.sha256(canonical).hexdigest()
    links = f'<a href="{base_path}/">Home</a>'
    for item in state['categories']:
        if not SLUG.fullmatch(item['slug']):
            raise ValueError('Invalid stored category slug.')
        links += f'<a href="{base_path}/categories/{item["slug"]}/">{escape(item["title"])}</a>'

    def page(title: str, body: str) -> str:
        return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)} | Connection proof</title><style>body{{background:{state['background']};color:#20332b;font:18px/1.6 system-ui,sans-serif;max-width:840px;margin:60px auto;padding:24px}}nav{{display:flex;gap:20px;flex-wrap:wrap}}a{{color:#284b3b}}h1{{font-size:2.5rem;line-height:1.1}}.notice{{border:1px solid #81998c;padding:12px}}code{{overflow-wrap:anywhere}}</style></head><body><nav>{links}</nav><p class="notice">Fictional connection test. No student information.</p><h1>{escape(title)}</h1>{body}<footer><p>Candidate identity: <code id="candidate-id">{identity}</code></p></footer></body></html>'''

    out.mkdir(parents=True, exist_ok=True)
    post_links = ''
    routes = ['/']
    for post in state['posts']:
        if not SLUG.fullmatch(post['slug']):
            raise ValueError('Invalid stored post slug.')
        route = f'/blog/{post["slug"]}/'
        folder = out / 'blog' / post['slug']
        folder.mkdir(parents=True, exist_ok=True)
        folder.joinpath('index.html').write_text(page(post['title'], f'<p>{escape(post["text"])}</p>'))
        post_links += f'<li><a href="{base_path}{route}">{escape(post["title"])}</a></li>'
        routes.append(route)
    for item in state['categories']:
        folder = out / 'categories' / item['slug']
        folder.mkdir(parents=True, exist_ok=True)
        folder.joinpath('index.html').write_text(page(item['title'], '<p>Category page created for the connection test.</p>'))
        routes.append(f'/categories/{item["slug"]}/')
    out.joinpath('index.html').write_text(page('BFF portfolio connection proof', f'<h2>Practice posts</h2><ul>{post_links}</ul>'))
    proof = {'fixture_only': True, 'candidate_sha256': identity, 'background': state['background'], 'base_path': base_path, 'routes': routes}
    out.joinpath('connection-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    return proof


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    build = sub.add_parser('build', help='render the current fictional site')
    build.add_argument('--output', type=Path, default=ROOT / 'dist')
    build.add_argument('--base-path', default='', help='project-site prefix, without a trailing slash')
    request = sub.add_parser('request', help='apply one content request to this local fixture')
    request.add_argument('--request-id', required=True)
    request.add_argument('--kind', choices=['color', 'blog', 'category'], required=True)
    request.add_argument('--value', required=True)
    request.add_argument('--slug', default='')
    request.add_argument('--text', default='')
    args = parser.parse_args()
    state = read_state(ROOT)
    if args.action == 'request':
        payload = {'request_id': args.request_id, 'kind': args.kind, 'value': args.value, 'slug': args.slug, 'text': args.text}
        state, changed = apply_request(state, payload)
        if changed:
            (ROOT / 'state.json').write_text(json.dumps(state, indent=2) + '\n')
        print(json.dumps({'changed': changed, 'fixture_only': True}))
    else:
        print(json.dumps(render(state, args.output, args.base_path), indent=2))


if __name__ == '__main__':
    main()
