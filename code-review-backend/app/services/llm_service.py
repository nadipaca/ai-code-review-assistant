import logging
from openai import AsyncOpenAI
import os
import re
import difflib

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def parse_individual_issues(llm_response: str, original_code: str, file_path: str) -> list:
    """
    Parse LLM response and generate individual issues with proper diffs including context.
    Each issue contains: comment, diff, highlighted_lines
    """
    issues = []
    # Use regex to extract issues in the expected format
    for match in re.finditer(
        r"Code:\s*```[a-zA-Z]*\n(.*?)```[\s\S]*?Issue:\s*(.*?)\n+Fix:\s*(.*?)(?=(?:\n+Code:|$))",
        llm_response, re.DOTALL
    ):
        code_snippet, issue_text, fix_text = match.groups()
        # Find line numbers by searching for the code_snippet in original_code
        highlighted_lines = []
        if code_snippet.strip():
            orig_lines = original_code.split('\n')
            snippet_lines = code_snippet.strip().split('\n')
            for i in range(len(orig_lines) - len(snippet_lines) + 1):
                if orig_lines[i:i+len(snippet_lines)] == snippet_lines:
                    highlighted_lines = list(range(i+1, i+1+len(snippet_lines)))
                    break
        # Generate diff using difflib
        diff = ''
        if code_snippet.strip() and fix_text.strip():
            diff_lines = list(difflib.unified_diff(
                code_snippet.strip().splitlines(),
                fix_text.strip().splitlines(),
                fromfile=f"a/{file_path}",
                tofile=f"b/{file_path}",
                lineterm='',
                n=3
            ))
            diff = '\n'.join(diff_lines)
        issues.append({
            "comment": f"Code:\n```{code_snippet}```\nIssue:\n{issue_text}\nFix:\n{fix_text}",
            "diff": diff,
            "highlighted_lines": highlighted_lines,
            "severity": "MEDIUM",  # or parse from LLM output
            "has_code_block": True
        })
    return issues

def extract_line_numbers(content: str, base_line: int) -> list:
    """Extract line numbers from AI response"""
    lines = []
    patterns = [
        r'Line (\d+)',
        r'Lines (\d+)-(\d+)',
        r'line (\d+)',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, content):
            if len(match.groups()) == 1:
                lines.append(base_line + int(match.group(1)))
            else:
                start = base_line + int(match.group(1))
                end = base_line + int(match.group(2))
                lines.extend(range(start, end + 1))
    return lines if lines else None

async def review_code_chunk_with_context(
    chunk: str,
    language: str,
    start_line: int,
    file_path: str,
    project_context: str,
    full_file_content: str
) -> dict:
    """Review code with intelligent severity filtering and context awareness."""

    # Determine if the file is a test file by common patterns
    test_file_patterns = [
        '/test/', '/tests/', '/__tests__/', '/spec/', '/__mocks__/', '/mock/', '/mocks/',
        'test_', '_test.', '.spec.', '.test.', 'tests.py', 'test.js', 'test.ts', 'test.java', 'test.jsx', 'test.tsx'
    ]
    is_test_file = any(pat in file_path.lower() for pat in test_file_patterns)

    prompt = f"""
You are a senior code reviewer. For each MEDIUM or HIGH severity issue you find, repeat the following format:

1. Code:
```{language}
<the relevant code snippet>
```
Issue:
<clear, simple explanation of the issue>

Fix:
<clear, actionable fix, with code example if possible>

Only output this format for each issue you find. If no issues, say "No issues found."
"""

    resp = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt.replace('<the relevant code snippet>', chunk)}],
        max_tokens=1500,
        temperature=0.1,
    )

    content = resp.choices[0].message.content

    logging.info(f"📥 RAW LLM RESPONSE ({len(content)} chars)")

    # Only apply false positive filtering for NON-test files
    if not is_test_file:
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
            logging.info(f"❌ FILTERED OUT: False positive detected")
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

    # For test files, be less strict about severity
    if is_test_file:
        if not severity and ("vulnerability" in content.lower() or "security" in content.lower()):
            severity = "MEDIUM"
            logging.warning(f"⚠️ Test file: Defaulting to MEDIUM severity")
    else:
        if severity not in ["HIGH", "MEDIUM"]:
            logging.info(f"❌ FILTERED OUT: Severity not HIGH/MEDIUM (was: {severity})")
            return {
                "comment": "✅ No significant issues found",
                "lines": None,
                "has_code_block": False,
                "severity": None
            }

    lines = extract_line_numbers(content, start_line)

    result = {
        "comment": content,
        "lines": lines if lines else None,
        "has_code_block": "```" in content,
        "severity": severity
    }

    logging.info(f"✅ RESULT: Severity={severity}, Lines={lines}, HasCode={'```' in content}")
    logging.info(f"{'='*80}\n")

    return result