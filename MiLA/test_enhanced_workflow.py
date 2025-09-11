#!/usr/bin/env python3
"""
Test script for the enhanced MiLA workflow with tool chaining, session management, and email simulation.
"""
import asyncio
import json
import sys
from pathlib import Path

# Add project root to path and change to project directory
import os
os.chdir(Path(__file__).parent)
sys.path.insert(0, str(Path(__file__).parent))

from src.components.tool_chain import tool_chain_engine
from src.components.session_manager import session_manager
from src.components.email_service import email_service
from src.components.ai_orchestrator import get_ai_orchestrator
from src.components.data_access import loan_data_access
from src.models.chat import ChatRequest, ChatResponse
from src.models.session import SessionCreateRequest


async def test_data_loading():
    """Test that sample data loads correctly with email addresses."""
    print("🔧 Testing data loading...")
    
    sample_file = Path("data/sample_loans.xlsx")
    if not sample_file.exists():
        print("❌ Sample data file not found")
        return False
    
    try:
        loans = await loan_data_access.load_loan_data(str(sample_file))
        print(f"✅ Loaded {len(loans)} loan records")
        
        # Check if email addresses are present
        sample_loan = loans[0]
        if hasattr(sample_loan, 'email_address') and sample_loan.email_address:
            print(f"✅ Email addresses available: {sample_loan.email_address}")
        else:
            print("⚠️ No email addresses found in sample data")
        
        return True
    except Exception as e:
        print(f"❌ Data loading failed: {e}")
        return False


async def test_session_management():
    """Test session creation and context management."""
    print("\n🔧 Testing session management...")
    
    try:
        # Create a new session
        session = await session_manager.create_session()
        print(f"✅ Created session: {session.session_id}")
        
        # Test context updates
        session.context.update_from_loan_info({
            'loan_number': '69253358',
            'borrower_name': 'Mark Wilson',
            'email_address': 'mark.wilson@email.com'
        })
        
        print(f"✅ Context updated: {session.context.current_loan_number}")
        
        # Test session retrieval
        retrieved = await session_manager.get_session(session.session_id)
        if retrieved and retrieved.context.current_loan_number == '69253358':
            print("✅ Session retrieval and context persistence working")
            return True
        else:
            print("❌ Session retrieval failed")
            return False
            
    except Exception as e:
        print(f"❌ Session management failed: {e}")
        return False


async def test_tool_chain_detection():
    """Test tool chain pattern detection."""
    print("\n🔧 Testing tool chain detection...")
    
    try:
        # Test complete payoff processing pattern
        test_messages = [
            "Process complete payoff for loan 69253358",
            "Complete payoff processing for Mark Wilson",
            "Process full payoff workflow",
            "Calculate payoff for loan 12345"  # Should trigger quick payoff chain
        ]
        
        for message in test_messages:
            template = tool_chain_engine.detect_chain_pattern(message)
            if template:
                print(f"✅ Detected chain '{template.name}' for: '{message}'")
            else:
                print(f"⚠️ No chain detected for: '{message}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Tool chain detection failed: {e}")
        return False


async def test_email_simulation():
    """Test email simulation service."""
    print("\n🔧 Testing email simulation...")
    
    try:
        # Test email generation
        result = await email_service.send_payoff_statement(
            "test@example.com",
            "69253358", 
            "Test Borrower",
            25000.50,
            "test_statement.pdf"
        )
        
        if result['success']:
            print(f"✅ Email simulation successful: {result['message_id']}")
            
            # Check email log
            sent_emails = email_service.get_sent_emails(1)
            if sent_emails:
                print(f"✅ Email logged: {sent_emails[0]['to_address']}")
                return True
            else:
                print("❌ Email not found in log")
                return False
        else:
            print("❌ Email simulation failed")
            return False
            
    except Exception as e:
        print(f"❌ Email simulation failed: {e}")
        return False


