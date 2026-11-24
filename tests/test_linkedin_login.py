"""Check login form selection without using real account credentials."""

import unittest
from unittest.mock import Mock

from selenium.webdriver.common.by import By

from linkedin_email_extractor import LinkedInEmailExtractor


class LinkedInLoginTest(unittest.TestCase):
    def test_visible_fields_are_filled_and_visible_button_is_clicked(self):
        browser = Mock()
        browser.current_url = "https://www.linkedin.com/login/"
        browser.get.side_effect = lambda url: setattr(browser, "current_url", url)

        hidden_email = Mock()
        hidden_email.is_displayed.return_value = False
        email = Mock()
        email.is_displayed.return_value = True
        email.is_enabled.return_value = True
        email.get_attribute.return_value = "candidate@example.com"

        hidden_password = Mock()
        hidden_password.is_displayed.return_value = False
        password = Mock()
        password.is_displayed.return_value = True
        password.is_enabled.return_value = True
        password.get_attribute.return_value = "dummy-password"

        hidden_button = Mock()
        hidden_button.is_displayed.return_value = False
        button = Mock()
        button.is_displayed.return_value = True
        button.is_enabled.return_value = True
        button.click.side_effect = lambda: setattr(
            browser, "current_url", "https://www.linkedin.com/feed/"
        )

        def elements(by, selector):
            if browser.current_url.endswith("/feed/"):
                return []
            if by == By.CSS_SELECTOR and "input#username" in selector:
                return [hidden_email, email]
            if by == By.CSS_SELECTOR and "input#password" in selector:
                return [hidden_password, password]
            if by == By.XPATH and "Sign in" in selector:
                return [hidden_button, button]
            return []

        browser.find_elements.side_effect = elements
        extractor = LinkedInEmailExtractor.__new__(LinkedInEmailExtractor)
        extractor.driver = browser
        extractor.linkedin_email = "candidate@example.com"
        extractor.linkedin_password = "dummy-password"
        extractor.update_status = Mock()

        self.assertFalse(extractor.is_logged_in_LN())
        extractor.login_to_linkedin()
        email.send_keys.assert_called_once_with("candidate@example.com")
        password.send_keys.assert_called_once_with("dummy-password")
        button.click.assert_called_once()
        self.assertTrue(extractor.is_logged_in_LN())


if __name__ == "__main__":
    unittest.main()
