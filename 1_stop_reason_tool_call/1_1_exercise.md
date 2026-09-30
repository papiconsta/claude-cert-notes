# Build a Multi-Tool Agent Loop

What you'll learn

* How the agentic loop lifecycle works with the Messages API
* Why stop_reason is the authoritative signal for loop control
* How to handle tool_use and end_turn stop_reason values correctly
* How to append tool results to conversation history for multi-turn execution
* When safety iteration caps are appropriate versus inappropriate as stopping mechanisms

## Exercises 

Check every line in a sequence !

Set up a Claude API client with two tools: a calculator tool (accepts expression, returns result) and a web search stub (accepts query, returns mock results)

Why: Multi-tool setups expose model-driven decision-making — Claude must select the right tool based on context, which is core to agentic architecture.

You should see: Two tool definitions registered with proper JSON Schema input_schema, each with name, description, and parameters.


```python
import os
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

load_dotenv()
```


```python
client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_KEY"])
```


```python
import asyncio
import json
def print_json(label: str, data) -> None:
    """Pretty-print a plain value or an Anthropic SDK object (pydantic model) as JSON."""

    def default(o):
        if hasattr(o, "model_dump"):
            return o.model_dump(mode="json")
        return str(o)

    print(f"\n--- {label} ---")
    print(json.dumps(data, indent=2, default=default))
```


```python
# Step 1: the user's request to the coordinator.
messages = [
    {"role": "user", "content": "What is 47 plus 89?"},
]
print_json("Step 1: user request to the coordinator", messages)
```

    
    --- Step 1: user request to the coordinator ---
    [
      {
        "role": "user",
        "content": "What is 47 plus 89?"
      }
    ]
    


```python
response = await client.messages.create(
    model="claude-sonnet-5",
    max_tokens=1024,
    messages=messages,
    # tools=tools,
)
print_json("Step 2: response.content from first API call", response.content)
```

    
    --- Step 2: response.content from first API call ---
    [
      {
        "citations": null,
        "text": "47 + 89 = 136",
        "type": "text"
      }
    ]
    

Now the AI Made the calculation. The goal of this notebook is how we can define a tool and then check the stop_reason


```python
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
```

now we have defined the schema of the tool

next step is to define the functions that will be called 


```python
async def add_two_numbers(a: float, b: float) -> float:
    """Adds two numbers together."""
    print(f"Adding {a} and {b}")
    return a + b
```

so now that we defined the function and tool let's call the API.


```python
response = await client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        messages=messages,
        tools=tools,
    )
```


```python
print_json("Step 2: response.content from first API call", response.content)
```

    
    --- Step 2: response.content from first API call ---
    [
      {
        "signature": "EpQCCpABCBEYAipA5StWfSOxMQdkxi+pBtdz8kDpHlcGIOw03yX+hFdBFpsTneBoo43rnchdw4/BJm4cQxMpWxvMLVPYrr4t2o2YMTIPY2xhdWRlLXNvbm5ldC01OABCCHRoaW5raW5nWiQwODAwMWVmNS0wNjFmLTQyZDctOWUyZC03M2ZiY2IyOGMyMWKoAYivitUGEgxrPY3OcNv8czeQZ8YaDO/yLXTkYxLq6vWjeyIwMg2UlhlSQtv5LLfP6/6bTbdwLNyz0hHYUAHDuC9aCQNA5F4l8J0k824f2XgWdbSEKjHsEyZWDJYFptSLdToLCwHhR/0UKfOoHoNm0eb4jdzNT6sXmUgcIbpMZeOzjVzfmwiwGAE=",
        "thinking": "",
        "type": "thinking"
      },
      {
        "id": "toolu_019aCY7kbefFi9Cq3tArCgzV",
        "caller": {
          "type": "direct"
        },
        "input": {
          "a": 47,
          "b": 89
        },
        "name": "add_two_numbers",
        "type": "tool_use"
      }
    ]
    

now we saw the inside the content ... lets check one object before ... 


