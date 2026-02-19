import argparse
import tempfile
import unittest
from pathlib import Path

from spring_initializr_cli.hooks import apply_post_generation_hooks
from spring_initializr_cli.models import ProjectSpec


class HookTests(unittest.TestCase):
    def test_file_hooks_create_expected_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            (project_dir / "mvnw").write_text("#!/bin/sh\n", encoding="utf-8")

            spec = ProjectSpec(
                project_type="maven-project",
                language="java",
                boot_version="3.4.0",
                group_id="com.example",
                artifact_id="demo",
                name="demo",
                package_name="com.example.demo",
                java_version="21",
                packaging="jar",
                dependencies=["web"],
            )

            args = argparse.Namespace(
                git_init=False,
                init_readme=True,
                add_docker=True,
                add_github_actions=True,
            )

            actions = apply_post_generation_hooks(project_dir, spec, args)

            self.assertTrue((project_dir / "README.md").exists())
            self.assertTrue((project_dir / "Dockerfile").exists())
            self.assertTrue((project_dir / ".dockerignore").exists())
            self.assertTrue((project_dir / ".github" / "workflows" / "ci.yml").exists())
            self.assertTrue(actions)


if __name__ == "__main__":
    unittest.main()
