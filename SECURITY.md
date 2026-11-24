# Security

Report security issues privately through GitHub's **Report a vulnerability** feature for this repository. Please do not put credentials, résumés, logs, or other personal data in a public issue.

This application is designed for local use on `127.0.0.1`. It has no user authentication, and it stores LinkedIn and SMTP credentials in a local plain-text JSON file. Do not expose its port to other computers or host it publicly without adding appropriate access controls and secret storage.

If you have cloned or used an older version of this repository, rotate any credentials that were committed or shared. Deleting a tracked file in a new commit does not erase older Git objects, forks, or clones.
