import logging
import os
import re
import difflib
from typing import List, Optional

from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Configure detailed logging (only once at module import)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def extract_line_numbers(content: str, base_line: int = 0) -> Optional[List[int]]:
    """
    Extract line numbers from LLM response.

    Supports very loose formats like:
      - "Line 12"
      - "Lines 12-15"
      - "Line(s): 12, 15-18, 30"
      - "Lines affected: 12-14 and 20"

    Strategy:
      1. Find any line starting with "Line" / "Lines" / "Line(s)" etc.
      2. Parse all numbers and ranges on that line.
    """
    line_numbers: set[int] = set()

    # Capture any "Line..." line and parse numbers from it
    for match in re.finditer(r"Line(?:s)?[^\n]*", content, re.IGNORECASE):
        segment = match.group(0)

        # Normalize Unicode dashes to regular '-'
        segment = segment.replace("–", "-").replace("—", "-")

        # First, handle ranges: 12-15
        for rng in re.finditer(r"(\d+)\s*-\s*(\d+)", segment):
            start = int(rng.group(1))
            end = int(rng.group(2))
            for n in range(start, end + 1):
                line_numbers.add(base_line + n)

        # Then individual numbers: 12, 30, etc.
        for single in re.finditer(r"\b(\d+)\b", segment):
            n = int(single.group(1))
            line_numbers.add(base_line + n)

    if not line_numbers:
        return None

    return sorted(line_numbers)


def parse_individual_issues(llm_response: str, original_code: str, file_path: str) -> list:
    """
    Parse LLM response and generate individual issues with proper diffs including context.
    Each issue contains: comment, diff, highlighted_lines, severity, has_code_block.

    Expected LLM format for each issue:

    Code:
    ```python
    <original snippet>
    ```
    Issue:
    Severity: HIGH
    Line(s): 42, 45-47
    Description: ...

    Fix:
    <short explanation>
    ```python
    <fixed snippet>
    ```
    """
    issues: List[dict] = []
    orig_lines = original_code.splitlines()

    # More robust regex that tolerates extra text between sections
    pattern = re.compile(
        r"Code:\s*```[a-zA-Z0-9_+\-]*\n(.*?)```"
        r"[\s\S]*?Issue:\s*(.*?)\n+Fix:\s*(.*?)(?=(?:\n+Code:|$))",
        re.DOTALL | re.IGNORECASE,
    )

    matches = list(pattern.finditer(llm_response))
    logging.info(f"parse_individual_issues: found {len(matches)} Code/Issue/Fix blocks")

    for match in matches:
        code_snippet, issue_section, fix_section = match.groups()
        code_snippet = code_snippet.strip("\n")
        issue_section = issue_section.strip()
        fix_section = fix_section.strip()

        # --- Severity -------------------------------------------------------
        severity = "MEDIUM"
        if re.search(r"Severity:\s*HIGH", issue_section, re.IGNORECASE):
            severity = "HIGH"
        elif re.search(r"Severity:\s*MEDIUM", issue_section, re.IGNORECASE):
            severity = "MEDIUM"
        elif re.search(r"Severity:\s*LOW", issue_section, re.IGNORECASE):
            severity = "LOW"

        # --- Line numbers: first try explicit "Line(s)" info ----------------
        highlighted_lines: List[int] = []
        explicit_lines = extract_line_numbers(issue_section, base_line=0)
        if explicit_lines:
            highlighted_lines = explicit_lines

        # --- Fallback: fuzzy match snippet back to original -----------------
        if not highlighted_lines and code_snippet:
            snippet_lines = code_snippet.splitlines()
            best_score = 0.0
            best_start: Optional[int] = None

            for start in range(0, max(0, len(orig_lines) - len(snippet_lines) + 1)):
                candidate = "\n".join(orig_lines[start : start + len(snippet_lines)])
                score = difflib.SequenceMatcher(
                    None, candidate.strip(), code_snippet.strip()
                ).ratio()
                if score > best_score:
                    best_score = score
                    best_start = start

            # Require reasonably high similarity
            if best_start is not None and best_score >= 0.8:
                highlighted_lines = list(
                    range(best_start + 1, best_start + 1 + len(snippet_lines))
                )

        # --- Extract the actual fixed code from Fix section -----------------
        fixed_code = ""
        code_blocks = re.findall(
            r"```[a-zA-Z0-9_+\-]*\n(.*?)```", fix_section, re.DOTALL
        )
        if code_blocks:
            # Use the last code block as the replacement snippet
            fixed_code = code_blocks[-1].strip("\n")
        else:
            fixed_code = fix_section

        # --- Generate diff --------------------------------------------------
        diff = ""
        if code_snippet and fixed_code:
            diff_lines = list(
                difflib.unified_diff(
                    code_snippet.splitlines(),
                    fixed_code.splitlines(),
                    fromfile=f"a/{file_path}",
                    tofile=f"b/{file_path}",
                    lineterm="",
                    n=3,
                )
            )
            diff = "\n".join(diff_lines)

        issues.append(
            {
                "comment": (
                    f"Code:\n```{code_snippet}```\n"
                    f"Issue:\n{issue_section}\n"
                    f"Fix:\n{fix_section}"
                ),
                "diff": diff,
                "highlighted_lines": highlighted_lines,
                "severity": severity,
                "has_code_block": True,
            }
        )

    return issues


