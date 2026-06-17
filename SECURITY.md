# Security Policy

Milcah is an early local-first research prototype. Treat it as unsuitable for
untrusted network exposure until authentication, authorization, and data-handling
boundaries are explicitly designed and tested.

## Reporting a vulnerability

**Please do not open a public issue for security problems.**

Report privately via GitHub's
[private vulnerability reporting](https://github.com/gellsmore-svg/Milcah/security/advisories/new)
("Report a vulnerability" under the repository's **Security** tab).

Milcah orchestrates LLM calls and may take API keys / connection strings for its
siblings (Hoglah, Tirzah, Mahalath). Keep those in local config and scrub them
from any logs before sharing.
