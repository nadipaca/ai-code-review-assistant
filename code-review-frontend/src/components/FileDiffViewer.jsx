import React, { useState, useMemo } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Button,
  Badge,
  Collapse,
  IconButton,
  Flex,
  Tooltip
} from '@chakra-ui/react';
import { ChevronDownIcon, ChevronRightIcon, ChatIcon } from '@chakra-ui/icons';
import { parseDiff, groupUnchangedLines, extractIssueDetails } from '../utils/diffParser';

/**
 * GitHub-style split diff viewer with side-by-side comparison
 * Shows accurate line numbers and collapsible unchanged sections
 */
export function FileDiffViewer({ 
  file, 
  issues, 
  onApproveIssue, 
  onRejectIssue,
  onApproveAll,
  onRejectAll 
}) {
  const [expandedIssues, setExpandedIssues] = useState(new Set());
  const [expandedCollapsed, setExpandedCollapsed] = useState(new Set());

  // Merge all diffs for this file
  const mergedDiff = useMemo(() => {
    if (!issues || issues.length === 0) return '';
    
    // If single issue, use its diff directly
    if (issues.length === 1) return issues[0].diff || '';
    
    // For multiple issues, concatenate diffs
    // TODO: Implement proper diff merging if needed
    return issues.map(issue => issue.diff || '').filter(d => d).join('\n');
  }, [issues]);

  // Parse the merged diff
  const parsedDiff = useMemo(() => {
    try {
      return parseDiff(mergedDiff);
    } catch (error) {
      console.error('Failed to parse diff:', error);
      return { lines: [], oldStart: 1, newStart: 1 };
    }
  }, [mergedDiff]);

  // Group unchanged lines for collapsing
  const processedLines = useMemo(() => {
    try {
      return groupUnchangedLines(parsedDiff.lines, 5);
    } catch (error) {
      console.error('Failed to group lines:', error);
      return parsedDiff.lines || [];
    }
  }, [parsedDiff]);

  // Create a mapping of line numbers to issues for inline comments
  const lineToIssues = useMemo(() => {
    const mapping = {};
    issues.forEach((issue, idx) => {
      (issue.highlighted_lines || []).forEach(lineNum => {
        if (!mapping[lineNum]) mapping[lineNum] = [];
        mapping[lineNum].push({ ...issue, issueIndex: idx });
      });
    });
    return mapping;
  }, [issues]);

  const toggleIssue = (index) => {
    const newExpanded = new Set(expandedIssues);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedIssues(newExpanded);
  };

  const toggleCollapsed = (index) => {
    const newExpanded = new Set(expandedCollapsed);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedCollapsed(newExpanded);
  };

  const getSeverityColor = (severity) => {
    switch (severity?.toUpperCase()) {
      case 'HIGH': return 'red';
      case 'MEDIUM': return 'orange';
      case 'LOW': return 'yellow';
      default: return 'gray';
    }
  };

  return (
    <Box
      w="100%"
      border="1px solid"
      borderColor="gray.300"
      borderRadius="md"
      overflow="hidden"
      bg="white"
      mb={4}
    >
      {/* File Header */}
      <Box bg="gray.50" px={4} py={3} borderBottom="1px solid" borderColor="gray.300">
        <Flex justify="space-between" align="center" mb={2}>
          <HStack spacing={3}>
            <Text fontWeight="bold" fontSize="md" fontFamily="monospace">
              📄 {file}
            </Text>
            <Badge colorScheme="blue" fontSize="xs">
              {issues.length} {issues.length === 1 ? 'issue' : 'issues'}
            </Badge>
          </HStack>

          <HStack spacing={2}>
            <Button 
              size="sm" 
              colorScheme="green" 
              onClick={onApproveAll}
              variant="outline"
            >
              Approve All
            </Button>
            <Button 
              size="sm" 
              colorScheme="red" 
              onClick={onRejectAll}
              variant="outline"
            >
              Reject All
            </Button>
          </HStack>
        </Flex>

        {/* Issue Summary */}
        <VStack align="stretch" spacing={1}>
          {issues.map((issue, idx) => {
            const details = extractIssueDetails(issue.comment || issue.suggestion);
            return (
              <HStack key={idx} spacing={2} fontSize="xs">
                <Badge colorScheme={getSeverityColor(details.severity)} fontSize="2xs">
                  {details.severity}
                </Badge>
                <Text color="gray.600">
                  Lines {issue.highlighted_lines?.[0] || '?'}: {details.title}
                </Text>
              </HStack>
            );
          })}
        </VStack>
      </Box>

      {/* Split Diff View */}
      <Box
        fontFamily="'Fira Code', 'Monaco', 'Menlo', monospace"
        fontSize="13px"
        bg="white"
      >
        {/* Show fallback if no diff lines parsed */}
        {processedLines.length === 0 ? (
          <Box p={4}>
            <VStack align="stretch" spacing={3}>
              {issues.map((issue, idx) => {
                const details = extractIssueDetails(issue.comment || issue.suggestion);
                return (
                  <Box
                    key={idx}
                    p={3}
                    bg="blue.50"
                    borderRadius="md"
                    border="1px solid"
                    borderColor="blue.200"
                  >
                    <HStack justify="space-between" mb={2}>
                      <HStack spacing={2}>
                        <Badge colorScheme={getSeverityColor(details.severity)}>
                          {details.severity}
                        </Badge>
                        <Text fontWeight="bold" fontSize="sm">
                          Line {issue.highlighted_lines?.[0] || '?'}
                        </Text>
                      </HStack>
                      <HStack spacing={2}>
                        <Button
                          size="xs"
                          colorScheme="green"
                          onClick={() => onApproveIssue(idx)}
                        >
                          Approve
                        </Button>
                        <Button
                          size="xs"
                          colorScheme="red"
                          variant="outline"
                          onClick={() => onRejectIssue(idx)}
                        >
                          Reject
                        </Button>
                      </HStack>
                    </HStack>
                    <Text fontSize="sm" color="gray.700">
                      {details.title}
                    </Text>
                  </Box>
                );
              })}
            </VStack>
          </Box>
        ) : (
          // Render normal split diff view
          processedLines.map((line, idx) => {
          // Render collapsed section
          if (line.type === 'collapsed') {
            const isExpanded = expandedCollapsed.has(idx);
            return (
              <Box key={`collapsed-${idx}`}>
                {!isExpanded ? (
                  <Flex
                    bg="gray.50"
                    borderY="1px solid"
                    borderColor="gray.200"
                    align="center"
                    justify="center"
                    py={1}
                    cursor="pointer"
                    _hover={{ bg: 'gray.100' }}
                    onClick={() => toggleCollapsed(idx)}
                  >
                    <HStack spacing={2} color="blue.600" fontSize="xs">
                      <ChevronRightIcon />
                      <Text>
                        ⬍ {line.count} unchanged lines ⬍
                      </Text>
                    </HStack>
                  </Flex>
                ) : (
                  <>
                    <Flex
                      bg="gray.50"
                      borderY="1px solid"
                      borderColor="gray.200"
                      align="center"
                      justify="center"
                      py={1}
                      cursor="pointer"
                      _hover={{ bg: 'gray.100' }}
                      onClick={() => toggleCollapsed(idx)}
                    >
                      <HStack spacing={2} color="blue.600" fontSize="xs">
                        <ChevronDownIcon />
                        <Text>Collapse {line.count} lines</Text>
                      </HStack>
                    </Flex>
                    {line.lines.map((contextLine, cIdx) => (
                      <SplitDiffLine
                        key={`collapsed-${idx}-${cIdx}`}
                        line={contextLine}
                        lineToIssues={lineToIssues}
                        expandedIssues={expandedIssues}
                        toggleIssue={toggleIssue}
                        getSeverityColor={getSeverityColor}
                        onApproveIssue={onApproveIssue}
                        onRejectIssue={onRejectIssue}
                      />
                    ))}
                  </>
                )}
              </Box>
            );
          }

          // Render hunk header
          if (line.type === 'hunk') {
            return (
              <Box
                key={`hunk-${idx}`}
                bg="blue.50"
                px={2}
                py={1}
                borderY="1px solid"
                borderColor="blue.200"
              >
                <Text color="blue.700" fontSize="xs">
                  {line.content}
                </Text>
              </Box>
            );
          }

          // Render regular diff line
          return (
            <SplitDiffLine
              key={idx}
              line={line}
              lineToIssues={lineToIssues}
              expandedIssues={expandedIssues}
              toggleIssue={toggleIssue}
              getSeverityColor={getSeverityColor}
              onApproveIssue={onApproveIssue}
              onRejectIssue={onRejectIssue}
            />
          );
        }))}
      </Box>
    </Box>
  );
}

