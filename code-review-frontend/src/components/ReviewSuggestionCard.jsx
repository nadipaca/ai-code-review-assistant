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

  // Parse diff lines from suggestion
  const renderDiff = () => {
    if (!suggestion.diff) return null;

    const lines = suggestion.diff.split('\n');
    
    return (
      <Box 
        bg="white" 
        border="1px solid" 
        borderColor="gray.200" 
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
      border="1px solid"
      borderColor="gray.200"
      borderRadius="md"
      overflow="hidden"
      bg="white"
      mb={4}
    >
      {/* Header with file info */}
      <Flex
        bg="gray.50"
        px={4}
        py={2}
        borderBottom="1px solid"
        borderColor="gray.200"
        align="center"
        justify="space-between"
      >
        <HStack>
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

      {/* AI Comment */}
      <Box px={4} py={3} bg="blue.50" borderBottom="1px solid" borderColor="blue.100">
        {isEditing ? (
          <VStack align="stretch" spacing={2}>
            <Textarea
              value={editedSuggestion}
              onChange={(e) => setEditedSuggestion(e.target.value)}
              size="sm"
              bg="white"
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
          <Text fontSize="sm" color="blue.900" whiteSpace="pre-wrap">
            {suggestion.comment}
          </Text>
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
          colorScheme="green"
          onClick={handleCommitSuggestion}
          isDisabled={!suggestion.applied}
        >
          Commit suggestion
        </Button>
      </Flex>
    </Box>
  );
}

export default ReviewSuggestionCard;