# Contributing

Thanks for helping improve the project. Open an issue to discuss substantial changes before starting them, then submit a focused pull request.

1. Install the project as described in [README.md](README.md).
2. Run `python -m unittest discover -s tests -v` before opening a pull request.
3. Keep tests offline and use mocks for LinkedIn, Chrome, and SMTP interactions.
4. Do not include credentials, personal details, résumés, browser profiles, recruiter contact lists, logs, or runtime JSON/CSV files. Use synthetic examples in tests and documentation.

The current release includes the dashboard, email extractor, and networking assistant. The old AI Easy Apply code is outside the maintained scope.
