# Dependency notices

The application source is licensed under the GNU AGPL-3.0-only from 1.2.0 (1.0.0 and 1.1.0
remain MIT); see `LICENSE` and `NOTICE`. Dependency packages keep their own licences and are
not relicensed by this application. Locked distributions carry their upstream licence files;
`licenses/` holds a copy of Pydantic's. This source package does not bundle a virtual
environment.

The CLI and plugin need only Pydantic and its dependencies at run time. The packages below are
every runtime package of the default install; build and test tools are not shipped. The unused
FastAPI/Uvicorn `api` extra and the React page were removed in 2.5.0.

| Package | Version | Licence | Source |
| --- | --- | --- | --- |
| Pydantic | 2.14.1 | MIT | https://github.com/pydantic/pydantic |
| pydantic-core | 2.50.1 | MIT | https://github.com/pydantic/pydantic-core |
| annotated-types | 0.8.0 | MIT | https://github.com/annotated-types/annotated-types |
| typing-extensions | 4.16.0 | PSF-2.0 | https://github.com/python/typing_extensions |
| typing-inspection | 0.4.4 | MIT | https://github.com/pydantic/typing-inspection |

## Optional `semantic` extra

Installed only on request (`eu-compliance-guard[semantic]`); the default install has none of it.
It adds [fastembed](https://github.com/qdrant/fastembed) 0.9.1 (Apache-2.0) and what fastembed
needs, all under permissive licences: ONNX Runtime (MIT), NumPy (BSD-3-Clause and others),
tokenizers, huggingface-hub, hf-xet, requests, packaging and flatbuffers (Apache-2.0), protobuf,
click, fsspec, httpx, httpcore and idna (BSD), anyio, filelock, h11, loguru, mmh3, pyyaml, urllib3,
charset-normalizer, py-rust-stemmers and pillow (MIT or MIT-style), and certifi and tqdm
(MPL-2.0). Exact versions and hashes are in `uv.lock`.

The model it downloads on `semantic setup` is not shipped with this package:
[BAAI/bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5) (MIT), in the ONNX build
`Qdrant/bge-small-en-v1.5-onnx-Q`, pinned by SHA-256 in `eu_compliance_guard/semantic.py`.

The official law texts in `fixtures/official/` are test data with their own attribution in
that folder's README (EUR-Lex reuse under Commission Decision 2011/833/EU; legislation.gov.uk
under the Open Government Licence v3.0). This table is a dependency inventory, not a legal
review of a release.
