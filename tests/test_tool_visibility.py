"""Local tools remain usable locally and never enter a public export."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from investdiy import export, registry
from investdiy.server import tools_payload


class VisibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.modules = {}
        self.add_tool('public_tool', visibility='public')
        self.add_tool('local_tool', visibility='local')
        self.add_tool('unspecified_tool')
        self.addCleanup(patch.stopall)
        patch.object(registry, 'TOOLS_DIR', self.root).start()
        patch.object(registry.importlib, 'import_module', side_effect=lambda name: self.modules[name]).start()

    def add_tool(self, slug, **extra):
        root = self.root / slug
        (root / 'web').mkdir(parents=True)
        (root / '__init__.py').touch()
        (root / 'web/index.html').write_text(slug)
        (root / 'web/app.js').write_text(f'// {slug} script')
        (root / 'data/out').mkdir(parents=True)
        (root / 'data/out/history.csv').write_text(f'date,value\n2026-11-05,{slug}\n')
        self.modules[f'investdiy.{slug}'] = SimpleNamespace(TOOL={'slug': slug, 'title': slug, **extra})

    def test_local_discovery_and_api_include_both_categories(self):
        tools = registry.discover()
        self.assertEqual(set(tools), {'public_tool', 'local_tool', 'unspecified_tool'})
        self.assertEqual({r['slug']: r['visibility'] for r in tools_payload(tools)}, {
            'public_tool': 'public', 'local_tool': 'local', 'unspecified_tool': 'local'})

    def test_public_discovery_requires_explicit_opt_in(self):
        self.assertEqual(set(registry.discover(public_only=True)), {'public_tool'})

    def test_invalid_visibility_rejects_public_export_before_deleting_old_files(self):
        self.modules['investdiy.local_tool'].TOOL['visibility'] = 'pubic'
        dist = self.root / 'site'
        (dist / 'api').mkdir(parents=True)
        (dist / 'api/tools.json').write_text('[]')
        (dist / 'marker.txt').write_text('previous export')
        with self.assertRaises(ValueError):
            export.build(dist)
        self.assertTrue((dist / 'marker.txt').exists())

    def test_export_omits_local_assets_and_removes_previously_exported_local_data(self):
        dist = self.root / 'site'
        (dist / 'api').mkdir(parents=True)
        (dist / 'api/tools.json').write_text('[{"slug":"local_tool"}]')
        (dist / 'local_tool/data').mkdir(parents=True)
        (dist / 'local_tool/data/history.csv').write_text('old public copy')
        (dist / 'local_tool/index.html').write_text('old local page')
        built = export.build(dist)
        self.assertEqual(built, ['public_tool'])
        payload = json.loads((dist / 'api/tools.json').read_text())
        self.assertEqual([r['slug'] for r in payload], ['public_tool'])
        self.assertTrue((dist / 'public_tool/app.js').exists())
        self.assertTrue((dist / 'public_tool/data/history.csv').exists())
        self.assertFalse((dist / 'local_tool').exists())
        self.assertFalse((dist / 'unspecified_tool').exists())
        # Export filtering must never delete the source tool or locally collected data.
        self.assertTrue((self.root / 'local_tool/web/index.html').exists())
        self.assertIn('local_tool', (self.root / 'local_tool/data/out/history.csv').read_text())

    def test_no_public_tools_still_exports_a_valid_empty_catalog(self):
        self.modules['investdiy.public_tool'].TOOL['visibility'] = 'local'
        dist = self.root / 'site'
        self.assertEqual(export.build(dist), [])
        self.assertEqual(json.loads((dist / 'api/tools.json').read_text()), [])
        self.assertTrue((dist / 'index.html').exists())
        self.assertFalse((dist / 'public_tool').exists())

    def test_becoming_local_removes_a_previously_public_tool(self):
        dist = self.root / 'site'
        export.build(dist)
        self.modules['investdiy.public_tool'].TOOL['visibility'] = 'local'
        export.build(dist)
        self.assertFalse((dist / 'public_tool').exists())
        self.assertEqual(json.loads((dist / 'api/tools.json').read_text()), [])


class ProjectVisibilityTests(unittest.TestCase):
    def test_freight_is_local_and_etf_is_public(self):
        all_tools = registry.discover()
        public_tools = registry.discover(public_only=True)
        self.assertEqual(all_tools['global-track-container-freight'][0].visibility, 'local')
        self.assertNotIn('global-track-container-freight', public_tools)
        self.assertIn('ashare-track-national-team-etf', public_tools)


if __name__ == '__main__':
    unittest.main()
