import React, { useState, useEffect } from 'react';
import {
  Box,
  VStack,
  Heading,
  Progress,
  Text,
  Button,
  HStack,
  Input,
  FormControl,
  FormLabel,
  Container
} from '@chakra-ui/react';
import FileDiffViewer from './FileDiffViewer';

/**
 * Full-screen review page that opens in a new tab
 * Shows file-grouped diffs with individual and bulk approve/reject controls
 */
export function FullscreenReview() {
  const [approvedChanges, setApprovedChanges] = useState([]);
  const [rejectedIssues, setRejectedIssues] = useState(new Set());
  const [branchName, setBranchName] = useState(`ai-review-${Date.now()}`);
  const [reviewData, setReviewData] = useState(null);
  const [owner, setOwner] = useState('');
  const [repo, setRepo] = useState('');

  // Load review data from sessionStorage (passed from main app)
  useEffect(() => {
    const storedData = sessionStorage.getItem('reviewData');
    const storedOwner = sessionStorage.getItem('reviewOwner');
    const storedRepo = sessionStorage.getItem('reviewRepo');
    
    if (storedData) {
      setReviewData(JSON.parse(storedData));
      setOwner(storedOwner || '');
      setRepo(storedRepo || '');
    }
  }, []);

  // Group suggestions by file
  const fileGroups = React.useMemo(() => {
    if (!reviewData?.review) return [];
    
    return reviewData.review.map(fileData => ({
      file: fileData.file,
      issues: (fileData.results || []).map((result, idx) => ({
        ...result,
        file: fileData.file,
        owner,
        repo,
        globalIndex: `${fileData.file}-${idx}`
      }))
    })).filter(group => group.issues.length > 0);
  }, [reviewData, owner, repo]);

  // Filter out files where all issues are rejected
  const visibleFileGroups = React.useMemo(() => {
    return fileGroups.map(group => ({
      ...group,
      issues: group.issues.filter(issue => !rejectedIssues.has(issue.globalIndex))
    })).filter(group => group.issues.length > 0);
  }, [fileGroups, rejectedIssues]);

  // Handle approving a single issue
  const handleApproveIssue = async (fileGroup, issueIndex) => {
    const issue = fileGroup.issues[issueIndex];
    
    setApprovedChanges([...approvedChanges, {
      file: issue.file,
      original_content: "",
      modified_content: "",
      suggestion: issue.suggestion || issue.comment || "Code improvement",
      diff: issue.diff || "",
      line_start: issue.highlighted_lines?.[0],
      line_end: issue.highlighted_lines?.[issue.highlighted_lines.length - 1]
    }]);
    
    setRejectedIssues(new Set([...rejectedIssues, issue.globalIndex]));
  };

  // Handle rejecting a single issue
  const handleRejectIssue = (fileGroup, issueIndex) => {
    const issue = fileGroup.issues[issueIndex];
    setRejectedIssues(new Set([...rejectedIssues, issue.globalIndex]));
  };

  // Handle approving all issues in a file
  const handleApproveAll = async (fileGroup) => {
    for (let i = 0; i < fileGroup.issues.length; i++) {
      await handleApproveIssue(fileGroup, i);
    }
  };

  // Handle rejecting all issues in a file
  const handleRejectAll = (fileGroup) => {
    const newRejected = new Set(rejectedIssues);
    fileGroup.issues.forEach(issue => newRejected.add(issue.globalIndex));
    setRejectedIssues(newRejected);
  };

  const handleFinalize = () => {
    if (approvedChanges.length === 0) {
      alert('No changes approved');
      return;
    }
    
    // Store approved changes and close window
    sessionStorage.setItem('approvedChanges', JSON.stringify(approvedChanges));
    sessionStorage.setItem('branchName', branchName);
    sessionStorage.setItem('reviewComplete', 'true');
    
    // Close this tab and notify parent
    window.close();
  };

  const handleCancel = () => {
    sessionStorage.setItem('reviewComplete', 'false');
    window.close();
  };

  if (!reviewData) {
    return (
      <Box w="100%" h="100vh" display="flex" alignItems="center" justifyContent="center">
        <Text>Loading review data...</Text>
      </Box>
    );
  }

  return (
    <Box w="100%" minH="100vh" bg="gray.50">
      {/* Fixed Header */}
      <Box
        position="sticky"
        top={0}
        bg="white"
        borderBottom="2px solid"
        borderColor="gray.200"
        zIndex={10}
        boxShadow="sm"
      >
        <Container maxW="100%" px={6} py={4}>
          <VStack align="stretch" spacing={3}>
            <HStack justify="space-between">
              <Heading size="lg">Code Review - {owner}/{repo}</Heading>
              <HStack spacing={3}>
                <Text fontSize="sm" color="gray.600">
                  {visibleFileGroups.length} {visibleFileGroups.length === 1 ? 'file' : 'files'} with changes
                </Text>
              </HStack>
            </HStack>
            
            <Progress
              value={(approvedChanges.length / fileGroups.flatMap(g => g.issues).length) * 100}
              colorScheme="green"
              size="sm"
              borderRadius="full"
            />
            
            <HStack justify="space-between">
              <Text fontSize="xs" color="gray.500">
                {approvedChanges.length} approved, {rejectedIssues.size} rejected
              </Text>
              
              {visibleFileGroups.length === 0 && (
                <HStack spacing={2}>
                  <FormControl w="300px">
                    <Input
                      value={branchName}
                      onChange={(e) => setBranchName(e.target.value)}
                      placeholder="Branch name"
                      size="sm"
                    />
                  </FormControl>
                  <Button size="sm" variant="outline" onClick={handleCancel}>
                    Cancel
                  </Button>
                  <Button size="sm" colorScheme="green" onClick={handleFinalize}>
                    Create PR with {approvedChanges.length} changes
                  </Button>
                </HStack>
              )}
            </HStack>
          </VStack>
        </Container>
      </Box>

      {/* File Diffs - Full Width */}
      <Container maxW="100%" px={6} py={6}>
        <VStack align="stretch" spacing={6}>
          {visibleFileGroups.map((fileGroup) => (
            <FileDiffViewer
              key={fileGroup.file}
              file={fileGroup.file}
              issues={fileGroup.issues}
              onApproveIssue={(issueIdx) => handleApproveIssue(fileGroup, issueIdx)}
              onRejectIssue={(issueIdx) => handleRejectIssue(fileGroup, issueIdx)}
              onApproveAll={() => handleApproveAll(fileGroup)}
              onRejectAll={() => handleRejectAll(fileGroup)}
            />
          ))}

          {visibleFileGroups.length === 0 && (
            <Box p={8} bg="white" borderRadius="md" textAlign="center">
              <Text fontSize="xl" fontWeight="bold" color="green.600" mb={2}>
                ✅ All suggestions reviewed!
              </Text>
              <Text color="gray.600">
                Ready to create pull request with your approved changes
              </Text>
            </Box>
          )}
        </VStack>
      </Container>
    </Box>
  );
}

export default FullscreenReview;
