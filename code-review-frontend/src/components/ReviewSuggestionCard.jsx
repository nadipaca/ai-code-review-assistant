import React, { useState } from 'react';
import {
  Box,
  Button,
  Text,
  VStack,
  HStack,
  Flex,
  IconButton,
  Code,
  Link,
  Badge,
  Divider
} from '@chakra-ui/react';
import { 
  ChevronUpIcon, 
  ChevronDownIcon, 
  CheckIcon, 
  ExternalLinkIcon,
  InfoIcon 
} from '@chakra-ui/icons';

export function ReviewSuggestionCard({ 
  suggestion, 
  onApprove, 
  onReject,
  owner,
  repo
}) {
  const [isExpanded, setIsExpanded] = useState(true);

  // ✅ Generate GitHub file URL
  const getGitHubFileUrl = () => {
    if (!owner || !repo || !suggestion.file) return null;
    
    const lineInfo = suggestion.highlighted_lines?.[0] 
      ? `#L${suggestion.highlighted_lines[0]}`
      : '';
    
    return `https://github.com/${owner}/${repo}/blob/main/${suggestion.file}${lineInfo}`;
  };

  // ✅ Extract plain English explanation from suggestion
  const getSimpleExplanation = () => {
    const text = suggestion.suggestion || suggestion.comment || '';
    
    // Extract "Issue:" or "Impact:" sections
    const issueMatch = text.match(/\*\*Issue:\*\*\s*([^\n*]+)/i);
    const impactMatch = text.split("Impact:")[1]?.trim() || "";;

    console.log(text,"-----", issueMatch);
    
    if (issueMatch) return issueMatch[1].trim();
    if (impactMatch) return impactMatch.trim();
    
    // Fallback: first sentence
    const firstSentence = text.split(/[.!?]/)[0];
    return firstSentence.length > 150 
      ? firstSentence.substring(0, 150) + '...' 
      : firstSentence;
  };

  // ✅ Enhanced diff rendering with context lines
   const renderDiffWithContext = () => {
    if (!suggestion.diff) return null;

    const lines = suggestion.diff.split('\n');
    
    console.log("📊 Diff lines count:", lines.length); // ✅ Debug log
    console.log("📄 First 5 lines:", lines.slice(0, 5)); // ✅ Check if context exists
    
    return (
      <Box mt={4}>
        <HStack mb={2} spacing={2}>
          <Text fontSize="xs" fontWeight="bold" color="gray.600">
            📝 PROPOSED CHANGES
          </Text>
          <Badge colorScheme="blue" fontSize="xs">
            Showing {lines.length} lines (with context)
          </Badge>
        </HStack>

        <Box 
          bg="gray.50" 
          border="1px solid" 
          borderColor="gray.300"
          borderRadius="md"
          overflow="hidden"
          fontFamily="'Fira Code', 'Monaco', 'Menlo', monospace"
          fontSize="13px"
        >
          {lines.map((line, idx) => {
            let bgColor = 'white';
            let textColor = 'gray.800';
            let lineNumberBg = 'gray.100';
            let showLineNumber = true;
            let linePrefix = '';
            let icon = null;

            // File headers (--- a/file, +++ b/file)
            if (line.startsWith('---') || line.startsWith('+++')) {
              bgColor = 'blue.50';
              textColor = 'blue.700';
              showLineNumber = false;
              icon = '📄';
            }
            // Diff position markers (@@ -56,7 +56,8 @@)
            else if (line.startsWith('@@')) {
              bgColor = 'blue.100';
              textColor = 'blue.800';
              showLineNumber = false;
              icon = '📍';
            }
            // Added lines (green)
            else if (line.startsWith('+') && !line.startsWith('+++')) {
              bgColor = 'green.50';
              textColor = 'green.900';
              lineNumberBg = 'green.200';
              linePrefix = '+';
              icon = '✅';
            }
            // Deleted lines (red)
            else if (line.startsWith('-') && !line.startsWith('---')) {
              bgColor = 'red.50';
              textColor = 'red.900';
              lineNumberBg = 'red.200';
              linePrefix = '−';
              icon = '❌';
            }
            // ✅ Context lines (unchanged - these should show up!)
            else if (line.startsWith(' ')) {
              bgColor = 'white';
              textColor = 'gray.700';
              linePrefix = ' ';
              icon = '⋮';  // Vertical ellipsis for context
            }
            else {
              showLineNumber = false;
            }

            const displayLine = line.startsWith('+') || line.startsWith('-') || line.startsWith(' ') 
              ? line.substring(1) 
              : line;

            return (
              <Flex
                key={idx}
                bg={bgColor}
                borderBottom="1px solid"
                borderColor="gray.200"
                _last={{ borderBottom: 'none' }}
                _hover={{ bg: bgColor !== 'white' ? bgColor : 'gray.50' }}
                transition="background 0.15s"
              >
                {/* Icon indicator */}
                {icon && (
                  <Box
                    px={2}
                    py={1}
                    fontSize="10px"
                    color="gray.500"
                    display="flex"
                    alignItems="center"
                  >
                    {icon}
                  </Box>
                )}

                {/* Line prefix (+, -, space) */}
                {showLineNumber && (
                  <Box
                    bg={lineNumberBg}
                    px={3}
                    py={1}
                    minW="50px"
                    textAlign="center"
                    color="gray.600"
                    fontSize="12px"
                    borderRight="2px solid"
                    borderColor={
                      linePrefix === '+' ? 'green.300' : 
                      linePrefix === '−' ? 'red.300' : 
                      'gray.300'
                    }
                    fontWeight="semibold"
                    userSelect="none"
                  >
                    {linePrefix}
                  </Box>
                )}

                {/* Code content */}
                <Code 
                  bg="transparent" 
                  color={textColor} 
                  whiteSpace="pre"
                  px={3}
                  py={1}
                  flex="1"
                  borderRadius="0"
                  fontSize="13px"
                  fontFamily="inherit"
                  fontWeight={linePrefix === '+' || linePrefix === '−' ? '500' : '400'}
                >
                  {displayLine}
                </Code>
              </Flex>
            );
          })}
        </Box>

        {/* Legend */}
        <HStack spacing={4} mt={2} fontSize="xs" color="gray.600">
          <HStack spacing={1}>
            <Box w="12px" h="12px" bg="green.100" borderRadius="sm" />
            <Text>Added</Text>
          </HStack>
          <HStack spacing={1}>
            <Box w="12px" h="12px" bg="red.100" borderRadius="sm" />
            <Text>Removed</Text>
          </HStack>
          <HStack spacing={1}>
            <Box w="12px" h="12px" bg="white" border="1px solid" borderColor="gray.300" borderRadius="sm" />
            <Text>Context (unchanged)</Text>
          </HStack>
        </HStack>
      </Box>
    );
  };

  const githubUrl = getGitHubFileUrl();
  const simpleExplanation = getSimpleExplanation();

  return (
    <Box
      border="2px solid"
      borderColor="gray.300"
      borderRadius="lg"
      overflow="hidden"
      bg="white"
      mb={4}
      boxShadow="md"
      _hover={{ boxShadow: 'lg' }}
      transition="box-shadow 0.2s"
    >
      {/* ✅ Header with clickable file path */}
      <Box bg="gray.100" p={3} borderBottom="2px solid" borderColor="gray.300">
        <HStack justify="space-between" align="start">
          <VStack align="start" spacing={1} flex="1">
            {githubUrl ? (
              <Link 
                href={githubUrl} 
                isExternal
                fontSize="sm" 
                fontWeight="bold" 
                color="blue.600"
                _hover={{ color: 'blue.800', textDecoration: 'underline' }}
              >
                📁 {suggestion.file} <ExternalLinkIcon mx="2px" />
              </Link>
            ) : (
              <Text fontSize="sm" fontWeight="bold" color="gray.800">
                📁 {suggestion.file}
              </Text>
            )}

            {/* ✅ Show line numbers if available */}
            {suggestion.highlighted_lines && suggestion.highlighted_lines.length > 0 && (
              <Badge colorScheme="purple" fontSize="xs" variant="subtle">
                Lines {suggestion.highlighted_lines[0]}
                {suggestion.highlighted_lines.length > 1 
                  ? `-${suggestion.highlighted_lines[suggestion.highlighted_lines.length - 1]}`
                  : ''}
              </Badge>
            )}
          </VStack>

          <IconButton
            size="sm"
            icon={isExpanded ? <ChevronUpIcon /> : <ChevronDownIcon />}
            onClick={() => setIsExpanded(!isExpanded)}
            variant="ghost"
            aria-label="Toggle details"
          />
        </HStack>
      </Box>

      {/* ✅ Content */}
      {isExpanded && (
        <Box p={4}>
          <VStack align="stretch" spacing={4}>
            {/* ✅ Simple explanation in plain English */}
            <Box bg="blue.50" p={3} borderRadius="md" borderLeft="4px solid" borderColor="blue.400">
              <Text fontSize="sm" color="gray.800" lineHeight="tall">
                {simpleExplanation}
              </Text>
            </Box>

            <Divider />

            {/* ✅ Show diff with context */}
            {renderDiffWithContext()}

            {/* ✅ Full AI suggestion (collapsible) */}
            <Box>
              <details>
                <summary style={{ cursor: 'pointer', fontSize: '13px', color: '#4A5568', fontWeight: 'bold' }}>
                  📋 View full AI analysis
                </summary>
                <Box mt={2} p={3} bg="gray.50" borderRadius="md" fontSize="sm" color="gray.700">
                  <Text whiteSpace="pre-wrap">
                    {suggestion.suggestion || suggestion.comment || 'No additional details'}
                  </Text>
                </Box>
              </details>
            </Box>

            {/* ✅ Action Buttons */}
            <HStack spacing={3} justify="flex-end" pt={2}>
              <Button 
                size="sm" 
                variant="outline" 
                colorScheme="red"
                onClick={() => onReject(suggestion)}
              >
                Dismiss
              </Button>
              {suggestion.diff && (
                <Button 
                  size="sm" 
                  colorScheme="green"
                  leftIcon={<CheckIcon />}
                  onClick={() => onApprove(suggestion)}
                >
                  Approve & Apply
                </Button>
              )}
            </HStack>
          </VStack>
        </Box>
      )}
    </Box>
  );
}

export default ReviewSuggestionCard;