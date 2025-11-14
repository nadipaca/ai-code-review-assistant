import React, { useState } from 'react';
import { 
  Box, Button, Flex, Heading, Text, VStack, HStack, Badge, Code,
  useToast, Progress, Alert, AlertIcon, Modal, ModalOverlay,
  ModalContent, ModalHeader, ModalBody, ModalFooter, Input, 
  FormControl, FormLabel, List, ListItem, ListIcon
} from '@chakra-ui/react';
import { CheckIcon, CloseIcon, WarningIcon } from '@chakra-ui/icons';

export function InteractiveReview({ reviewResults, onComplete, onCancel }) {
  const [currentFileIndex, setCurrentFileIndex] = useState(0);
  const [currentSuggestionIndex, setCurrentSuggestionIndex] = useState(0);
  const [approvedChanges, setApprovedChanges] = useState([]);
  const [branchName, setBranchName] = useState(`ai-review-${Date.now()}`);
  const [showBranchModal, setShowBranchModal] = useState(false);
  const toast = useToast();

  const validFiles = React.useMemo(() => {
    if (!reviewResults?.review) return [];
    return reviewResults.review.filter(file => 
      !file.error && file.results && file.results.length > 0
    );
  }, [reviewResults]);

  const currentFile = validFiles[currentFileIndex];
  const suggestions = currentFile?.results || [];
  const currentSuggestion = suggestions[currentSuggestionIndex];
  
  const totalFiles = validFiles.length;
  const totalSuggestions = validFiles.reduce((sum, file) => sum + (file.results?.length || 0), 0);
  const progressPercentage = totalSuggestions > 0 ? ((approvedChanges.length + currentSuggestionIndex + 1) / totalSuggestions) * 100 : 0;

  const moveToNext = () => {
    if (currentSuggestionIndex < suggestions.length - 1) {
      setCurrentSuggestionIndex(currentSuggestionIndex + 1);
    } else if (currentFileIndex < totalFiles - 1) {
      setCurrentFileIndex(currentFileIndex + 1);
      setCurrentSuggestionIndex(0);
    } else {
      setShowBranchModal(true);
    }
  };

  const handleKeep = () => {
    if (!currentSuggestion) return;

    const change = {
      file: currentFile.file,
      original_content: currentSuggestion.original_content || '',
      modified_content: currentSuggestion.modified_content || '',
      suggestion: currentSuggestion.suggestion || '',
      line_start: currentSuggestion.highlighted_lines?.[0],
      line_end: currentSuggestion.highlighted_lines?.[currentSuggestion.highlighted_lines.length - 1],
    };

    setApprovedChanges([...approvedChanges, change]);
    toast({ title: 'Change kept', status: 'success', duration: 1000 });
    moveToNext();
  };

  const handleDiscard = () => {
    toast({ title: 'Change discarded', status: 'info', duration: 1000 });
    moveToNext();
  };

  const handleFinishReview = () => {
    if (approvedChanges.length === 0) {
      toast({ title: 'No changes kept', status: 'warning', duration: 3000 });
      onCancel();
      return;
    }
    onComplete(approvedChanges, branchName);
  };

  const parseSuggestion = (suggestion) => {
    if (!suggestion) return { items: [], hasCodeBlocks: false };
    
    // Split by numbered items
    const parts = suggestion.split(/\n\d+\.\s+/).filter(s => s.trim());
    
    const items = parts.map(part => {
      // Extract line numbers
      const lineMatch = part.match(/\*\*Line[s]?\s+(\d+)(?:-(\d+))?\*\*/i);
      const lines = lineMatch ? `Lines ${lineMatch[1]}${lineMatch[2] ? `-${lineMatch[2]}` : ''}` : null;
      
      // Extract description (before code block)
      const descMatch = part.match(/(.*?)```/s);
      const description = descMatch ? descMatch[1].trim() : part.split('```')[0].trim();
      
      // Check if has code block
      const hasCode = part.includes('```');
      
      return { description, lines, hasCode };
    });
    
    return {
      items,
      hasCodeBlocks: items.some(i => i.hasCode)
    };
  };

  // Render GitHub-style diff
  const renderGitHubStyleDiff = () => {
    if (!currentSuggestion?.diff) {
      // ✅ FALLBACK: Show structured suggestion even without diff
      const parsed = parseSuggestion(currentSuggestion?.suggestion);
      
      if (parsed.items.length > 0) {
        return (
          <Box p={4} bg="blue.50" borderRadius="md" border="1px solid" borderColor="blue.200">
            <Text fontWeight="semibold" color="blue.800" mb={3}>
              📝 Suggested Changes:
            </Text>
            <List spacing={3}>
              {parsed.items.map((item, idx) => (
                <ListItem key={idx} p={3} bg="white" borderRadius="md" border="1px solid" borderColor="blue.200">
                  {item.lines && (
                    <Badge colorScheme="blue" fontSize="xs" mb={2}>
                      {item.lines}
                    </Badge>
                  )}
                  <Text fontSize="sm" color="gray.700" whiteSpace="pre-wrap">
                    {item.description}
                  </Text>
                  {item.hasCode && (
                    <Badge colorScheme="green" fontSize="xs" mt={2}>
                      ✓ Code fix provided
                    </Badge>
                  )}
                </ListItem>
              ))}
            </List>
          </Box>
        );
      }

  if (!reviewResults || !reviewResults.review || reviewResults.review.length === 0) {
    return <Alert status="warning"><AlertIcon />No review results to display</Alert>;
  }

  if (validFiles.length === 0) {
    return <Alert status="error"><AlertIcon />All files had errors during review</Alert>;
  }

  if (!currentSuggestion) {
    return <Alert status="warning"><AlertIcon />No suggestion available</Alert>;
  }

   return (
        <Box p={4} bg="gray.50" borderRadius="md" border="1px solid" borderColor="gray.300">
          <Text color="gray.600" fontSize="sm">No code changes extracted</Text>
        </Box>
      );
    }

    // Original diff rendering code
    const diffLines = currentSuggestion.diff.split('\n');
    
    return (
      <Box 
        bg="white" 
        border="1px solid" 
        borderColor="gray.300" 
        borderRadius="md" 
        overflow="hidden"
        fontFamily="monospace"
        fontSize="13px"
      >
        {diffLines.map((line, idx) => {
          let bgColor = 'white';
          let textColor = 'gray.800';
          
          if (line.startsWith('+++') || line.startsWith('---')) {
            bgColor = 'gray.100';
            textColor = 'gray.600';
          } else if (line.startsWith('+')) {
            bgColor = '#e6ffed';
            textColor = '#24292f';
          } else if (line.startsWith('-')) {
            bgColor = '#ffebe9';
            textColor = '#24292f';
          } else if (line.startsWith('@@')) {
            bgColor = '#f0f7ff';
            textColor = '#0969da';
          }
          
          return (
            <Box
              key={idx}
              bg={bgColor}
              px={4}
              py={0.5}
              _hover={{ bg: line.startsWith('+') ? '#d1f4db' : line.startsWith('-') ? '#ffd8d3' : bgColor }}
            >
              <Code bg="transparent" color={textColor} whiteSpace="pre">
                {line}
              </Code>
            </Box>
          );
        })}
      </Box>
    );
  };

  // ...rest of the component remains the same...

  return (
    <Box w="100%" maxW="1200px" mx="auto" p={4} bg="white">
      {/* ...existing progress bar... */}

      {/* Main Review Card */}
      <Box bg="white" border="1px solid" borderColor="gray.300" borderRadius="md" overflow="hidden">
        {/* ...existing file header... */}

        {/* AI Suggestion */}
        <Box px={4} py={3} bg="blue.50" borderBottom="1px solid" borderColor="blue.200">
          <Text fontSize="sm" color="blue.800" fontWeight="semibold" mb={1}>💡 AI Review:</Text>
          <Text fontSize="sm" color="blue.900" whiteSpace="pre-wrap">
            {currentSuggestion.suggestion || 'No suggestion provided'}
          </Text>
          
          {/* ✅ Show applied status */}
          {currentSuggestion.applied ? (
            <Badge colorScheme="green" mt={2}>
              ✓ Changes extracted successfully
            </Badge>
          ) : (
            <Badge colorScheme="yellow" mt={2}>
              <WarningIcon mr={1} /> Review only (no code changes)
            </Badge>
          )}
        </Box>

        {/* Diff View */}
        <Box p={4}>
          {renderGitHubStyleDiff()}
        </Box>

        {/* Action Buttons */}
        <Box px={4} py={3} bg="gray.50" borderTop="1px solid" borderColor="gray.300">
          <HStack spacing={3} justify="center">
            <Button leftIcon={<CloseIcon />} colorScheme="red" size="lg" onClick={handleDiscard}>Discard</Button>
            <Button leftIcon={<CheckIcon />} colorScheme="green" size="lg" onClick={handleKeep} isDisabled={!currentSuggestion.applied}>Keep</Button>
          </HStack>
          <Text textAlign="center" mt={2} fontSize="sm" color="gray.600">
            <Button variant="link" size="sm" onClick={onCancel}>Cancel Review</Button>
          </Text>
        </Box>
      </Box>

      {/* Branch Modal */}
      <Modal isOpen={showBranchModal} onClose={() => setShowBranchModal(false)} isCentered>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Create Pull Request</ModalHeader>
          <ModalBody>
            <VStack spacing={4} align="stretch">
              <Text fontSize="sm">Review complete! {approvedChanges.length} changes will be applied.</Text>
              <FormControl>
                <FormLabel fontSize="sm">Branch Name</FormLabel>
                <Input value={branchName} onChange={(e) => setBranchName(e.target.value)} placeholder="ai-review-branch" />
              </FormControl>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onCancel}>Cancel</Button>
            <Button colorScheme="blue" onClick={handleFinishReview} isDisabled={!branchName.trim()}>Create PR</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
}

export default InteractiveReview;