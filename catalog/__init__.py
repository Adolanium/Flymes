"""Hermes plugin entry point. The scientific runtime stays in the companion."""
from .plugin_init import register as register_native
from .plugin_worker import register as register_worker


def register(ctx):
    register_native(ctx)
    register_worker(ctx)
