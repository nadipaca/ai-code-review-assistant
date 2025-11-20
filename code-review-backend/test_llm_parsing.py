import asyncio
import os
import sys
from dotenv import load_dotenv

# Add current directory to path so we can import app
sys.path.append(os.getcwd())

# Load environment variables
load_dotenv()

from app.services.llm_service import review_code_chunk_with_context, parse_individual_issues

async def test_llm_logic():
    file_path = "test-repo/src/javascript/test.js"
    abs_path = os.path.abspath(file_path)
    
    print(f"Reading file: {abs_path}")
    with open(abs_path, "r") as f:
        content = f.read()

    print(f"File content length: {len(content)}")

    # Mock project context
    project_context = "Project structure: test-repo/src/javascript/test.js\nTotal files: 1"

    print("\n--- Calling LLM Service ---")
    try:
        # We'll treat the whole file as one chunk for this test
        result = await review_code_chunk_with_context(
            chunk=content,
            language="javascript",
            start_line=1,
            file_path=file_path,
            project_context=project_context,
            full_file_content=content
        )
        
        print("\n--- Raw LLM Comment ---")
        print(result["comment"])
        
        print("\n--- Parsed Issues ---")
        if result.get("severity") in ["HIGH", "MEDIUM"]:
            issues = parse_individual_issues(result["comment"], content, file_path)
            for i, issue in enumerate(issues):
                print(f"\nIssue #{i+1}:")
                print(f"Severity: {issue['severity']}")
                print(f"Lines: {issue['highlighted_lines']}")
                print(f"Has Code Block: {issue['has_code_block']}")
                print(f"Diff Length: {len(issue['diff'])}")
                if issue['diff']:
                    print("Diff Preview:")
                    print(issue['diff'][:200] + "..." if len(issue['diff']) > 200 else issue['diff'])
                else:
                    print("No Diff Generated (Explanation only?)")
        else:
            print("No HIGH/MEDIUM issues found by LLM.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_llm_logic())
