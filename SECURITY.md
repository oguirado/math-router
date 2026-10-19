# Security policy

Report vulnerabilities, leaked credentials or private data found in this repository privately, using the e-mail address in `Contact.md`. Please do not open a public issue for them. Expect an acknowledgement within a few days.

The router is an offline, standard-library Python program with no network access; the main risks are private data or credentials in committed files. Committed files, including `papers/`, are scanned in CI with gitleaks (`.gitleaks.toml` allowlists only the public sha256 hashes and paper coordinates) and by `tools/publication_lint.py`.

A credential that was committed is considered compromised: it is rotated or revoked first. Removing it in a new commit does not remove it from the Git history, so where history is public the maintainers may also rewrite it (a force-push after a coordinated notice); anyone holding a clone should then re-clone.
