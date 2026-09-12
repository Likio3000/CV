import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PublicProjectDownloadsTests(unittest.TestCase):
    def test_downloaded_sources_match_manifests_and_recorded_demos(self):
        for name in ('commerce-cdc', 'signalforge'):
            with self.subTest(project=name), tempfile.TemporaryDirectory() as directory:
                manifest = json.loads((ROOT / 'downloads' / f'{name}-manifest.json').read_text())
                with zipfile.ZipFile(ROOT / 'downloads' / f'{name}.zip') as archive:
                    self.assertIsNone(archive.testzip())
                    self.assertEqual(set(archive.namelist()),
                                     {f'{name}/{path}' for path in manifest['source_sha256']})
                    for relative, digest in manifest['source_sha256'].items():
                        self.assertFalse(Path(relative).is_absolute())
                        self.assertNotIn('..', Path(relative).parts)
                        self.assertEqual(hashlib.sha256(archive.read(f'{name}/{relative}')).hexdigest(), digest)
                    archive.extractall(directory)
                project = Path(directory) / name
                result = subprocess.run([sys.executable, 'pipeline.py', 'demo'], cwd=project,
                                        capture_output=True, text=True, check=True, timeout=30)
                self.assertEqual(json.loads(result.stdout),
                                 json.loads((ROOT / 'downloads' / f'{name}-demo.json').read_text()))


if __name__ == '__main__':
    unittest.main()
