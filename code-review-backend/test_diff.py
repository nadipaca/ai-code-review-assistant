import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv()

from app.services.llm_service import review_code_chunk_with_context, parse_individual_issues

async def test_diff():
    file_path = "test-repo/src/javascript/test.js"
    with open(file_path, "r") as f:
        content = f.read()

    project_context = "Test project"
    
    result = await review_code_chunk_with_context(
        chunk=content,
        language="javascript",
        start_line=1,
        file_path=file_path,
        project_context=project_context,
        full_file_content=content
    )
    
    if result.get("severity") in ["HIGH", "MEDIUM"]:
        issues = parse_individual_issues(result["comment"], content, file_path)
        if issues:
            print("\n=== FIRST ISSUE DIFF ===")
            print(issues[0]['diff'])
            print("\n=== END DIFF ===")

if __name__ == "__main__":
    asyncio.run(test_diff())
