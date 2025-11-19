/**
 * Parse unified diff format and extract line-by-line information
 * for split diff view with accurate old/new line numbers
 */

/**
 * Parse a unified diff into structured line information
 * @param {string} diff - Unified diff string
 * @returns {Object} Parsed diff data with line mappings
 */
export function parseDiff(diff) {
  if (!diff) return { lines: [], oldStart: 1, newStart: 1 };

  const diffLines = diff.split('\n');
  const result = {
    lines: [],
    oldStart: 1,
    newStart: 1,
    oldFileName: '',
    newFileName: ''
  };

  let oldLineNum = 1;
  let newLineNum = 1;
  let inHunk = false;

  for (let i = 0; i < diffLines.length; i++) {
    const line = diffLines[i];

    // Parse file headers
    if (line.startsWith('--- ')) {
      result.oldFileName = line.substring(4).replace(/^a\//, '');
      continue;
    }
    if (line.startsWith('+++ ')) {
      result.newFileName = line.substring(4).replace(/^b\//, '');
      continue;
    }

    // Parse hunk header (@@ -oldStart,oldCount +newStart,newCount @@)
    if (line.startsWith('@@')) {
      const match = line.match(/@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@/);
      if (match) {
        oldLineNum = parseInt(match[1], 10);
        newLineNum = parseInt(match[3], 10);
        result.oldStart = oldLineNum;
        result.newStart = newLineNum;
        inHunk = true;

        result.lines.push({
          type: 'hunk',
          content: line,
          oldLineNum: null,
          newLineNum: null
        });
      }
      continue;
    }

    if (!inHunk) continue;

    // Parse diff content lines
    if (line.startsWith('-') && !line.startsWith('---')) {
      // Deleted line - only has old line number
      result.lines.push({
        type: 'delete',
        content: line.substring(1),
        oldLineNum: oldLineNum,
        newLineNum: null
      });
      oldLineNum++;
    } else if (line.startsWith('+') && !line.startsWith('+++')) {
      // Added line - only has new line number
      result.lines.push({
        type: 'add',
        content: line.substring(1),
        oldLineNum: null,
        newLineNum: newLineNum
      });
      newLineNum++;
    } else if (line.startsWith(' ')) {
      // Unchanged line - has both line numbers
      result.lines.push({
        type: 'context',
        content: line.substring(1),
        oldLineNum: oldLineNum,
        newLineNum: newLineNum
      });
      oldLineNum++;
      newLineNum++;
    } else if (line === '') {
      // Empty line in context
      result.lines.push({
        type: 'context',
        content: '',
        oldLineNum: oldLineNum,
        newLineNum: newLineNum
      });
      oldLineNum++;
      newLineNum++;
    }
  }

  return result;
}

/**
 * Group consecutive unchanged lines for collapsing
 * @param {Array} lines - Parsed diff lines
 * @param {number} threshold - Minimum consecutive lines to collapse (default: 5)
 * @returns {Array} Lines with collapse markers
 */
export function groupUnchangedLines(lines, threshold = 5) {
  const result = [];
  let unchangedGroup = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.type === 'context') {
      unchangedGroup.push(line);
    } else {
      // Flush unchanged group if it meets threshold
      if (unchangedGroup.length >= threshold) {
        result.push({
          type: 'collapsed',
          count: unchangedGroup.length,
          lines: unchangedGroup,
          firstLine: unchangedGroup[0],
          lastLine: unchangedGroup[unchangedGroup.length - 1]
        });
      } else {
        // Too few to collapse, add them normally
        result.push(...unchangedGroup);
      }
      unchangedGroup = [];
      result.push(line);
    }
  }

  // Handle remaining unchanged group at end
  if (unchangedGroup.length >= threshold) {
    result.push({
      type: 'collapsed',
      count: unchangedGroup.length,
      lines: unchangedGroup,
      firstLine: unchangedGroup[0],
      lastLine: unchangedGroup[unchangedGroup.length - 1]
    });
  } else {
    result.push(...unchangedGroup);
  }

  return result;
}

/**
 * Merge multiple diffs for the same file into a single unified diff
 * @param {Array} diffs - Array of diff strings for the same file
 * @returns {string} Merged unified diff
 */
export function mergeDiffs(diffs) {
  if (!diffs || diffs.length === 0) return '';
  if (diffs.length === 1) return diffs[0];

  // For now, return concatenated diffs
  // TODO: Implement proper diff merging if hunks overlap
  const allParsed = diffs.map(parseDiff);
  
  // Simple concatenation approach - works if hunks don't overlap
  const firstDiff = allParsed[0];
  let mergedLines = [...firstDiff.lines];

  for (let i = 1; i < allParsed.length; i++) {
    const parsed = allParsed[i];
    // Skip file headers and add hunk content
    mergedLines.push(...parsed.lines);
  }

  return reconstructDiff(firstDiff.oldFileName, firstDiff.newFileName, mergedLines);
}

/**
 * Reconstruct unified diff from parsed lines
 * @param {string} oldFileName
 * @param {string} newFileName
 * @param {Array} lines
 * @returns {string}
 */
function reconstructDiff(oldFileName, newFileName, lines) {
  let result = '';
  if (oldFileName) result += `--- a/${oldFileName}\n`;
  if (newFileName) result += `+++ b/${newFileName}\n`;

  for (const line of lines) {
    if (line.type === 'hunk') {
      result += line.content + '\n';
    } else if (line.type === 'delete') {
      result += '-' + line.content + '\n';
    } else if (line.type === 'add') {
      result += '+' + line.content + '\n';
    } else if (line.type === 'context') {
      result += ' ' + line.content + '\n';
    }
  }

  return result;
}

/**
 * Extract issue comments from suggestion text
 * @param {string} suggestionText - Full suggestion/comment text
 * @returns {Object} Extracted issue details
 */
export function extractIssueDetails(suggestionText) {
  if (!suggestionText) return { title: '', description: '', severity: 'MEDIUM' };

  const text = suggestionText;

  // Extract severity (look for HIGH, MEDIUM, LOW anywhere in text)
  const severityMatch = text.match(/\b(HIGH|MEDIUM|LOW)\b/i);
  const severity = severityMatch ? severityMatch[1].toUpperCase() : 'MEDIUM';

  // For simple format: "No input validation in `fetchUserData` function (Line 7)"
  // Use the entire comment as the title
  const title = text.trim();

  // Extract issue title/summary - try multiple patterns
  const issueMatch = text.match(/\*\*Issue:\*\*\s*([^\n*]+)/i);
  const betterTitle = issueMatch ? issueMatch[1].trim() : title;

  // Extract impact/description
  const impactMatch = text.match(/\*\*Impact:\*\*\s*([^\n*]+)/i);
  const suggestionMatch = text.match(/\*\*Suggestion:\*\*\s*([^\n*]+)/i);
  
  const description = impactMatch 
    ? impactMatch[1].trim() 
    : suggestionMatch 
      ? suggestionMatch[1].trim() 
      : ''; // No separate description if using simple format

  return { 
    title: betterTitle, 
    description: description || betterTitle, 
    severity 
  };
}
