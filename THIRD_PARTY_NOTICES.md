# Dependency notices

The application source uses the repository's MIT license. Dependency packages retain their own licenses; they are not relicensed by this application. Locked distributions retain their upstream license files. This source package does not bundle the virtual environment.

Direct dependencies selected on 2026-10-15. The CLI and plugin need only Pydantic at
run time. The unused FastAPI/Uvicorn `api` extra and the React page were removed in 2.5.0.

| Dependency | Version | License | Source |
| --- | --- | --- | --- |
| Pydantic | 2.14.1 | MIT | https://github.com/pydantic/pydantic |

Build/test tools and their transitive dependencies remain recorded in uv.lock. Bundled browser assets, scanner rules, Graphify and release distributions require their own actual-content license inventory before release; this table is not that release acceptance.
