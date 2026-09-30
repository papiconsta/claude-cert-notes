# The Round Trip

*How one question to Claude turns into two API calls, with your own code running in between — from `stop_reason/main.py`.*

## TL;DR

Claude never runs code. When it wants to use a tool, it stops and asks *you* to run it. Your Python script executes the function, reports the result back, and only then does Claude finish its answer. For the question **"What is 47 plus 89?"**, that means:

- **2** network round trips to the Claude API
- **1** local function call (`add_two_numbers`) that never touches the network
- A `messages` list that grows from **1 → 2 → 3** turns along the way

## The flow

```mermaid
sequenceDiagram
    participant Y as Your Script (main.py)
    participant C as Claude API

    Note over Y: Step 1 — build messages[]<br/>1 turn: your question
    Y->>C: Step 2 · POST /v1/messages<br/>question + tool schema
    C-->>Y: tool_use block<br/>add_two_numbers(a=47, b=89)
    Note over Y: Step 3 — filter response.content<br/>read-only, still 1 turn
    Note over Y: Step 4 — messages.append(assistant)<br/>→ 2 turns, append starts here
    Note over Y: Step 5 — run add_two_numbers(47, 89)<br/>→ 136, the only real computation
    Note over Y: Step 6 — messages.append(tool_result)<br/>→ 3 turns
    Y->>C: Step 6 · POST /v1/messages<br/>full 3-turn history
    C-->>Y: text block<br/>"47 plus 89 is 136."
    Note over Y: Step 7 — print(block.text)
```

> Solid arrows crossing to **Claude API** are network round trips — they cost latency, tokens, and money. Everything marked as a `Note` happens locally in Python, for free.

## Step by step

### Step 1 — Build the conversation

```python
messages = [
    {"role": "user", "content": "What is 47 plus 89?"},
]
```

Just a plain Python list. Nothing has been sent anywhere yet.

### Step 2 — First API call

```python
response = await client.messages.create(
    model=MODEL,
    max_tokens=1024,
    messages=messages,
    tools=tools,
)
```

Claude can't run code, so when it decides the question needs the `add_two_numbers` tool, it replies with a *request* instead of an answer:

```json
[{"type": "tool_use", "id": "toolu_01Abc...", "name": "add_two_numbers", "input": {"a": 47, "b": 89}}]
```

### Step 3 — Find the tool call

```python
tool_use_blocks = [block for block in response.content if block.type == "tool_use"]
```

This only *reads* `response.content` and filters it. `messages` is untouched here — still 1 turn.

### Step 4 — Save Claude's request into history

```python
messages.append({"role": "assistant", "content": response.content})
```

The API is **stateless** — it has no memory between calls. This is the actual append: `messages` becomes 2 turns long.

### Step 5 — Actually run the tool

```python
result = await add_two_numbers(**block.input)   # 136.0
```

The one step Claude itself can't do — it only asked, your code executes. Every other step here is just moving data around; this is where real computation happens.

### Step 6 — Report the result, second API call

```python
tool_results.append({
    "type": "tool_result",
    "tool_use_id": block.id,
    "content": str(result),
})
messages.append({"role": "user", "content": tool_results})

response = await client.messages.create(
    model=MODEL, max_tokens=1024, messages=messages, tools=tools,
)
```

`messages` is now 3 turns long and gets sent back in full. Claude sees the real number and writes: *"47 plus 89 is 136."*

### Step 7 — Print the answer

```python
for block in response.content:
    if block.type == "text":
        print("Text:", block.text)
```

## messages[], growing

| After step | Turns | What's in it |
|---|---|---|
| 1 | 1 | Your question |
| 4 | 2 | + Claude's `tool_use` request |
| 6 | 3 | + your `tool_result` |

```json
// After Step 1
messages = [
  {"role": "user", "content": "What is 47 plus 89?"}
]

// After Step 4  <-- this is the append people usually ask about
messages = [
  {"role": "user", "content": "What is 47 plus 89?"},
  {"role": "assistant", "content": [
    {"type": "tool_use", "id": "toolu_01Abc...", "name": "add_two_numbers", "input": {"a": 47, "b": 89}}
  ]}
]

// After Step 6
messages = [
  {"role": "user", "content": "What is 47 plus 89?"},
  {"role": "assistant", "content": [ /* ...as above... */ ]},
  {"role": "user", "content": [
    {"type": "tool_result", "tool_use_id": "toolu_01Abc...", "content": "136.0"}
  ]}
]
```

## The one-line takeaway

Only two things ever leave the machine: the two `POST /v1/messages` calls. Filtering, appending, and running `add_two_numbers` all happen locally, for free, in Python — the API only ever sees the *result* of your function, never the function itself.
