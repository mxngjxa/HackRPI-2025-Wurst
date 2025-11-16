"""
Test script for Function Calling implementation.

Tests both RAG mode and Function Calling mode.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported."""
    print("=" * 60)
    print("Test 1: Module Imports")
    print("=" * 60)
    
    try:
        from backend.config import (
            USE_FUNCTION_CALLING,
            ENABLE_SEMANTIC_SEARCH_TOOL,
            ENABLE_KEYWORD_SEARCH_TOOL,
            ENABLE_DOCUMENT_QUERY_TOOL,
            MAX_FUNCTION_CALLS
        )
        print("✅ Config imports successful")
        print(f"   USE_FUNCTION_CALLING: {USE_FUNCTION_CALLING}")
        print(f"   MAX_FUNCTION_CALLS: {MAX_FUNCTION_CALLS}")
        
        from backend.mcp_tools import get_available_tools, execute_tool
        print("✅ Function tools imports successful")
        
        from backend.function_handler import FunctionHandler
        print("✅ Function handler imports successful")
        
        from backend.llm_client import (
            GeminiFunctionCallingClient,
            get_llm_client
        )
        print("✅ LLM client imports successful")
        
        from backend.chat_service import handle_question
        print("✅ Chat service imports successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_tools():
    """Test that tools are properly defined."""
    print("\n" + "=" * 60)
    print("Test 2: Tool Definitions")
    print("=" * 60)
    
    try:
        from backend.mcp_tools import get_available_tools
        
        tools = get_available_tools()
        print(f"✅ Found {len(tools)} tools")
        
        for tool in tools:
            print(f"   - {tool['name']}: {tool['description'][:50]}...")
        
        # Verify expected tools
        tool_names = [t['name'] for t in tools]
        expected = ['semantic_search', 'list_documents', 'keyword_search']
        
        for expected_tool in expected:
            if expected_tool in tool_names:
                print(f"✅ Tool '{expected_tool}' found")
            else:
                print(f"❌ Tool '{expected_tool}' missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Tool test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_llm_client_factory():
    """Test LLM client factory."""
    print("\n" + "=" * 60)
    print("Test 3: LLM Client Factory")
    print("=" * 60)
    
    try:
        from backend.llm_client import get_llm_client
        from backend.config import USE_FUNCTION_CALLING, USE_MOCK_LLM
        
        client = get_llm_client()
        client_type = type(client).__name__
        
        print(f"✅ Client created: {client_type}")
        print(f"   USE_MOCK_LLM: {USE_MOCK_LLM}")
        print(f"   USE_FUNCTION_CALLING: {USE_FUNCTION_CALLING}")
        
        # Verify correct client type
        if USE_MOCK_LLM:
            expected = "MockLLMClient"
        elif USE_FUNCTION_CALLING:
            expected = "GeminiFunctionCallingClient"
        else:
            expected = "GeminiLLMClient"
        
        if client_type == expected:
            print(f"✅ Correct client type: {client_type}")
        else:
            print(f"❌ Wrong client type. Expected: {expected}, Got: {client_type}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Client factory test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_function_handler():
    """Test Function Handler initialization."""
    print("\n" + "=" * 60)
    print("Test 4: Function Handler")
    print("=" * 60)
    
    try:
        from backend.function_handler import FunctionHandler
        
        handler = FunctionHandler()
        print(f"✅ FunctionHandler initialized")
        print(f"   Model: {handler.model_name}")
        print(f"   Tools: {len(handler.tools)} tool(s)")
        
        return True
        
    except Exception as e:
        print(f"❌ Function handler test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_config_validation():
    """Test configuration validation."""
    print("\n" + "=" * 60)
    print("Test 5: Configuration Validation")
    print("=" * 60)
    
    try:
        from backend.config import (
            DATABASE_URL,
            GEMINI_API_KEY,
            MAX_FUNCTION_CALLS
        )
        
        # Check DATABASE_URL
        if DATABASE_URL:
            print(f"✅ DATABASE_URL is set")
        else:
            print(f"⚠️  DATABASE_URL is empty (will fail when accessing DB)")
        
        # Check GEMINI_API_KEY
        if GEMINI_API_KEY and len(GEMINI_API_KEY) > 10:
            print(f"✅ GEMINI_API_KEY is set ({GEMINI_API_KEY[:10]}...)")
        else:
            print(f"❌ GEMINI_API_KEY is missing or invalid")
            return False
        
        # Check MAX_FUNCTION_CALLS
        if MAX_FUNCTION_CALLS > 0:
            print(f"✅ MAX_FUNCTION_CALLS is valid: {MAX_FUNCTION_CALLS}")
        else:
            print(f"❌ MAX_FUNCTION_CALLS is invalid: {MAX_FUNCTION_CALLS}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Config validation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests."""
    print("\n" + "🧪 " * 20)
    print("FUNCTION CALLING IMPLEMENTATION TESTS")
    print("🧪 " * 20 + "\n")
    
    tests = [
        ("Module Imports", test_imports),
        ("Tool Definitions", test_tools),
        ("LLM Client Factory", test_llm_client_factory),
        ("Function Handler", test_function_handler),
        ("Configuration", test_config_validation),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("\n" + "-" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("-" * 60)
    
    if passed == total:
        print("\n🎉 All tests passed! Implementation is ready.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review.")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
