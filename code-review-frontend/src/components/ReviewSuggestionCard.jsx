import React, { useState } from 'react';
import {
  Box,
  Button,
  Text,
  VStack,
  HStack,
  Flex,
  IconButton,
  Code
} from '@chakra-ui/react';
import { ChevronUpIcon, ChevronDownIcon, CheckIcon } from '@chakra-ui/icons';

export function ReviewSuggestionCard({ 
  suggestion, 
  onApprove, 
  onReject, 
}) {
   const [isExpanded, setIsExpanded] = useState(true);

  // Enhanced diff rendering with proper GitHub-style formatting
  const renderDiff = () => {
    if (!suggestion.diff) return null;

    const lines = suggestion.diff.split('\n');
    
    return (
      <Box mt={4}>
        <Text fontSize="xs" fontWeight="bold" color="gray.600" mb={2}>
          SUGGESTED CHANGE
        </Text>
        <Box 
          bg="gray.50" 
          border="1px solid" 
          borderColor="gray.300"
          borderRadius="md"
          overflow="hidden"
          fontFamily="'Monaco', 'Menlo', 'Ubuntu Mono', monospace"
          fontSize="13px"
        >
          {lines.map((line, idx) => {
            let bgColor = 'white';
            let textColor = 'gray.800';
            let lineNumberBg = 'gray.100';
            let showLineNumber = true;
            let linePrefix = '';

            // File headers
            if (line.startsWith('+++') || line.startsWith('---')) {
              bgColor = 'gray.100';
              textColor = 'gray.700';
              showLineNumber = false;
              linePrefix = '';
            }
            // Diff position markers
            else if (line.startsWith('@@')) {
              bgColor = 'blue.50';
              textColor = 'blue.700';
              showLineNumber = false;
              linePrefix = '';
            }
            // Added lines
            else if (line.startsWith('+') && !line.startsWith('+++')) {
              bgColor = 'green.50';
              textColor = 'green.900';
              lineNumberBg = 'green.100';
              linePrefix = '+';
            }
            // Deleted lines
            else if (line.startsWith('-') && !line.startsWith('---')) {
              bgColor = 'red.50';
              textColor = 'red.900';
              lineNumberBg = 'red.100';
              linePrefix = '-';
            }
            // Context lines (unchanged)
            else if (line.startsWith(' ')) {
              bgColor = 'white';
              textColor = 'gray.800';
              linePrefix = ' ';
            }
            // Empty or other lines
            else {
              showLineNumber = false;
            }

            // Remove the prefix from the actual line content for display
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
              >
                {showLineNumber && (
                  <Box
                    bg={lineNumberBg}
                    px={3}
                    py={1}
                    minW="50px"
                    textAlign="right"
                    color="gray.600"
                    fontSize="12px"
                    borderRight="1px solid"
                    borderColor="gray.300"
                    userSelect="none"
                  >
                    {linePrefix}
                  </Box>
                )}
                <Code 
                  bg="transparent" 
                  color={textColor} 
                  whiteSpace="pre"
                  px={showLineNumber ? 3 : 2}
                  py={1}
                  flex="1"
                  borderRadius="0"
                  fontSize="13px"
                  fontFamily="inherit"
                >
                  {displayLine}
                </Code>
              </Flex>
            );
          })}
        </Box>
      </Box>
    );
};

const handleCommitSuggestion = () => {
  onApprove(suggestion);
};

return (
      <Box
        border="1px solid"
        borderColor="gray.300"
        borderRadius="md"
        overflow="hidden"
        bg="white"
        mb={4}
      >
        {/* Header - Just file path */}
        <Box bg="gray.50" p={3} borderBottom="1px solid" borderColor="gray.200">
          <HStack justify="space-between">
            <Text fontSize="sm" fontWeight="semibold" color="gray.800">
              📁 {suggestion.file}
            </Text>
            <IconButton
              size="sm"
              icon={isExpanded ? <ChevronUpIcon /> : <ChevronDownIcon />}
              onClick={() => setIsExpanded(!isExpanded)}
              variant="ghost"
            />
          </HStack>
        </Box>
  
        {/* Content */}
        {isExpanded && (
          <Box p={4}>
            <VStack align="stretch" spacing={4}>
              {/* Comment */}
              <Box>
                <Text fontSize="sm" color="gray.800" lineHeight="tall">
                  {suggestion.comment || 'No details provided'}
                </Text>
              </Box>

              {/* Render diff if available */}
              {renderDiff()}
  
              {/* Action Buttons - Only show Approve if there's a diff */}
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
                    onClick={handleCommitSuggestion}
                  >
                    Approve Change
                  </Button>
                )}
              </HStack>
            </VStack>
          </Box>
        )}
      </Box>
    );
};

export default ReviewSuggestionCard;