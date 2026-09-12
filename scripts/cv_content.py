"""Read the visible CV headline and project selection for the downloadable PDF."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path


class CVContentParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.content = {'role': '', 'summary': '', 'projects': []}
        self.project = None
        self.capture = None
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set(attrs.get('class', '').split())
        if tag == 'a' and 'cv-project' in classes:
            self.project = {'href': attrs.get('href', '')}
        field = None
        if tag == 'p' and 'profile-role' in classes:
            field = 'role'
        elif tag == 'p' and 'profile-summary' in classes:
            field = 'summary'
        elif self.project is not None:
            if tag == 'h3':
                field = 'title'
            elif tag == 'p' and 'work-stack' in classes:
                field = 'stack'
            elif tag == 'p' and 'work-summary' in classes:
                field = 'description'
        if field is not None:
            self.capture = (tag, field)
            self.parts = []

    def handle_data(self, data):
        if self.capture is not None:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if self.capture is not None and tag == self.capture[0]:
            field = self.capture[1]
            target = self.content if field in ('role', 'summary') else self.project
            target[field] = ' '.join(''.join(self.parts).split())
            self.capture = None
        if tag == 'a' and self.project is not None:
            required = ('title', 'stack', 'description', 'href')
            if not all(self.project.get(field) for field in required):
                raise ValueError('Each selected CV project needs visible title, stack and summary text')
            self.content['projects'].append(self.project)
            self.project = None


def read_cv_content(source: str) -> dict:
    parser = CVContentParser()
    parser.feed(source)
    parser.close()
    if not parser.content['role'] or not parser.content['summary'] or not parser.content['projects']:
        raise ValueError('The HTML CV needs a role, profile summary and selected projects')
    return parser.content


def load_cv_content(root: Path) -> dict:
    return read_cv_content((root / 'index.html').read_text(encoding='utf-8'))
