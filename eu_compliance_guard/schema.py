"""Export the one Python contract for generated frontend types and drift checks."""

import argparse
import json
from pathlib import Path

from pydantic.json_schema import models_json_schema
from . import models

SCHEMA_PATH = Path(__file__).resolve().parent / "contract.schema.json"


def contract_schema() -> dict:
    records = [value for value in vars(models).values()
               if isinstance(value, type) and issubclass(value, models.Record)
               and value is not models.Record]
    _, definitions = models_json_schema([(record, "validation") for record in records])
    command = models.COMMAND_ADAPTER.json_schema()
    for name, definition in command.pop("$defs", {}).items():
        if name in definitions["$defs"] and definitions["$defs"][name] != definition:
            raise ValueError("inconsistent generated contract definition")
        definitions["$defs"][name] = definition
    return {"$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Command", **command, **definitions}


def schema_bytes() -> bytes:
    return (json.dumps(contract_schema(), sort_keys=True, indent=2,
                       ensure_ascii=False) + "\n").encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = schema_bytes()
    if args.check:
        if not SCHEMA_PATH.is_file() or SCHEMA_PATH.read_bytes() != content:
            raise SystemExit("Shared contract schema is out of date")
        print("Shared contract schema is in sync")
    else:
        SCHEMA_PATH.write_bytes(content)
        print("Exported shared contract schema")


if __name__ == "__main__":
    main()
