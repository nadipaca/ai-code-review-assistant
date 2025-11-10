import React, { useEffect, useState } from "react";
console.log("App.jsx loaded");

// Simple error boundary to show runtime errors instead of blank screen
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, info) {
    console.error("ErrorBoundary caught:", error, info);
  }
  render() {
    if (this.state.hasError) {
      return (
        <Box p={6}>
          <Heading size="md" color="red.300">Runtime error</Heading>
          <Text mt={3} color="red.200">{String(this.state.error)}</Text>
        </Box>
      );
    }
    return this.props.children;
  }
}
import {
  ChakraProvider,
  Box,
  Text,
  useToast,
  Grid,
  GridItem,
  Heading,
  VStack,
  Center,
} from "@chakra-ui/react";
import { getRepos, startReview, publishReviewToPR } from "./services/api";
import { LoginScreen } from "./LoginScreen";
import Header from "./components/Header";
import RepoList from "./components/RepoList";
import ReviewPanel from "./components/ReviewPanel";

function App() {
    const [repos, setRepos] = useState([]);
    const [isAuthenticated, setIsAuthenticated] = useState(false);

    const [selectedRepo, setSelectedRepo] = useState(null);
    const [selectedFiles, setSelectedFiles] = useState([]);
    const [breadcrumbs, setBreadcrumbs] = useState([]);
    const [reviewResults, setReviewResults] = useState(null);
    const [reviewLoading, setReviewLoading] = useState(false);
    const [prNumber, setPrNumber] = useState("");
    const [publishing, setPublishing] = useState(false);
    const [loadingRepos, setLoadingRepos] = useState(false);
    const toast = useToast();

    async function handleLogout() {
      try {
        await fetch('/api/auth/github/logout', { method: 'POST', credentials: 'include' });
      } catch (e) {
        console.error('Logout request failed', e);
      }
      // Clear client state
      setIsAuthenticated(false);
      setRepos([]);
      setSelectedRepo(null);
      setSelectedFiles([]);
      setReviewResults(null);
    }

    useEffect(() => {
      // Check session/profile then load repos
      (async () => {
        try {
          const res = await fetch("/api/profile", { credentials: "include" });
          if (!res.ok) return setIsAuthenticated(false);
          await res.json();
          setIsAuthenticated(true);
          // load repos inline to avoid stale-deps warning
          setLoadingRepos(true);
          try {
            const data = await getRepos();
            // backend returns { repos: [...] } — normalize to an array
            setRepos(Array.isArray(data) ? data : (data && data.repos) ? data.repos : []);
          } catch (err) {
            if (err && err.status === 401) setIsAuthenticated(false);
            else console.error("Failed to load repos", err);
          } finally {
            setLoadingRepos(false);
          }
        } catch {
          setIsAuthenticated(false);
        }
      })();
    }, []);

    // loadRepos moved inline into useEffect to avoid stale-deps warnings

    function handleRepoSelect(repo) {
      setSelectedRepo(repo);
      setBreadcrumbs([]);
      setSelectedFiles([]);
      setReviewResults(null);
    }

    function handleSelectFile(file) {
      // toggle selection
      setSelectedFiles((prev) => {
        const exists = prev.find((f) => f.path === file.path);
        if (exists) return prev.filter((f) => f.path !== file.path);
        return [...prev, file];
      });
    }

    async function handleReview() {
      if (!selectedRepo || selectedFiles.length === 0) return;
      setReviewLoading(true);
      try {
        const payload = selectedFiles.map((f) => ({ owner: selectedRepo.owner.login, repo: selectedRepo.name, path: f.path }));
        const res = await startReview(payload);
        setReviewResults(res);
        toast({ title: "Review complete", status: "success", duration: 3000, isClosable: true });
      } catch (err) {
        toast({ title: "Review failed", description: err.message || String(err), status: "error", duration: 4000, isClosable: true });
      } finally {
        setReviewLoading(false);
      }
    }

    async function handlePublishToPR() {
      if (!selectedRepo || !prNumber || !reviewResults) return;
      setPublishing(true);
      try {
        await publishReviewToPR(selectedRepo.owner.login, selectedRepo.name, prNumber, reviewResults);
        toast({ title: "Published to PR", status: "success", duration: 3000, isClosable: true });
      } catch (err) {
        toast({ title: "Publish failed", description: err.message || String(err), status: "error", duration: 4000, isClosable: true });
      } finally {
        setPublishing(false);
      }
    }

    function sanitizeFilename(name) {
      return name.replace(/[^a-z0-9._-]/gi, "_");
    }

    if (!isAuthenticated) {
      return (
        <ChakraProvider>
          <LoginScreen />
        </ChakraProvider>
      );
    }

    return (
      <ChakraProvider>
        <ErrorBoundary>
        <Box minH="100vh" bgGradient="linear(to-br, teal.900 0%, gray.900 100%)" color="gray.100">
          <Header onLogout={handleLogout} />

          <Box py={8} w="100%">
            <Box w="100%" maxW="7xl" mx="auto" px={6}>
              <Grid templateColumns={{ base: "1fr", md: "3fr 1fr" }} gap={8} alignItems="start">
                <GridItem>
                  <VStack align="stretch" spacing={4}>
                    {!selectedRepo && (
                      <Box
                        bg="gray.800"
                        color="gray.200"
                        p={4}
                        borderRadius="md"
                        boxShadow="sm"
                        textAlign="center"
                      >
                        <Heading size="sm" color="teal.300">Select a repository to start code review.</Heading>
                      </Box>
                    )}

                    <Box>
                      <RepoList repos={repos} loading={loadingRepos} onOpenRepo={handleRepoSelect} selectedRepo={selectedRepo} />
                    </Box>
                  </VStack>
                </GridItem>

                <GridItem>
                  {!selectedRepo ? (
                    <Box minH="400px" bg="white" boxShadow="sm" display="flex" alignItems="center" justifyContent="center" borderRadius="md">
                      <Text fontSize="lg" color="gray.400" textAlign="center">Open a repository from the left to browse files and run reviews.</Text>
                    </Box>
                  ) : (
                    <ReviewPanel
                      selectedRepo={selectedRepo}
                      setSelectedRepo={setSelectedRepo}
                      breadcrumbs={breadcrumbs}
                      setBreadcrumbs={setBreadcrumbs}
                      handleSelectFile={handleSelectFile}
                      selectedFiles={selectedFiles}
                      handleReview={handleReview}
                      reviewLoading={reviewLoading}
                      reviewResults={reviewResults}
                      prNumber={prNumber}
                      setPrNumber={setPrNumber}
                      publishing={publishing}
                      handlePublishToPR={handlePublishToPR}
                      sanitizeFilename={sanitizeFilename}
                      toast={toast}
                    />
                  )}
                </GridItem>
              </Grid>
            </Box>
          </Box>
        </Box>
        </ErrorBoundary>
      </ChakraProvider>
    );
  }

  export default App;