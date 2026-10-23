"""Behavior checks for the fictional proof fixture, not Eduba integration tests."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('fixture', Path(__file__).with_name('fixture.py'))
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
TMP_ROOT = '/private/tmp' if Path('/private/tmp').is_dir() else None


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.state = {'background': '#f6f8f7', 'posts': [], 'categories': [], 'requests': {}}

    def test_color_and_idempotent_repeat(self):
        request = {'request_id': 'green-test', 'kind': 'color', 'value': '#d9eddc'}
        state, changed = fixture.apply_request(self.state, request)
        self.assertTrue(changed)
        self.assertEqual(state['background'], '#d9eddc')
        repeated, changed = fixture.apply_request(state, request)
        self.assertFalse(changed)
        self.assertEqual(repeated, state)
        with self.assertRaises(ValueError):
            fixture.apply_request(state, {**request, 'value': '#ffffff'})

    def test_blog_and_category_routes_with_safe_text(self):
        state, _ = fixture.apply_request(self.state, {'request_id': 'new-post', 'kind': 'blog', 'slug': 'meeting-notes', 'value': 'Meeting notes practice', 'text': '<script>unsafe()</script>'})
        state, _ = fixture.apply_request(state, {'request_id': 'new-category', 'kind': 'category', 'slug': 'automation', 'value': 'Automation'})
        with tempfile.TemporaryDirectory(prefix='bff-proof-', dir=TMP_ROOT) as tmp:
            out = Path(tmp)
            proof = fixture.render(state, out)
            self.assertTrue((out / 'blog/meeting-notes/index.html').is_file())
            self.assertTrue((out / 'categories/automation/index.html').is_file())
            self.assertIn('/categories/automation/', (out / 'index.html').read_text())
            post = (out / 'blog/meeting-notes/index.html').read_text()
            self.assertNotIn('<script>', post)
            self.assertIn('&lt;script&gt;', post)
            self.assertEqual(proof, json.loads((out / 'connection-proof.json').read_text()))

    def test_rejects_path_and_css_injection(self):
        for slug in ['../../private', 'a/b', '<script>', 'UPPER']:
            with self.assertRaises(ValueError):
                fixture.apply_request(self.state, {'request_id': 'bad-slug', 'kind': 'category', 'slug': slug, 'value': 'Test'})
        with self.assertRaises(ValueError):
            fixture.apply_request(self.state, {'request_id': 'bad-css', 'kind': 'color', 'value': 'green; background:url(https://example.invalid)'})

    def test_revert_color_preserves_other_work(self):
        state, _ = fixture.apply_request(self.state, {'request_id': 'make-green', 'kind': 'color', 'value': '#d9eddc'})
        state, _ = fixture.apply_request(state, {'request_id': 'add-blog', 'kind': 'blog', 'slug': 'sample', 'value': 'Sample', 'text': 'Fictional practice.'})
        state, _ = fixture.apply_request(state, {'request_id': 'restore-color', 'kind': 'color', 'value': '#f6f8f7'})
        self.assertEqual(state['background'], self.state['background'])
        self.assertEqual(len(state['posts']), 1)

    def test_project_site_links_and_base_path_validation(self):
        state, _ = fixture.apply_request(self.state, {'request_id': 'project-post', 'kind': 'blog', 'slug': 'sample', 'value': 'Sample', 'text': 'Fictional.'})
        state, _ = fixture.apply_request(state, {'request_id': 'project-category', 'kind': 'category', 'slug': 'automation', 'value': 'Automation'})
        with tempfile.TemporaryDirectory(prefix='bff-proof-', dir=TMP_ROOT) as tmp:
            root = Path(tmp)
            fixture.render(state, root, '/bff-eduba-portfolio-proof')
            home = (root / 'index.html').read_text()
            for route in ['/', '/blog/sample/', '/categories/automation/']:
                self.assertIn(f'href="/bff-eduba-portfolio-proof{route}"', home)
            with self.assertRaises(ValueError):
                fixture.render(state, root, '/../../private')


if __name__ == '__main__':
    unittest.main()
