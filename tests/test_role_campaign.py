"""Local campaign checks that do not start a browser or send mail."""

import tempfile
import unittest
from pathlib import Path

from role_campaign import UPLOADS, campaign_roles
from professional_dashboard_api import ProfessionalBotController, app
from linkedin_email_extractor import LinkedInEmailExtractor


class CampaignRolesTest(unittest.TestCase):
    def setUp(self):
        UPLOADS.mkdir(exist_ok=True)
        self.files = []
        for _ in range(2):
            with tempfile.NamedTemporaryFile(dir=UPLOADS, suffix=".pdf", delete=False) as file:
                file.write(b"%PDF-1.4\n")
                self.files.append(Path(file.name))

    def tearDown(self):
        for file in self.files:
            file.unlink(missing_ok=True)

    def test_each_role_keeps_its_own_template_terms_and_resume(self):
        roles = []
        for name, resume in zip(("React", "UI"), self.files):
            roles.append({
                "role": name.lower(), "subject": f"Apply for {name}",
                "searchTerms": [name, ""], "emailTemplate": f"<p>{name}</p>",
                "resumeFile": str(resume),
            })
        result = campaign_roles({"roles": roles})
        self.assertEqual([role["subject"] for role in result], ["Apply for React", "Apply for UI"])
        self.assertEqual([role["search_terms"] for role in result], [["React"], ["UI"]])
        self.assertNotEqual(result[0]["resume_file"], result[1]["resume_file"])

    def test_missing_resume_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "resume"):
            campaign_roles({"roles": [{
                "role": "react", "subject": "Apply", "searchTerms": ["React"],
                "emailTemplate": "Hello", "resumeFile": "uploads/missing.pdf",
            }]})

    def test_resume_outside_uploads_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "uploaded"):
            campaign_roles({"roles": [{
                "role": "react", "subject": "Apply", "searchTerms": ["React"],
                "emailTemplate": "Hello", "resumeFile": "../private.pdf",
            }]})

    def test_dashboard_prepares_each_role_email(self):
        roles = []
        for name, resume in zip(("React", "UI"), self.files):
            roles.append({
                "role": name.lower(), "subject": name, "searchTerms": [name],
                "emailTemplate": f"<p>{name}: [FULL_NAME]</p>",
                "resumeFile": str(resume),
            })
        config = ProfessionalBotController._prepare_job_config(None, {
            "personal": {"fullName": "Example Candidate"},
            "job": {"roles": roles, "botType": "email"},
        })
        self.assertEqual([role["email_body"] for role in config["roles"]], [
            "<p>React: Example Candidate</p>", "<p>UI: Example Candidate</p>",
        ])
        self.assertEqual(config["resume_file"], str(self.files[0]))

    def test_snapshot_endpoint_copies_resume(self):
        client = app.test_client()
        response = client.post("/api/snapshot-resume", json={"path": str(self.files[0])})
        self.assertEqual(response.status_code, 200)
        snapshot = UPLOADS / Path(response.json["path"]).name
        self.files.append(snapshot)
        self.assertEqual(snapshot.read_bytes(), self.files[0].read_bytes())

    def test_dashboard_renders_campaign_controls(self):
        response = app.test_client().get("/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Multi-role campaign", response.data)

    def test_old_entry_points_open_current_dashboard(self):
        response = app.test_client().get("/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/dashboard")
        from app import app as history_app
        from dashboard_api import app as legacy_app
        self.assertEqual(history_app.test_client().get("/").status_code, 302)
        self.assertEqual(legacy_app.test_client().get("/").status_code, 302)

    def test_email_message_uses_selected_role_and_requires_resume(self):
        extractor = LinkedInEmailExtractor.__new__(LinkedInEmailExtractor)
        extractor.SENDER_EMAIL = "candidate@example.com"
        for name, resume in zip(("React", "UI"), self.files):
            extractor.SUBJECT = f"Apply for {name}"
            extractor.BODY_HTML = f"<html><body>{name}</body></html>"
            extractor.ATTACHMENT_PATH = str(resume)
            message = extractor.create_email_message("hiring@example.com")
            self.assertEqual(message["Subject"], f"Apply for {name}")
            alternatives = message.get_payload()[0]
            self.assertEqual(alternatives.get_content_subtype(), "alternative")
            self.assertEqual([part.get_content_subtype() for part in alternatives.get_payload()], ["plain", "html"])
            self.assertIn(name, alternatives.get_payload()[1].get_payload(decode=True).decode())
            self.assertEqual(message.get_payload()[1].get_payload(decode=True), resume.read_bytes())
        extractor.ATTACHMENT_PATH = str(UPLOADS / "missing.pdf")
        with self.assertRaises(FileNotFoundError):
            extractor.create_email_message("hiring@example.com")


if __name__ == "__main__":
    unittest.main()
