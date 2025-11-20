import React, { useState, useMemo } from 'react';
import {
    Box,
    VStack,
    HStack,
    Text,
    Button,
    Code,
    Badge,
    Collapse,
    IconButton,
    useColorModeValue,
    Flex,
    Divider
} from '@chakra-ui/react';
import { ChevronDownIcon, ChevronUpIcon, CheckIcon, CloseIcon } from '@chakra-ui/icons';

const SuggestionBlock = ({ suggestion, onApprove, onReject }) => {
    const bgColor = useColorModeValue('white', 'gray.800');
    const borderColor = useColorModeValue('gray.200', 'gray.700');

    // Parse diff lines
    const diffLines = useMemo(() => {
        if (!suggestion.diff) return [];
        return suggestion.diff.split('\n').filter(line =>
            !line.startsWith('---') && !line.startsWith('+++') && !line.startsWith('@@')
        );
    }, [suggestion.diff]);

    return (
        <Box
            my={4}
            border="1px solid"
            borderColor="blue.200"
            borderRadius="md"
            overflow="hidden"
            boxShadow="sm"
            bg={bgColor}
        >
            {/* Header / Issue Description */}
            <Box bg="blue.50" p={3} borderBottom="1px solid" borderColor="blue.100">
                <VStack align="stretch" spacing={2}>
                    <HStack justify="space-between">
                        <Badge colorScheme={suggestion.severity === 'HIGH' ? 'red' : 'orange'}>
                            {suggestion.severity}
                        </Badge>
                        <HStack>
                            <Button
                                size="xs"
                                colorScheme="red"
                                variant="ghost"
                                leftIcon={<CloseIcon />}
                                onClick={() => onReject(suggestion)}
                            >
                                Dismiss
                            </Button>
                            <Button
                                size="xs"
                                colorScheme="green"
                                leftIcon={<CheckIcon />}
                                onClick={() => onApprove(suggestion)}
                            >
                                Accept
                            </Button>
                        </HStack>
                    </HStack>
                    <Text fontSize="sm" color="gray.700">
                        {suggestion.comment.split('Issue:')[1]?.split('Fix:')[0]?.trim() || suggestion.comment}
                    </Text>
                </VStack>
            </Box>

            {/* Diff View */}
            <Box fontFamily="monospace" fontSize="xs" bg="gray.50" overflowX="auto">
                {diffLines.map((line, idx) => {
                    let bg = 'transparent';
                    let color = 'gray.600';
                    let prefix = ' ';

                    if (line.startsWith('+')) {
                        bg = 'green.50';
                        color = 'green.700';
                        prefix = '+';
                    } else if (line.startsWith('-')) {
                        bg = 'red.50';
                        color = 'red.700';
                        prefix = '-';
                    }

                    return (
                        <Flex key={idx} bg={bg} minW="100%">
                            <Box
                                w="24px"
                                textAlign="center"
                                color="gray.400"
                                userSelect="none"
                                borderRight="1px solid"
                                borderColor="gray.200"
                                mr={2}
                            >
                                {prefix}
                            </Box>
                            <Code bg="transparent" color={color} px={0} whiteSpace="pre">
                                {line.substring(1)}
                            </Code>
                        </Flex>
                    );
                })}
            </Box>
        </Box>
    );
};

export function FileReview({ file, originalContent, suggestions, onApprove, onReject }) {
    const [isExpanded, setIsExpanded] = useState(true);

    // Map starting lines to suggestions
    const suggestionsMap = useMemo(() => {
        const map = new Map();
        suggestions.forEach(s => {
            const startLine = s.highlighted_lines?.[0];
            if (startLine) {
                if (!map.has(startLine)) map.set(startLine, []);
                map.get(startLine).push(s);
            }
        });
        return map;
    }, [suggestions]);

    // Split content into lines
    const lines = useMemo(() => {
        return originalContent ? originalContent.split('\n') : [];
    }, [originalContent]);

    // Helper to check if a line is covered by a suggestion (to hide original if needed)
    // For now, we will show original lines unless they are part of the diff context?
    // Actually, the "VS Code" style usually shows the original code, and then inserts the diff view 
    // at the location of the issue.
    // Or, it shows the file, and when you click/hover, or inline, it shows the diff.
    // The user asked for "continuous view... like a full file diff with comments interspersed".

    // Strategy: Render all lines. If a line has a suggestion start, insert the SuggestionBlock AFTER it (or BEFORE?).
    // Usually inline reviews show up *after* the relevant line.

    return (
        <Box mb={6} border="1px solid" borderColor="gray.200" borderRadius="lg" overflow="hidden" bg="white">
            {/* File Header */}
            <Flex
                p={3}
                bg="gray.100"
                align="center"
                justify="space-between"
                cursor="pointer"
                onClick={() => setIsExpanded(!isExpanded)}
                borderBottom={isExpanded ? "1px solid" : "none"}
                borderColor="gray.200"
            >
                <HStack>
                    <IconButton
                        icon={isExpanded ? <ChevronUpIcon /> : <ChevronDownIcon />}
                        variant="ghost"
                        size="sm"
                        aria-label="Toggle file"
                    />
                    <Text fontWeight="bold" fontSize="sm">{file}</Text>
                    <Badge ml={2} colorScheme="blue">{suggestions.length} suggestions</Badge>
                </HStack>
            </Flex>

            <Collapse in={isExpanded} animateOpacity>
                <Box overflowX="auto">
                    {lines.map((lineContent, idx) => {
                        const lineNumber = idx + 1;
                        const lineSuggestions = suggestionsMap.get(lineNumber);

                        return (
                            <React.Fragment key={lineNumber}>
                                {/* Only show original line if there's NO suggestion for it */}
                                {!lineSuggestions && (
                                    <Flex
                                        _hover={{ bg: 'gray.50' }}
                                        borderBottom="1px solid"
                                        borderColor="gray.100"
                                    >
                                        <Box
                                            w="50px"
                                            textAlign="right"
                                            pr={3}
                                            color="gray.400"
                                            fontSize="xs"
                                            userSelect="none"
                                            bg="gray.50"
                                            py={1}
                                        >
                                            {lineNumber}
                                        </Box>
                                        <Code
                                            flex="1"
                                            bg="transparent"
                                            fontSize="xs"
                                            px={4}
                                            py={1}
                                            whiteSpace="pre"
                                        >
                                            {lineContent}
                                        </Code>
                                    </Flex>
                                )}

                                {/* Suggestions for this line - this will show the diff which includes the original line */}
                                {lineSuggestions && (
                                    <Box px={4} py={2} bg="blue.50" borderBottom="1px solid" borderColor="blue.100">
                                        {lineSuggestions.map((suggestion, sIdx) => (
                                            <SuggestionBlock
                                                key={sIdx}
                                                suggestion={suggestion}
                                                onApprove={onApprove}
                                                onReject={onReject}
                                            />
                                        ))}
                                    </Box>
                                )}
                            </React.Fragment>
                        );
                    })}
                </Box>
            </Collapse>
        </Box>
    );
}

export default FileReview;
