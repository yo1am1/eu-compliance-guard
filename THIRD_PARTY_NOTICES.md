# Dependency notices

The application source is licensed under the GNU AGPL-3.0-only from 1.2.0 (1.0.0 and 1.1.0
remain MIT); see `LICENSE` and `NOTICE`. Dependency packages keep their own licences and are
not relicensed by this application. Locked distributions carry their upstream licence files;
`licenses/` holds a copy of Pydantic's. This source package does not bundle a virtual
environment.

The CLI and plugin need only Pydantic and its dependencies at run time. The packages below are
every runtime package in `uv.lock` (2.5.1); build and test tools are not shipped. The unused
FastAPI/Uvicorn `api` extra and the React page were removed in 2.5.0.

| Package | Version | Licence | Source |
| --- | --- | --- | --- |
| Pydantic | 2.14.1 | MIT | https://github.com/pydantic/pydantic |
| pydantic-core | 2.50.1 | MIT | https://github.com/pydantic/pydantic-core |
| annotated-types | 0.8.0 | MIT | https://github.com/annotated-types/annotated-types |
| typing-extensions | 4.16.0 | PSF-2.0 | https://github.com/python/typing_extensions |
| typing-inspection | 0.4.4 | MIT | https://github.com/pydantic/typing-inspection |

The official law texts in `fixtures/official/` are test data with their own attribution in
that folder's README (EUR-Lex reuse under Commission Decision 2011/833/EU; legislation.gov.uk
under the Open Government Licence v3.0). This table is a dependency inventory, not a legal
review of a release.
