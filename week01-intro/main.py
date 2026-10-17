"""
Week 1: First LLM Interaction Script
Simple CLI script to send user input to Claude and print the response.
"""

import sys
import anthropic

# Target Model
MODEL_NAME = "claude-sonnet-5-5"


def generate_response(prompt: str) -> None:
    """Sends a user prompt to Claude and prints the returned response."""
    try:
        # Client automatically reads ANTHROPIC_API_KEY from the environment
        client = anthropic.Anthropic()

        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        print("\n" + "=" * 20 + " CLAUDE RESPONSE " + "=" * 20)
        for block in response.content:
            if block.type == "text":
                print(block.text)
        print("=" * 57 + "\n")

    except anthropic.AuthenticationError:
        print(
            "\n[Error] Authentication failed. Check that ANTHROPIC_API_KEY is correctly set.",
            file=sys.stderr,
        )
    except anthropic.APIConnectionError:
        print(
            "\n[Error] Network error. Could not connect to Anthropic servers.",
            file=sys.stderr,
        )
    except anthropic.APIError as err:
        print(f"\n[Error] API call failed: {err.message}", file=sys.stderr)


def main() -> None:
    user_prompt = input("Enter your prompt for Claude: ").strip()

    if not user_prompt:
        print("Prompt cannot be empty. Exiting.")
        return

    generate_response(user_prompt)


if __name__ == "__main__":
    main()