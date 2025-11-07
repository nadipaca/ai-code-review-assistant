import React, { useEffect, useState } from "react";
import {
  ChakraProvider, Box, Heading, List, ListItem, Button, Text, Breadcrumb, BreadcrumbItem, BreadcrumbLink, Checkbox, Icon
} from "@chakra-ui/react";
import { Spinner } from "@chakra-ui/react";
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

  if (loading) return <Spinner />;

  const handleFolderClick = (folder) => {
    setBreadcrumbs([...breadcrumbs, folder.name]);
  };

  const handleBackClick = () => {
    setBreadcrumbs(breadcrumbs.slice(0, -1));
  };

  const currentPath = breadcrumbs.join("/");

  return (
    <Box mt={4}>
      <Breadcrumb spacing="8px" separator={<ChevronRightIcon color="gray.500" />}>
        <BreadcrumbItem>
          <BreadcrumbLink onClick={() => setBreadcrumbs([])}>root</BreadcrumbLink>
        </BreadcrumbItem>
        {breadcrumbs.map((bc, idx) => (
          <BreadcrumbItem key={bc}>
            <BreadcrumbLink onClick={() => setBreadcrumbs(breadcrumbs.slice(0, idx + 1))}>{bc}</BreadcrumbLink>
          </BreadcrumbItem>
        ))}
      </Breadcrumb>
      <List spacing={2} mt={2}>
        {files
          .filter((f) => f.type === "dir")
          .map((folder) => (
            <ListItem key={folder.path}>
              <Button
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
          .map((file) => (
            <ListItem key={file.path}>
              <Checkbox
                isChecked={selectedFiles.some((f) => f.path === file.path)}
                onChange={() => onSelectFile(file)}
                colorScheme={file.name.endsWith(".js") || file.name.endsWith(".java") ? "green" : "gray"}
                isDisabled={!(file.name.endsWith(".js") || file.name.endsWith(".java"))}
              >
                {file.name}
              </Checkbox>
            </ListItem>
          ))}
      </List>
      {breadcrumbs.length > 0 && (
        <Button onClick={handleBackClick} mt={3} size="xs" variant="outline" colorScheme="gray">
          Go Up
        </Button>
      )}
    </Box>
  );
}