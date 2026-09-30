import asyncio
import json
from pathlib import Path

import dotenv
from anthropic import AsyncAnthropic

MODEL = "claude-sonnet-5"

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
dotenv.load_dotenv(ENV_PATH)
ANTHROPIC_API_KEY = dotenv.get_key(ENV_PATH, "ANTHROPIC_KEY")

# The problem this file solves: a coordinator asked for "a comprehensive
# analysis of the EV market" will happily jump straight to the obvious
# subtasks (sales figures, battery tech, manufacturers) and stop there.
# Once those are delegated, each subagent only ever sees its own isolated
# task -- none of them can look at the others and say "hey, nobody's
# covering charging infrastructure." A too-narrow initial decomposition
# means entire topics silently never get researched. So before this
# coordinator may delegate anything, it must submit its planned subtask
# list through submit_decomposition and explicitly name what might still
# be missing.
COORDINATOR_SYSTEM = (
    "You are a coordinator agent. You do not perform concrete work yourself "
    "-- you decompose the user's request into subtasks and delegate each "
    "one to a subagent.\n\n"
    "Before delegating anything, submit your subtask breakdown with the "
    "submit_decomposition tool. When decomposing a task:\n"
    "1. Generate an initial list of subtasks.\n"
    "2. Ask yourself: what perspectives, stakeholders, or dimensions are "
    "missing?\n"
    "3. Add subtasks to cover those gaps.\n"
    "4. Only then submit the final list.\n\n"
    "For research tasks specifically, consider:\n"
    "- quantitative AND qualitative angles\n"
    "- supply AND demand sides\n"
    "- short-term AND long-term factors\n"
    "- supporting infrastructure, not just the primary subject\n"
    "- policy, regulatory, and economic context\n"
    "- risks and failure modes, not just opportunities\n\n"
    "Once your decomposition is submitted, delegate each subtask separately "
    "with the delegate_task tool -- one call per subtask, covering every "
    "item in the list you submitted. Each delegated task must stand "
    "entirely on its own: the subagent has no memory of this conversation, "
    "so include every piece of context it needs. Once all results come "
    "back, weave them into a single, well-organized final answer."
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
    single task string it was handed.
    """
    print(f"\n>>> Subagent starting task: {task!r}")

    response = await client.messages.create(
        model=MODEL,
        max_tokens=1536,
        system=SUBAGENT_SYSTEM,
        messages=[{"role": "user", "content": task}],
    )

    result_text = next(block.text for block in response.content if block.type == "text")
    print(f"<<< Subagent finished ({len(result_text)} chars)")
    return result_text


async def main() -> None:
    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    tools = [
        {
            "name": "submit_decomposition",
            "description": "Submit your subtask breakdown for review before delegating anything.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "subtasks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Full list of subtasks you plan to delegate.",
                    },
                    "coverage_rationale": {
                        "type": "string",
                        "description": "Explain what dimensions of the topic each subtask covers. Keep it to 2-4 sentences.",
                    },
                    "potential_gaps": {
                        "type": "string",
                        "description": "What might still be missing from this decomposition? Keep it to 1-3 sentences.",
                    },
                },
                "required": ["subtasks", "coverage_rationale", "potential_gaps"],
            },
        },
        {
            "name": "delegate_task",
            "description": (
                "Delegate ONE narrow, self-contained subtask to a subagent "
                "worker. Call this once per subtask from your submitted "
                "decomposition."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "A clear, self-contained description of ONE subtask for the subagent to complete.",
                    },
                },
                "required": ["task"],
            },
        },
    ]

    # Step 1: the user's request to the coordinator.
    messages = [
        {"role": "user", "content": "Give me a comprehensive analysis of the EV market."},
    ]
    print_json("Step 1: user request to the coordinator", messages)

    # Step 2: force the coordinator to plan before it can touch delegate_task
    # at all. tool_choice pins it to submit_decomposition, so the model has
    # no way to skip straight to delegating -- it must externalize its
    # subtask list, its coverage rationale, and its own guess at what's
    # still missing, all before a single subagent runs. Only submit_decomposition
    # is exposed here (not delegate_task) -- with both schemas in view, the
    # model can bleed field names from the other tool once it's under token
    # pressure, e.g. writing "task" instead of "subtasks".
    response = await client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=COORDINATOR_SYSTEM,
        messages=messages,
        tools=[tools[0]],
        tool_choice={"type": "tool", "name": "submit_decomposition"},
    )
    print_json("Step 2: coordinator's proposed decomposition", response.content)
    print(f"(stop_reason: {response.stop_reason})")

    decomposition_block = next(b for b in response.content if b.type == "tool_use")
    subtasks = decomposition_block.input["subtasks"]
    print(f"\nCoverage rationale: {decomposition_block.input.get('coverage_rationale', '(not provided -- response likely truncated)')}")
    print(f"Potential gaps flagged: {decomposition_block.input.get('potential_gaps', '(not provided -- response likely truncated)')}")
    print(f"\n{len(subtasks)} subtask(s) proposed:")
    for t in subtasks:
        print(f"  - {t}")

    # Step 3: acknowledge the plan, then hand control back with tool_choice
    # switched to "any" -- the coordinator must now act, and the only tool
    # left that makes sense given its own system prompt is delegate_task,
    # called once per subtask it just committed to.
    messages.append({"role": "assistant", "content": response.content})
    messages.append({
        "role": "user",
        "content": [{
            "type": "tool_result",
            "tool_use_id": decomposition_block.id,
            "content": "Decomposition received. Proceed to delegate each subtask.",
        }],
    })

    response = await client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=COORDINATOR_SYSTEM,
        messages=messages,
        tools=tools,
        tool_choice={"type": "any"},
    )
    print_json("Step 4: coordinator's delegate_task calls", response.content)

    tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
    delegate_count = sum(1 for b in tool_use_blocks if b.name == "delegate_task")
    print(f"\nCoordinator issued {delegate_count} delegate_task call(s):")
    for b in tool_use_blocks:
        if b.name == "delegate_task":
            print(f"  - {b.input['task']!r}")

    # Step 5: fan out -- every subtask runs as its own isolated subagent
    # call, concurrently. That's only safe because narrow, self-contained
    # subtasks don't depend on each other's output.
    async def handle(block):
        if block.name == "delegate_task":
            result_text = await run_subagent(client, **block.input)
        else:
            result_text = f"Unknown tool: {block.name}"
        return {"type": "tool_result", "tool_use_id": block.id, "content": result_text}

    tool_results = await asyncio.gather(*(handle(b) for b in tool_use_blocks))

    # Step 6: report every subagent's result back to the coordinator in one turn.
    messages.append({"role": "assistant", "content": response.content})
    messages.append({"role": "user", "content": tool_results})
    print_json("Step 6: messages sent back to the coordinator", messages)

    # Step 7: the coordinator weaves every subtask's result into one answer.
    response = await client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=COORDINATOR_SYSTEM,
        messages=messages,
        tools=tools,
    )
    print_json("Step 7: coordinator's final response", response.content)

    for block in response.content:
        if block.type == "text":
            print("\nFinal answer to user:\n", block.text)


if __name__ == "__main__":
    asyncio.run(main())
