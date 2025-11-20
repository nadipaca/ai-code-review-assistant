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

    # More robust regex that tolerates extra text between sections and optional "Code:" prefix
    # The lookahead checks for the START of the next issue (Code block followed closely by "Issue:")
    # We need to ensure the Fix section captures up to and including the closing ```
    pattern = re.compile(
        r"(?:Code:\s*)?```[a-zA-Z0-9_+\-]*\n(.*?)```"
        r"[\s\S]*?Issue:\s*(.*?)\n+Fix:\s*(.*?)(?=\n+Code:|$)",
        re.DOTALL | re.IGNORECASE,
    )

    matches = list(pattern.finditer(llm_response))
    logging.info(f"parse_individual_issues: found {len(matches)} Code/Issue/Fix blocks")

    for match in matches:
        code_snippet, issue_section, fix_section = match.groups()
        code_snippet = code_snippet.strip("\n")
        issue_section = issue_section.strip()
        fix_section = fix_section.strip()
        
        # Strip line numbers from code_snippet if present (format: "  12: code")
        # The LLM sometimes includes them despite being told not to
        # IMPORTANT: Only strip the line number, preserve indentation AFTER the colon
        code_snippet_lines = code_snippet.splitlines()
        cleaned_code_lines = []
        for line in code_snippet_lines:
            # Match pattern like "  12: " at start of line, but keep everything after the colon
            # The pattern captures leading whitespace + digits + colon + space, then keeps the rest
            cleaned_line = re.sub(r'^\s*\d+:\s?', '', line, count=1)
            cleaned_code_lines.append(cleaned_line)
        code_snippet = "\n".join(cleaned_code_lines)

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
            # If snippet NOT found literally at all, don't try to match
            if code_snippet not in original_code:
                logging.warning(
                    "Code snippet not found verbatim in original file for %s; "
                    "will only rely on explicit line numbers.",
                    file_path,
                )
            else:
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
        logging.info(f"DEBUG: fix_section='{fix_section}'")
        fixed_code = ""
        code_blocks = re.findall(
            r"```[a-zA-Z0-9_+\-]*\n(.*?)```", fix_section, re.DOTALL
        )
        if code_blocks:
            # Use the last code block as the replacement snippet
            fixed_code = code_blocks[-1].strip("\n")
            
            # Strip line numbers from fixed_code if present
            fixed_code_lines = fixed_code.splitlines()
            cleaned_fixed_lines = []
            for line in fixed_code_lines:
                # Match pattern like "  12: " at start of line, but keep everything after the colon
                cleaned_line = re.sub(r'^\s*\d+:\s?', '', line, count=1)
                cleaned_fixed_lines.append(cleaned_line)
            fixed_code = "\n".join(cleaned_fixed_lines)
        else:
            # STRICT: If no code block is found, assume it's just an explanation.
            # We do NOT want to treat plain text as code for diffs.
            fixed_code = ""

        # --- Generate diff --------------------------------------------------
        # Heuristic: if fixed_code looks like English explanation, skip diff
        looks_english = bool(re.search(r"[A-Za-z]{4,}\s+[A-Za-z]{4,}\s+[A-Za-z]{4,}", fixed_code))
        contains_quote_backtick = "`" in fixed_code
        
        logging.info(f"DEBUG: Issue {len(issues)+1}")
        logging.info(f"DEBUG: fixed_code='{fixed_code}'")
        logging.info(f"DEBUG: looks_english={looks_english}, contains_quote_backtick={contains_quote_backtick}")
        logging.info(f"DEBUG: About to generate diff with fixed_code length={len(fixed_code)}")

        # If it looks like English sentence OR starts with "Use ", "Ensure ", etc.
        if (looks_english and contains_quote_backtick) or fixed_code.lower().startswith(("use ", "ensure ", "avoid ", "implement ")):
            logging.info("DEBUG: Skipping diff - looks like English")
            diff = ""
        else:
            # Build code_snippet_for_diff from original lines and highlighted_lines if available
            # This ensures we diff against the REAL file content, not just what the LLM echoed
            code_snippet_for_diff = code_snippet
            if highlighted_lines:
                start_idx = min(highlighted_lines) - 1
                end_idx = max(highlighted_lines)
                # Ensure indices are within bounds
                start_idx = max(0, start_idx)
                end_idx = min(len(orig_lines), end_idx)
                
                if start_idx < end_idx:
                    code_snippet_for_diff = "\n".join(orig_lines[start_idx:end_idx])
            
            logging.info(f"DEBUG: code_snippet_for_diff='{code_snippet_for_diff}'")
            
            # CRITICAL: Preserve indentation from original code
            # The LLM often doesn't preserve indentation, so we need to copy it from code_snippet_for_diff
            if code_snippet_for_diff and fixed_code:
                # Get the indentation from the first line of the ACTUAL original code
                code_lines = code_snippet_for_diff.splitlines()
                if code_lines:
                    first_line = code_lines[0]
                    # Extract leading whitespace
                    indent_match = re.match(r'^(\s*)', first_line)
                    if indent_match:
                        indent = indent_match.group(1)
                        if indent:  # Only apply if there's actual indentation
                            logging.info(f"DEBUG: Detected indent from file='{indent}' (length={len(indent)})")
                            logging.info(f"DEBUG: Before indentation - fixed_code='{fixed_code[:50]}'")
                            # Apply this indentation to all lines of fixed_code
                            fixed_lines = fixed_code.splitlines()
                            indented_fixed_lines = []
                            for i, line in enumerate(fixed_lines):
                                if i == 0:
                                    # First line gets the original indent
                                    indented_fixed_lines.append(indent + line.lstrip())
                                else:
                                    # Subsequent lines: preserve their relative indentation
                                    # but add the base indent
                                    indented_fixed_lines.append(indent + line)
                            fixed_code = "\n".join(indented_fixed_lines)
                            logging.info(f"DEBUG: After indentation - fixed_code='{fixed_code[:50]}'")

            diff = ""
            if code_snippet_for_diff and fixed_code:
                diff_lines = list(
                    difflib.unified_diff(
                        code_snippet_for_diff.splitlines(),
                        fixed_code.splitlines(),
                        fromfile=f"a/{file_path}",
                        tofile=f"b/{file_path}",
                        lineterm="",
                        n=3,
                    )
                )
                diff = "\n".join(diff_lines)
                logging.info(f"DEBUG: Generated diff length={len(diff)}")
            else:
                logging.info("DEBUG: Skipping diff - missing snippet or fixed code")

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
        f"You are a senior {language} security and code quality expert performing a professional code review for file: {file_path}.\n\n"
        "The code below is shown with its ORIGINAL line numbers on the left:\n\n"
        f"```{language}\n"
        f"{numbered_chunk}\n"
        "```\n\n"
        "## YOUR MISSION\n"
        "Identify MEDIUM or HIGH severity issues (ignore LOW severity / nitpicks) and provide WORKING, SECURE code fixes.\n\n"
        "## CRITICAL RULES - READ CAREFULLY\n"
        "1. **NEVER suggest comment-only fixes** - Every fix MUST include actual working code, not just `// TODO: fix this`\n"
        "2. **NEVER suggest equally insecure alternatives** - If the original is insecure, your fix must be ACTUALLY SECURE\n"
        "3. **Provide complete, working code** - Your fix must be copy-paste ready and syntactically correct\n"
        "4. **Preserve indentation exactly** - Match the original code's leading whitespace (critical for Python)\n"
        "5. **Be specific and actionable** - Vague suggestions like 'use a library' are NOT acceptable\n\n"
        "## SECURITY GUIDELINES (MANDATORY)\n\n"
        "### Code Execution Vulnerabilities\n"
        "- **eval() / Function()**: BOTH are equally dangerous. Suggest:\n"
        "  ✅ GOOD: Remove the function entirely with explanation, OR use a safe parser library (e.g., math.js, expr-eval)\n"
        "  ❌ BAD: Replacing eval() with Function() or new Function()\n"
        "  ❌ BAD: Just adding a comment like '// This is unsafe'\n\n"
        "### XSS (Cross-Site Scripting)\n"
        "- **innerHTML with user input**: Use textContent or framework-provided escaping\n"
        "  ✅ GOOD: element.textContent = userInput\n"
        "  ❌ BAD: element.innerHTML = sanitize(userInput) // manual sanitization is error-prone\n\n"
        "### Hardcoded Secrets\n"
        "- **API keys, passwords in code**: Use environment variables\n"
        "  ✅ GOOD: const apiKey = process.env.API_KEY;\n"
        "  ❌ BAD: const apiKey = 'sk-...' // still hardcoded\n\n"
        "### SQL Injection\n"
        "- **String concatenation in queries**: Use parameterized queries\n"
        "  ✅ GOOD: db.query('SELECT * FROM users WHERE id = ?', [userId])\n"
        "  ❌ BAD: db.query(`SELECT * FROM users WHERE id = '${userId}'`)\n\n"
        "### Client-Side Payment Processing\n"
        "- **Stripe/payment APIs on client**: Move to server-side\n"
        "  ✅ GOOD: Replace with fetch('/api/process-payment', {method: 'POST', body: ...})\n"
        "  ❌ BAD: stripe.charges.create() on client, even with tokenization\n\n"
        "### Memory Leaks (Caches, Event Listeners)\n"
        "- **Unbounded caches**: Implement actual cleanup with working code\n"
        "  ✅ GOOD: Add TTL-based cleanup or LRU eviction with actual implementation\n"
        "  ❌ BAD: globalCache[id] = data; // Consider adding cleanup\n\n"
        "### Async/Await\n"
        "- **await without async**: Include function signature with async keyword\n"
        "  ✅ GOOD: Include both 'async function foo()' and 'await bar()' in your fix\n"
        "  ❌ BAD: Only showing 'await bar()' without making function async\n\n"
        "## OUTPUT FORMAT (STRICT)\n\n"
        "For each issue, use this EXACT format:\n\n"
        "Code:\n"
        f"```{language}\n"
        "<Exact copy of problematic code from above, WITHOUT line numbers>\n"
        "```\n"
        "Issue:\n"
        "Severity: <HIGH | MEDIUM>\n"
        "Line(s): <line numbers, e.g., 44 or 31-35>\n"
        "Description: <What's wrong AND why it's dangerous/problematic>\n\n"
        "Fix:\n"
        f"```{language}\n"
        "<COMPLETE, WORKING replacement code with SAME indentation as original>\n"
        "```\n"
        "<Brief explanation of why this fix is secure/better>\n\n"
        "## EXAMPLES OF GOOD FIXES\n\n"
        "### Example 1: eval() vulnerability\n"
        "Code:\n"
        "```javascript\n"
        "return eval(userInput);\n"
        "```\n"
        "Issue:\n"
        "Severity: HIGH\n"
        "Line(s): 28\n"
        "Description: eval() executes arbitrary code, allowing attackers to run malicious JavaScript.\n\n"
        "Fix:\n"
        "```javascript\n"
        "// Remove this function - it's inherently unsafe.\n"
        "// If you need math evaluation, use a library like 'expr-eval':\n"
        "// const Parser = require('expr-eval').Parser;\n"
        "// const parser = new Parser();\n"
        "// return parser.evaluate(userInput);\n"
        "throw new Error('This function has been removed for security reasons. Use a safe expression parser.');\n"
        "```\n"
        "This removes the vulnerability entirely. For math expressions, use a dedicated parser library that doesn't execute arbitrary code.\n\n"
        "### Example 2: Memory leak in cache\n"
        "Code:\n"
        "```javascript\n"
        "globalCache[userId] = data;\n"
        "```\n"
        "Issue:\n"
        "Severity: MEDIUM\n"
        "Line(s): 44\n"
        "Description: Cache grows unbounded, causing memory leaks in long-running applications.\n\n"
        "Fix:\n"
        "```javascript\n"
        "const CACHE_TTL = 3600000; // 1 hour\n"
        "globalCache[userId] = { data, timestamp: Date.now() };\n"
        "// Cleanup old entries\n"
        "Object.keys(globalCache).forEach(key => {\n"
        "    if (Date.now() - globalCache[key].timestamp > CACHE_TTL) {\n"
        "        delete globalCache[key];\n"
        "    }\n"
        "});\n"
        "```\n"
        "Implements TTL-based cache eviction to prevent unbounded growth.\n\n"
        "## FINAL CHECKLIST\n"
        "Before submitting your review, verify:\n"
        "- [ ] Every fix contains WORKING CODE, not just comments\n"
        "- [ ] Security fixes are ACTUALLY SECURE, not just slightly better\n"
        "- [ ] Code is syntactically correct and copy-paste ready\n"
        "- [ ] Indentation matches the original exactly\n"
        "- [ ] Explanations are specific and actionable\n\n"
        "If no MEDIUM or HIGH severity issues found, reply exactly: No issues found.\n"
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