```python
print_json("Step 2: response.content from first API call", response)
```

    
    --- Step 2: response.content from first API call ---
    {
      "id": "msg_011CeuhRfes6yfhxa26CaL5p",
      "container": null,
      "content": [
        {
          "signature": "EpQCCpABCBEYAipA5StWfSOxMQdkxi+pBtdz8kDpHlcGIOw03yX+hFdBFpsTneBoo43rnchdw4/BJm4cQxMpWxvMLVPYrr4t2o2YMTIPY2xhdWRlLXNvbm5ldC01OABCCHRoaW5raW5nWiQwODAwMWVmNS0wNjFmLTQyZDctOWUyZC03M2ZiY2IyOGMyMWKoAYivitUGEgxrPY3OcNv8czeQZ8YaDO/yLXTkYxLq6vWjeyIwMg2UlhlSQtv5LLfP6/6bTbdwLNyz0hHYUAHDuC9aCQNA5F4l8J0k824f2XgWdbSEKjHsEyZWDJYFptSLdToLCwHhR/0UKfOoHoNm0eb4jdzNT6sXmUgcIbpMZeOzjVzfmwiwGAE=",
          "thinking": "",
          "type": "thinking"
        },
        {
          "id": "toolu_019aCY7kbefFi9Cq3tArCgzV",
          "caller": {
            "type": "direct"
          },
          "input": {
            "a": 47,
            "b": 89
          },
          "name": "add_two_numbers",
          "type": "tool_use"
        }
      ],
      "model": "claude-sonnet-5",
      "role": "assistant",
      "stop_details": null,
      "stop_reason": "tool_use",
      "stop_sequence": null,
      "type": "message",
      "usage": {
        "cache_creation": {
          "ephemeral_1h_input_tokens": 0,
          "ephemeral_5m_input_tokens": 0
        },
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "inference_geo": "global",
        "input_tokens": 474,
        "output_tokens": 87,
        "output_tokens_details": {
          "thinking_tokens": 14
        },
        "server_tool_use": null,
        "service_tier": "standard"
      }
    }
    

so now we can see that the stop_reason is "tool_use" so now the agent is preparing its own INPUT to the model in order to call the tool 


```python
tool_use_blocks = [block for block in response.content if block.type == "tool_use"]
print_json("Step 3: tool_use_blocks (filtered from response.content)", tool_use_blocks)
```

    
    --- Step 3: tool_use_blocks (filtered from response.content) ---
    [
      {
        "id": "toolu_019aCY7kbefFi9Cq3tArCgzV",
        "caller": {
          "type": "direct"
        },
        "input": {
          "a": 47,
          "b": 89
        },
        "name": "add_two_numbers",
        "type": "tool_use"
      }
    ]
    

so now we need to call the Claude API in order to give this input to their model and then they can run the functions that we defined.


```python
messages.append({"role": "assistant", "content": response.content})
```


```python
print_json("Step 4: Feed the LLM the previous answer with the tool response.content", messages)
```

    
    --- Step 4: Feed the LLM the previous answer with the tool response.content ---
    [
      {
        "role": "user",
        "content": "What is 47 plus 89?"
      },
      {
        "role": "assistant",
        "content": [
          {
            "signature": "EpQCCpABCBEYAipA5StWfSOxMQdkxi+pBtdz8kDpHlcGIOw03yX+hFdBFpsTneBoo43rnchdw4/BJm4cQxMpWxvMLVPYrr4t2o2YMTIPY2xhdWRlLXNvbm5ldC01OABCCHRoaW5raW5nWiQwODAwMWVmNS0wNjFmLTQyZDctOWUyZC03M2ZiY2IyOGMyMWKoAYivitUGEgxrPY3OcNv8czeQZ8YaDO/yLXTkYxLq6vWjeyIwMg2UlhlSQtv5LLfP6/6bTbdwLNyz0hHYUAHDuC9aCQNA5F4l8J0k824f2XgWdbSEKjHsEyZWDJYFptSLdToLCwHhR/0UKfOoHoNm0eb4jdzNT6sXmUgcIbpMZeOzjVzfmwiwGAE=",
            "thinking": "",
            "type": "thinking"
          },
          {
            "id": "toolu_019aCY7kbefFi9Cq3tArCgzV",
            "caller": {
              "type": "direct"
            },
            "input": {
              "a": 47,
              "b": 89
            },
            "name": "add_two_numbers",
            "type": "tool_use"
          }
        ]
      }
    ]
    


