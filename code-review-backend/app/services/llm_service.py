from openai import AsyncOpenAI
import os
import re
import logging

# Use the new OpenAI client (async) to call the Chat Completions API
client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


async def review_code_chunk(chunk: str, language: str = "java", start_line: int = 1) -> dict:
    """Call LLM API to review a code chunk, return suggestions with line numbers.

    Uses the new openai-python v1+ API (AsyncOpenAI).
    
    Args:
        chunk: The code chunk to review
        language: Programming language (java, js, python, etc.)
        start_line: The starting line number of this chunk in the original file
    
    Returns:
        dict with 'comment' and optionally 'lines' (list of line numbers)
    """
    prompt = (
        f"You are an expert {language} code reviewer. Carefully study the following code block "
        f"(starting at line {start_line}) and return constructive improvement suggestions.\n\n"
        f"IMPORTANT: When you identify issues, specify the EXACT line number(s) where the issue occurs.\n"
        f"Format: 'Line X: issue description' or 'Lines X-Y: issue description'\n\n"
        f"Code:\n{chunk}\n\n"
        f"Provide specific, actionable feedback with line numbers:"
    )

    # Call the chat completions endpoint
    resp = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.2,
    )

    try:
        content = resp.choices[0].message.content
    except Exception:
        content = getattr(resp.choices[0].message, 'content', str(resp))
    
    # Extract line numbers from the response
    lines = extract_line_numbers(content, start_line)
    
    return {
        "comment": content,
        "lines": lines if lines else None
    }


def extract_line_numbers(text: str, offset: int = 0) -> list:
    """
    Extract line numbers mentioned in the review text.
    
    Patterns matched:
    - "Line 42: ..."
    - "Lines 10-15: ..."
    - "line 7" (case insensitive)
    
    Args:
        text: The review comment text
        offset: Starting line offset to add to relative line numbers
    
    Returns:
        List of absolute line numbers mentioned in the review
    """
    lines = set()
    
    # Pattern: "Line 42" or "Lines 10-15"
    patterns = [
        r'\bline[s]?\s+(\d+)(?:\s*-\s*(\d+))?\b',  # Line 42 or Lines 10-15
        r'\bat\s+line[s]?\s+(\d+)\b',               # at line 42
        r'\bon\s+line[s]?\s+(\d+)\b',               # on line 42
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else start
            
            # Add all lines in range
            for line_num in range(start, end + 1):
                lines.add(line_num + offset)
    
    result = sorted(list(lines))
    logging.debug(f"Extracted line numbers: {result} from text: {text[:100]}...")
    return result