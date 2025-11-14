from openai import AsyncOpenAI
import os
import re
import logging

# Use the new OpenAI client (async) to call the Chat Completions API
client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


async def review_code_chunk(chunk: str, language: str = "java", start_line: int = 1) -> dict:
    """Call LLM API to review a code chunk and return actionable suggestions with code."""
    prompt = (
        f"You are an expert {language} code reviewer. Study this code (starting at line {start_line}) "
        f"and provide improvement suggestions.\n\n"
        f"For each issue:\n"
        f"1. Explain the problem clearly\n"
        f"2. Provide the EXACT line numbers\n"
        f"3. Show the improved code in a code block\n\n"
        f"Format your response like this:\n"
        f"**Issue:** [description]\n"
        f"**Lines:** X-Y\n"
        f"**Fix:**\n"
        f"```{language}\n"
        f"[corrected code]\n"
        f"```\n\n"
        f"Code to review:\n{chunk}"
    )

    resp = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.2,
    )

    content = resp.choices[0].message.content
    lines = extract_line_numbers(content, start_line)
    
    return {
        "comment": content,
        "lines": lines if lines else None,
        "has_code_block": "```" in content
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

async def review_code_chunk_with_context(
    chunk: str,
    language: str,
    start_line: int,
    file_path: str,
    project_context: str,
    full_file_content: str
) -> dict:
    """
    Review code chunk with full project context to avoid suggesting deletions.
    """
    prompt = (
        f"You are an expert {language} code reviewer analyzing **{file_path}** in a multi-file project.\n\n"
        f"{project_context}\n\n"
        f"**IMPORTANT RULES:**\n"
        f"1. This is part of a larger project - DO NOT suggest removing code unless it's genuinely unused\n"
        f"2. Consider dependencies from other files listed above\n"
        f"3. Look for actual bugs, security issues, or performance problems\n"
        f"4. Suggest improvements ONLY if they add value\n"
        f"5. If the code is fine, respond with: 'No issues found - code looks good!'\n\n"
        f"**Full File Context (for reference):**\n"
        f"```{language}\n"
        f"{full_file_content[:500]}...\n"  # Show beginning of file
        f"```\n\n"
        f"**Code Chunk to Review (Lines {start_line}+):**\n"
        f"```{language}\n"
        f"{chunk}\n"
        f"```\n\n"
        f"Provide specific, actionable feedback with line numbers and corrected code ONLY if there are real issues."
    )

    resp = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
        temperature=0.2,
    )

    content = resp.choices[0].message.content
    
    # ✅ Filter out "no issues" responses
    if "no issues" in content.lower() or "looks good" in content.lower():
        return {
            "comment": "✅ No issues found - code quality is good!",
            "lines": None,
            "has_code_block": False
        }
    
    lines = extract_line_numbers(content, start_line)
    
    return {
        "comment": content,
        "lines": lines if lines else None,
        "has_code_block": "```" in content
    }