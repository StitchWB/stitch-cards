"""RPC entry point for the stitch-cards service plugin.

Spawned by ``ServicePluginHost`` as ``python -m stitch_cards``.
Implements the JSON-RPC 2.0 line protocol via ``RpcPluginServer``
(imported from ``autoreg.plugin.rpc`` when available, otherwise from
the vendored ``_vendor/rpc_server.py`` copy).

Protocol methods handled by ``RpcPluginServer``:
  - ``plugin.init``    → stores handshake params (db_path, data_dir).
  - ``plugin.call``    → dispatches to command handlers.
  - ``plugin.ping``    → returns ``"pong"``.
  - ``plugin.shutdown`` → returns ``None`` and exits.

Commands mirror the built-in card command names (identity mapping — no
prefix to strip) so the dual-format proxy can route to them when the
plugin is installed and healthy.
"""

# _generated_by: stitch_plugin_tools scaffold v3

from __future__ import annotations

from typing import Any

from . import service

try:
    from autoreg.plugin.rpc import RpcPluginServer
except ImportError:
    from ._vendor.rpc_server import RpcPluginServer


# ── State received in plugin.init handshake ───────────────────────────────


class _Ctx:
    """Mutable container for plugin.init handshake state."""

    db_path: str = ""
    data_dir: str = ""


ctx = _Ctx()


def _handle_init(params: dict[str, Any]) -> dict[str, Any]:
    """Store handshake params and return them as the init result."""
    ctx.db_path = str(params.get("db_path", ""))
    ctx.data_dir = str(params.get("data_dir", ""))
    return {
        "plugin_id": params.get("plugin_id", ""),
        "db_path": ctx.db_path,
        "data_dir": ctx.data_dir,
        # Capability negotiation: no reverse-RPC used.  Declared
        # explicitly for contract uniformity.
        "capabilities": [],
    }


def _handle_migrate_db(params: dict[str, Any]) -> dict[str, Any]:
    """No-op migration (storage.sqlite=false). Returns version ack."""
    return {
        "from_version": params.get("from_version", 0),
        "to_version": params.get("to_version", 1),
    }


# ── Mirrored card commands ──────────────────────────────────────────────────


def _handle_generate_cards(params: dict[str, Any]) -> dict[str, Any] | list[dict[str, Any]]:
    """Generate cards with valid Luhn check digits (mirrors generate_cards)."""
    req = params.get("req", params)
    bin_str = req.get("bin", "")
    quantity = int(req.get("quantity", 1))
    month = req.get("month")
    year = req.get("year")
    try:
        return service.generate_cards(bin_str, quantity, month, year)
    except ValueError as exc:
        return {"success": False, "error": str(exc)}


def _handle_check_card_rust(params: dict[str, Any]) -> dict[str, Any]:
    """Check a card via BIN lookup API (mirrors check_card_rust)."""
    card_data = params.get("cardData", params.get("card_data", ""))
    return service.check_card(card_data, proxy=params.get("proxy"))


def _handle_find_live_card(params: dict[str, Any]) -> dict[str, Any] | None:
    """Generate and check cards until a live one is found (mirrors find_live_card)."""
    bin_str = params.get("bin", "")
    max_attempts = int(params.get("maxAttempts", params.get("max_attempts", 50)))
    month = params.get("month")
    year = params.get("year")
    try:
        return service.find_live_card(
            bin_str, max_attempts, month, year, proxy=params.get("proxy")
        )
    except ValueError as exc:
        return {"success": False, "error": str(exc)}


# ── Server entry point ────────────────────────────────────────────────────


def main() -> None:
    """Register handlers and serve the JSON-RPC loop."""
    server = RpcPluginServer()
    server.set_init_handler(_handle_init)
    server.register("_migrate_db", _handle_migrate_db)
    server.register("generate_cards", _handle_generate_cards)
    server.register("check_card_rust", _handle_check_card_rust)
    server.register("find_live_card", _handle_find_live_card)
    server.serve()


if __name__ == "__main__":
    main()