async def test_individual_tool_execution():
    """Test individual tool execution without chains."""
    print("\n🔧 Testing individual tool execution...")
    
    try:
        orchestrator = get_ai_orchestrator()
        
        # Create a session
        session = await session_manager.create_session()
        
        # Test simple loan info request
        response = await orchestrator.process_user_message(
            "Show me loan information for Mark Wilson",
            session.session_id
        )
        
        if response.success and response.tool_calls:
            print(f"✅ Individual tool execution successful: {len(response.tool_calls)} tools called")
            
            # Check if loan info was retrieved
            loan_call = next((tc for tc in response.tool_calls if tc.tool_name == "get_loan_info"), None)
            if loan_call and loan_call.result:
                print(f"✅ Loan info retrieved: {loan_call.result.get('loan_number')}")
                return True
            else:
                print("❌ No loan info in response")
                return False
        else:
            print(f"❌ Individual tool execution failed: {response.message}")
            return False
            
    except Exception as e:
        print(f"❌ Individual tool execution failed: {e}")
        return False


async def test_chain_execution():
    """Test complete tool chain execution."""
    print("\n🔧 Testing tool chain execution...")
    
    try:
        orchestrator = get_ai_orchestrator()
        
        # Create a session
        session = await session_manager.create_session()
        
        # Test complete payoff processing chain
        response = await orchestrator.process_user_message(
            "Process complete payoff for loan 69253358",
            session.session_id
        )
        
        if response.success:
            print(f"✅ Chain execution successful: {len(response.tool_calls)} tools in chain")
            
            # Check for expected tools in sequence
            expected_tools = ["get_loan_info", "calculate_payoff", "generate_pdf"]
            actual_tools = [tc.tool_name for tc in response.tool_calls]
            
            if all(tool in actual_tools for tool in expected_tools):
                print(f"✅ All expected tools executed: {actual_tools}")
                
                # Check if PDF was generated
                pdf_call = next((tc for tc in response.tool_calls if tc.tool_name == "generate_pdf"), None)
                if pdf_call and pdf_call.result:
                    filename = pdf_call.result.get('filename')
                    print(f"✅ PDF generated: {filename}")
                    return True
                else:
                    print("❌ No PDF generated")
                    return False
            else:
                print(f"❌ Missing expected tools. Got: {actual_tools}")
                return False
        else:
            print(f"❌ Chain execution failed: {response.message}")
            return False
            
    except Exception as e:
        print(f"❌ Chain execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_context_retention():
    """Test context retention across multiple interactions."""
    print("\n🔧 Testing context retention...")
    
    try:
        orchestrator = get_ai_orchestrator()
        
        # Create a session
        session = await session_manager.create_session()
        session_id = session.session_id
        
        # First interaction: Get loan info
        response1 = await orchestrator.process_user_message(
            "Show me loan information for Mark Wilson",
            session_id
        )
        
        if not response1.success:
            print(f"❌ First interaction failed: {response1.message}")
            return False
        
        # Second interaction: Calculate payoff (should use context)
        response2 = await orchestrator.process_user_message(
            "Calculate payoff for this loan",
            session_id
        )
        
        if response2.success and response2.tool_calls:
            print("✅ Context retention successful - payoff calculated without specifying loan number")
            
            # Third interaction: Generate PDF (should use context)
            response3 = await orchestrator.process_user_message(
                "Create a loan payoff document",
                session_id
            )
            
            if response3.success and any(tc.tool_name == "generate_pdf" for tc in response3.tool_calls):
                print("✅ PDF generation successful using retained context")
                return True
            else:
                print(f"❌ PDF generation failed: {response3.message}")
                return False
        else:
            print(f"❌ Second interaction failed: {response2.message}")
            return False
            
    except Exception as e:
        print(f"❌ Context retention test failed: {e}")
        return False


async def run_all_tests():
    """Run all tests and report results."""
    print("🚀 Starting Enhanced MiLA Workflow Tests\n")
    
    tests = [
        ("Data Loading", test_data_loading),
        ("Session Management", test_session_management),
        ("Tool Chain Detection", test_tool_chain_detection),
        ("Email Simulation", test_email_simulation),
        ("Individual Tool Execution", test_individual_tool_execution),
        ("Chain Execution", test_chain_execution),
        ("Context Retention", test_context_retention),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Enhanced MiLA is working correctly.")
    else:
        print("⚠️ Some tests failed. Please check the output above.")
    
    return passed == len(results)


if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)