import asyncio
import json
from pathlib import Path

import dotenv
from anthropic import AsyncAnthropic

MODEL = "claude-sonnet-5"

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
dotenv.load_dotenv(ENV_PATH)
ANTHROPIC_API_KEY = dotenv.get_key(ENV_PATH, "ANTHROPIC_KEY")

COORDINATOR_SYSTEM = (
    "You are a coordinator agent. You do not perform concrete, self-contained "
    "tasks yourself -- delegate them to a subagent using the delegate_task "
    "tool, then relay its result back to the user. Only respond directly for "
    "clarifying questions."
)

SUBAGENT_SYSTEM = (
    "You are a focused subagent. Complete exactly the task you are given and "
    "return only the result -- no preamble, no follow-up questions."
)


def print_json(label: str, data) -> None:
    """Pretty-print a plain value or an Anthropic SDK object (pydantic model) as JSON."""

    def default(o):
        if hasattr(o, "model_dump"):
            return o.model_dump(mode="json")
        return str(o)

    print(f"\n--- {label} ---")
    print(json.dumps(data, indent=2, default=default))


async def run_subagent(client: AsyncAnthropic, task: str) -> str:
    """The subagent: a brand new, isolated conversation with its own client
    call. It has no memory of the coordinator's conversation -- only the
    single task string it was handed. That isolation (a fresh messages list,
    a narrow system prompt) is what makes it a subagent rather than just a
    continuation of the coordinator's own context.
    """
    print(f"\n>>> Subagent starting task: {task!r}")

    response = await client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SUBAGENT_SYSTEM,
        messages=[{"role": "user", "content": task}],
    )

    result_text = next(block.text for block in response.content if block.type == "text")
    print(f"<<< Subagent finished: {result_text!r}")
    return result_text


async def main() -> None:

    # Step 0: create a client for the coordinator. It will be used for all
    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    # here we define a tool that the coordinator can use to delegate a task to a subagent. 
    # αρα εδω κοιτάζει ο coordinator αν η δουλεια που του ζητηθηκε ειναι concrete και self-contained task και αν ναι τοτε το δινει στον subagent να το κανει.
    tools = [
        {
            "name": "delegate_task",
            "description": (
                "Delegate a self-contained task to a subagent worker. Use this"
                "for any concrete piece of work -- writing, summarizing, "
                "research -- rather than doing it yourself."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "A clear, self-contained description of the task for the subagent to complete.",
                    },
                },
                "required": ["task"],
            },
        }
    ]

    # Step 1: the user's request to the coordinator.
    messages = [
        {"role": "user", "content": "Write a haiku about the ocean."},
    ]
    print_json("Step 1: user request to the coordinator", messages)

    # Step 2: the coordinator decides whether to delegate. Its system prompt
    # tells it to hand off concrete tasks rather than doing them itself.
    response = await client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=COORDINATOR_SYSTEM,
        messages=messages,
        tools=tools,
    )
    print_json("Step 2: coordinator's response", response.content)

    for block in response.content:
        if block.type == "text":
            print("\nCoordinator's text response:", block.text)
        if block.type == "tool_use":
            print_json(f"Coordinator's tool call: {block.name}", block.input)
    tool_use_blocks = [block for block in response.content if block.type == "tool_use"]

    if tool_use_blocks:
        # Step 3: the coordinator asked to delegate -- keep its request in
        # history before replying to it, same as any other tool call.
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in tool_use_blocks:
            if block.name == "delegate_task":
                # Step 4: the actual hand-off -- a brand new, isolated API
                # call the coordinator has no visibility into except for
                # whatever text comes back from it.
                result_text = await run_subagent(client, **block.input)
            else:
                result_text = f"Unknown tool: {block.name}"

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result_text,
            })

        # Step 5: report the subagent's result back to the coordinator.
        messages.append({"role": "user", "content": tool_results})
        print_json("Step 5: messages sent back to the coordinator", messages)

        # Step 6: the coordinator sees the subagent's result and produces the
        # final answer for the user.
        response = await client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=COORDINATOR_SYSTEM,
            messages=messages,
            tools=tools,
        )
        print_json("Step 6: coordinator's final response", response.content)

    for block in response.content:
        if block.type == "text":
            print("\nFinal answer to user:", block.text)


if __name__ == "__main__":
    asyncio.run(main())