```python
tool_results = []
```


```python
if response.content[1].name == "add_two_numbers":
    result = await add_two_numbers(**response.content[1].input)
```

    Adding 47 and 89
    

but now we need to enforce a schema that has the proper values ...


```python
tool_results.append({
                "type": "tool_result",
                "tool_use_id": response.content[1].id,
                "content": str(result),
            })
```


```python
print_json("Step 5: tool_results computed locally", tool_results)
```

    
    --- Step 5: tool_results computed locally ---
    [
      {
        "type": "tool_result",
        "tool_use_id": "toolu_019aCY7kbefFi9Cq3tArCgzV",
        "content": "136"
      }
    ]
    


```python
messages.append({"role": "user", "content": tool_results})
```

We GIVE the results as a input from role user because the results came from our computer so it's like an input from us not from claude.


```python
print_json("Step 6: messages sent on second API call", messages)
```

    
    --- Step 6: messages sent on second API call ---
    [
      {
        "role": "user",
        "content": "What is 47 plus 89?"
      },
      {
        "role": "assistant",
        "content": [
          {
            "signature": "EpQCCpABCBEYAipA5StWfSOxMQdkxi+pBtdz8kDpHlcGIOw03yX+hFdBFpsTneBoo43rnchdw4/BJm4cQxMpWxvMLVPYrr4t2o2YMTIPY2xhdWRlLXNvbm5ldC01OABCCHRoaW5raW5nWiQwODAwMWVmNS0wNjFmLTQyZDctOWUyZC03M2ZiY2IyOGMyMWKoAYivitUGEgxrPY3OcNv8czeQZ8YaDO/yLXTkYxLq6vWjeyIwMg2UlhlSQtv5LLfP6/6bTbdwLNyz0hHYUAHDuC9aCQNA5F4l8J0k824f2XgWdbSEKjHsEyZWDJYFptSLdToLCwHhR/0UKfOoHoNm0eb4jdzNT6sXmUgcIbpMZeOzjVzfmwiwGAE=",
            "thinking": "",
            "type": "thinking"
          },
          {
            "id": "toolu_019aCY7kbefFi9Cq3tArCgzV",
            "caller": {
              "type": "direct"
            },
            "input": {
              "a": 47,
              "b": 89
            },
            "name": "add_two_numbers",
            "type": "tool_use"
          }
        ]
      },
      {
        "role": "user",
        "content": [
          {
            "type": "tool_result",
            "tool_use_id": "toolu_019aCY7kbefFi9Cq3tArCgzV",
            "content": "136"
          }
        ]
      }
    ]
    


```python
response = await client.messages.create(
            model="claude-sonnet-5",
            max_tokens=1024,
            messages=messages,
            tools=tools,
        )
print_json("Step 6: response.content from second API call", response.content)
```

    
    --- Step 6: response.content from second API call ---
    [
      {
        "citations": null,
        "text": "47 plus 89 equals **136**.",
        "type": "text"
      }
    ]
    

### Now that we saw how a Claude API lifecycle performs we need to build this in an Agentic Loop


```python
####################################################
#                                                  #
#                my implementation                 #
#                                                  #
####################################################

messages = [
    {"role": "user", "content": "What is 47 plus 89?"},
]

tool_results = []
while True:

    response = await client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        messages=messages,
        tools=tools,
    )

    if response.stop_reason == "end_turn":
        print(response.content.text)

    if response.stop_reason == "tool_use":
        messages.append({"role": "assistant", "content": response.content})

        if response.content[1].name == "add_two_numbers":
            result = await add_two_numbers(**response.content[1].input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": response.content[1].id,
                "content": str(result),
            })
    messages.append({"role": "user", "content": tool_results})
    


```

    Adding 47 and 89
    


    ---------------------------------------------------------------------------

    AttributeError                            Traceback (most recent call last)

    Cell In[21], line 22
         18         tools=tools,
         19     )
         20 
         21     if response.stop_reason == "end_turn":
    ---> 22         print(response.content.text)
         23 
         24     if response.stop_reason == "tool_use":
         25         messages.append({"role": "assistant", "content": response.content})
    

    AttributeError: 'list' object has no attribute 'text'



