import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cv_content', ROOT / 'scripts/cv_content.py')
cv_content = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cv_content)


class CVContentTests(unittest.TestCase):
    def test_pdf_content_follows_visible_headline_and_selection(self):
        source = '''<p class="profile-role">Data engineering &amp; Python.</p>
          <p class="profile-summary">Build <em>reproducible</em> pipelines.</p>
          <a class="cv-project" href="portfolio.html#second">
            <h3>Second project</h3><p class="work-stack">Python, SQL</p>
            <p class="work-summary">A changed description.</p></a>
          <a class="cv-project" href="portfolio.html#first">
            <h3>First project</h3><p class="work-stack">dbt</p>
            <p class="work-summary">Another project.</p></a>'''
        content = cv_content.read_cv_content(source)
        self.assertEqual(content['role'], 'Data engineering & Python.')
        self.assertEqual(content['summary'], 'Build reproducible pipelines.')
        self.assertEqual([item['title'] for item in content['projects']],
                         ['Second project', 'First project'])
        self.assertEqual(content['projects'][0]['description'], 'A changed description.')

    def test_missing_visible_fields_fail_instead_of_producing_a_partial_cv(self):
        with self.assertRaises(ValueError):
            cv_content.read_cv_content('<p class="profile-role">Engineer</p>')
        with self.assertRaisesRegex(ValueError, 'Each selected CV project'):
            cv_content.read_cv_content('<a class="cv-project"><h3>Incomplete</h3></a>')


if __name__ == '__main__':
    unittest.main()
