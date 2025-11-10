import React from 'react';
import { Box, Flex, Heading, Text, Button } from '@chakra-ui/react';
export function Header({ onLogout }) {
  return (
    <Box as="header" bg="teal.600" py={3} boxShadow="md" position="sticky" top="0" zIndex="1000">
      <Box w="100%" maxW="7xl" mx="auto" >
        <Flex align="center" justify="space-between">
          <Box>
            <Heading color="white" size="lg" letterSpacing="tight">
              AI Code Review Assistant
            </Heading>
            <Text color="teal.100" fontSize="sm" mt={0}>Review your GitHub repositories with AI</Text>
          </Box>

          <Box>
            {onLogout ? (
              <Button
                size="sm"
                onClick={onLogout}
                bg="white"
                color="gray.800"
                boxShadow="sm"
                _hover={{ bg: 'gray.100' }}
                _active={{ bg: 'gray.200' }}
                borderRadius="md"
              >
                Logout
              </Button>
            ) : null}
          </Box>
        </Flex>
      </Box>
    </Box>
  );
}

export default Header;