```python
messages = [
    {"role": "user", "content": "What is 47 plus 89?"},
]

while True:

    # the Claude processes the query either user or assistant
    response = await client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        messages=messages,
        tools=tools,
    )

    if response.stop_reason == "end_turn":
        for block in response.content:
            if block.type == "text":
                print(block.text)
        break

    if response.stop_reason == "tool_use":
        messages.append({"role": "assistant", "content": response.content}) # First here is the Tool Use append

        tool_results = []
        for block in response.content:
            if block.type == "tool_use" and block.name == "add_two_numbers":
                result = await add_two_numbers(**block.input) # We run the Tool
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                })

        messages.append({"role": "user", "content": tool_results}) # We reply back as an user but is our computers results
```

    Adding 47 and 89
    47 plus 89 equals **136**.
    

The difference with mine is that claude gives Two {} or blocks with data :

#Block 1
```json
    {
        "signature": "EpQCCpABCBEYAipA5StWfSOxMQdkxi+pBtdz8kDpHlcGIOw03yX+hFdBFpsTneBoo43rnchdw4/BJm4cQxMpWxvMLVPYrr4t2o2YMTIPY2xhdWRlLXNvbm5ldC01OABCCHRoaW5raW5nWiQwODAwMWVmNS0wNjFmLTQyZDctOWUyZC03M2ZiY2IyOGMyMWKoAYivitUGEgxrPY3OcNv8czeQZ8YaDO/yLXTkYxLq6vWjeyIwMg2UlhlSQtv5LLfP6/6bTbdwLNyz0hHYUAHDuC9aCQNA5F4l8J0k824f2XgWdbSEKjHsEyZWDJYFptSLdToLCwHhR/0UKfOoHoNm0eb4jdzNT6sXmUgcIbpMZeOzjVzfmwiwGAE=",
        "thinking": "",
        "type": "thinking"
  },
```

#Block 2

```json
 {
        "id": "toolu_019aCY7kbefFi9Cq3tArCgzV",
        "caller": {
          "type": "direct"
        },
        "input": {
          "a": 47,
          "b": 89
        },
        "name": "add_two_numbers",
        "type": "tool_use"
 }
    
```

So what I was doing before is I was checking the first block type which was thinking ... so ok perfect now makes sence !

### Safety iteration cap

`stop_reason` is still the *primary* way the loop ends -- `end_turn` means Claude is done, `tool_use` means keep going. A max-iteration counter is not a replacement for that check, it's a fallback for when `stop_reason` never resolves to `end_turn` at all: a buggy tool that always fails and Claude keeps retrying it, a bad prompt that sends Claude in circles, or an unexpected `stop_reason` value you didn't handle.

- **Appropriate**: a `counter` incremented once per loop pass, compared against a `MAX_ITERATIONS` cap, that breaks the loop *in addition to* the `stop_reason` check -- so a runaway loop can't run forever, but a normal 2-3 step tool conversation is never affected by it.
- **Inappropriate**: using the counter as the *only* stopping condition (e.g. `for _ in range(MAX_ITERATIONS):` with no `stop_reason` check) -- that can cut off a legitimate multi-step tool chain right before its final answer, or silently swallow a real `end_turn` a step early.

`MAX_ITERATIONS = 10` here is arbitrary for this toy example -- pick a cap based on how many tool round-trips a *legitimate* conversation for your use case would realistically need, not a global default.


```python
MAX_ITERATIONS = 10

messages = [
    {"role": "user", "content": "What is 47 plus 89? and the mean of them ?"},
]

counter = 0
while True:
    counter += 1
    if counter > MAX_ITERATIONS:
        print(f"Stopping: hit MAX_ITERATIONS={MAX_ITERATIONS} without an end_turn. "
              f"Last stop_reason seen: {response.stop_reason!r}")
        break

    response = await client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        messages=messages,
        tools=tools,
    )

    if response.stop_reason == "end_turn":
        for block in response.content:
            if block.type == "text":
                print(block.text)
        break

    if response.stop_reason == "tool_use":
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use" and block.name == "add_two_numbers":
                result = await add_two_numbers(**block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                })

        messages.append({"role": "user", "content": tool_results})

print(f"\nLoop ran {counter} iteration(s)")
```

    Adding 47 and 89
    **47 + 89 = 136**
    
    For the mean of the two numbers, divide the sum by 2:
    
    136 ÷ 2 = **68**
    
    So the mean of 47 and 89 is **68**.
    
    Loop ran 2 iteration(s)
    

