
from openai import AsyncOpenAI
import os

# Use the new OpenAI client (async) to call the Chat Completions API
client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


async def review_code_chunk(chunk: str, language: str = "java") -> dict:
    """Call LLM API to review a code chunk, return suggestions.

    Uses the new openai-python v1+ API (AsyncOpenAI).
    """
    prompt = (
        f"You are an expert {language} code reviewer. Carefully study the following code block and return constructive improvement suggestions"
        f" and, if possible, highlight problematic lines. Review:\n\n{chunk}\n\nSuggestions:"
    )

    # Call the chat completions endpoint
    resp = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
        temperature=0.2,
    )

    # New response shape: access the first choice's message content
    # resp.choices[0].message.content or resp.choices[0].message['content']
    try:
        content = resp.choices[0].message.content
    except Exception:
        # Fallback for different response shapes
        content = getattr(resp.choices[0].message, 'content', str(resp))

    return {"comment": content}
