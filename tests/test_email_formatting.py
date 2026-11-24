import unittest

from email_formatting import plain_text_from_html, render_email_html


class EmailFormattingTests(unittest.TestCase):
    def test_saved_markdown_inside_html_wrapper(self):
        template = (
            '<html><head><style>body {color:#333}</style></head><body>'
            'Dear Hiring Manager,\n\n'
            'I am applying for **Playwright Automation Engineer**.\n\n'
            '**Skills:**\n\n• **Playwright** and TypeScript\n'
            '• API testing\n\n'
            'LinkedIn: [Profile](https://example.com/profile)'
            '</body></html>'
        )
        result = render_email_html(template)
        self.assertIn('<style>body {color:#333}</style>', result)
        self.assertIn('<p>Dear Hiring Manager,</p>', result)
        self.assertIn('<strong>Playwright Automation Engineer</strong>', result)
        self.assertIn('<ul>', result)
        self.assertIn('<li><strong>Playwright</strong> and TypeScript</li>', result)
        self.assertIn('<a href="https://example.com/profile">Profile</a>', result)
        self.assertNotIn('**', result)
        plain = plain_text_from_html(result)
        self.assertTrue(plain.startswith('Dear Hiring Manager,'))
        self.assertNotIn('color:#333', plain)
        self.assertIn('Dear Hiring Manager,\n\nI am applying', plain)
        self.assertIn('Profile <https://example.com/profile>', plain)

    def test_existing_html_structure_is_preserved(self):
        template = '<p>Hello <strong>team</strong>,</p><p>See my <a href="https://example.com">work</a>.</p>'
        result = render_email_html(template)
        self.assertIn(template, result)

    def test_plain_text_linebreaks_and_bold(self):
        result = render_email_html('Hello,\n\n**QA engineer**\nThank you')
        self.assertIn('<p>Hello,</p>', result)
        self.assertIn('<strong>QA engineer</strong><br>', result)


if __name__ == '__main__':
    unittest.main()
