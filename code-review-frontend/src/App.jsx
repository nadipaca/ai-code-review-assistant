import React, { useEffect, useState } from "react";
import {
  ChakraProvider,
  Box,
  Heading,
  Button,
  Spinner,
  Text,
  Flex,
  Stack,
  Card,
  CardBody,
  CardHeader,
  Divider,
  useToast,
  IconButton,
  Badge,
  Alert,
  AlertIcon,
  CloseButton,
  SlideFade,
  SimpleGrid,
  Center,
  HStack,
  Input,
} from "@chakra-ui/react";
import { ArrowBackIcon } from "@chakra-ui/icons";
import { getRepos, startReview, publishReviewToPR } from "./services/api";
import { FileBrowser } from "./FileBrowser";
import { LoginScreen } from "./LoginScreen";

function App() {
  const [repos, setRepos] = useState([]);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Check authentication by calling backend on mount
  useEffect(() => {
    checkAuth().then(setIsAuthenticated);
  }, []);
// Helper function to check authentication by calling backend
async function checkAuth() {
  try {
    const res = await fetch("http://localhost:8000/api/profile", {
      credentials: "include",
    });
    if (!res.ok) return false;
    const data = await res.json();
    return !!data.user_id;
  } catch {
    return false;
  }
}
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [breadcrumbs, setBreadcrumbs] = useState([]);
  const [reviewResults, setReviewResults] = useState(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [error, setError] = useState("");
  const [prNumber, setPrNumber] = useState("");
  const [publishing, setPublishing] = useState(false);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [fileSelectMsg, setFileSelectMsg] = useState("");
  const toast = useToast();

  // Helper to create a safe filename from a path
  function sanitizeFilename(path) {
    return path.replace(/[^a-z0-9.\-_/]/gi, '_').replace(/\//g, '_');
  }

  useEffect(() => {
    if (!isAuthenticated) return;
    setLoadingRepos(true);
    getRepos()
      .then((r) => setRepos(r.repos))
      .catch((e) => {
        // If unauthorized, redirect to login by flipping auth state
        if (e && e.status === 401) {
          setIsAuthenticated(false);
          return;
        }
        setError(e.message || String(e));
      })
      .finally(() => setLoadingRepos(false));
  }, [isAuthenticated]);

  const handleRepoSelect = (repo) => {
    setSelectedRepo(repo);
    setBreadcrumbs([]);
    setSelectedFiles([]);
    setReviewResults(null);
    setFileSelectMsg("");
  };

  // Show a message when a file is selected
  const handleSelectFile = (file) => {
    setSelectedFiles((prev) => {
      let updated;
      if (prev.some((f) => f.path === file.path)) {
        updated = prev.filter((f) => f.path !== file.path);
      } else {
        updated = [...prev, file];
        setFileSelectMsg(`File "${file.name}" was selected for code review.`);
        setTimeout(() => setFileSelectMsg(""), 2000);
      }
      return updated;
    });
  };

  const handleReview = async () => {
    setReviewLoading(true);
    try {
      // send owner/repo/path so backend can fetch file contents
      const payload = selectedFiles.map((f) => ({
        owner: selectedRepo.owner.login,
        repo: selectedRepo.name,
        path: f.path,
      }));
      // startReview expects an array of file refs; it will wrap into { files: [...] }
      const result = await startReview(payload);
      setReviewResults(result);
      // Summarize any per-file errors
      const fileErrors = (result.review || []).filter((f) => f.error);
      const chunkErrors = (result.review || []).flatMap((f) => (f.results || []).filter((r) => r && r.error)).map((r) => r.error);
      if (fileErrors.length || chunkErrors.length) {
        const msgs = [];
        if (fileErrors.length) msgs.push(`${fileErrors.length} file(s) failed: ${fileErrors.map(f => f.file).join(', ')}`);
        if (chunkErrors.length) msgs.push(`${chunkErrors.length} chunk review errors`);
        toast({ title: "Review completed with issues", description: msgs.join(' — '), status: "warning", duration: 6000, isClosable: true });
      } else {
        toast({ title: "Review complete.", status: "success", duration: 3000, isClosable: true });
      }
    } catch (e) {
      // Redirect to login if unauthorized
      if (e && e.status === 401) {
        setIsAuthenticated(false);
        return;
      }
      setError(e.message || String(e));
      toast({
        title: "Review failed.",
        description: e.message,
        status: "error",
        duration: 4000,
        isClosable: true,
      });
    } finally {
      setReviewLoading(false);
    }
  };

  const handlePublishToPR = async () => {
    if (!prNumber) {
      setError("Please enter a PR number");
      return;
    }

    if (!reviewResults || !reviewResults.review) {
      setError("No review results to publish");
      return;
    }

    setPublishing(true);
    try {
      // Extract suggestions from review results (use 'results' entries)
      const suggestions = reviewResults.review.map((file) => ({
        file: file.file,
        comment: (file.results || [])
          .map((r) => r.error ? `Error: ${r.error}` : (r.suggestion || ""))
          .filter(Boolean)
          .join("\n\n") || (file.error || "No suggestions"),
      }));

      await publishReviewToPR(
        selectedRepo.owner.login,
        selectedRepo.name,
        parseInt(prNumber, 10),
        suggestions
      );

      setError("");
      toast({ title: "Review published to GitHub PR", status: "success", duration: 4000, isClosable: true });
      setPrNumber("");
    } catch (e) {
      const msg = (e && (e.message || e.message) ) || String(e);
      setError(`Publishing failed: ${msg}`);
      toast({ title: "Publish failed", description: msg, status: "error", duration: 6000, isClosable: true });
    } finally {
      setPublishing(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <ChakraProvider>
        <LoginScreen />
      </ChakraProvider>
    );
  }
  return (
    <ChakraProvider>
      <Box minH="100vh" bgGradient="linear(to-br, teal.900 0%, gray.900 100%)" color="gray.100">
        {/* Header */}
        <Box as="header" bg="teal.600" py={4} boxShadow="md">
          <Center>
            <Box w="100%" maxW="7xl" px={6}>
              <Heading color="white" size="lg" letterSpacing="tight">
                AI Code Review Assistant
              </Heading>
              <Text color="teal.100" fontSize="md" mt={1}>
                Review your GitHub repositories with AI
              </Text>
            </Box>
          </Center>
        </Box>

        <Center py={8} w="100%">
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={8} w="100%" maxW="7xl">
            {/* Sidebar: Repo List */}
            <Box>
              {/* Error Message */}
              {error && (
                <Alert status="error" mb={4} borderRadius="md">
                  <AlertIcon />
                  {error}
                  <CloseButton
                    position="absolute"
                    right="8px"
                    top="8px"
                    onClick={() => setError("")}
                  />
                </Alert>
              )}

              {/* File select message */}
              <SlideFade in={!!fileSelectMsg} offsetY="20px">
                {fileSelectMsg && (
                  <Alert status="info" mb={4} borderRadius="md">
                    <AlertIcon />
                    {fileSelectMsg}
                  </Alert>
                )}
              </SlideFade>

              {!selectedRepo && (
                <Card boxShadow="lg">
                  <CardHeader>
                    <Heading size="md" color="teal.700">
                      Your Repositories
                    </Heading>
                  </CardHeader>
                  <CardBody>
                    {loadingRepos ? (
                      <Flex justify="center" align="center" minH="80px">
                        <Spinner size="lg" color="teal.500" />
                      </Flex>
                    ) : (
                      <Stack spacing={3}>
                        {repos.map((repo) => (
                          <Flex
                            key={repo.id}
                            align="center"
                            justify="space-between"
                            bg="gray.50"
                            color="gray.800"
                            p={3}
                            borderRadius="md"
                            _hover={{ bg: "teal.50" }}
                            transition="background 0.2s"
                          >
                            <Box>
                              <Text fontWeight="bold">{repo.name}</Text>
                              <Text fontSize="sm" color="gray.500">
                                {repo.owner?.login}
                              </Text>
                            </Box>
                            <Button
                              colorScheme="teal"
                              variant="solid"
                              size="sm"
                              onClick={() => handleRepoSelect(repo)}
                            >
                              Open
                            </Button>
                          </Flex>
                        ))}
                      </Stack>
                    )}
                  </CardBody>
                </Card>
              )}

              {/* Sidebar for selected files (when repo is open) */}
              {selectedRepo && (
                <Card boxShadow="lg">
                  <CardHeader>
                    <Heading size="sm" color="teal.700">
                      Selected Files
                    </Heading>
                  </CardHeader>
                  <CardBody>
                    <Stack spacing={2}>
                      {selectedFiles.length === 0 ? (
                        <Text color="gray.400" fontSize="sm">
                          No files selected.
                        </Text>
                      ) : (
                        selectedFiles.map((file) => (
                          <Flex key={file.path} align="center" justify="space-between">
                            <Text fontSize="sm">{file.name}</Text>
                            <Badge colorScheme="green" fontSize="0.7em">
                              Ready
                            </Badge>
                          </Flex>
                        ))
                      )}
                    </Stack>
                  </CardBody>
                </Card>
              )}
            </Box>

            {/* Main Content: File Browser and Review */}
            <Box>
              {!selectedRepo && (
                <Center h="100%" minH="400px">
                  <Text fontSize="2xl" color="gray.400">
                    Select a repository to start code review.
                  </Text>
                </Center>
              )}
              {selectedRepo && (
                <Card boxShadow="lg" mb={8}>
                  <CardHeader>
                    <Flex align="center" justify="space-between">
                      <Heading size="md" color="teal.700">
                        Files in {selectedRepo.name}
                      </Heading>
                      <IconButton
                        icon={<ArrowBackIcon />}
                        aria-label="Back to Repos"
                        size="sm"
                        variant="ghost"
                        colorScheme="teal"
                        onClick={() => setSelectedRepo(null)}
                      />
                    </Flex>
                  </CardHeader>
                  <Divider />
                  <CardBody>
                    <FileBrowser
                      owner={selectedRepo.owner.login}
                      repo={selectedRepo.name}
                      path={breadcrumbs.join("/")}
                      onSelectFile={handleSelectFile}
                      selectedFiles={selectedFiles}
                      breadcrumbs={breadcrumbs}
                      setBreadcrumbs={setBreadcrumbs}
                    />
                    <Flex mt={6} gap={4} align="center" justify="flex-end">
                      <Button
                        colorScheme="green"
                        isDisabled={selectedFiles.length === 0}
                        onClick={handleReview}
                      >
                        Review Selected Files
                      </Button>
                      <Button
                        variant="outline"
                        colorScheme="gray"
                        onClick={() => {
                          setSelectedFiles([]);
                          setReviewResults(null);
                        }}
                      >
                        Clear Selection
                      </Button>
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
                              {fileObj.error && (
                                <Text color="red.300" fontSize="sm">{fileObj.error}</Text>
                              )}
                            </Box>
                            <Box>
                              {(fileObj.error) ? (
                                <Button size="sm" colorScheme="red" isDisabled>
                                  Error
                                </Button>
                              ) : (
                                <Button
                                  size="sm"
                                  colorScheme="teal"
                                  onClick={() => {
                                    try {
                                      const parts = [];
                                      parts.push(`File: ${fileObj.file}`);
                                      parts.push('');
                                      (fileObj.results || []).forEach((r, idx) => {
                                        if (r.error) {
                                          parts.push(`Chunk ${idx + 1} error: ${r.error}`);
                                          parts.push('');
                                          return;
                                        }
                                        parts.push(`Suggestion ${idx + 1}:`);
                                        parts.push(r.suggestion || '');
                                        parts.push('');
                                        parts.push('Chunk preview:');
                                        parts.push(r.chunk_preview || '');
                                        if (r.highlighted_lines) {
                                          parts.push('Highlighted lines: ' + r.highlighted_lines.join(', '));
                                        }
                                        parts.push('');
                                      });

                                      const blob = new Blob([parts.join('\n')], { type: 'text/plain;charset=utf-8' });
                                      const url = URL.createObjectURL(blob);
                                      const a = document.createElement('a');
                                      const fname = sanitizeFilename(fileObj.file) + '.review.txt';
                                      a.href = url;
                                      a.download = fname;
                                      document.body.appendChild(a);
                                      a.click();
                                      a.remove();
                                      URL.revokeObjectURL(url);
                                      toast({ title: 'Exported review', description: fname, status: 'success', duration: 3000, isClosable: true });
                                    } catch (err) {
                                      toast({ title: 'Export failed', description: String(err), status: 'error', duration: 4000, isClosable: true });
                                    }
                                  }}
                                >
                                  Export
                                </Button>
                              )}
                            </Box>
                          </Box>
                        ))}
                        {/* Publish to PR Section */}
                        <Box mt={6} p={4} bg="gray.700" borderRadius="md">
                          <Heading size="sm" mb={3} color="teal.200">Publish to GitHub PR</Heading>
                          <HStack spacing={2}>
                            <Input
                              placeholder="Enter PR number (e.g., 42)"
                              type="number"
                              value={prNumber}
                              onChange={(e) => setPrNumber(e.target.value)}
                              maxW="150px"
                              bg="gray.600"
                              color="white"
                            />
                            <Button
                              colorScheme="green"
                              onClick={handlePublishToPR}
                              isLoading={publishing}
                              isDisabled={!prNumber}
                            >
                              📤 Publish to PR
                            </Button>
                          </HStack>
                        </Box>
                      </Box>
                    )}
                  </CardBody>
                </Card>
              )}
            </Box>
          </SimpleGrid>
        </Center>
      </Box>
    </ChakraProvider>
  );
}

export default App;