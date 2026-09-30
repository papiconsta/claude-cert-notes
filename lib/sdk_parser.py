"""Formatting and logging helpers for Anthropic SDK example scripts."""

from __future__ import annotations

import json
from typing import Any

SEPARATOR = "-" * 70

# What each stop_reason means - used to annotate logged responses.
STOP_REASON_MEANINGS = {
    "end_turn": "model finished its turn naturally",
    "tool_use": "model paused to call a tool and needs a tool_result",
    "max_tokens": "response was cut off because max_tokens was reached",
    "stop_sequence": "model hit one of the provided stop_sequences",
    "pause_turn": "long-running turn paused; resume by replaying the response",
    "refusal": "model declined to generate part of the response",
}


def print_header(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def print_section(title: str) -> None:
    print(f"\n{SEPARATOR}\n{title}\n{SEPARATOR}")


def format_content_block(block: Any) -> str:
    """Render a single response content block (text / tool_use) as readable text."""
    block_type = getattr(block, "type", None)

    if block_type == "text":
        return f"[text]\n{block.text}"

    if block_type == "tool_use":
        args = json.dumps(block.input, indent=2)
        return f"[tool_use] id={block.id} name={block.name}\ninput={args}"

    return f"[{block_type}] {block}"


def log_message(message: Any, label: str = "Response") -> None:
    """Log the key fields of a Message returned by client.messages.create()."""
    print_section(label)
    print(f"id            : {message.id}")
    print(f"model         : {message.model}")
    print(f"role          : {message.role}")
    print(f"stop_reason   : {message.stop_reason}")
    print(f"stop_sequence : {message.stop_sequence}")
    print(
        f"usage         : input={message.usage.input_tokens} "
        f"output={message.usage.output_tokens}"
    )
    print("content:")
    for block in message.content:
        rendered = format_content_block(block).replace("\n", "\n  ")
        print(f"  {rendered}")


def log_stop_reason(message: Any, label: str = "") -> None:
    """Call out the stop_reason explicitly with a short explanation of what it means."""
    explanation = STOP_REASON_MEANINGS.get(message.stop_reason, "unknown stop_reason")
    prefix = f"{label} " if label else ""
    print(f"\n>>> {prefix}stop_reason = '{message.stop_reason}'  ({explanation})")


def log_messages_array(messages: list, label: str = "Conversation state") -> None:
    """Print the full messages list to show how turns/results get appended."""
    print_section(f"{label} ({len(messages)} messages)")
    for i, msg in enumerate(messages):
        role = msg["role"]
        content = msg["content"]
        if isinstance(content, str):
            preview = content
        else:
            parts = []
            for block in content:
                block_type = block["type"] if isinstance(block, dict) else getattr(block, "type", "?")
                parts.append(block_type)
            preview = f"[{', '.join(parts)}]"
        print(f"  [{i}] role={role:<9} content={preview}")