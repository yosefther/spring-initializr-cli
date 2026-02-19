import unittest

from spring_initializr_cli.metadata import metadata_dependencies, metadata_values


class MetadataTests(unittest.TestCase):
    def test_metadata_values_ignores_invalid_items(self):
        metadata = {
            "bootVersion": {
                "values": [
                    {"id": "3.4.0"},
                    {"name": "missing-id"},
                    "invalid",
                ]
            }
        }

        self.assertEqual(metadata_values(metadata, "bootVersion"), ["3.4.0"])

    def test_metadata_dependencies_ignores_invalid_shapes(self):
        metadata = {
            "dependencies": {
                "values": [
                    {
                        "values": [
                            {"id": "web", "name": "Spring Web"},
                            {"id": "aop"},
                            "invalid",
                        ]
                    },
                    "invalid-group",
                ]
            }
        }

        self.assertEqual(
            metadata_dependencies(metadata),
            {
                "web": "Spring Web",
                "aop": "aop",
            },
        )


if __name__ == "__main__":
    unittest.main()
