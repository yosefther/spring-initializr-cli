import argparse
import tempfile
import unittest
from pathlib import Path

from spring_initializr_cli.config import apply_preset_to_args, load_preset_file, resolve_preset_path


class ConfigTests(unittest.TestCase):
    def _new_args(self) -> argparse.Namespace:
        return argparse.Namespace(
            command="new",
            group_id=None,
            dependencies=None,
            force=None,
            output="",
            print_spec=None,
            use_cache=None,
            retries=None,
            timeout=None,
            cache_ttl=None,
            backoff=None,
            limit=None,
            format=None,
        )

    def test_apply_preset_sets_unset_values(self):
        args = self._new_args()
        preset = {
            "defaults": {
                "group-id": "com.acme",
                "force": True,
            },
            "new": {
                "dependencies": ["web", "actuator"],
                "output": "./services/demo",
            },
        }

        apply_preset_to_args(args, preset)

        self.assertEqual(args.group_id, "com.acme")
        self.assertTrue(args.force)
        self.assertEqual(args.dependencies, "web,actuator")
        self.assertEqual(args.output, "./services/demo")

    def test_command_section_overrides_defaults(self):
        args = self._new_args()
        preset = {
            "defaults": {"format": "text"},
            "new": {"format": "json"},
        }

        apply_preset_to_args(args, preset)

        self.assertEqual(args.format, "json")

    def test_cli_values_override_preset(self):
        args = self._new_args()
        args.group_id = "com.cli"

        apply_preset_to_args(args, {"defaults": {"group-id": "com.preset"}})

        self.assertEqual(args.group_id, "com.cli")

    def test_invalid_preset_type_raises(self):
        args = self._new_args()

        with self.assertRaises(ValueError):
            apply_preset_to_args(args, {"defaults": {"force": "yes"}})

    def test_resolve_and_load_preset_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            preset_file = tmp_path / "preset.toml"
            preset_file.write_text("[defaults]\ngroup-id = 'com.example'\n", encoding="utf-8")

            resolved = resolve_preset_path(str(preset_file))
            loaded = load_preset_file(resolved)

            self.assertEqual(loaded["defaults"]["group-id"], "com.example")


if __name__ == "__main__":
    unittest.main()
