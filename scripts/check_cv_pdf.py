"""Fail if the published one-page PDF no longer matches its HTML source."""
import re
from pathlib import Path

from pypdf import PdfReader

from cv_content import load_cv_content
from build_cv_pdf import plain, section


def check(root: Path) -> None:
    content = load_cv_content(root)
    reader = PdfReader(root / 'Alex-Bethune-CV.pdf')
    if len(reader.pages) != 1:
        raise ValueError('The downloadable CV must remain one page')
    text = ' '.join(reader.pages[0].extract_text().split())
    expected = [content['role'], content['summary']]
    for project in content['projects']:
        expected.extend(project[key] for key in ('title', 'stack', 'description'))
    source = (root / 'index.html').read_text()
    for field in ('experience-title', 'education-title', 'toolbox-title'):
        expected.extend(plain(value) for value in re.findall(
            r'<(?:dt|dd)(?:\s[^>]*)?>(.*?)</(?:dt|dd)>', section(source, field), re.S
        ))
    for value in expected:
        if ' '.join(value.split()) not in text:
            raise ValueError(f'PDF is out of sync with HTML: {value}')
    print(f'One-page PDF matches the HTML headline, {len(content["projects"])} projects, experience, education and skills.')


if __name__ == '__main__':
    check(Path(__file__).resolve().parents[1])
