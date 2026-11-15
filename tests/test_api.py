"""The signature must match api/v1/lib/ApiAuth.php byte for byte."""

import importlib
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "windrose"

# Load api.py without importing the package __init__ (which needs Home Assistant).
pkg = types.ModuleType("windrose_pkg")
pkg.__path__ = [str(ROOT)]
sys.modules["windrose_pkg"] = pkg
api = importlib.import_module("windrose_pkg.api")


def test_signature_sorts_query_like_the_server():
    # Expected values come from PHP: hash_hmac('sha256', "GET\n/api/v1/current/5\na=1&b=2\n1700000000", 'secretvalue')
    sig = api.sign("GET", "/api/v1/current/5", {"b": 2, "a": 1}, 1700000000, "secretvalue")
    assert sig == "485af902899479ddc6e013b3222a449e48f83e84470d6a4930919308d33669dd"


def test_signature_without_query():
    sig = api.sign("POST", "/api/v1/tools/forecast", None, 1700000000, "secretvalue")
    assert sig == "3886f9e51e3b5a8e7e55a680d36ed7850a62f2bf2ef0710074cd67f0785e8d15"
