"""Deployment hardening: refuse insecure network listening, run unprivileged, no world-writable dirs."""

import os
import unittest
from pathlib import Path
from unittest import mock

from cryptography.fernet import Fernet

from ecostream.app import server

ROOT = Path(__file__).resolve().parents[1]
GOOD_KEY = "eco_prod_secret_token_2026"

ENC_KEY = Fernet.generate_key().decode("ascii")


class StartupGuardTests(unittest.TestCase):
    def _env(self, **extra):
        base = {k: v for k, v in os.environ.items() if k not in ("ECOSTREAM_API_KEY", "ECOSTREAM_ENCRYPTION_KEY", "PORT", "HOST", "ECOSTREAM_HOST")}
        base.update(extra)
        return mock.patch.dict(os.environ, base, clear=True)

    def test_loopback_allowed_without_keys(self):
        with self._env():
            server.assert_safe_to_serve("127.0.0.1")
            server.assert_safe_to_serve("localhost")

    def test_network_bind_refused_without_any_keys(self):
        with self._env():
            with self.assertRaises(RuntimeError) as cm:
                server.assert_safe_to_serve("0.0.0.0")
        self.assertIn("ECOSTREAM_API_KEY", str(cm.exception))
        self.assertIn("ECOSTREAM_ENCRYPTION_KEY", str(cm.exception))

    def test_network_bind_refused_without_encryption_key(self):
        with self._env(ECOSTREAM_API_KEY=GOOD_KEY):
            with self.assertRaises(RuntimeError) as cm:
                server.assert_safe_to_serve("0.0.0.0")
        self.assertNotIn("ECOSTREAM_API_KEY (", str(cm.exception))
        self.assertIn("ECOSTREAM_ENCRYPTION_KEY", str(cm.exception))

    def test_short_api_key_refused(self):
        with self._env(ECOSTREAM_API_KEY="short", ECOSTREAM_ENCRYPTION_KEY=ENC_KEY):
            with self.assertRaises(RuntimeError):
                server.assert_safe_to_serve("0.0.0.0")

    def test_network_bind_allowed_with_both_keys(self):
        with self._env(ECOSTREAM_API_KEY=GOOD_KEY, ECOSTREAM_ENCRYPTION_KEY=ENC_KEY):
            server.assert_safe_to_serve("0.0.0.0")

    def test_malformed_encryption_key_refused(self):
        with self._env(ECOSTREAM_API_KEY=GOOD_KEY, ECOSTREAM_ENCRYPTION_KEY="x" * 44):
            with self.assertRaises(RuntimeError) as cm:
                server.assert_safe_to_serve("0.0.0.0")
        self.assertIn("không phải khóa Fernet hợp lệ", str(cm.exception))

    def test_run_server_refuses_before_listening(self):
        """run_server must raise before uvicorn.run is ever called."""
        with self._env(PORT="8123"), mock.patch.object(server.uvicorn, "run") as run:
            with self.assertRaises(RuntimeError):
                server.run_server()
            run.assert_not_called()


class DockerfileTests(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    def test_runs_as_unprivileged_user(self):
        self.assertIn("USER ecostream", self.text)
        self.assertNotIn("chmod -R 777", self.text)

    def test_dockerignore_excludes_local_runs_and_secrets(self):
        ignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").split()
        for item in ("runs", ".git", ".cache", ".env", "**/*.enc"):
            self.assertIn(item, ignore)

    def test_compose_requires_security_keys(self):
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("ECOSTREAM_API_KEY=${ECOSTREAM_API_KEY:?", compose)
        self.assertIn("ECOSTREAM_ENCRYPTION_KEY=${ECOSTREAM_ENCRYPTION_KEY:?", compose)


if __name__ == "__main__":
    unittest.main()
