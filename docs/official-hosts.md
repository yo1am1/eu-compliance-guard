# Official host registry

`--fetch-official` retrieves law text only from the exact hosts below, registered per
jurisdiction in `eu_compliance_guard/jurisdictions.py`. Each EU host is an institution site
under `europa.eu`, the EU institutions' own domain; the UK host is legislation.gov.uk, run by
The National Archives. A test keeps this table and the code in step and checks each host sits
under its jurisdiction's official domain: adding a host means adding a row here, with its
operator and purpose.

Official hosting shows where a text came from. It does not establish that the text is
binding, complete, applicable or current; reviewers decide that.

| Host | Operator | Purpose |
|---|---|---|
| `eur-lex.europa.eu` | Publications Office of the EU | EUR-Lex, official access to EU law and consolidated texts |
| `publications.europa.eu` | Publications Office of the EU | Cellar repository, which serves act content by CELEX number, and its SPARQL endpoint (`/webapi/rdf/sparql`), which lists an act's consolidated versions |
| `curia.europa.eu` | Court of Justice of the EU | Case law |
| `commission.europa.eu` | European Commission | Commission policy pages and guidance |
| `digital-strategy.ec.europa.eu` | European Commission (DG CONNECT) | Digital policy and guidance (AI Act, Data Act, DSA) |
| `www.edpb.europa.eu` | European Data Protection Board | GDPR guidelines and opinions |
| `www.legislation.gov.uk` | The National Archives (UK) | UK legislation: Acts, statutory instruments and assimilated EU law such as the UK GDPR, as enacted, revised, or on a date |

## Reachability

`make verify-hosts` sends one HTTPS request to each host. It needs explicit consent and
never runs in the tests. A host that fails is recorded here as a review gap, and the tool
never falls back to another site.

Last check: 2026-11-05, through this project's cloud environment.

| Host | Result |
|---|---|
| `commission.europa.eu` | HTTP 200 |
| `curia.europa.eu` | HTTP 403. The site answers over TLS but refuses automated clients at the root; retrieval may need a manually downloaded copy. |
| `digital-strategy.ec.europa.eu` | HTTP 200 |
| `eur-lex.europa.eu` | HTTP 202. This is a bot challenge, not the page. `admit_source_content` already refuses challenge pages, so act text should come from `publications.europa.eu` (Cellar) with a consolidated CELEX number. |
| `publications.europa.eu` | HTTP 200 |
| `www.edpb.europa.eu` | HTTP 200 |
| `www.legislation.gov.uk` | HTTP 200 (checked 2026-11-06). `data.xht` returns the XHTML of a whole act. `ico.org.uk` (the UK regulator) answered HTTP 403 to automated clients and is not registered. |
