"""Executable policy for the small Python filtering demonstration.

This deliberately supports a small pure expression grammar, not arbitrary Python.
No model-supplied code is executed until it passes this validator.
"""
from __future__ import annotations

import ast
import difflib
import hashlib
from pathlib import Path


class BoundaryError(ValueError):
    pass


def validate_demo_code(source: str) -> None:
    if not isinstance(source, str):
        raise BoundaryError('Source must be text')
    if len(source.encode('utf-8')) > 16384:
        raise BoundaryError('Edit exceeds 16 KiB')
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise BoundaryError('Invalid Python syntax') from exc
    body = list(tree.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body.pop(0)
    if len(body) != 1 or not isinstance(body[0], ast.FunctionDef):
        raise BoundaryError('Only visible_items function and a docstring are allowed')
    fn = body[0]
    if fn.name != 'visible_items' or fn.decorator_list or fn.returns or fn.type_comment:
        raise BoundaryError('Unsupported function declaration')
    if getattr(fn, 'type_params', []):
        raise BoundaryError('Generic functions are not allowed')
    args = fn.args
    if ([a.arg for a in args.args] != ['items', 'query'] or args.posonlyargs or args.kwonlyargs
            or args.vararg or args.kwarg or args.defaults or args.kw_defaults
            or any(a.annotation for a in args.args)):
        raise BoundaryError('Expected visible_items(items, query)')
    statements = list(fn.body)
    if statements and isinstance(statements[0], ast.Expr) and isinstance(statements[0].value, ast.Constant) and isinstance(statements[0].value.value, str):
        statements.pop(0)
    if len(statements) != 1 or not isinstance(statements[0], ast.Return):
        raise BoundaryError('Function must contain one return expression')
    expr = statements[0].value
    allowed = (ast.ListComp, ast.comprehension, ast.Name, ast.Load, ast.Store,
               ast.Compare, ast.In, ast.NotIn, ast.Eq, ast.NotEq, ast.Call,
               ast.Attribute, ast.Constant, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not)
    nodes = list(ast.walk(expr))
    if len(nodes) > 100:
        raise BoundaryError('Expression too large')
    for node in nodes:
        if not isinstance(node, allowed):
            raise BoundaryError(f'Unsupported expression: {type(node).__name__}')
        if isinstance(node, ast.Name) and node.id not in {'items', 'query', 'item'}:
            raise BoundaryError('Unknown variable')
        if isinstance(node, ast.Attribute) and node.attr not in {'lower', 'casefold', 'strip'}:
            raise BoundaryError('Only string normalization methods are allowed')
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Attribute) or node.args or node.keywords):
            raise BoundaryError('Only zero-argument string normalization calls are allowed')
        if isinstance(node, ast.Constant) and not isinstance(node.value, (str, bool, type(None))):
            raise BoundaryError('Unsupported constant')
        if isinstance(node, ast.comprehension) and (node.is_async or not isinstance(node.target, ast.Name)
                or node.target.id != 'item' or not isinstance(node.iter, ast.Name) or node.iter.id != 'items'):
            raise BoundaryError('Only iteration over supplied items is allowed')
    if not isinstance(expr, ast.ListComp) or len(expr.generators) != 1:
        raise BoundaryError('Expected a single filtering list comprehension')


class WorkspaceBoundary:
    def __init__(self, workspace: Path, editable_files=('app.py',)):
        self.root = Path(workspace).resolve(strict=True)
        self.editable = frozenset(editable_files)
        self.original = {name: self.read(name) for name in self.editable}

    def path(self, name: str) -> Path:
        if not isinstance(name, str) or '\x00' in name or ':' in name or '\\' in name:
            raise BoundaryError('Invalid relative path')
        candidate = self.root / name
        if '..' in Path(name).parts or Path(name).is_absolute():
            raise BoundaryError('Invalid relative path')
        resolved = candidate.resolve(strict=True)
        if not resolved.is_relative_to(self.root) or not resolved.is_file():
            raise BoundaryError('Path outside workspace')
        # Reject every symlink/junction component, even if it points inside.
        current = candidate
        while current != self.root:
            if current.is_symlink() or (hasattr(current, 'is_junction') and current.is_junction()):
                raise BoundaryError('Linked paths are forbidden')
            current = current.parent
        if resolved.stat().st_nlink != 1:
            raise BoundaryError('Hard-linked files are forbidden')
        return resolved

    def read(self, name: str) -> str:
        path = self.path(name)
        if path.stat().st_size > 65536:
            raise BoundaryError('File exceeds read budget')
        return path.read_text(encoding='utf-8')

    def files(self) -> list[str]:
        # Dedicated fixture only. No traversal into metadata, secrets or other files.
        return sorted(self.editable)

    def replace(self, name: str, content: str, expected_sha256: str) -> dict:
        if name not in self.editable or name != 'app.py':
            raise BoundaryError('File is outside approved edit scope')
        before = self.read(name)
        if hashlib.sha256(before.encode()).hexdigest() != expected_sha256:
            raise BoundaryError('File changed since inspection')
        validate_demo_code(content)
        self.path(name).write_text(content, encoding='utf-8')
        return {'path': name, 'changed': before != content, 'bytes': len(content.encode()), 'sha256': hashlib.sha256(content.encode()).hexdigest()}

    def diff(self) -> str:
        return '\n'.join(''.join(difflib.unified_diff(before.splitlines(True), self.read(name).splitlines(True), fromfile=name, tofile=name)) for name, before in self.original.items())

    def validate_current(self):
        validate_demo_code(self.read('app.py'))
