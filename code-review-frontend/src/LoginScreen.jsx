import React from "react";
import {
  Box,
  Button,
  Heading,
  Text,
  Center,
  VStack,
  Image,
} from "@chakra-ui/react";

export function LoginScreen() {
  const handleLogin = () => {
    window.location.href = "http://localhost:8000/api/auth/github/login";
  };

  return (
    <Center minH="100vh" bgGradient="linear(to-br, teal.900 0%, gray.900 100%)">
      <Box
        bg="gray.800"
        p={10}
        borderRadius="xl"
        boxShadow="2xl"
        minW={{ base: "90vw", sm: "400px" }}
        textAlign="center"
      >
        <VStack spacing={6}>
          <Image
            src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
            alt="GitHub Logo"
            boxSize="60px"
            mx="auto"
          />
          <Heading color="teal.300" size="lg">
            Sign in with GitHub
          </Heading>
          <Text color="gray.200">
            Authorize your GitHub account to use the AI Code Review Assistant.
          </Text>
          <Button
            colorScheme="teal"
            size="lg"
            onClick={handleLogin}
            leftIcon={
              <Image
                src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
                alt="GitHub"
                boxSize="24px"
              />
            }
            fontWeight="bold"
            mt={4}
          >
            Sign in with GitHub
          </Button>
        </VStack>
      </Box>
    </Center>
  );
}
