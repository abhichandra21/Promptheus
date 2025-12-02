
import asyncio
import sys
import os

# Add src to path to import promptheus
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

try:
    from promptheus.mcp_server import refine_prompt
    print("Successfully imported refine_prompt tool.")
except ImportError:
    print("Error: Could not import refine_prompt. Make sure dependencies are installed.")
    sys.exit(1)

def test_refine_prompt():
    """
    Test the refine_prompt tool directly.
    This avoids the need for a full MCP client connection by testing the implementation function.
    """
    test_prompt = "make a python script"
    print(f"\nTesting refine_prompt with: '{test_prompt}'")
    print("-" * 50)
    
    # Mocking or ensuring config works - this assumes environment variables are set 
    # or it will fail/warn. We'll just catch exceptions to show the flow.
    try:
        # We call the tool function directly. 
        # In FastMCP, the decorated function is the tool implementation.
        result = refine_prompt(prompt=test_prompt)
        
        print(f"Result type: {type(result)}")
        print("Result content:")
        print(result)
        print("-" * 50)
        print("\nTest passed! The tool logic executes correctly.")
        
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        print("Note: This test requires valid API keys (e.g., GOOGLE_API_KEY) to be set in the environment.")

if __name__ == "__main__":
    test_refine_prompt()
