"""
Service to apply AI suggestions to code and generate diffs.
"""
import re
from typing import Dict, List, Optional, Tuple
import difflib
import logging


class CodeApplier:
    """Apply AI-suggested changes to code"""
    
    @staticmethod
    def extract_code_blocks(suggestion: str) -> List[Tuple[str, str]]:
        """
        Extract ALL code blocks from AI suggestion with their language.
        
        Returns:
            List of (language, code) tuples
        """
        # Pattern: ```language\ncode\n```
        pattern = r'```(\w*)\n(.*?)\n```'
        matches = re.findall(pattern, suggestion, re.DOTALL)
        
        if matches:
            return [(lang or 'text', code.strip()) for lang, code in matches]
        
        return []
    
    @staticmethod
    def extract_line_ranges(suggestion: str) -> List[Tuple[int, int]]:
        """
        Extract line ranges from suggestions like "Line 12" or "Lines 10-15"
        
        Returns:
            List of (start_line, end_line) tuples
        """
        ranges = []
        
        # Pattern: "Line 42" or "Lines 10-15"
        patterns = [
            r'\*\*Line\s+(\d+):\*\*',           # **Line 12:**
            r'Line\s+(\d+)',                     # Line 42
            r'Lines\s+(\d+)-(\d+)',              # Lines 10-15
            r'\*\*Lines\s+(\d+)-(\d+):\*\*',    # **Lines 10-15:**
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, suggestion, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) == 2:  # Range
                    start = int(match.group(1))
                    end = int(match.group(2))
                    ranges.append((start, end))
                else:  # Single line
                    line = int(match.group(1))
                    ranges.append((line, line))
        
        return ranges
    
    @staticmethod
    def detect_code_block_range(
        original_code: str,
        fix_code: str,
        suggested_start: int,
        suggested_end: int,
        file_path: str = "file"
    ) -> Tuple[int, int]:
        """
        Intelligently detect the actual line range needed for applying a fix.
        
        If the fix code contains a complete function/class/block definition,
        this will search the original code to find the full range of that block.
        
        Args:
            original_code: The original file content
            fix_code: The suggested fix code block
            suggested_start: Line number from AI suggestion (where issue was detected)
            suggested_end: End line from AI suggestion
            file_path: File path for language detection
            
        Returns:
            (actual_start, actual_end) tuple with expanded range if block detected,
            or original (suggested_start, suggested_end) if no expansion needed
        """
        lines = original_code.split('\n')
        fix_lines = fix_code.strip().split('\n')
        
        if not fix_lines:
            return (suggested_start, suggested_end)
        
        # Detect language from file extension
        ext = file_path.lower().split('.')[-1] if '.' in file_path else ''
        
        # Check if fix code starts with a function/class/method definition
        first_line = fix_lines[0].strip()
        
        # Language-specific patterns for function/class definitions
        is_function_def = False
        function_name = None
        
        # JavaScript/TypeScript patterns
        if ext in ['js', 'jsx', 'ts', 'tsx', 'mjs']:
            # function foo(), async function foo(), const foo = function()
            js_patterns = [
                r'^(?:export\s+)?(?:async\s+)?function\s+(\w+)',
                r'^(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function',
                r'^(?:const|let|var)\s+(\w+)\s*=\s*\([^)]*\)\s*=>'
            ]
            for pattern in js_patterns:
                match = re.match(pattern, first_line)
                if match:
                    is_function_def = True
                    function_name = match.group(1)
                    break
        
        # Python patterns
        elif ext in ['py']:
            # def foo(), async def foo(), class Foo
            py_patterns = [
                r'^(?:async\s+)?def\s+(\w+)',
                r'^class\s+(\w+)'
            ]
            for pattern in py_patterns:
                match = re.match(pattern, first_line)
                if match:
                    is_function_def = True
                    function_name = match.group(1)
                    break
        
        # Java/C#/C++ patterns
        elif ext in ['java', 'cs', 'cpp', 'c', 'h']:
            # public void foo(), private static int bar()
            java_pattern = r'(?:public|private|protected)\s+(?:static\s+)?(?:\w+\s+)+(\w+)\s*\('
            match = re.match(java_pattern, first_line)
            if match:
                is_function_def = True
                function_name = match.group(1)
        
        # If we didn't detect a function definition, return original range
        if not is_function_def:
            logging.info(f"No function/class definition detected in fix code, using original range {suggested_start}-{suggested_end}")
            return (suggested_start, suggested_end)
        
        logging.info(f"Detected function/class definition: {function_name}")
        
        # Now search for the complete block in the original code
        # IMPORTANT: The suggested range might be INSIDE the function body,
        # so we need to search BACKWARDS to find the function definition
        search_start = max(0, suggested_start - 20)  # Increased to 20 lines before
        search_end = min(len(lines), suggested_end + 10)
        
        # Find the function definition line by searching for the function name
        actual_start = None
        
        # Strategy 1: Search for exact function definition (including before suggested range)
        for i in range(search_start, search_end):
            if i >= len(lines):
                break
            line = lines[i].strip()
            
            # Check if this line contains the function definition
            if function_name and function_name in line:
                # Verify it's actually a definition, not just a call
                if ext in ['js', 'jsx', 'ts', 'tsx', 'mjs']:
                    if re.search(r'\bfunction\s+' + re.escape(function_name) + r'\b', lines[i]) or \
                       re.search(r'\b' + re.escape(function_name) + r'\s*[=:]\s*(?:async\s+)?(?:function|\()', lines[i]):
                        actual_start = i + 1  # Convert to 1-indexed
                        logging.info(f"Found function definition at line {actual_start}")
                        break
                elif ext in ['py']:
                    if re.search(r'\b(?:def|class)\s+' + re.escape(function_name) + r'\b', lines[i]):
                        actual_start = i + 1
                        logging.info(f"Found function definition at line {actual_start}")
                        break
                elif ext in ['java', 'cs', 'cpp', 'c', 'h']:
                    if re.search(r'\b' + re.escape(function_name) + r'\s*\(', lines[i]):
                        actual_start = i + 1
                        logging.info(f"Found function definition at line {actual_start}")
                        break
        
        # Strategy 2: If we couldn't find by name, search backwards for ANY function/class definition
        # that would contain the suggested lines
        if actual_start is None:
            logging.info(f"Function {function_name} not found by name, searching for containing function...")
            
            for i in range(suggested_start - 1, max(0, suggested_start - 30), -1):
                if i < 0 or i >= len(lines):
                    continue
                line = lines[i].strip()
                
                # Look for function/class definitions
                if ext in ['js', 'jsx', 'ts', 'tsx', 'mjs']:
                    if re.search(r'\b(?:async\s+)?function\s+\w+\s*\(', line) or \
                       re.search(r'\b(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?function', line) or \
                       re.search(r'\b(?:const|let|var)\s+\w+\s*=\s*\([^)]*\)\s*=>', line):
                        actual_start = i + 1
                        logging.info(f"Found containing function at line {actual_start}")
                        break
                elif ext in ['py']:
                    if re.search(r'\b(?:def|class)\s+\w+', line):
                        actual_start = i + 1
                        logging.info(f"Found containing function at line {actual_start}")
                        break
        
        if actual_start is None:
            logging.warning(f"Could not find function definition for {function_name}, using suggested range")
            return (suggested_start, suggested_end)
        
        # Find the closing of the block
        actual_end = None
        
        if ext in ['js', 'jsx', 'ts', 'tsx', 'mjs', 'java', 'cs', 'cpp', 'c', 'h']:
            # Brace-based languages: count opening and closing braces
            brace_count = 0
            started = False
            
            for i in range(actual_start - 1, min(len(lines), actual_start + 200)):
                line = lines[i]
                
                # Count braces
                for char in line:
                    if char == '{':
                        brace_count += 1
                        started = True
                    elif char == '}':
                        brace_count -= 1
                        
                        # When we reach 0 after starting, we've found the end
                        if started and brace_count == 0:
                            actual_end = i + 1  # Convert to 1-indexed
                            break
                
                if actual_end is not None:
                    break
        
        elif ext in ['py']:
            # Python: detect based on indentation
            # Find the indentation level of the function def
            def_line = lines[actual_start - 1]
            def_indent = len(def_line) - len(def_line.lstrip())
            
            # Find where indentation returns to the same or less level
            last_function_line = actual_start  # Start with first line as fallback
            for i in range(actual_start, min(len(lines), actual_start + 200)):
                line = lines[i]
                
                # Skip empty lines
                if not line.strip():
                    continue
                
                # Check indentation
                current_indent = len(line) - len(line.lstrip())
                
                # If we're back to the same or less indentation, the block ended on the previous non-empty line
                if current_indent <= def_indent:
                    actual_end = last_function_line  # Last line that was part of the function
                    break
                else:
                    # This line is still part of the function
                    last_function_line = i + 1  # Convert to 1-indexed
            
            # If we didn't find the end (e.g., function goes to end of file)
            if actual_end is None:
                actual_end = last_function_line
        
        if actual_end is None:
            logging.warning(f"Could not find end of block for {function_name}, using suggested range")
            return (suggested_start, suggested_end)
        
        # Log the expansion
        if actual_start != suggested_start or actual_end != suggested_end:
            logging.info(f"📏 Expanded line range from {suggested_start}-{suggested_end} to {actual_start}-{actual_end} (detected complete {function_name})")
        
        return (actual_start, actual_end)
    
    @staticmethod
    def smart_extract_changes(suggestion: str) -> List[Dict]:
        """
        Extract ALL changes from a multi-part suggestion.
        
        Returns:
            List of changes: [{"lines": (start, end), "code": "...", "description": "..."}]
        """
        changes = []
        
        # Split by numbered items (1., 2., 3., etc.)
        parts = re.split(r'\n\d+\.\s+', suggestion)
        
        for part in parts:
            if not part.strip():
                continue
            
            # Extract description (everything before the code block)
            code_blocks = CodeApplier.extract_code_blocks(part)
            line_ranges = CodeApplier.extract_line_ranges(part)
            
            # Get description (first paragraph before code block)
            description_match = re.match(r'(.*?)```', part, re.DOTALL)
            description = description_match.group(1).strip() if description_match else part[:200]
            
            # Create change entry
            for code_lang, code in code_blocks:
                for start_line, end_line in line_ranges:
                    changes.append({
                        "lines": (start_line, end_line),
                        "code": code,
                        "description": description,
                        "language": code_lang
                    })
                    break  # Only use first line range per code block
                break  # Only use first code block per part
        
        return changes
    
    @staticmethod
    def apply_line_replacement(
        original_code: str,
        line_start: int,
        line_end: int,
        replacement: str
    ) -> str:
        """
        Replace lines [line_start, line_end] with replacement text.
        """
        lines = original_code.split('\n')
        
        # Convert to 0-indexed
        start_idx = max(0, line_start - 1)
        end_idx = min(len(lines), line_end)
        
        # Split replacement into lines
        replacement_lines = replacement.split('\n')
        
        # Apply replacement
        new_lines = lines[:start_idx] + replacement_lines + lines[end_idx:]
        
        return '\n'.join(new_lines)
    
    @staticmethod
    def generate_diff(original: str, modified: str, filename: str = "file", context_lines: int = 3) -> str:
        """
        Generate unified diff between original and modified content with context lines.
        
        Args:
            original: Original file content
            modified: Modified file content
            filename: File name for diff headers
            context_lines: Number of unchanged lines to show around changes (default: 3)
        
        Returns:
            Unified diff string with context
        """
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm='',
            n=context_lines
        )
        
        return ''.join(diff)
    
    @staticmethod
    def smart_apply_suggestion(
        original_code: str,
        suggestion: str,
        line_start: int,
        line_end: Optional[int] = None,
        file_path: str = "file"
    ) -> Dict:
        """
        Intelligently apply an AI suggestion to code.
        
        Handles multiple formats:
        1. Multi-part suggestions with numbered items
        2. Single code block suggestions
        3. Plain text suggestions
        
        Returns:
            {
                "modified_code": str,
                "diff": str,
                "applied": bool,
                "changes": List[Dict],  # Details of all changes
                "error": Optional[str]
            }
        """
        try:
            # STRATEGY 1: Look for explicit "Fix:" section (Standard format)
            # This is the most reliable way to get the intended change
            fix_match = re.search(r"Fix:\s*\n(.*?)$", suggestion, re.DOTALL | re.IGNORECASE)
            if fix_match:
                fix_content = fix_match.group(1)
                code_blocks = CodeApplier.extract_code_blocks(fix_content)
                if code_blocks:
                    # Use the first code block found in the Fix section
                    lang, code = code_blocks[0]
                    
                    # Strip line numbers if present (just in case)
                    cleaned_lines = []
                    for line in code.splitlines():
                        cleaned_lines.append(re.sub(r'^\s*\d+:\s?', '', line, count=1))
                    code = "\n".join(cleaned_lines)
                    
                    # INTELLIGENT RANGE DETECTION
                    # Detect if the fix code contains a complete function/class/block
                    # and expand the line range accordingly
                    detected_start, detected_end = CodeApplier.detect_code_block_range(
                        original_code=original_code,
                        fix_code=code,
                        suggested_start=line_start,
                        suggested_end=line_end or line_start,
                        file_path=file_path
                    )
                    
                    # Construct changes list to reuse existing logic
                    changes = [{
                        "lines": (detected_start, detected_end),
                        "code": code,
                        "description": "Applied fix from suggestion",
                        "language": lang
                    }]

            # STRATEGY 2: Extract all changes (Multi-part suggestions)
            changes = CodeApplier.smart_extract_changes(suggestion)
            
            if not changes:
                # STRATEGY 3: Fallback to simple extraction (take the LAST code block)
                # The last block is usually the fix (Code: ... Fix: ...)
                code_blocks = CodeApplier.extract_code_blocks(suggestion)
                if code_blocks:
                    # Use the LAST code block, as the first one might be the "Code:" block (original)
                    lang, code = code_blocks[-1]
                    changes = [{
                        "lines": (line_start, line_end or line_start),
                        "code": code,
                        "description": suggestion[:200],
                        "language": lang
                    }]
                else:
                    logging.warning(f"No code blocks found in suggestion: {suggestion[:100]}...")
                    return {
                        "modified_code": original_code,
                        "diff": "",
                        "applied": False,
                        "changes": [],
                        "error": "No code block found in suggestion"
                    }
            
            # Apply all changes sequentially
            modified_code = original_code
            all_changes_applied = []
            
            for change in changes:
                start, end = change["lines"]
                code = change["code"]
                
                try:
                    modified_code = CodeApplier.apply_line_replacement(
                        modified_code,
                        start,
                        end,
                        code
                    )
                    all_changes_applied.append(change)
                    logging.info(f"Applied change at lines {start}-{end}")
                except Exception as e:
                    logging.error(f"Failed to apply change at lines {start}-{end}: {e}")
                    continue
            
            if not all_changes_applied:
                return {
                    "modified_code": original_code,
                    "diff": "",
                    "applied": False,
                    "changes": [],
                    "error": "Failed to apply any changes"
                }
            
            # Generate diff
            diff = CodeApplier.generate_diff(
                original_code, 
                modified_code, 
                file_path,
                context_lines=5 
            )
            
            return {
                "modified_code": modified_code,
                "diff": diff,
                "applied": True,
                "changes": all_changes_applied,
                "error": None
            }
            
        except Exception as e:
            logging.exception(f"Error in smart_apply_suggestion: {e}")
            return {
                "modified_code": original_code,
                "diff": "",
                "applied": False,
                "changes": [],
                "error": str(e)
            }