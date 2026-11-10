"""Cheap structural rules that keep the package easy to read: checked by parsing, nothing is run."""
import ast
from pathlib import Path
import unittest

PACKAGE = Path(__file__).resolve().parents[1] / "eu_compliance_guard"


class HygieneTests(unittest.TestCase):
    def test_no_module_imports_a_name_it_never_uses(self):
        unused = []
        for path in sorted(PACKAGE.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imported = {}
            for node in tree.body:
                if isinstance(node, ast.Import):
                    imported.update({(alias.asname or alias.name).split(".")[0]: node.lineno for alias in node.names})
                elif isinstance(node, ast.ImportFrom) and node.module != "__future__":
                    imported.update({alias.asname or alias.name: node.lineno for alias in node.names})
            used = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
            unused += [f"{path.name}:{line} {name}" for name, line in imported.items()
                       if name not in used and path.name != "__init__.py"]
        self.assertEqual(unused, [])

    def test_tool_errors_share_one_class(self):
        """A new error type subclasses errors.CodedError instead of repeating its three lines."""
        repeated = []
        for path in sorted(PACKAGE.glob("*.py")):
            for node in ast.parse(path.read_text(encoding="utf-8")).body:
                if isinstance(node, ast.ClassDef) and path.name != "errors.py" and any(
                        isinstance(item, ast.FunctionDef) and item.name == "__init__"
                        and [arg.arg for arg in item.args.args] == ["self", "code"] and len(item.body) == 2
                        for item in node.body):
                    repeated.append(f"{path.name}:{node.name}")
        # NoRun is a LookupError on purpose ("no run yet" is not bad input); the other two map any
        # unregistered code to a safe default, which CodedError does not.
        self.assertEqual(repeated, ["nextstep.py:NoRun", "revalidation.py:RevalidationError", "sources.py:RetrievalFailure"])

    def test_the_cli_reports_failures_in_one_place(self):
        tree = ast.parse((PACKAGE / "__main__.py").read_text(encoding="utf-8"))
        broad = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler)
                 and isinstance(node.type, ast.Name) and node.type.id == "Exception"]
        self.assertLessEqual(len(broad), 2)  # _try, and opening a browser


if __name__ == "__main__":
    unittest.main()
