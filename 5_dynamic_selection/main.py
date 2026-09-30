import asyncio
import json
from pathlib import Path

import dotenv
from anthropic import AsyncAnthropic

MODEL = "claude-sonnet-5"  # the coordinator always uses this -- only the subagents vary

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
dotenv.load_dotenv(ENV_PATH)
ANTHROPIC_API_KEY = dotenv.get_key(ENV_PATH, "ANTHROPIC_KEY")

# One profile per kind of subtask: which model it runs on, how it's
# instructed, and which tools it gets. A "lookup" doesn't need Opus and a
# "critique" shouldn't be trusted to a model tuned for one-line answers --
# see 5_dynamic_selection/dynamic_selection for the reasoning behind this.
SUBAGENT_PROFILES = {
    "lookup": {
        "model": "claude-haiku-4-5-20251001",
        "system": (
            "You are a focused subagent. Answer the factual question "
            "directly in one or two sentences. No preamble, no hedging, no "
            "follow-up questions."
        ),
        "tools": [],
    },
    "research": {
        "model": "claude-sonnet-5",
        "system": (
            "You are a focused research subagent. Synthesize what you know "
            "into a clear, well-organized answer covering the angles the "
            "task asks for. No preamble, no follow-up questions."
        ),
        "tools": [],
    },
    "writing": {
        "model": "claude-sonnet-5",
        "system": (
            "You are a focused writing subagent. Produce polished, "
            "publication-ready prose for exactly what's asked. Return only "
            "the writing itself -- no preamble, no notes about your process."
        ),
        "tools": [],
    },
    "code": {
        "model": "claude-sonnet-5",
        "system": (
            "You are a focused coding subagent. Write correct, minimal code "
            "for exactly what's asked. Return only the code and, if useful, "
            "a one-line explanation -- no preamble."
        ),
        "tools": [],
    },
    "critique": {
        "model": "claude-opus-5",
        "system": (
            "You are a focused critique subagent. Evaluate the given "
            "content rigorously and specifically -- call out real issues, "
            "don't just praise it. Return only the critique, no preamble."
        ),
        "tools": [],
    },
}

COORDINATOR_SYSTEM = (
    "You are a coordinator agent. You do not perform concrete work yourself "
    "-- you break the user's request into independent subtasks and "
    "delegate each one to a subagent.\n\n"
    "For every subtask, pick the subagent_type that fits it -- the "
    "cheapest type that can still do the job well, not the most capable "
    "type by default:\n"
    "- lookup: a short, well-known fact with a one-line answer.\n"
    "- research: requires gathering/synthesizing several facts or angles.\n"
    "- writing: producing polished prose or copy.\n"
    "- code: writing or explaining code.\n"
    "- critique: rigorously evaluating existing content.\n\n"
    "Delegate every subtask separately with delegate_task -- one call per "
    "subtask. Each delegated task must stand entirely on its own: the "
    "subagent has no memory of this conversation, so include every piece "
    "of context it needs. Once all results come back, weave them into a "
    "single, well-organized final answer."
)


def print_json(label: str, data) -> None:
    """Pretty-print a plain value or an Anthropic SDK object (pydantic model) as JSON."""

    def default(o):
        if hasattr(o, "model_dump"):
            return o.model_dump(mode="json")
        return str(o)

    print(f"\n--- {label} ---")
    print(json.dumps(data, indent=2, default=default))


async def run_subagent(client: AsyncAnthropic, task: str, subagent_type: str) -> str:
    """Runs the task through whichever model/system/tools the chosen
    profile specifies -- not one fixed setup for every subtask.
    """
    profile = SUBAGENT_PROFILES[subagent_type]
    print(f"\n>>> [{subagent_type} / {profile['model']}] {task!r}")

    kwargs = dict(
        model=profile["model"],
        max_tokens=1024,
        system=profile["system"],
        messages=[{"role": "user", "content": task}],
    )
    if profile["tools"]:
        kwargs["tools"] = profile["tools"]

    response = await client.messages.create(**kwargs)
    result_text = next(block.text for block in response.content if block.type == "text")
    print(f"<<< [{subagent_type}] finished ({len(result_text)} chars)")
    return result_text


