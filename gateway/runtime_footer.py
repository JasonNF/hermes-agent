"""Gateway runtime-metadata footer.

Renders a compact footer showing runtime state (model, context %, cwd) and
appends it to the FINAL message of an agent turn when enabled. Off by default
to keep replies minimal.

Config (``~/.hermes/config.yaml``)::

    display:
      runtime_footer:
        enabled: true                       # off by default
        fields: [model, context_pct, cwd]   # order shown; drop any to hide
        style: plain                        # "plain" (default) or "labeled_quote"

Available fields:
    model             — bare model id, vendor prefix dropped (``gpt-5.4``)
    context_pct       — last-call context occupancy as a percent (``5%``)
    latency           — wall-clock duration of the turn (``22s``, ``1m05s``)
    elapsed_s         — elapsed seconds with one decimal (``22.4s``)
    reasoning_effort  — configured reasoning effort (``high``)
    cwd               — home-relative working dir (``~``)

``latency`` and ``elapsed_s`` are opt-in: neither is in the default field set,
so a footer whose ``fields`` are unset renders exactly as before. Use
``latency`` for the upstream compact duration format; ``elapsed_s`` remains
available for the local labeled Telegram quote configuration.

When ``style: labeled_quote`` is set, each supported field is emoji-prefixed
and the whole line is wrapped in a block quote (``> ...``), giving a compact,
scannable Telegram footer.

Per-platform overrides live under
``display.platforms.<platform>.runtime_footer``. Users can toggle the global
setting with ``/footer on|off`` from both the CLI and any gateway platform.
"""

from __future__ import annotations

import os
from typing import Any, Iterable, Optional

_DEFAULT_FIELDS: tuple[str, ...] = ("model", "context_pct", "cwd")
_SEP = " · "


def _home_relative_cwd(cwd: str) -> str:
    """Return *cwd* with ``$HOME`` collapsed to ``~``. Empty string if unset."""
    if not cwd:
        return ""
    try:
        home = os.path.expanduser("~")
        path = os.path.abspath(cwd)
        if home and (path == home or path.startswith(home + os.sep)):
            return "~" + path[len(home):]
        return path
    except Exception:
        return cwd


def _model_short(model: Optional[str]) -> str:
    """Drop ``vendor/`` prefix for readability (``openai/gpt-5.4`` → ``gpt-5.4``)."""
    if not model:
        return ""
    return model.rsplit("/", 1)[-1]


def resolve_footer_config(
    user_config: dict[str, Any] | None,
    platform_key: str | None = None,
) -> dict[str, Any]:
    """Resolve effective runtime-footer config for *platform_key*.

    Merge order (later wins):
        1. Built-in defaults (enabled=False)
        2. ``display.runtime_footer``
        3. ``display.platforms.<platform_key>.runtime_footer``
    """
    resolved = {"enabled": False, "fields": list(_DEFAULT_FIELDS), "style": "plain"}
    display_config = (user_config or {}).get("display") or {}

    global_config = display_config.get("runtime_footer")
    if isinstance(global_config, dict):
        if "enabled" in global_config:
            resolved["enabled"] = bool(global_config.get("enabled"))
        if isinstance(global_config.get("fields"), list) and global_config["fields"]:
            resolved["fields"] = [str(field) for field in global_config["fields"]]
        if isinstance(global_config.get("style"), str) and global_config["style"]:
            resolved["style"] = str(global_config["style"])

    if platform_key:
        platforms = display_config.get("platforms") or {}
        platform_config = platforms.get(platform_key)
        if isinstance(platform_config, dict):
            platform_footer = platform_config.get("runtime_footer")
            if isinstance(platform_footer, dict):
                if "enabled" in platform_footer:
                    resolved["enabled"] = bool(platform_footer.get("enabled"))
                if isinstance(platform_footer.get("fields"), list) and platform_footer["fields"]:
                    resolved["fields"] = [str(field) for field in platform_footer["fields"]]
                if isinstance(platform_footer.get("style"), str) and platform_footer["style"]:
                    resolved["style"] = str(platform_footer["style"])

    return resolved


def _format_latency(seconds: float) -> str:
    """Humanize a turn duration: ``<1s``, ``22s``, ``1m05s``."""
    if seconds < 1:
        return "<1s"
    total = int(round(seconds))
    if total < 60:
        return f"{total}s"
    minutes, seconds_remainder = divmod(total, 60)
    return f"{minutes}m{seconds_remainder:02d}s"


def format_runtime_footer(
    *,
    model: Optional[str],
    context_tokens: int,
    context_length: Optional[int],
    cwd: Optional[str] = None,
    turn_seconds: Optional[float] = None,
    fields: Iterable[str] = _DEFAULT_FIELDS,
    elapsed_s: Optional[float] = None,
    reasoning_effort: Optional[str] = None,
    style: str = "plain",
) -> str:
    """Render the footer line, or return ``""`` if no fields have data.

    Fields are skipped silently when their data is missing. With
    ``style="labeled_quote"``, each supported field has an emoji prefix and the
    completed footer is returned as one block quote.
    """
    rich_style = str(style or "plain") == "labeled_quote"
    parts: list[str] = []
    for field in fields:
        if field == "model":
            value = _model_short(model)
            if value:
                parts.append(f"🧠 {value}" if rich_style else value)
        elif field == "elapsed_s":
            if elapsed_s is not None and elapsed_s >= 0:
                value = f"{elapsed_s:.1f}s"
                parts.append(f"⏰ {value}" if rich_style else value)
        elif field == "context_pct":
            if context_length and context_length > 0 and context_tokens >= 0:
                value = f"{max(0, min(100, round((context_tokens / context_length) * 100)))}%"
                parts.append(f"🪟 {value}" if rich_style else value)
        elif field == "latency":
            if turn_seconds is not None and turn_seconds >= 0:
                value = _format_latency(turn_seconds)
                parts.append(f"⏰ {value}" if rich_style else value)
        elif field == "cwd":
            value = _home_relative_cwd(cwd or os.environ.get("TERMINAL_CWD", ""))
            if value:
                parts.append(f"📁 {value}" if rich_style else value)
        elif field == "reasoning_effort":
            value = str(reasoning_effort or "").strip().lower()
            if value:
                parts.append(f"💭 {value}" if rich_style else value)
        # Unknown field names are silently ignored.

    if not parts:
        return ""
    line = _SEP.join(parts)
    return f"> {line}" if rich_style else line


def build_footer_line(
    *,
    user_config: dict[str, Any] | None,
    platform_key: str | None,
    model: Optional[str],
    context_tokens: int,
    context_length: Optional[int],
    cwd: Optional[str] = None,
    turn_seconds: Optional[float] = None,
    elapsed_s: Optional[float] = None,
    reasoning_effort: Optional[str] = None,
) -> str:
    """Build the enabled footer from resolved config and supplied turn metadata."""
    config = resolve_footer_config(user_config, platform_key)
    if not config.get("enabled"):
        return ""
    return format_runtime_footer(
        model=model,
        context_tokens=context_tokens,
        context_length=context_length,
        cwd=cwd,
        turn_seconds=turn_seconds,
        elapsed_s=elapsed_s,
        reasoning_effort=reasoning_effort,
        fields=config.get("fields") or _DEFAULT_FIELDS,
        style=str(config.get("style") or "plain"),
    )
