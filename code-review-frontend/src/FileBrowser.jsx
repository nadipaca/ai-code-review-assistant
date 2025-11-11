import React, { useEffect, useState } from "react";
import {
  Box, List, ListItem, Button, Text, Breadcrumb, BreadcrumbItem, BreadcrumbLink, Checkbox, Spinner, Flex
} from "@chakra-ui/react";
import { ChevronRightIcon } from "@chakra-ui/icons";
import { FaFolder } from "react-icons/fa";
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

  return (
    <Box mt={4}>
      <Breadcrumb spacing="8px" separator={<ChevronRightIcon color="gray.500" />} mb={3}>
        <BreadcrumbItem>
          <BreadcrumbLink href="#" onClick={(e) => { e.preventDefault(); setBreadcrumbs([]); }}>root</BreadcrumbLink>
        </BreadcrumbItem>
        {breadcrumbs.map((bc, idx) => (
          <BreadcrumbItem key={bc}>
            <BreadcrumbLink
              href="#"
              onClick={(e) => {
                e.preventDefault();
                setBreadcrumbs(breadcrumbs.slice(0, idx + 1));
              }}
            >
              {bc}
            </BreadcrumbLink>
          </BreadcrumbItem>
        ))}
      </Breadcrumb>

      {/* Fixed-height container so layout does not jump */}
      <Box minH="300px" position="relative">
        {loading ? (
          <Flex justify="center" align="center" minH="300px">
            <Spinner size="lg" color="teal.500" />
          </Flex>
        ) : (
          <List spacing={2}>
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
                  >
                    {folder.name}
                  </Button>
                </ListItem>
              ))}
            {files
              .filter((f) => f.type === "file")
              .map((file) => {
                const codeExtensions = [".js", ".java", ".py"];
                const isCodeFile = codeExtensions.some(ext => file.name.endsWith(ext));
                
                return (
                  <ListItem key={file.path}>
                    <Checkbox
                      isChecked={selectedFiles.some((f) => f.path === file.path)}
                      onChange={() => onSelectFile(file)}
                      colorScheme={isCodeFile ? "green" : "gray"}
                      isDisabled={!isCodeFile}
                    >
                      {file.name}
                    </Checkbox>
                  </ListItem>
                );
              })}
          </List>
        )}
      </Box>

      {breadcrumbs.length > 0 && (
        <Button onClick={handleBackClick} mt={3} size="xs" variant="outline" colorScheme="gray" type="button">
          Go Up
        </Button>
      )}
    </Box>
  );
}