import time
import tempfile
import unittest
from pathlib import Path

from spring_initializr_cli.client import SpringInitializrClient, _looks_like_metadata


class ClientTests(unittest.TestCase):
    def test_looks_like_metadata(self):
        self.assertTrue(_looks_like_metadata({"bootVersion": {"values": [{"id": "3.4.0"}]}}))
        self.assertFalse(_looks_like_metadata({"_links": {"self": {"href": "x"}}}))

    def test_fetch_metadata_uses_fresh_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "metadata.json"
            client = SpringInitializrClient(cache_path=cache_path, max_retries=0)
            client._discover_endpoints = lambda: {}

            sample = {"bootVersion": {"values": [{"id": "3.4.0"}]}}
            client._fetch_json = lambda url: sample

            first = client.fetch_metadata()
            self.assertEqual(first, sample)
            self.assertEqual(client.last_metadata_source, "network")

            def fail(_url: str):
                raise RuntimeError("offline")

            client._fetch_json = fail
            second = client.fetch_metadata()
            self.assertEqual(second, sample)
            self.assertEqual(client.last_metadata_source, "cache-fresh")

    def test_fetch_metadata_uses_stale_cache_on_network_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "metadata.json"
            stale_payload = {
                "saved_at": time.time() - 999,
                "source_url": "https://start.spring.io/metadata/client",
                "metadata": {"bootVersion": {"values": [{"id": "3.3.0"}]}}
            }
            cache_path.write_text(__import__("json").dumps(stale_payload), encoding="utf-8")

            client = SpringInitializrClient(
                cache_path=cache_path,
                cache_ttl_seconds=1,
                refresh_metadata=True,
                max_retries=0,
            )
            client._discover_endpoints = lambda: {}

            def fail(_url: str):
                raise RuntimeError("offline")

            client._fetch_json = fail
            metadata = client.fetch_metadata()

            self.assertEqual(metadata["bootVersion"]["values"][0]["id"], "3.3.0")
            self.assertEqual(client.last_metadata_source, "cache-stale")


if __name__ == "__main__":
    unittest.main()
