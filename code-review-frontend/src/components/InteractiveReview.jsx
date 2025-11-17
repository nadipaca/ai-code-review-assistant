import React, { useState } from 'react';
import { Box, VStack, Heading, Progress, Text, Button, HStack, Input, FormControl, FormLabel } from '@chakra-ui/react';
import ReviewSuggestionCard from './ReviewSuggestionCard';
import { applySuggestion } from '../services/api';

export function InteractiveReview({ reviewResults, onComplete, onCancel, owner, repo }) {
  const [approvedChanges, setApprovedChanges] = useState([]);
  const [rejectedSuggestions, setRejectedSuggestions] = useState(new Set());
  const [branchName, setBranchName] = useState(`ai-review-${Date.now()}`);
  const [loadingDiff, setLoadingDiff] = useState(new Set());

  // Flatten all suggestions into a single array
  const allSuggestions = React.useMemo(() => {
    if (!reviewResults?.review) return [];
    
    return reviewResults.review.flatMap(file => 
      // ✅ Use "results" to match backend
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

  // Enhanced approve handler that fetches diff
  const handleApprove = async (suggestion, index) => {
    setLoadingDiff(new Set([...loadingDiff, index]));
    
    try {
      // Fetch the diff from backend
      const result = await applySuggestion(
        suggestion.owner,
        suggestion.repo,
        suggestion.file,
        suggestion.suggestion || suggestion.comment,
        suggestion.highlighted_lines?.[0] || 1,
        suggestion.highlighted_lines?.[suggestion.highlighted_lines.length - 1]
      );

      setApprovedChanges([...approvedChanges, {
        file: suggestion.file,
        original_content: result.original_content || "",
        modified_content: result.modified_code || "",
        suggestion: suggestion.suggestion || suggestion.comment || "Code improvement",
        diff: result.diff || "",  // ✅ Include diff
        line_start: suggestion.highlighted_lines?.[0],
        line_end: suggestion.highlighted_lines?.[suggestion.highlighted_lines.length - 1]
      }]);
      
      setRejectedSuggestions(new Set([...rejectedSuggestions, index]));
    } catch (error) {
      console.error('Failed to apply suggestion:', error);
      alert('Failed to generate diff: ' + (error.message || 'Unknown error'));
    } finally {
      setLoadingDiff((prev) => {
        const next = new Set(prev);
        next.delete(index);
        return next;
      });
    }
  };

  const handleReject = (_, index) => {
    setRejectedSuggestions(new Set([...rejectedSuggestions, index]));
  };

  const handleEditSuggestion = (updatedSuggestion) => {
    console.log('Edit suggestion:', updatedSuggestion);
  };

  const handleFinalize = () => {
    if (approvedChanges.length === 0) {
      alert('No changes approved');
      return;
    }
    onComplete(approvedChanges, branchName);
  };
  
  return (
    <Box w="100%" maxW="1200px" mx="auto" p={4} bg="white" borderRadius="md" boxShadow="lg">
      {/* Progress Header */}
 <VStack align="stretch" spacing={4}>
        {visibleSuggestions.map((suggestion, idx) => {
          const actualIndex = allSuggestions.indexOf(suggestion);
          const isLoading = loadingDiff.has(actualIndex);
          
          return (
            <ReviewSuggestionCard
              key={actualIndex}
              suggestion={suggestion}
              onApprove={(s) => handleApprove(s, actualIndex)}
              onReject={(s) => handleReject(s, actualIndex)}
              isLoading={isLoading}
              owner={owner}  // ✅ Pass owner
              repo={repo}    // ✅ Pass repo
            />
          );
        })}
      </VStack>
  
      {/* Suggestions List */}
      <VStack align="stretch" spacing={4}>
        {visibleSuggestions.map((suggestion) => {
          const actualIndex = allSuggestions.indexOf(suggestion);
          const isLoading = loadingDiff.has(actualIndex);
          
          return (
            <ReviewSuggestionCard
              key={actualIndex}
              suggestion={suggestion}
              onApprove={(s) => handleApprove(s, actualIndex)}
              onReject={(s) => handleReject(s, actualIndex)}
              onEdit={handleEditSuggestion}
              isLoading={isLoading}
            />
          );
        })}
      </VStack>
  
      {/* Final Actions */}
      {visibleSuggestions.length === 0 && (
        <Box mt={6} p={4} bg="green.50" borderRadius="md">
          <VStack align="stretch" spacing={4}>
            <Text color="gray.800" textAlign="center" fontWeight="bold">
              All suggestions reviewed! Ready to create PR.
            </Text>
            
            <FormControl>
              <FormLabel fontSize="sm" color="gray.700">Branch Name</FormLabel>
              <Input 
                value={branchName}
                onChange={(e) => setBranchName(e.target.value)}
                placeholder="ai-review-branch"
                size="sm"
                bg="white"
              />
            </FormControl>
            
            <HStack justify="center" spacing={3}>
              <Button variant="outline" onClick={onCancel}>
                Cancel
              </Button>
              <Button colorScheme="green" onClick={handleFinalize}>
                Create PR with {approvedChanges.length} changes
              </Button>
            </HStack>
          </VStack>
        </Box>
      )}
    </Box>
  );
}

export default InteractiveReview;