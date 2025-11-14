import React, { useState } from 'react';
import { Box, VStack, Heading, Progress, Text, Button, HStack } from '@chakra-ui/react';
import ReviewSuggestionCard from './ReviewSuggestionCard';

export function InteractiveReview({ reviewResults, onComplete, onCancel, owner, repo }) {
  const [approvedChanges, setApprovedChanges] = useState([]);
  const [rejectedSuggestions, setRejectedSuggestions] = useState(new Set());

  // Flatten all suggestions into a single array
  const allSuggestions = React.useMemo(() => {
    if (!reviewResults?.review) return [];
    
    return reviewResults.review.flatMap(file => 
      (file.results || []).map(result => ({
        ...result,
        file: file.file,
        owner,
        repo
      }))
    );
  }, [reviewResults, owner, repo]);

  const visibleSuggestions = allSuggestions.filter((_, idx) => 
    !rejectedSuggestions.has(idx)
  );

  const handleApprove = (suggestion, index) => {
    setApprovedChanges([...approvedChanges, {
      file: suggestion.file,
      original_content: suggestion.original_content,
      modified_content: suggestion.modified_content,
      suggestion: suggestion.suggestion,
      line_start: suggestion.highlighted_lines?.[0],
      line_end: suggestion.highlighted_lines?.[suggestion.highlighted_lines.length - 1]
    }]);
    
    setRejectedSuggestions(new Set([...rejectedSuggestions, index]));
  };

  const handleReject = (_, index) => {
    setRejectedSuggestions(new Set([...rejectedSuggestions, index]));
  };

  const handleEditSuggestion = (updatedSuggestion) => {
    // Update suggestion in state (you'll need to manage this)
    console.log('Edit suggestion:', updatedSuggestion);
  };

  const handleFinalize = () => {
    if (approvedChanges.length === 0) {
      alert('No changes approved');
      return;
    }
    onComplete(approvedChanges);
  };

  const progressPercent = (rejectedSuggestions.size / allSuggestions.length) * 100;

  return (
    <Box w="100%" maxW="1200px" mx="auto" p={4}>
      {/* Progress Header */}
      <VStack align="stretch" spacing={4} mb={6}>
        <Heading size="md" color="gray.700">
          Code Review - {approvedChanges.length} approved, {rejectedSuggestions.size - approvedChanges.length} dismissed
        </Heading>
        <Progress value={progressPercent} colorScheme="green" />
        <Text fontSize="sm" color="gray.600">
          {visibleSuggestions.length} suggestion(s) remaining
        </Text>
      </VStack>

      {/* Suggestions List */}
      <VStack align="stretch" spacing={4}>
        {visibleSuggestions.map((suggestion, idx) => (
          <ReviewSuggestionCard
            key={idx}
            suggestion={suggestion}
            onApprove={(s) => handleApprove(s, allSuggestions.indexOf(suggestion))}
            onReject={(s) => handleReject(s, allSuggestions.indexOf(suggestion))}
            onEdit={handleEditSuggestion}
          />
        ))}
      </VStack>

      {/* Final Actions */}
      {visibleSuggestions.length === 0 && (
        <Box mt={6} p={4} bg="green.50" borderRadius="md" textAlign="center">
          <Text mb={3}>All suggestions reviewed!</Text>
          <HStack justify="center" spacing={3}>
            <Button variant="outline" onClick={onCancel}>
              Cancel
            </Button>
            <Button colorScheme="green" onClick={handleFinalize}>
              Create PR with {approvedChanges.length} changes
            </Button>
          </HStack>
        </Box>
      )}
    </Box>
  );
}

export default InteractiveReview;