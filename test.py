import anthropic

client = anthropic.Anthropic()

# Take prompt input from the user
user_prompt = input("Enter your prompt: ")

# Send the prompt to Claude
response = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=1000,
    messages=[
        {"role": "user", "content": user_prompt}
    ],
)

# Print the output clearly labeled
print("\n" + "=" * 20 + " RESPONSE " + "=" * 20)
for block in response.content:
    if block.type == "text":
        print(block.text)
print("=" * 48)