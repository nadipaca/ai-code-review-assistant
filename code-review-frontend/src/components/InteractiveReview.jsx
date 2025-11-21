import React, { useState } from 'react';
import { Box, VStack, Heading, Progress, Text, Button, HStack, Input, FormControl, FormLabel } from '@chakra-ui/react';
import FileReview from './FileReview';
import { applySuggestion } from '../services/api';

export function InteractiveReview({ reviewResults, onComplete, onCancel, owner, repo }) {
  const [approvedChanges, setApprovedChanges] = useState([]);
  const [rejectedSuggestions, setRejectedSuggestions] = useState(new Set());
  const [branchName, setBranchName] = useState(`ai-review-${Date.now()}`);
  const [loadingDiff, setLoadingDiff] = useState(new Set());

  // Track cumulative file content for each file
  const [fileContents, setFileContents] = useState(() => {
    // Initialize with original content for each file
    const initialContents = {};
    reviewResults?.review?.forEach(fileReview => {
      initialContents[fileReview.file] = fileReview.original_content;
    });
    return initialContents;
  });

  // Calculate total suggestions for progress tracking
  const totalSuggestions = React.useMemo(() => {
    if (!reviewResults?.review) return 0;
    return reviewResults.review.reduce((acc, file) => acc + (file.results?.length || 0), 0);
  }, [reviewResults]);

  const handledCount = approvedChanges.length + rejectedSuggestions.size;
  const progress = totalSuggestions === 0 ? 100 : (handledCount / totalSuggestions) * 100;

  // Enhanced approve handler with cumulative state
  const handleApprove = async (suggestion, fileRef) => {
    const suggestionId = `${fileRef.file}-${suggestion.highlighted_lines?.[0]}`;
    setLoadingDiff(new Set([...loadingDiff, suggestionId]));

    try {
      // Get current file content (with all previous approved fixes)
      const currentContent = fileContents[fileRef.file];

      // Apply the suggestion using the pre-computed diff and current content
      const result = await applySuggestion(
        owner,
        repo,
        fileRef.file,
        suggestion.comment,
        suggestion.highlighted_lines?.[0] || 1,
        suggestion.highlighted_lines?.[suggestion.highlighted_lines.length - 1],
        suggestion.diff, // Pass the pre-computed diff
        currentContent   // Pass current content for cumulative changes
      );

      // Update the file content with the newly modified version
      setFileContents(prev => ({
        ...prev,
        [fileRef.file]: result.modified_code
      }));

      // Store approved change
      setApprovedChanges([...approvedChanges, {
        file: fileRef.file,
        original_content: fileRef.original_content,
        modified_content: result.modified_code,
        suggestion: suggestion.comment || "Code improvement",
        diff: result.diff || suggestion.diff || "",
        line_start: suggestion.highlighted_lines?.[0],
        line_end: suggestion.highlighted_lines?.[suggestion.highlighted_lines.length - 1]
      }]);

      // Hide the approved suggestion
      setRejectedSuggestions(new Set([...rejectedSuggestions, suggestion]));
    } catch (error) {
      console.error('Failed to apply suggestion:', error);
      alert('Failed to apply suggestion: ' + (error.message || 'Unknown error'));
    } finally {
      setLoadingDiff((prev) => {
        const next = new Set(prev);
        next.delete(suggestionId);
        return next;
      });
    }
  };

  const handleReject = (suggestion) => {
    setRejectedSuggestions(new Set([...rejectedSuggestions, suggestion]));
  };

  const handleFinalize = () => {
    if (approvedChanges.length === 0) {
      alert('No changes approved');
      return;
    }
    onComplete(approvedChanges, branchName);
  };

  return (
    <Box w="100%" maxW="1400px" mx="auto" p={4}>
      {/* Header & Progress */}
      <Box mb={6} bg="white" p={4} borderRadius="md" boxShadow="sm">
        <VStack align="stretch" spacing={4}>
          <HStack justify="space-between">
            <Heading size="md">AI Code Review</Heading>
            <Text fontWeight="bold" color="blue.600">
              {handledCount} / {totalSuggestions} suggestions handled
            </Text>
          </HStack>
          <Progress value={progress} colorScheme="blue" borderRadius="full" size="sm" />
        </VStack>
      </Box>

      {/* File Reviews */}
      <VStack align="stretch" spacing={6}>
        {reviewResults?.review?.map((fileReview, idx) => {
          // Filter out handled suggestions
          const activeSuggestions = (fileReview.results || []).filter(
            s => !rejectedSuggestions.has(s)
          );

          if (activeSuggestions.length === 0) return null;

          return (
            <FileReview
              key={idx}
              file={fileReview.file}
              originalContent={fileContents[fileReview.file]} // Use cumulative content
              suggestions={activeSuggestions}
              onApprove={(s) => handleApprove(s, fileReview)}
              onReject={handleReject}
            />
          );
        })}
      </VStack>

      {/* Final Actions */}
      {handledCount === totalSuggestions && totalSuggestions > 0 && (
        <Box mt={6} p={6} bg="green.50" borderRadius="md" boxShadow="md" textAlign="center">
          <VStack spacing={4}>
            <Heading size="md" color="green.800">All suggestions reviewed!</Heading>
            <Text color="gray.700">
              You have approved {approvedChanges.length} changes. Ready to create PR?
            </Text>

            <FormControl maxW="400px" mx="auto">
              <FormLabel>Branch Name</FormLabel>
              <Input
                value={branchName}
                onChange={(e) => setBranchName(e.target.value)}
                bg="white"
              />
            </FormControl>

            <HStack justify="center" spacing={4}>
              <Button variant="outline" onClick={onCancel}>
                Cancel
              </Button>
              <Button colorScheme="green" size="lg" onClick={handleFinalize}>
                Create PR
              </Button>
            </HStack>
          </VStack>
        </Box>
      )}
    </Box>
  );
}

// Import FileReview at the top (I will add the import in a separate block or assume it's added)
// Wait, I need to add the import.


export default InteractiveReview;