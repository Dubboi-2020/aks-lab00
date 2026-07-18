"""
Minimal agent service.

Exposes POST /chat which:
  1. sends the user's message to a free Groq-hosted LLM
  2. lets the model decide whether to call the `calculator` tool
  3. if it does, runs the tool locally and sends the result back to the model
  4. returns the final natural-language answer (+ a trace of any tool calls)


"""
import json
import os

from flask import Flask, jsonify, request
from openai import OpenAI

app = Flask(__name__)

# Groq exposes an OpenAI-compatible API, so the official `openai` SDK works
# unmodified -- point base_url at Groq and use a Groq API key.
client = OpenAI(
    api_key=os.environ["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1",
)

MODEL = os.environ.get("LLM_MODEL", "llama-3.1-8b-instant")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a basic arithmetic expression, e.g. '42 * 17'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "A basic arithmetic expression using + - * / and parentheses.",
                    }
                },
                "required": ["expression"],
            },
        },
    }
]


def calculator(expression: str) -> str:
    # Small, explicit allow-list eval -- fine for a demo tool, don't do raw
    # eval() on arbitrary input in anything real.
    allowed = set("0123456789+-*/(). ")
    if not set(expression) <= allowed:
        return "error: expression contains disallowed characters"
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"error: {e}"


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/chat", methods=["POST"])
def chat():
    body = request.get_json(force=True)
    user_message = body.get("message", "")
    if not user_message:
        return jsonify({"error": "missing 'message' field"}), 400

    messages = [
        {
            "role": "system",
            "content": (
                "You are a concise technical assistant. Use the calculator tool "
                "for any arithmetic instead of computing it yourself."
            ),
        },
        {"role": "user", "content": user_message},
    ]

    tool_trace = []

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
    )
    msg = response.choices[0].message

    # single-round tool loop.
    if msg.tool_calls:
        # Append a minimal, clean assistant message rather than the full SDK
        # object dump -- msg.model_dump() includes legacy fields like
        # function_call: null which Groq's stricter validation rejects
        # (OpenAI's own API tolerates it, Groq's does not).
        messages.append(
            {
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in msg.tool_calls
                ],
            }
        )
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments)
            if call.function.name == "calculator":
                result = calculator(args.get("expression", ""))
            else:
                result = "error: unknown tool"

            tool_trace.append(
                {"tool": call.function.name, "args": args, "result": result}
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": result,
                }
            )

        response = client.chat.completions.create(model=MODEL, messages=messages)
        msg = response.choices[0].message

    return jsonify({"reply": msg.content, "tool_calls": tool_trace})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)