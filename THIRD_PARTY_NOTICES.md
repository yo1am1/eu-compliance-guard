# Dependency notices

The application source uses the repository's MIT license. Dependency packages retain their own licenses; they are not relicensed by this application. Locked distributions retain their upstream license files. This source package does not bundle the virtual environment or node_modules.

Direct runtime dependencies selected on 2026-10-15:

| Dependency | Version | License | Source |
| --- | --- | --- | --- |
| FastAPI | 0.143.1 | MIT | https://github.com/fastapi/fastapi |
| Pydantic | 2.14.1 | MIT | https://github.com/pydantic/pydantic |
| Uvicorn | 0.54.0 | BSD-3-Clause | https://github.com/Kludex/uvicorn |
| React / React DOM | 19.3.1 | MIT | https://github.com/facebook/react |

Build/test tools and their transitive dependencies remain recorded in uv.lock and frontend/package-lock.json. Bundled browser assets, scanner rules, Graphify and release distributions require their own actual-content license inventory before release; this table is not that release acceptance.
