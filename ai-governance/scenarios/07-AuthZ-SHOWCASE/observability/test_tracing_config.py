"""
Tests for tracing_config.py — validates experiment resolution and config logic.

Run: python -m pytest observability/test_tracing_config.py -v
"""

import os
import unittest
from unittest.mock import patch, MagicMock


class TestTracingConfig(unittest.TestCase):
    """Unit tests for tracing configuration module."""

    def _import_fresh(self):
        """Re-import to pick up patched env vars."""
        import importlib
        from observability import tracing_config
        importlib.reload(tracing_config)
        return tracing_config

    @patch.dict(os.environ, {"MLFLOW_EXPERIMENT_NAME": ""}, clear=False)
    def test_init_tracing_raises_without_experiment_name(self):
        """init_tracing() must raise if MLFLOW_EXPERIMENT_NAME is empty."""
        tc = self._import_fresh()
        with self.assertRaises(RuntimeError) as ctx:
            tc.init_tracing()
        self.assertIn("MLFLOW_EXPERIMENT_NAME", str(ctx.exception))

    @patch.dict(
        os.environ,
        {"MLFLOW_EXPERIMENT_NAME": "/Users/test@db.com/test-experiment"},
        clear=False,
    )
    @patch("mlflow.set_experiment")
    @patch("mlflow.get_experiment_by_name")
    def test_init_tracing_resolves_experiment(self, mock_get, mock_set):
        """init_tracing() resolves experiment_id from the env var name."""
        mock_exp = MagicMock()
        mock_exp.experiment_id = "12345"
        mock_get.return_value = mock_exp

        tc = self._import_fresh()
        exp_id = tc.init_tracing()

        mock_set.assert_called_once_with("/Users/test@db.com/test-experiment")
        mock_get.assert_called_once_with("/Users/test@db.com/test-experiment")
        self.assertEqual(exp_id, "12345")

    @patch.dict(
        os.environ,
        {"MLFLOW_EXPERIMENT_NAME": "/Users/test@db.com/test-experiment"},
        clear=False,
    )
    @patch("mlflow.set_experiment")
    @patch("mlflow.get_experiment_by_name", return_value=None)
    def test_init_tracing_raises_if_experiment_not_found(self, mock_get, mock_set):
        """init_tracing() raises if experiment cannot be resolved."""
        tc = self._import_fresh()
        with self.assertRaises(RuntimeError) as ctx:
            tc.init_tracing()
        self.assertIn("could not be resolved", str(ctx.exception))

    def test_get_service_tags_returns_expected_keys(self):
        """get_service_tags() returns consistent tag dict."""
        from observability.tracing_config import get_service_tags

        tags = get_service_tags("test-service")
        self.assertEqual(tags["service_name"], "test-service")
        self.assertIn("app_version", tags)
        self.assertIn("environment", tags)

    @patch.dict(
        os.environ,
        {
            "MLFLOW_EXPERIMENT_NAME": "/test",
            "MLFLOW_TRACE_SAMPLING_RATIO": "0.5",
        },
        clear=False,
    )
    @patch("mlflow.set_experiment")
    @patch("mlflow.get_experiment_by_name")
    def test_env_var_override_respected(self, mock_get, mock_set):
        """User-set env vars should not be overwritten by defaults."""
        mock_exp = MagicMock()
        mock_exp.experiment_id = "99"
        mock_get.return_value = mock_exp

        tc = self._import_fresh()
        tc.init_tracing()

        # os.environ.setdefault should NOT overwrite the user's 0.5
        self.assertEqual(os.environ["MLFLOW_TRACE_SAMPLING_RATIO"], "0.5")


if __name__ == "__main__":
    unittest.main()
