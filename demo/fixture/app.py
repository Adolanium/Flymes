"""Intentionally faulty demo fixture. Search is supposed to ignore letter case."""


def visible_items(items, query):
    return [item for item in items if query in item]
