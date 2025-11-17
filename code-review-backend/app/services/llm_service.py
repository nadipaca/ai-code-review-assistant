from openai import AsyncOpenAI
import os
import re
import logging

# Use the new OpenAI client (async) to call the Chat Completions API
client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

async def review_code_chunk_with_context(
    chunk: str,
    language: str,
    start_line: int,
    file_path: str,
    project_context: str,
    full_file_content: str
) -> dict:
    """Review code with strict severity filtering and context awareness."""
    prompt = (
        f"You are an expert {language} code reviewer analyzing **{file_path}**.\n\n"
        f"{project_context}\n\n"
        f"**CRITICAL RULES:**\n"
        f"1. **NEVER suggest removing imports or breaking existing functionality**\n"
        f"2. **Check if the issue is already handled** - don't suggest redundant fixes\n"
        f"3. **Understand helper functions** - review the full file context before suggesting changes\n"
        f"4. **DO NOT suggest removing code** unless it's a clear bug or security vulnerability\n"
        f"5. **DO NOT suggest style changes** (formatting, naming, comments)\n"
        f"6. **ONLY report MEDIUM/HIGH severity issues:**\n"
        f"   - 🔴 **HIGH**: Unhandled security vulnerabilities, SQL injection, XSS, data exposure\n"
        f"   - 🟠 **MEDIUM**: Input validation gaps, race conditions, unvalidated user input\n"
        f"7. **If code has proper error handling**: Respond with 'No issues found'\n"
        f"8. **Preserve existing functionality** - only suggest ADDITIONS, never DELETIONS of working code\n"
        f"9. **Verify the issue exists** - check if error handling is already present elsewhere\n\n"
        f"**Full File Context:**\n"
        f"```{language}\n{full_file_content[:1200]}```\n\n"
        f"**Code Chunk to Review (Lines {start_line}+):**\n"
        f"```{language}\n{chunk}\n```\n\n"
        f"**Response Format (only for REAL MEDIUM/HIGH severity issues):**\n"
        f"**Severity:** [HIGH/MEDIUM]\n"
        f"**Issue:** [What's wrong - be specific and verify it's not already handled]\n"
        f"**Impact:** [Concrete security/stability risk with example exploit]\n"
        f"**Fix:** [PRECISE code to ADD - never remove imports or break modules]\n"
        f"```{language}\n"
        f"// Show ONLY the lines to change with minimal context\n"
        f"// DO NOT remove imports or module-level code\n"
        f"```\n"
    )

    resp = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1200,
        temperature=0.05,  # Lower temperature for more precise/conservative reviews
    )

    content = resp.choices[0].message.content
    
    # ✅ Enhanced filtering for false positives
    false_positive_patterns = [
        "already handled",
        "existing error handling",
        "appears to handle",
        "seems to be handled",
        "no issues",
        "looks good",
        "properly handled"
    ]
    
    if any(pattern in content.lower() for pattern in false_positive_patterns):
        return {
            "comment": "✅ No issues found - error handling is adequate",
            "lines": None,
            "has_code_block": False,
            "severity": None
        }
    
    severity = None
    if "**Severity:** HIGH" in content or "🔴" in content:
        severity = "HIGH"
    elif "**Severity:** MEDIUM" in content or "🟠" in content:
        severity = "MEDIUM"
    
    if severity not in ["HIGH", "MEDIUM"]:
        logging.info(f"Skipping LOW severity issue: {content[:100]}")
        return {
            "comment": "✅ No significant issues found",
            "lines": None,
            "has_code_block": False,
            "severity": None
        }
    
    lines = extract_line_numbers(content, start_line)
    
    return {
        "comment": content,
        "lines": lines if lines else None,
        "has_code_block": "```" in content,
        "severity": severity
    }