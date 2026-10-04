"""Avvio automatico del web server Remote Control (generato da unreal-mcp)."""

import unreal

try:
    unreal.SystemLibrary.execute_console_command(None, "WebControl.StartServer")
    unreal.log("[unreal-mcp] Remote Control web server avviato sulla porta 30010.")
except Exception as exc:  # noqa: BLE001
    unreal.log_error("[unreal-mcp] Avvio web server fallito: %s" % exc)
