import asyncio
import json
from pathlib import Path

import dotenv
from anthropic import AsyncAnthropic

MODEL = "claude-sonnet-5"

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
dotenv.load_dotenv(ENV_PATH)
ANTHROPIC_API_KEY = dotenv.get_key(ENV_PATH, "ANTHROPIC_KEY")


def print_json(label: str, data) -> None:
    """Pretty-print a plain value or an Anthropic SDK object (pydantic model) as JSON."""

    def default(o):
        if hasattr(o, "model_dump"):
            return o.model_dump(mode="json")
        return str(o)

    print(f"\n--- {label} ---")
    print(json.dumps(data, indent=2, default=default))


async def add_two_numbers(a: float, b: float) -> float:
    """Adds two numbers together."""
    print(f"Adding {a} and {b}")
    return a + b


tools = [
        {
            "name": "add_two_numbers",
            "description": "Adds two numbers together",
            "input_schema": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "The first number"},
                    "b": {"type": "number", "description": "The second number"},
                },
                "required": ["a", "b"],
            },
        }
    ]


async def main() -> None:
    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    # Step 1: the conversation starts as a single user turn -- just a plain
    # Python list we build ourselves. Nothing has been sent to the API yet.
    # messages == [{"role": "user", "content": "What is 47 plus 89?"}]
    messages = [
        {"role": "user", "content": "What is 47 plus 89?"},
    ]
    print_json("Step 1: initial messages", messages)

    # Step 2: first API call. We send the question *and* the tool definitions.
    # Claude can't run code itself, so instead of answering directly it may
    # reply with a *request* to call a tool. Example response.content then:
    #   [ToolUseBlock(type="tool_use", id="toolu_01Abc...",
    #                 name="add_two_numbers", input={"a": 47, "b": 89})]

    # If Claude didn't need the tool, response.content would instead be:
    #   [TextBlock(type="text", text="47 plus 89 is 136.")]
    # and everything below would be skipped (tool_use_blocks would be empty).

    response = await client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=messages,
        tools=tools,
    )
    print_json("Step 2: response.content from first API call", response.content)

    # Step 3: pull out only the "please call a tool" blocks from the response.
    # response.content can mix text blocks and tool_use blocks, or contain
    # several tool_use blocks at once (parallel tool calls) -- this filters
    # down to just the ones we need to act on.
    # Example: [ToolUseBlock(name="add_two_numbers", input={"a": 47, "b": 89},
    #                        id="toolu_01Abc...")]
    tool_use_blocks = [block for block in response.content if block.type == "tool_use"]
    print_json("Step 3: tool_use_blocks (filtered from response.content)", tool_use_blocks)

    if tool_use_blocks:
        # Step 4: the API is stateless -- it has no memory of the last call.
        # We must re-append Claude's "I want to call a tool" turn to the
        # conversation ourselves before we can reply to it. messages is now:
        #   [{"role": "user", "content": "What is 47 plus 89?"},
        #    {"role": "assistant", "content": [ToolUseBlock(...)]}]
        messages.append({"role": "assistant", "content": response.content})
        print_json("Step 4: messages after appending assistant tool request", messages)

        tool_results = []
        for block in tool_use_blocks:
            # Step 5: actually run the tool -- the one thing Claude itself
            # cannot do; it only asked, we execute.
            # block.input == {"a": 47, "b": 89}  ->  result == 136.0
            if block.name == "add_two_numbers":
                result = await add_two_numbers(**block.input)
            else:
                result = f"Unknown tool: {block.name}"

            # Package the result as a tool_result block, tagged with the same
            # tool_use_id Claude sent us, so Claude can match this result
            # back to the specific call it made (matters if there were
            # several calls at once). Example:
            #   {"type": "tool_result", "tool_use_id": "toolu_01Abc...",
            #    "content": "136.0"}
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": str(result),
            })
        print_json("Step 5: tool_results computed locally", tool_results)

        # All tool_result blocks go back together as one new user turn.
        # messages now has 3 entries: user question -> assistant tool
        # request -> user tool result(s).
        messages.append({"role": "user", "content": tool_results})
        print_json("Step 6: messages sent on second API call", messages)

        # Second API call, sending the whole conversation (including the
        # tool result) so Claude can write a real answer.
        # Example response.content this time:
        #   [TextBlock(type="text", text="47 plus 89 is 136.")]
        response = await client.messages.create(
            model=MODEL,
            max_tokens=1024,
            messages=messages,
            tools=tools,
        )
        print_json("Step 6: response.content from second API call", response.content)

    # Step 7: print whichever response we ended up with -- either the
    # tool-informed answer from Step 6, or the direct answer from Step 2 if
    # no tool was needed at all.
    print_json("Step 7: final response.content", response.content)
    for block in response.content:
        if block.type == "text":
            print("Text:", block.text)
        elif block.type == "tool_use":
            print(f"Tool call detected: {block.name} with input: {json.dumps(block.input)}")


if __name__ == "__main__":
    asyncio.run(main())
