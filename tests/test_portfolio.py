from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PAGES = ('index.html', 'portfolio.html', 'work-logs.html')


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids = []
        self.resources = []
        self.text = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        for key in ('href', 'src'):
            if key in attrs:
                self.resources.append(attrs[key])

    def handle_data(self, data):
        self.text.append(data)


class PortfolioIntegrityTests(unittest.TestCase):
    def test_local_assets_and_navigation_anchors_resolve(self):
        for filename in PAGES:
            document = Document((ROOT / filename).read_text())
            self.assertEqual(len(document.ids), len(set(document.ids)), filename)
            for resource in document.resources:
                url = urlsplit(resource)
                if url.scheme or url.netloc:
                    continue
                target = ROOT / (unquote(url.path) or filename)
                self.assertTrue(target.is_file(), f'{filename}: {resource}')
                if url.fragment and target.suffix == '.html':
                    self.assertIn(unquote(url.fragment), Document(target.read_text()).ids)

    def test_cv_content_is_available_as_text(self):
        text = ' '.join(Document((ROOT / 'index.html').read_text()).text)
        for content in ('Woolworths', 'Fujifilm', 'Junior Data Analyst', 'Dataquest', 'Python'):
            self.assertIn(content, text)
        self.assertTrue((ROOT / 'Alex-Bethune-CV.pdf').read_bytes().startswith(b'%PDF-'))

    def test_public_pages_do_not_link_unselected_repositories(self):
        allowed = set(json.loads((ROOT / 'public-projects.json').read_text())['repositories'])
        for filename in PAGES:
            for resource in Document((ROOT / filename).read_text()).resources:
                url = urlsplit(resource)
                if url.netloc == 'github.com' and url.path.startswith('/Likio3000/'):
                    root = '/'.join(resource.split('/')[:5])
                    self.assertIn(root.split('#')[0], allowed)

    def test_archive_contains_only_selected_public_repositories(self):
        source = (ROOT / 'work-log-data.js').read_text()
        data = json.loads(source[source.index('{'):].rstrip().rstrip(';'))
        allowed = set(json.loads((ROOT / 'public-projects.json').read_text())['repositories'])
        self.assertTrue(data['entries'])
        self.assertTrue(all(entry['repoUrl'] in allowed for entry in data['entries']))
        self.assertEqual(data['projectCount'], len({entry['repoUrl'] for entry in data['entries']}))


class ArchivePublicationTests(unittest.TestCase):
    def test_generator_skips_unselected_activity_before_reading_it(self):
        spec = importlib.util.spec_from_file_location('worklog_generator', ROOT / 'scripts/generate_work_log.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            allowlist = folder / 'public.json'
            allowed = 'https://github.com/Likio3000/typing-quest'
            allowlist.write_text(json.dumps({'repositories': [allowed]}))
            config = {'projects': [
                {'name': 'Public', 'path': directory, 'repo_url': allowed},
                {'name': 'Private', 'path': directory, 'repo_url': 'https://github.com/Likio3000/Private'},
            ]}
            output = folder / 'data.js'
            entry = {'date': '2026-03-01', 'timestamp': '2026-03-01', 'project': 'Public', 'repoUrl': allowed}
            with patch.object(module, 'load_config', return_value=config), \
                 patch.object(module, 'PUBLIC_PROJECTS_PATH', allowlist), \
                 patch.object(module, 'OUTPUT_PATH', output), \
                 patch.object(module, 'read_structured_entries', return_value=[]) as structured, \
                 patch.object(module, 'read_git_entries', return_value=[entry]) as commits:
                self.assertEqual(module.main(), 0)
            structured.assert_called_once()
            commits.assert_called_once()
            self.assertEqual(commits.call_args.kwargs['project_name'], 'Public')
            exported = output.read_text()
            self.assertNotIn('Private', exported)
            data = json.loads(exported[exported.index('{'):].rstrip().rstrip(';'))
            self.assertEqual(data['projectCount'], 1)
            self.assertEqual(data['entries'], [entry])


if __name__ == '__main__':
    unittest.main()
