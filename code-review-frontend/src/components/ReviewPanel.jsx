import React from 'react';
import {
  Card,
  CardHeader,
  CardBody,
  Heading,
  Flex,
  IconButton,
  Divider,
  Button,
  Center,
  Spinner,
  Text,
  Box,
  HStack,
  Input,
} from '@chakra-ui/react';
import { ArrowBackIcon } from '@chakra-ui/icons';
import { FileBrowser } from '../FileBrowser';

export function ReviewPanel({
  selectedRepo,
  setSelectedRepo,
  breadcrumbs,
  setBreadcrumbs,
  handleSelectFile,
  selectedFiles,
  handleReview,
  reviewLoading,
  reviewResults,
  prNumber,
  setPrNumber,
  publishing,
  handlePublishToPR,
  sanitizeFilename,
  toast,
  onBack,
}) {
  if (!selectedRepo) return null;

  return (
    <Card boxShadow="lg" mb={8}>
      <CardHeader>
          <Flex align="center" justify="space-between">
            <Heading size="md" color="teal.700">Files in {selectedRepo.name}</Heading>
            <Flex align="center" gap={2}>
              <Button size="sm" variant="ghost" colorScheme="teal" onClick={() => { if (onBack) onBack(); else setSelectedRepo(null); }}>Back to repos</Button>
              <IconButton
                icon={<ArrowBackIcon />}
                aria-label="Back to Repos"
                size="sm"
                variant="ghost"
                colorScheme="teal"
                onClick={() => { if (onBack) onBack(); else setSelectedRepo(null); }}
              />
            </Flex>
          </Flex>
      </CardHeader>
      <Divider />
      <CardBody>
        {/* Fixed-height browser container prevents layout jump */}
        <Box minH="350px">
          <FileBrowser
            owner={selectedRepo.owner.login}
            repo={selectedRepo.name}
            path={breadcrumbs.join('/')}
            onSelectFile={handleSelectFile}
            selectedFiles={selectedFiles}
            breadcrumbs={breadcrumbs}
            setBreadcrumbs={setBreadcrumbs}
          />
        </Box>

        <Flex mt={6} gap={4} align="center" justify="flex-end">
          <Button colorScheme="green" isDisabled={selectedFiles.length === 0} onClick={handleReview}>Review Selected Files</Button>
          <Button variant="outline" colorScheme="gray" onClick={() => { /* clear handled in parent */ }}>Clear Selection</Button>
        </Flex>

        {reviewLoading && (
          <Center mt={8}>
            <Spinner size="xl" color="teal.400" />
            <Text ml={4}>Reviewing code...</Text>
          </Center>
        )}

        {reviewResults && (
          <Box mt={6} p={4} bg="gray.800" borderRadius="md">
            <Heading size="md" mb={4}>Review Results</Heading>
            {reviewResults.review.map((fileObj, i) => (
              <Box key={i} mb={4} p={3} bg="gray.700" borderRadius="md" display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Text fontWeight="bold" color="teal.300">{fileObj.file}</Text>
                  {fileObj.error && (<Text color="red.300" fontSize="sm">{fileObj.error}</Text>)}
                </Box>
                <Box>
                  {(fileObj.error) ? (
                    <Button size="sm" colorScheme="red" isDisabled> Error </Button>
                  ) : (
                    <Button size="sm" colorScheme="teal" onClick={() => {
                      try {
                        const parts = [];
                        parts.push(`File: ${fileObj.file}`);
                        parts.push('');
                        (fileObj.results || []).forEach((r, idx) => {
                          if (r.error) { parts.push(`Chunk ${idx + 1} error: ${r.error}`); parts.push(''); return; }
                          parts.push(`Suggestion ${idx + 1}:`);
                          parts.push(r.suggestion || '');
                          parts.push('');
                          parts.push('Chunk preview:');
                          parts.push(r.chunk_preview || '');
                          if (r.highlighted_lines) parts.push('Highlighted lines: ' + r.highlighted_lines.join(', '));
                          parts.push('');
                        });

                        const blob = new Blob([parts.join('\n')], { type: 'text/plain;charset=utf-8' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        const fname = sanitizeFilename(fileObj.file) + '.review.txt';
                        a.href = url; a.download = fname; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
                        toast({ title: 'Exported review', description: fname, status: 'success', duration: 3000, isClosable: true });
                      } catch (err) {
                        toast({ title: 'Export failed', description: String(err), status: 'error', duration: 4000, isClosable: true });
                      }
                    }}>Export</Button>
                  )}
                </Box>
              </Box>
            ))}

            <Box mt={6} p={4} bg="gray.700" borderRadius="md">
              <Heading size="sm" mb={3} color="teal.200">Publish to GitHub PR</Heading>
              <HStack spacing={2}>
                <Input placeholder="Enter PR number (e.g., 42)" type="number" value={prNumber} onChange={(e) => setPrNumber(e.target.value)} maxW="150px" bg="gray.600" color="white" />
                <Button colorScheme="green" onClick={handlePublishToPR} isLoading={publishing} isDisabled={!prNumber}>📤 Publish to PR</Button>
              </HStack>
            </Box>
          </Box>
        )}
      </CardBody>
    </Card>
  );
}

export default ReviewPanel;