async def main() -> None:
    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    tools = [
        {
            "name": "delegate_task",
            "description": (
                "Delegate ONE narrow, self-contained subtask to a subagent "
                "worker. Call this once per subtask. You must also pick "
                "the subagent_type that best matches what the subtask "
                "needs -- pick the cheapest type that can still do the job "
                "well."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "A clear, self-contained description of the subtask.",
                    },
                    "subagent_type": {
                        "type": "string",
                        "enum": list(SUBAGENT_PROFILES.keys()),
                        "description": (
                            "lookup: a simple factual question with a short, "
                            "well-known answer. research: requires gathering "
                            "and synthesizing multiple facts or angles. "
                            "writing: producing polished prose/copy. code: "
                            "writing or explaining code. critique: "
                            "evaluating existing content for quality/"
                            "correctness."
                        ),
                    },
                },
                "required": ["task", "subagent_type"],
            },
        }
    ]

    # Step 1: a request that naturally bundles a fact lookup, a research
    # question, a writing task, and a coding task -- four different kinds
    # of work with four different ideal subagent setups.
    messages = [
        {
            "role": "user",
            "content": (
                "I'm writing a blog post about Python's asyncio library. I "
                "need: (1) what Python version introduced asyncio, (2) a "
                "short comparison of asyncio vs. threading for I/O-bound "
                "work, (3) a catchy 2-sentence intro paragraph for the "
                "post, and (4) a minimal working code example of an async "
                "function run with asyncio.run()."
            ),
        },
    ]
    print_json("Step 1: user request to the coordinator", messages)

    # Step 2: force delegation, letting the coordinator issue one
    # delegate_task call per subtask -- each tagged with the subagent_type
    # it judged best for that subtask.
    response = await client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=COORDINATOR_SYSTEM,
        messages=messages,
        tools=tools,
        tool_choice={"type": "any"},
    )
    print_json("Step 2: coordinator's delegate_task calls", response.content)

    tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
    print(f"\nCoordinator issued {len(tool_use_blocks)} delegate_task call(s):")
    for b in tool_use_blocks:
        print(f"  - [{b.input.get('subagent_type')}] {b.input.get('task')!r}")

    # Step 3: keep the coordinator's tool calls in history.
    messages.append({"role": "assistant", "content": response.content})

    # Step 4: fan out -- every subtask runs concurrently, each against the
    # model/system/tools its assigned profile specifies.
    async def handle(block):
        if block.name == "delegate_task":
            result_text = await run_subagent(client, **block.input)
        else:
            result_text = f"Unknown tool: {block.name}"
        return {"type": "tool_result", "tool_use_id": block.id, "content": result_text}

    tool_results = await asyncio.gather(*(handle(b) for b in tool_use_blocks))

    print("\n--- Routing summary ---")
    for b in tool_use_blocks:
        profile = SUBAGENT_PROFILES.get(b.input.get("subagent_type"), {})
        print(f"  {b.input.get('subagent_type'):<10} -> {profile.get('model', '?'):<28} {b.input.get('task')[:60]!r}")

    # Step 5: report every subagent's result back to the coordinator.
    messages.append({"role": "user", "content": tool_results})
    print_json("Step 5: messages sent back to the coordinator", messages)

    # Step 6: the coordinator weaves every subtask's result into one answer.
    response = await client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=COORDINATOR_SYSTEM,
        messages=messages,
        tools=tools,
    )
    print_json("Step 6: coordinator's final response", response.content)

    for block in response.content:
        if block.type == "text":
            print("\nFinal answer to user:\n", block.text)


if __name__ == "__main__":
    asyncio.run(main())
