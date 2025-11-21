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
                    
                    code = "\n".join(cleaned_lines)
                    
                    # Construct changes list to reuse existing logic
                    changes = [{
                        "lines": (line_start, line_end or line_start),
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