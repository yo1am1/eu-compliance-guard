# Security policy

## Supported versions

Only the latest release receives fixes. Upgrade with `/plugin update eu-compliance-guard`
or by installing the latest tag.

## Reporting a vulnerability

Please report vulnerabilities privately through
[GitHub private vulnerability reporting](https://github.com/yo1am1/eu-compliance-guard/security/advisories/new),
not in a public issue. Include the version, the command or plugin action involved, and
a minimal synthetic reproduction. Never include real audit evidence or personal data.

You can expect an acknowledgement within a week. Fixes are released under a new version
and credited in the changelog unless you prefer otherwise.

## Scope

In scope: the CLI, the Claude Code plugin (skills, hooks, band and panel), the MCP server,
the generated report and dashboard pages, and the GitHub Action example. Examples:

- reading or writing outside the declared project or private run folder, including
  through symbolic links;
- a report, dashboard or panel that executes or loads anything from untrusted input;
- network access without consent, or to a host outside the official registry;
- a signature, lockfile or digest check that can be bypassed;
- untrusted imported content treated as instructions.

Out of scope: the legal correctness of any output. The tool never gives legal advice or
a compliance verdict, and a named reviewer decides.