### Test with a prompt that requires multiple sequential tool calls (e.g., search for a value then calculate something with it) and verify the loop continues correctly through all iterations


```python
tools.append(
        {
            "name": "divide_two_numbers",
            "description": "divide two numbers",
            "input_schema": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "The first number"},
                    "b": {"type": "number", "description": "The second number"},
                },
                "required": ["a", "b"],
            },
        }
    )
```


```python
async def divide_two_numbers(a: float, b: float) -> float:
    """Divide two numbers"""
    if b == 0:
        return 0
    return a/b
```


```python
messages = [
    {"role": "user", "content": "What is 47 plus 89? and later what is the mean ?"},
]

iteration = 0
while True:
    iteration +=1
    print_json(f"The iteration is:{iteration}",messages)
    
    # the Claude processes the query either user or assistant
    response = await client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        messages=messages,
        tools=tools,
    )

    if response.stop_reason == "end_turn":
        for block in response.content:
            if block.type == "text":
                print(block.text)
        break

    if response.stop_reason == "tool_use":
        messages.append({"role": "assistant", "content": response.content}) # First here is the Tool Use append

        tool_results = []
        for block in response.content:
            if block.type == "tool_use" and block.name == "add_two_numbers":
                result = await add_two_numbers(**block.input) # We run the Tool
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                })
            if block.type == "tool_use" and block.name == "divide_two_numbers":
                result = await divide_two_numbers(**block.input) # We run the Tool
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                })

        messages.append({"role": "user", "content": tool_results}) # We reply back as an user but is our computers results
```

    
    --- The iteration is:1 ---
    [
      {
        "role": "user",
        "content": "What is 47 plus 89? and later what is the mean ?"
      }
    ]
    Adding 47 and 89
    
    --- The iteration is:2 ---
    [
      {
        "role": "user",
        "content": "What is 47 plus 89? and later what is the mean ?"
      },
      {
        "role": "assistant",
        "content": [
          {
            "signature": "Er4ECpABCBEYAipAArnro4UJFCnY1fby8vTPLXG7P8gtf+/hC1GsccDdrxwJNfT3yNCp72i/X4atr4NJ4mp05578V1jmnTUA9hFNGTIPY2xhdWRlLXNvbm5ldC01OABCCHRoaW5raW5nWiQwODAwMWVmNS0wNjFmLTQyZDctOWUyZC03M2ZiY2IyOGMyMWKoAbivitUGEgzVR8aUnj7QOhVFWHEaDM4yCuf7cmJ8/Ht+/SIwJN/GoSHjZlLrami84o/pB0Zh3boltsdB/pEjtOfUyCQ1+KeVjTj8VBgsdFKrmslaKtoCHCfv6o5dp6jy5beUjgwpc7AFHImm9rSssyQJOhgNKf/7gwKoIPbwxJ/5Bm4PMc9rxGXg9KhN0l/vYcMa+kzg97aFlxw4TsO2UPIP4qwTWDFWMXC1f62B21JOexLwmp2GCVKwL9eGJJ+XGDwf4eBIhhnjceH/8zLlnPNhEPrMoo1/yLWFHIMX83GzLlN/RHLUVyJIFwmo4GkL80b5JqPbge6lzvmIyFoAdQF/mE1SF1QSm9Ig97G3hTGTAvPCsDaFqW+2XwdJsUnIMsDKbKWzM9+MlQtw3bjuQY4cvM4tT7o/WriaECCVO+QUdDTvREWpY5j3NtzIkIXEy7sk9k5+rryNfU9tvLDnKFMxjLbRCW08VVpSdMcjEHi0biOrZuAk2Xa0mumL9SdrMK4CVqutySP6QhAriwTc6Xa3YZLndNCcsgTUXItsOTdMcvIeRY8GwlWNeL9g19ldmhgB",
            "thinking": "",
            "type": "thinking"
          },
          {
            "citations": null,
            "text": "I'll calculate the sum first, and then determine the mean of the two numbers (47 and 89) by dividing the sum by 2.",
            "type": "text"
          },
          {
            "id": "toolu_01DS5GPSWAgzuGDxTnQ118QF",
            "caller": {
              "type": "direct"
            },
            "input": {
              "a": 47,
              "b": 89
            },
            "name": "add_two_numbers",
            "type": "tool_use"
          }
        ]
      },
      {
        "role": "user",
        "content": [
          {
            "type": "tool_result",
            "tool_use_id": "toolu_01DS5GPSWAgzuGDxTnQ118QF",
            "content": "136"
          }
        ]
      }
    ]
    
    --- The iteration is:3 ---
    [
      {
        "role": "user",
        "content": "What is 47 plus 89? and later what is the mean ?"
      },
      {
        "role": "assistant",
        "content": [
          {
            "signature": "Er4ECpABCBEYAipAArnro4UJFCnY1fby8vTPLXG7P8gtf+/hC1GsccDdrxwJNfT3yNCp72i/X4atr4NJ4mp05578V1jmnTUA9hFNGTIPY2xhdWRlLXNvbm5ldC01OABCCHRoaW5raW5nWiQwODAwMWVmNS0wNjFmLTQyZDctOWUyZC03M2ZiY2IyOGMyMWKoAbivitUGEgzVR8aUnj7QOhVFWHEaDM4yCuf7cmJ8/Ht+/SIwJN/GoSHjZlLrami84o/pB0Zh3boltsdB/pEjtOfUyCQ1+KeVjTj8VBgsdFKrmslaKtoCHCfv6o5dp6jy5beUjgwpc7AFHImm9rSssyQJOhgNKf/7gwKoIPbwxJ/5Bm4PMc9rxGXg9KhN0l/vYcMa+kzg97aFlxw4TsO2UPIP4qwTWDFWMXC1f62B21JOexLwmp2GCVKwL9eGJJ+XGDwf4eBIhhnjceH/8zLlnPNhEPrMoo1/yLWFHIMX83GzLlN/RHLUVyJIFwmo4GkL80b5JqPbge6lzvmIyFoAdQF/mE1SF1QSm9Ig97G3hTGTAvPCsDaFqW+2XwdJsUnIMsDKbKWzM9+MlQtw3bjuQY4cvM4tT7o/WriaECCVO+QUdDTvREWpY5j3NtzIkIXEy7sk9k5+rryNfU9tvLDnKFMxjLbRCW08VVpSdMcjEHi0biOrZuAk2Xa0mumL9SdrMK4CVqutySP6QhAriwTc6Xa3YZLndNCcsgTUXItsOTdMcvIeRY8GwlWNeL9g19ldmhgB",
            "thinking": "",
            "type": "thinking"
          },
          {
            "citations": null,
            "text": "I'll calculate the sum first, and then determine the mean of the two numbers (47 and 89) by dividing the sum by 2.",
            "type": "text"
          },
          {
            "id": "toolu_01DS5GPSWAgzuGDxTnQ118QF",
            "caller": {
              "type": "direct"
            },
            "input": {
              "a": 47,
              "b": 89
            },
            "name": "add_two_numbers",
            "type": "tool_use"
          }
        ]
      },
      {
        "role": "user",
        "content": [
          {
            "type": "tool_result",
            "tool_use_id": "toolu_01DS5GPSWAgzuGDxTnQ118QF",
            "content": "136"
          }
        ]
      },
      {
        "role": "assistant",
        "content": [
          {
            "citations": null,
            "text": "Now that I have the sum (136), I'll divide it by 2 to find the mean of the two numbers.",
            "type": "text"
          },
          {
            "id": "toolu_01GgdM2DJpPV9LfMv9koHfnr",
            "caller": {
              "type": "direct"
            },
            "input": {
              "a": 136,
              "b": 2
            },
            "name": "divide_two_numbers",
            "type": "tool_use"
          }
        ]
      },
      {
        "role": "user",
        "content": [
          {
            "type": "tool_result",
            "tool_use_id": "toolu_01GgdM2DJpPV9LfMv9koHfnr",
            "content": "68.0"
          }
        ]
      }
    ]
    ## Results
    
    - **47 + 89 = 136**
    - **Mean of 47 and 89 = 68**
    


```python

```
