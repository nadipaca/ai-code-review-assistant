import React, { useState } from 'react';
import {
  Box,
  Button,
  Text,
  VStack,
  HStack,
  Badge,
  Code,
  Textarea,
  Flex,
  IconButton,
  useToast
} from '@chakra-ui/react';
import { CheckIcon, CloseIcon, EditIcon } from '@chakra-ui/icons';

export function ReviewSuggestionCard({ 
  suggestion, 
  onApprove, 
  onReject, 
  onEdit 
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedSuggestion, setEditedSuggestion] = useState(suggestion.comment);
  const toast = useToast();

  const getSeverityInfo = () => {
    const comment = suggestion.comment || "";
    if (comment.includes("**Severity:** HIGH") || comment.includes("🔴")) {
      return { level: "HIGH", color: "red", label: "High Severity" };
    }
    if (comment.includes("**Severity:** MEDIUM") || comment.includes("🟠")) {
      return { level: "MEDIUM", color: "orange", label: "Medium Severity" };
    }
    return { level: "INFO", color: "blue", label: "Information" };
  };
// ✅ Detect dangerous deletions
  const isDeletion = suggestion.diff && suggestion.diff.includes('--- a/') && 
                     (suggestion.diff.match(/^-/gm) || []).length > 10;
  const severity = getSeverityInfo();

  // Parse diff lines from suggestion
  const renderDiff = () => {
    if (!suggestion.diff) return null;

    const lines = suggestion.diff.split('\n');
    
    return (
      <Box 
        bg="white" 
        border="2px solid" 
        borderColor={isDeletion ? "red.500" : severity.level === "HIGH" ? "red.300" : "orange.300"}
        borderRadius="md"
        overflow="hidden"
        fontFamily="monospace"
        fontSize="13px"
      >
        {lines.map((line, idx) => {
          let bgColor = 'white';
          let textColor = 'gray.800';
          let symbol = '';

          if (line.startsWith('+++') || line.startsWith('---')) {
            bgColor = 'gray.50';
            textColor = 'gray.600';
          } else if (line.startsWith('+')) {
            bgColor = 'green.50';
            textColor = 'green.800';
            symbol = '+';
          } else if (line.startsWith('-')) {
            bgColor = 'red.50';
            textColor = 'red.800';
            symbol = '-';
          } else if (line.startsWith('@@')) {
            bgColor = 'blue.50';
            textColor = 'blue.700';
          }

          return (
            <Box
              key={idx}
              bg={bgColor}
              px={3}
              py={0.5}
              _hover={{ 
                bg: line.startsWith('+') ? 'green.100' : 
                    line.startsWith('-') ? 'red.100' : bgColor 
              }}
            >
              <Code bg="transparent" color={textColor} whiteSpace="pre">
                {symbol && <Text as="span" fontWeight="bold" mr={2}>{symbol}</Text>}
                {line}
              </Code>
            </Box>
          );
        })}
      </Box>
    );
  };

  const handleCommitSuggestion = () => {
    onApprove(suggestion);
    toast({
      title: 'Suggestion approved',
      status: 'success',
      duration: 2000
    });
  };

  return (
    <Box
      border="2px solid"
      borderColor={severity.level === "HIGH" ? "red.300" : severity.level === "MEDIUM" ? "orange.300" : "gray.200"}
      borderRadius="md"
      overflow="hidden"
      bg="white"
      mb={4}
    >
      {/* Header with file info */}
      <Flex
        bg={severity.level === "HIGH" ? "red.50" : severity.level === "MEDIUM" ? "orange.50" : "gray.50"}
        px={4}
        py={2}
        borderBottom="1px solid"
        borderColor="gray.200"
        align="center"
        justify="space-between"
      >
        <HStack>
          <Badge colorScheme={severity.color}>
            {severity.label}
          </Badge>
          <Badge colorScheme={suggestion.applied ? 'green' : 'yellow'}>
            {suggestion.applied ? 'Ready to apply' : 'Review only'}
          </Badge>
          <Text fontSize="sm" fontWeight="medium" color="gray.700">
            {suggestion.file}
          </Text>
          {suggestion.highlighted_lines && (
            <Badge colorScheme="blue" fontSize="xs">
              Lines {suggestion.highlighted_lines[0]}-{suggestion.highlighted_lines[suggestion.highlighted_lines.length - 1]}
            </Badge>
          )}
        </HStack>
        <IconButton
          icon={<EditIcon />}
          size="xs"
          variant="ghost"
          onClick={() => setIsEditing(!isEditing)}
        />
      </Flex>

      {isDeletion && (
        <Box px={4} py={2} bg="red.50" borderBottom="1px solid" borderColor="red.200">
          <Text fontSize="xs" color="red.800" fontWeight="bold">
            ⚠️ WARNING: This suggestion removes significant code. Review carefully before applying!
          </Text>
        </Box>
      )}
      
      {/* AI Comment with Explanation */}
      <Box px={4} py={3} bg="blue.50" borderBottom="1px solid" borderColor="blue.100">
        {isEditing ? (
          <VStack align="stretch" spacing={2}>
            <Textarea
              value={editedSuggestion}
              onChange={(e) => setEditedSuggestion(e.target.value)}
              size="sm"
              bg="white"
              rows={6}
            />
            <HStack justify="flex-end">
              <Button size="xs" onClick={() => setIsEditing(false)}>Cancel</Button>
              <Button 
                size="xs" 
                colorScheme="blue"
                onClick={() => {
                  onEdit({ ...suggestion, comment: editedSuggestion });
                  setIsEditing(false);
                }}
              >
                Save
              </Button>
            </HStack>
          </VStack>
        ) : (
          <Box>
            <Text fontSize="sm" color="blue.900" whiteSpace="pre-wrap">
              {suggestion.comment}
            </Text>
            {/* ✅ Show impact/explanation prominently */}
            {suggestion.comment && suggestion.comment.includes("**Impact:**") && (
              <Box mt={3} p={2} bg="yellow.50" borderLeft="4px solid" borderColor="yellow.400" borderRadius="md">
                <Text fontSize="xs" fontWeight="bold" color="gray.700">💡 Why this matters:</Text>
                <Text fontSize="xs" color="gray.600" mt={1}>
                  {suggestion.comment.match(/\*\*Impact:\*\* (.+?)(?:\n|\*\*)/)?.[1] || "See details above"}
                </Text>
              </Box>
            )}
          </Box>
        )}
      </Box>

      {/* Diff View */}
      <Box p={4}>
        {renderDiff()}
      </Box>

      {/* Action Buttons */}
      <Flex
        px={4}
        py={3}
        bg="gray.50"
        borderTop="1px solid"
        borderColor="gray.200"
        justify="flex-end"
        gap={3}
      >
        <Button
          leftIcon={<CloseIcon />}
          size="sm"
          variant="outline"
          onClick={() => onReject(suggestion)}
        >
          Dismiss
        </Button>
        <Button
          leftIcon={<CheckIcon />}
          size="sm"
          colorScheme={severity.level === "HIGH" ? "red" : "green"}
          onClick={handleCommitSuggestion}
          isDisabled={!suggestion.applied}
        >
          {severity.level === "HIGH" ? "⚠️ Apply Critical Fix" : "Commit suggestion"}
        </Button>
      </Flex>
    </Box>
  );
}

export default ReviewSuggestionCard;