async def review_code_chunk_with_context(
    chunk: str,
    language: str,
    start_line: int,
    file_path: str,
    project_context: str,
    full_file_content: str,
) -> dict:
    """Review code with intelligent severity filtering and context awareness.

    This version:
      - Adds explicit line numbers to the chunk (global to the file)
      - Asks the LLM to reference those line numbers
      - Encourages *small, targeted line edits* instead of full rewrites
        (following the “surgical edits” idea from the blog post)
    """

    # Determine if the file is a test file by common patterns
    test_file_patterns = [
        "/test/",
        "/tests/",
        "/__tests__/",
        "/spec/",
        "/__mocks__/",
        "/mock/",
        "/mocks/",
        "test_",
        "_test.",
        ".spec.",
        ".test.",
        "tests.py",
        "test.js",
        "test.ts",
        "test.java",
        "test.jsx",
        "test.tsx",
    ]
    is_test_file = any(pat in file_path.lower() for pat in test_file_patterns)

    # Number the chunk with *global* line numbers so the LLM can reliably say "Line 42"
    chunk_lines = chunk.splitlines()
    numbered_chunk = "\n".join(
        f"{lineno:4d}: {code_line}"
        for lineno, code_line in enumerate(chunk_lines, start=start_line)
    )

    # Build prompt WITHOUT triple-quoted f-strings (to avoid EOF issues)
    prompt = (
        f"You are a senior {language} code reviewer. You are analyzing code from file: {file_path}.\n\n"
        "The code below is shown with its ORIGINAL line numbers on the left:\n\n"
        f"```{language}\n"
        f"{numbered_chunk}\n"
        "```\n\n"
        "Your job is to:\n"
        "- Find only MEDIUM or HIGH severity issues (ignore LOW severity / nitpicks).\n"
        "- Propose **small, targeted line edits**, NOT full rewrites of the whole snippet.\n\n"
        "For each issue you find, STRICTLY use this format:\n\n"
        "Code:\n"
        f"```{language}\n"
        "<the smallest relevant code snippet copied exactly from the original code (WITHOUT the line number prefixes)>\n"
        "```\n"
        "Issue:\n"
        "Severity: <HIGH | MEDIUM>\n"
        "Line(s): <comma-separated line numbers from the numbered code above>\n"
        "Description: <clear, simple explanation of the issue>\n\n"
        "Fix:\n"
        "<short explanation of the fix>\n"
        f"```{language}\n"
        "<fixed version of the same snippet>\n"
        "```\n\n"
        "Rules:\n"
        "- Always include both a `Severity:` line and a `Line(s):` line under the Issue section.\n"
        "- Reuse the exact line numbers from the numbered code block (these map directly to the original file).\n"
        "- Prefer changing only the problematic lines instead of rewriting large sections.\n"
        "- If you do not see any MEDIUM or HIGH severity issues, reply exactly with: No issues found.\n"
    )

    resp = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        temperature=0.1,
    )

    content = resp.choices[0].message.content or ""
    logging.info(f"📥 RAW LLM RESPONSE ({len(content)} chars)")
    logging.debug(content)

    normalized = content.strip().lower()

    # Only apply false positive / "no issue" filtering for NON-test files
    if not is_test_file:
        if normalized in ("no issues found", "no issues found."):
            logging.info("✅ No issues found in this chunk")
            return {
                "comment": "✅ No issues found",
                "lines": None,
                "has_code_block": False,
                "severity": None,
            }

        false_positive_patterns = [
            "already handled",
            "existing error handling",
            "appears to handle",
            "seems to be handled",
            "no issues",
            "looks good",
            "properly handled",
        ]
        if any(pat in content.lower() for pat in false_positive_patterns):
            logging.info("❌ FILTERED OUT: False positive detected")
            return {
                "comment": "✅ No issues found - error handling is adequate",
                "lines": None,
                "has_code_block": False,
                "severity": None,
            }

    # Determine highest severity mentioned in the chunk
    severity: Optional[str] = None
    if re.search(r"Severity:\s*HIGH", content, re.IGNORECASE):
        severity = "HIGH"
    elif re.search(r"Severity:\s*MEDIUM", content, re.IGNORECASE):
        severity = "MEDIUM"

    # For test files, be less strict about severity (keep security-ish issues)
    if is_test_file:
        if not severity and (
            "vulnerability" in content.lower() or "security" in content.lower()
        ):
            severity = "MEDIUM"
            logging.warning(
                "⚠️ Test file: Defaulting to MEDIUM severity due to security-related text"
            )
    else:
        # For non-test files, drop chunks that don't clearly contain MEDIUM/HIGH issues
        if severity not in ("HIGH", "MEDIUM"):
            logging.info(
                f"❌ FILTERED OUT: Severity not HIGH/MEDIUM (was: {severity})"
            )
            return {
                "comment": "✅ No significant issues found",
                "lines": None,
                "has_code_block": False,
                "severity": None,
            }

    # Extract explicit line numbers back from the LLM response (global line numbers)
    lines = extract_line_numbers(content, base_line=0)

    # Fallback: highlight entire chunk if model forgot to emit Line(s)
    if severity in ("HIGH", "MEDIUM") and not lines:
        logging.warning(
            "⚠️ Severity=%s but no explicit line numbers. "
            "Falling back to whole chunk (%s-%s).",
            severity,
            start_line,
            start_line + len(chunk_lines) - 1,
        )
        lines = list(range(start_line, start_line + len(chunk_lines)))

    result = {
        "comment": content,
        "lines": lines if lines else None,
        "has_code_block": "```" in content,
        "severity": severity,
    }

    logging.info(
        f"✅ RESULT: Severity={severity}, Lines={lines}, HasCode={'```' in content}"
    )
    logging.info("=" * 80 + "\n")

    return result
