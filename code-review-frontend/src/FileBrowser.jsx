import React, { useEffect, useState } from "react";
import {
  Box, List, ListItem, Button, Text, Breadcrumb, BreadcrumbItem, BreadcrumbLink, Checkbox, Spinner, Flex, Badge
} from "@chakra-ui/react";
import { ChevronRightIcon } from "@chakra-ui/icons";
import { FaFolder, FaFileCode } from "react-icons/fa";
import { getFiles } from "./services/api";

export function FileBrowser({ owner, repo, path, onSelectFile, selectedFiles, breadcrumbs, setBreadcrumbs }) {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getFiles(owner, repo, path)
      .then((f) => setFiles(f))
      .finally(() => setLoading(false));
  }, [owner, repo, path]);

  const handleFolderClick = (folder) => {
    setBreadcrumbs([...breadcrumbs, folder.name]);
  };

  const handleBackClick = () => {
    setBreadcrumbs(breadcrumbs.slice(0, -1));
  };

  // ✅ Updated to match backend support (reviews.py and rag_service.py)
  const getSupportedFileTypes = () => {
    return [
      { ext: '.java', label: 'Java', color: 'orange' },
      { ext: '.js', label: 'JavaScript', color: 'yellow' },
      { ext: '.jsx', label: 'JSX', color: 'blue' },
      { ext: '.ts', label: 'TypeScript', color: 'blue' },
      { ext: '.tsx', label: 'TSX', color: 'purple' },
      { ext: '.py', label: 'Python', color: 'green' }
    ];
  };

  const getFileType = (filename) => {
    const supportedTypes = getSupportedFileTypes();
    const fileType = supportedTypes.find(type => filename.endsWith(type.ext));
    return fileType || null;
  };

  const isCodeFile = (filename) => {
    return getFileType(filename) !== null;
  };

  return (
    <Box mt={4}>
      {/* Breadcrumb Navigation */}
      <Breadcrumb spacing="8px" separator={<ChevronRightIcon color="gray.500" />} mb={3}>
        <BreadcrumbItem>
          <BreadcrumbLink 
            href="#" 
            onClick={(e) => { e.preventDefault(); setBreadcrumbs([]); }}
            color="teal.300"
            _hover={{ color: 'teal.200' }}
          >
            root
          </BreadcrumbLink>
        </BreadcrumbItem>
        {breadcrumbs.map((bc, idx) => (
          <BreadcrumbItem key={bc}>
            <BreadcrumbLink
              href="#"
              onClick={(e) => {
                e.preventDefault();
                setBreadcrumbs(breadcrumbs.slice(0, idx + 1));
              }}
              color="teal.300"
              _hover={{ color: 'teal.200' }}
            >
              {bc}
            </BreadcrumbLink>
          </BreadcrumbItem>
        ))}
      </Breadcrumb>

      {/* File List Container */}
      <Box minH="300px" position="relative">
        {loading ? (
          <Flex justify="center" align="center" minH="300px">
            <Spinner size="lg" color="teal.500" />
            <Text ml={3} color="gray.400">Loading files...</Text>
          </Flex>
        ) : (
          <List spacing={2}>
            {/* Folders First */}
            {files
              .filter((f) => f.type === "dir")
              .map((folder) => (
                <ListItem key={folder.path}>
                  <Button
                    type="button"
                    size="sm"
                    leftIcon={<FaFolder/>}
                    onClick={() => handleFolderClick(folder)}
                    colorScheme="blue"
                    variant="outline"
                    _hover={{ bg: 'blue.700', color: 'white' }}
                  >
                    {folder.name}
                  </Button>
                </ListItem>
              ))}
            
            {files
              .filter((f) => f.type === "file")
              .map((file) => {
                const fileType = getFileType(file.name);
                const supported = isCodeFile(file.name);
                
                return (
                  <ListItem key={file.path}>
                    <Flex align="center" gap={2}>
                      <Checkbox
                        isChecked={selectedFiles.some((f) => f.path === file.path)}
                        onChange={() => onSelectFile(file)}
                        colorScheme={supported ? "teal" : "gray"}
                        isDisabled={!supported}
                      >
                        <Flex align="center" gap={2}>
                          {supported && <FaFileCode color="teal" />}
                          <Text color={supported ? "gray.800" : "gray.500"}>
                            {file.name}
                          </Text>
                        </Flex>
                      </Checkbox>
                      
                      {fileType && (
                        <Badge colorScheme={fileType.color} fontSize="xs">
                          {fileType.label}
                        </Badge>
                      )}
                      
                      {!supported && file.name.match(/\.(txt|md|json|yml|yaml|xml|html|css)$/i) && (
                        <Badge colorScheme="gray" fontSize="xs" variant="outline">
                          Not supported
                        </Badge>
                      )}
                    </Flex>
                  </ListItem>
                );
              })}
          </List>
        )}
        
        {/* Empty State */}
        {!loading && files.length === 0 && (
          <Flex justify="center" align="center" minH="200px" direction="column">
            <Text color="gray.400" mb={2}>No files or folders found</Text>
            <Text color="gray.500" fontSize="sm">This directory is empty</Text>
          </Flex>
        )}
      </Box>

      {/* Navigation Buttons */}
      <Flex mt={4} gap={2}>
        {breadcrumbs.length > 0 && (
          <Button 
            onClick={handleBackClick} 
            size="xs" 
            variant="outline" 
            colorScheme="gray" 
            type="button"
          >
            ← Go Up
          </Button>
        )}
        
        {selectedFiles.length > 0 && (
          <Badge colorScheme="teal" fontSize="sm" p={2} borderRadius="md">
            {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''} selected
          </Badge>
        )}
      </Flex>

      {/* Supported File Types Info */}
      <Box mt={4} p={3} bg="gray.700" borderRadius="md">
        <Text fontSize="xs" color="gray.400" mb={2}>
          ✅ Supported file types:
        </Text>
        <Flex gap={2} flexWrap="wrap">
          {getSupportedFileTypes().map(type => (
            <Badge key={type.ext} colorScheme={type.color} fontSize="xs">
              {type.ext}
            </Badge>
          ))}
        </Flex>
      </Box>
    </Box>
  );
}