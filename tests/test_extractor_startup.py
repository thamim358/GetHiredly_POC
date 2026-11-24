"""Check startup failures without opening Chrome or sending mail."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from professional_dashboard_api import ProfessionalBotController


class ExtractorStartupTest(unittest.TestCase):
    def test_dll_failure_is_reported_before_real_extractor_launch(self):
        controller = ProfessionalBotController()
        with (
            patch("professional_dashboard_api.os.path.exists", return_value=True),
            patch("professional_dashboard_api.subprocess.run", return_value=SimpleNamespace(returncode=3221225794)),
            patch("professional_dashboard_api.subprocess.Popen") as launch,
        ):
            result = controller.start_email_extractor()
        self.assertFalse(result["success"])
        self.assertIn("0xC0000142", result["error"])
        launch.assert_not_called()

    def test_extractor_crash_is_reported_as_error(self):
        controller = ProfessionalBotController()
        controller.email_extractor_process = Mock()
        controller.email_extractor_process.poll.return_value = 1
        controller.stats["email_extractor"]["status"] = "running"
        with patch.object(controller, "_update_email_stats"):
            controller._monitor_email_extractor()
        self.assertEqual(controller.stats["email_extractor"]["status"], "error")


if __name__ == "__main__":
    unittest.main()
