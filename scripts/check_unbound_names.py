"""Report names a Python file uses but never binds — missing imports, mostly.

Written for the app.py split (see CATALOG.md §"Tách một khối route khỏi
app.py"). Moving a block of code into a new module quietly drops whatever it
relied on from the old file's imports, and the gap only surfaces when the one
line that needs it actually runs. During the reports extraction a missing
``ROOT`` sat on a single line out of 883 and got through to the test suite; the
import extraction that followed was checked with this script first, which
caught a missing ``field_validator`` and ``access_logger`` before any test ran.

This is a static check, so it cannot see names created at runtime (``globals()``
tricks, star imports, conditional definitions). Treat a clean result as "no
obvious gap", not proof — the test suite is still the real gate. It is
deliberately not wired into CI: the false-negative risk above means a failing
run here is worth a look, but a passing one guarantees nothing.

Usage:
    python scripts/check_unbound_names.py backend/reports_api.py
    python scripts/check_unbound_names.py backend/*.py

Exit code is 1 when anything looks unbound, so it chains with && in a shell.
"""
from __future__ import annotations

import argparse
import ast
import builtins
import glob
import sys
from pathlib import Path

# Bound by the interpreter rather than by any statement we can see in the tree.
IMPLICIT_MODULE_GLOBALS = frozenset({
    "__file__", "__name__", "__doc__", "__package__", "__spec__", "__loader__",
    "__builtins__", "__debug__",
})


def _bound_names(tree: ast.AST) -> set[str]:
    """Every name the module binds: imports, defs, assignments, loop targets."""
    bound: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bound.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, ast.ClassDef):
            bound.add(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            bound.add(node.name)
            args = node.args
            for arg in args.posonlyargs + args.args + args.kwonlyargs:
                bound.add(arg.arg)
            if args.vararg:
                bound.add(args.vararg.arg)
            if args.kwarg:
                bound.add(args.kwarg.arg)
        elif isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.For,
                               ast.AsyncFor, ast.comprehension, ast.withitem,
                               ast.NamedExpr, ast.ExceptHandler)):
            for inner in ast.walk(node):
                if isinstance(inner, ast.Name) and isinstance(inner.ctx, ast.Store):
                    bound.add(inner.id)
            if isinstance(node, ast.ExceptHandler) and node.name:
                bound.add(node.name)
        elif isinstance(node, ast.Global):
            bound.update(node.names)
    return bound


def _loaded_names(tree: ast.AST) -> set[str]:
    """Every name the module reads, including the root of attribute chains."""
    used = {
        node.id for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            root = node
            while isinstance(root, ast.Attribute):
                root = root.value
            if isinstance(root, ast.Name):
                used.add(root.id)
    return used


def unbound_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    missing = _loaded_names(tree) - _bound_names(tree) - IMPLICIT_MODULE_GLOBALS
    return sorted(name for name in missing if not hasattr(builtins, name))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()

    failed = False
    paths: list[Path] = []
    for argument in args.paths:
        if glob.has_magic(argument):
            matches = glob.glob(argument)
            if not matches:
                print(f"{argument}: NOT FOUND")
                failed = True
                continue
            paths.extend(Path(match) for match in matches)
        else:
            paths.append(Path(argument))

    for path in paths:
        if not path.is_file():
            print(f"{path}: NOT FOUND")
            failed = True
            continue
        missing = unbound_names(path)
        if missing:
            failed = True
            print(f"{path}: MISSING {', '.join(missing)}")
        else:
            print(f"{path}: OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
