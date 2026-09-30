import asyncio
import os
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = ["claude-sonnet-4-5","claude-opus-5"]


async def add_two_numbers(a: float, b: float) -> float:
    """Adds two numbers together."""
    print(f"Adding {a} and {b}")
    return a + b

"""This is how you define a tool"""
tools = [
        {
            "name": "add_two_numbers", # name of the function written above
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

"""
Example of a message returned by the agentic loop:

{
  "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "Hello!"
    }
  ],
  "model": "claude-opus-5",
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 12,
    "output_tokens": 6
  }
}

"""

async def agentic_loop(messages=None):
    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    if messages is None:
        messages = [
            {"role": "user", "content": "What is 47 plus 89?"},
        ]
    else:
        messages  = [
            {"role": "user", "content": messages},
        ]

    while True:

        message = await client.messages.create(
        model=MODEL[0],
        max_tokens=1024,
        messages=messages,
        tools=tools,
    )
        if message.stop_reason == "end_turn":
            print("Agent has finished its task.")
            print(message.content[0].text)
            break

        if message.stop_reason == "tool_use":
            message = await client.messages.create(
                    model=MODEL[0],
                    max_tokens=1024,
                    messages=messages,
                    tools=tools,
            )




if __name__ == "__main__":
    asyncio.run(agentic_loop())
    

    