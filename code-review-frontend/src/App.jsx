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
  Heading,
  VStack,
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
  // view controls which single panel is visible: 'repos' | 'review'
  const [view, setView] = useState('repos');
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
      setView('repos');
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

    function handleRepoSelect(repo) {
      setSelectedRepo(repo);
      setBreadcrumbs([]);
      setSelectedFiles([]);
      setReviewResults(null);
      // navigate to review panel
      setView('review');
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
        // Transform reviewResults -> suggestions: [{ file, comment }]
        const suggestions = (reviewResults && Array.isArray(reviewResults.review))
          ? reviewResults.review.map((fileObj) => {
              if (fileObj.error) {
                return { file: fileObj.file, comment: `Error: ${fileObj.error}` };
              }
              // Build a readable markdown comment per file
              const parts = [];
              (fileObj.results || []).forEach((r, idx) => {
                if (r.error) {
                  parts.push(`**Chunk ${idx + 1} - Error:** ${r.error}`);
                  return;
                }
                if (r.suggestion) {
                  parts.push(`**Suggestion ${idx + 1}:**\n${r.suggestion}`);
                }
                if (r.chunk_preview) {
                  parts.push("```" + "\n" + r.chunk_preview + "\n" + "```");
                }
                if (r.highlighted_lines) {
                  parts.push(`Highlighted lines: ${r.highlighted_lines.join(", ")}`);
                }
              });
              const comment = parts.join("\n\n") || "_No suggestion provided._";
              return { file: fileObj.file, comment };
            })
          : [];

        if (suggestions.length === 0) {
          toast({ title: "Nothing to publish", description: "No review suggestions available.", status: "warning", duration: 3000, isClosable: true });
          setPublishing(false);
          return;
        }

        // Ensure PR number is numeric
        const prNum = Number(prNumber);

        await publishReviewToPR(selectedRepo.owner.login, selectedRepo.name, prNum, suggestions);
        toast({ title: "Published to PR", status: "success", duration: 3000, isClosable: true });
       // After successful publish, return to repo list and clear selection
       setView('repos');
       setSelectedRepo(null);
       setSelectedFiles([]);
       setReviewResults(null);
      } catch (err) {
        toast({ title: "Publish failed", description: err.message || JSON.stringify(err), status: "error", duration: 4000, isClosable: true });
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
          <Header onLogout={() => { handleLogout(); }} />

          <Box py={6} w="100%">
            <Box w="100%" maxW="1100px" mx="auto" px={{ base: 4, md: 6 }}>
              {view === 'repos' && (
                <VStack align="stretch" spacing={4}>
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

                  <RepoList repos={repos} loading={loadingRepos} onOpenRepo={handleRepoSelect} selectedRepo={selectedRepo} />
                </VStack>
              )}

              {view === 'review' && (
                <ReviewPanel
                  selectedRepo={selectedRepo}
                  setSelectedRepo={(r) => { setSelectedRepo(r); if (!r) setView('repos'); }}
                  onBack={() => { setSelectedRepo(null); setView('repos'); }}
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
            </Box>
          </Box>
        </Box>
        </ErrorBoundary>
      </ChakraProvider>
    );
  }

  export default App;