# LinkedIn Career Assistant

A local dashboard for two workflows: (1) searching LinkedIn hiring posts and sending job application emails, and (2) finding jobs and people and sending reviewed LinkedIn connection notes. The former AI Easy Apply bot is no longer part of this release. This is an independent project and is not affiliated with LinkedIn.

## Requirements

- Python 3.11 or newer
- Google Chrome
- A LinkedIn account
- For email sending: a Gmail account with a working SMTP app password

Selenium Manager obtains a compatible ChromeDriver when Chrome starts. Do not download or commit a driver binary for this project.

## Install and run

Run commands from the repository root.

**Windows PowerShell**

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe professional_dashboard_api.py
```

**macOS or Linux**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python professional_dashboard_api.py
```

Open <http://127.0.0.1:5000/dashboard>. The server binds to your own computer only. Stop it with Ctrl+C. The dashboard is a local tool: anyone who can access its port can operate it and read local activity, so do not expose it to the internet or an untrusted network.

## Email campaign

1. Open **Email campaign** and enter your profile and LinkedIn sign-in details. Enter a Gmail sender address and app password to send emails.

   To get an app password, turn on [2-Step Verification](https://support.google.com/accounts/answer/185839), then open [Google App Passwords](https://myaccount.google.com/apppasswords) and create one for this app. Enter that password in the dashboard instead of your regular Google password. [Google's help](https://support.google.com/accounts/answer/185833) explains why App Passwords may be unavailable on some accounts.
2. Pick a role or write your own title, search terms, subject, and message. The template accepts `[FULL_NAME]`, `[EMAIL]`, `[PHONE]`, `[WEBSITE]`, and `[LOCATION]`; use **Preview formatted email** to review it.
3. Upload a PDF, DOC, or DOCX résumé (up to 10 MB). Use **Add role to campaign** to add more roles; each role keeps its own résumé and template.
4. Set the date filter and sending limits. Click **Save campaign**, then **Start email extractor**. This action can send real emails automatically. Check the recipients, message, and limits first. Previously emailed addresses are skipped using the local sent log.
5. Use **Stop extractor** to stop the run. See **Activity** for history and a local data export.

For a new install, enter credentials in the dashboard. There is no need to edit Python source files or add a `config/secrets.py` file.

## Jobs and networking

1. Save your LinkedIn credentials in **Email campaign** first.
2. Open **Networking**, enter locations, target titles, related titles, and skills. Select an uploaded PDF or DOCX résumé if you want résumé-based job ranking.
3. Click **Find jobs and people**. The assistant searches recent LinkedIn jobs and hiring posts and suggests recruiter or hiring-manager queries.
4. Review and edit each connection note before clicking **Send reviewed invitation**. A note is required and has a 200-character limit. LinkedIn may require verification or restrict invitations; finish those steps in the browser when prompted.
5. Use **Close browser** when finished. Networking and email extraction have separate browser controls.

## Local data and privacy

The app stores credentials in `linkedin_credentials.json` and form data in `user_config.json` on this computer. Passwords are stored as plain text in the local credentials file; protect your computer account and keep the dashboard bound to localhost. Résumés, logs, sent-email history, invitation history, and exports can contain personal or third-party data. They are ignored by Git, and existing tracked copies have been removed from this release's index. The dashboard also keeps some form progress in browser storage.

Before sharing a screenshot, ZIP export, or issue report, inspect it for personal data. Do not commit any local JSON, CSV, log, résumé, or browser profile files.

## Development

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

The automated tests use mocks and do not sign in to LinkedIn or send email. Browser automation depends on LinkedIn's current interface and can need maintenance.

## Publishing this repository safely

**The existing GitHub repository is already public and its history contains credentials, personal data, résumés, sent-email records, and logs. A new commit removing those files does not remove them from old commits or the existing remote.** Before sharing a new release:

1. Rotate the LinkedIn password, Gmail app password, and any other secrets that appeared in older commits. Check all branches and tags. Treat those secrets as exposed.
2. Publish the cleaned working tree in a **new repository with fresh history**. Do not reuse the old `.git` directory or push this branch's old history. Copy only the source, documentation, tests, assets, `LICENSE`, and `.gitignore` into the new repository. Inspect `git status` and `git ls-files` before the first push. From the new local repository, create an empty GitHub repository and run `git remote add origin https://github.com/YOUR_NAME/NEW_REPOSITORY.git` followed by `git push -u origin main`.
3. Keep the old repository private, or remove it after coordinating with anyone who uses it. GitHub history rewriting and force pushing are separate actions that need coordination with collaborators; old clones and forks can retain the data.

See [SECURITY.md](SECURITY.md) for reporting security issues.

## License

GNU Affero General Public License v3.0; see [LICENSE](LICENSE). The repository's earlier setup script already declared AGPL. LinkedIn and Chrome names and marks belong to their respective owners.

Earlier versions of this repository were based on [GodsScion/Auto_job_applier_linkedIn](https://github.com/GodsScion/Auto_job_applier_linkedIn). Its MIT license notice is preserved in [THIRD_PARTY_LICENSES/GodsScion-MIT.txt](THIRD_PARTY_LICENSES/GodsScion-MIT.txt).