/**
 * Individual split diff line with old/new side-by-side
 */
function SplitDiffLine({ 
  line, 
  lineToIssues, 
  expandedIssues, 
  toggleIssue, 
  getSeverityColor,
  onApproveIssue,
  onRejectIssue 
}) {
  // Determine colors based on line type
  let oldBg = 'white';
  let newBg = 'white';
  let oldColor = 'gray.800';
  let newColor = 'gray.800';
  let oldLineNumBg = 'gray.50';
  let newLineNumBg = 'gray.50';

  if (line.type === 'delete') {
    oldBg = 'red.50';
    oldColor = 'red.900';
    oldLineNumBg = 'red.100';
    newBg = 'gray.50';
  } else if (line.type === 'add') {
    newBg = 'green.50';
    newColor = 'green.900';
    newLineNumBg = 'green.100';
    oldBg = 'gray.50';
  }

  // Check if this line has associated issues/comments
  const oldLineIssues = lineToIssues[line.oldLineNum] || [];
  const newLineIssues = lineToIssues[line.newLineNum] || [];
  const hasIssues = oldLineIssues.length > 0 || newLineIssues.length > 0;
  const allIssues = [...oldLineIssues, ...newLineIssues];

  return (
    <Box>
      {/* Split View: Old | New */}
      <Flex borderBottom="1px solid" borderColor="gray.100">
        {/* Old (Left) Side */}
        <Flex flex={1} bg={oldBg} borderRight="1px solid" borderColor="gray.200">
          {/* Old Line Number */}
          <Box
            w="50px"
            textAlign="right"
            px={2}
            py={1}
            bg={oldLineNumBg}
            borderRight="1px solid"
            borderColor="gray.300"
            userSelect="none"
            color="gray.500"
            fontSize="xs"
          >
            {line.oldLineNum || ''}
          </Box>
          
          {/* Old Code Content */}
          <Box 
            flex={1} 
            px={3} 
            py={1} 
            color={oldColor} 
            whiteSpace="pre-wrap"
            wordBreak="break-word"
            fontFamily="'Fira Code', 'Monaco', 'Menlo', monospace"
          >
            {line.type === 'delete' && <Text as="span" color="red.600">- </Text>}
            {line.content || ' '}
          </Box>
        </Flex>

        {/* New (Right) Side */}
        <Flex flex={1} bg={newBg} position="relative">
          {/* New Line Number */}
          <Box
            w="50px"
            textAlign="right"
            px={2}
            py={1}
            bg={newLineNumBg}
            borderRight="1px solid"
            borderColor="gray.300"
            userSelect="none"
            color="gray.500"
            fontSize="xs"
          >
            {line.newLineNum || ''}
          </Box>
          
          {/* New Code Content */}
          <Box 
            flex={1} 
            px={3} 
            py={1} 
            color={newColor} 
            whiteSpace="pre-wrap"
            wordBreak="break-word"
            fontFamily="'Fira Code', 'Monaco', 'Menlo', monospace"
          >
            {line.type === 'add' && <Text as="span" color="green.600">+ </Text>}
            {line.content || ' '}
          </Box>

          {/* Comment Button */}
          {hasIssues && (
            <Box position="absolute" right={2} top="50%" transform="translateY(-50%)">
              <Tooltip label="View issue details" fontSize="xs">
                <IconButton
                  icon={<ChatIcon />}
                  size="xs"
                  colorScheme="blue"
                  variant="ghost"
                  onClick={() => toggleIssue(allIssues[0].issueIndex)}
                />
              </Tooltip>
            </Box>
          )}
        </Flex>
      </Flex>

      {/* Inline Issue Thread (GitHub style) */}
      {hasIssues && allIssues.map((issue) => {
        const isExpanded = expandedIssues.has(issue.issueIndex);
        const details = extractIssueDetails(issue.comment || issue.suggestion);

        return (
          <Collapse key={issue.issueIndex} in={isExpanded}>
            <Box
              bg="blue.50"
              borderBottom="1px solid"
              borderColor="blue.200"
              p={3}
              ml="50px"
            >
              <VStack align="stretch" spacing={2}>
                <HStack spacing={2}>
                  <Badge colorScheme={getSeverityColor(details.severity)} fontSize="xs">
                    {details.severity}
                  </Badge>
                  <Text fontWeight="bold" fontSize="sm">
                    {details.title}
                  </Text>
                </HStack>

                <Text fontSize="sm" color="gray.700">
                  {details.description}
                </Text>

                <HStack spacing={2} pt={2}>
                  <Button
                    size="xs"
                    colorScheme="green"
                    onClick={() => onApproveIssue(issue.issueIndex)}
                  >
                    Approve
                  </Button>
                  <Button
                    size="xs"
                    colorScheme="red"
                    variant="outline"
                    onClick={() => onRejectIssue(issue.issueIndex)}
                  >
                    Reject
                  </Button>
                </HStack>
              </VStack>
            </Box>
          </Collapse>
        );
      })}
    </Box>
  );
}

export default FileDiffViewer;
