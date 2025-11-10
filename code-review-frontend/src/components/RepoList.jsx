import React, { useEffect, useState } from 'react';
import {
  Card,
  CardHeader,
  CardBody,
  Heading,
  Stack,
  Flex,
  Text,
  Button,
  Spinner,
  Input,
  Box,
  Center,
  IconButton,
} from '@chakra-ui/react';
import { ChevronLeftIcon, ChevronRightIcon } from '@chakra-ui/icons';

const RepoList = ({ repos = [], loading = false, onOpenRepo, selectedRepo }) => {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 5;
  
  // Reset page to 1 when search changes
  useEffect(() => {
    setPage(1);
  }, [search]);
  
  // Ensure repos is always an array
  const reposArr = Array.isArray(repos) ? repos : [];
  
  const filtered = reposArr.filter((r) => (r.name || '').toLowerCase().includes(search.toLowerCase()));
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const start = (page - 1) * PAGE_SIZE;
  const paged = filtered.slice(start, start + PAGE_SIZE);

  return (
    <Box w="100%">
      <Card boxShadow="lg">
        <CardHeader>
          <Flex align="center" justify="space-between" gap={4} flexWrap="wrap">
            <Heading size="md" color="teal.700">Your Repositories</Heading>
            <Input
              placeholder="Search repositories..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              size="sm"
              bg="gray.50"
              color="gray.800"
              maxW={{ base: '100%', sm: '260px' }}
            />
          </Flex>
        </CardHeader>
        <CardBody>
          {loading ? (
            <Flex justify="center" align="center" minH="120px">
              <Spinner size="lg" color="teal.500" />
            </Flex>
          ) : (
            <>
              {paged.length === 0 ? (
                <Center py={8}>
                  <Text color="gray.400">{search ? 'No repositories match your search.' : 'No repositories found.'}</Text>
                </Center>
              ) : (
                <Stack spacing={3}>
                  {paged.map((repo) => (
                    <Flex
                      key={repo.id}
                      align="center"
                      justify="space-between"
                      bg="gray.50"
                      color="gray.800"
                      p={3}
                      borderRadius="md"
                      _hover={{ bg: 'teal.50' }}
                      width="100%"
                    >
                      <Box overflow="hidden" mr={4}>
                        <Text fontWeight="bold" isTruncated>{repo.name}</Text>
                        <Text fontSize="sm" color="gray.500" isTruncated>{repo.owner?.login}</Text>
                      </Box>
                      <Box>
                        <Button
                          colorScheme="teal"
                          variant="solid"
                          size="sm"
                          onClick={() => onOpenRepo(repo)}
                          isDisabled={selectedRepo && selectedRepo.id === repo.id}
                        >
                          Open
                        </Button>
                      </Box>
                    </Flex>
                  ))}
                </Stack>
              )}

              {filtered.length > PAGE_SIZE && (
                <Flex mt={4} align="center" justify="space-between">
                  <IconButton aria-label="Prev page" icon={<ChevronLeftIcon />} size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} isDisabled={page === 1} />
                  <Text fontSize="sm" color="gray.300">Page {page} / {totalPages} ({filtered.length} repos)</Text>
                  <IconButton aria-label="Next page" icon={<ChevronRightIcon />} size="sm" onClick={() => setPage((p) => Math.min(totalPages, p + 1))} isDisabled={page === totalPages} />
                </Flex>
              )}
            </>
          )}
        </CardBody>
      </Card>
    </Box>
  );
}
export default RepoList;