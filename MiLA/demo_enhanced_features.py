#!/usr/bin/env python3
"""
Demo script showcasing the enhanced MiLA features without requiring Ollama.
This demonstrates the tool chaining, session management, and email simulation.
"""
import asyncio
import json
import sys
from pathlib import Path
import os

# Setup paths
os.chdir(Path(__file__).parent)
sys.path.insert(0, str(Path(__file__).parent))

from src.components.tool_chain import tool_chain_engine, ToolStep, ToolChainPlan
from src.components.session_manager import session_manager
from src.components.email_service import email_service
from src.components.data_access import loan_data_access
from src.models.tool_chain import ToolStepStatus
from src.models.session import SessionCreateRequest


async def demo_session_with_context():
    """Demonstrate session management with context retention."""
    print("🔄 DEMO: Session Management with Context Retention")
    print("=" * 60)
    
    # Create a session
    session = await session_manager.create_session(
        SessionCreateRequest(debug_mode=True, expiry_hours=1)
    )
    print(f"✅ Created session: {session.session_id}")
    print(f"   Debug mode: {session.context.debug_mode}")
    print(f"   Expires at: {session.expires_at}")
    
    # Simulate loan lookup context
    loan_data = {
        'loan_number': '69253358',
        'borrower_name': 'Mark Wilson',
        'principal_balance': 19886.00,
        'annual_interest_rate': 16.64,
        'email_address': 'mark.wilson@email.com'
    }
    
    session.context.update_from_loan_info(loan_data)
    print(f"\n✅ Updated context with loan: {session.context.current_loan_number}")
    print(f"   Borrower: {session.context.current_borrower_name}")
    print(f"   Email: {session.context.borrower_email}")
    
    # Simulate payoff calculation context
    payoff_data = {
        'principal_balance': 19886.00,
        'interest_accrued': 270.78,
        'total_payoff': 20156.78,
        'calculation_date': '2025-09-10',
        'days_since_payment': 90
    }
    
    session.context.update_from_payoff_calc(payoff_data)
    print(f"\n✅ Updated context with payoff: ${session.context.current_payoff_data['total_payoff']:,.2f}")
    
    # Simulate PDF generation context
    pdf_data = {
        'filename': 'payoff_statement_69253358_Mark_Wilson_20250910.pdf',
        'download_url': '/api/files/payoff_statement_69253358_Mark_Wilson_20250910.pdf'
    }
    
    session.context.update_from_pdf_generation(pdf_data)
    print(f"✅ Updated context with PDF: {session.context.generated_pdf_filename}")
    
    # Test context clearing trigger
    print(f"\n🔄 Testing context clearing...")
    should_clear = session.should_clear_context("Show me loan information for loan 12345678")
    print(f"   Should clear context for new loan request: {should_clear}")
    
    if should_clear:
        session.clear_context()
        print(f"   ✅ Context cleared: {session.context.has_loan_context()}")
    
    return session


async def demo_tool_chain_creation():
    """Demonstrate tool chain creation and pattern detection."""
    print("\n\n🔗 DEMO: Tool Chain Creation and Pattern Detection")
    print("=" * 60)
    
    test_messages = [
        "Process complete payoff for loan 69253358",
        "Complete payoff processing for Mark Wilson", 
        "Calculate payoff for loan 12345",
        "Show me loan information for Steven Lopez",
        "Send email with payoff information"
    ]
    
    for message in test_messages:
        print(f"\n📝 Message: '{message}'")
        
        # Detect chain pattern
        template = tool_chain_engine.detect_chain_pattern(message)
        
        if template:
            print(f"   🔗 Detected chain: {template.name}")
            print(f"   📋 Description: {template.description}")
            print(f"   🛠️ Steps: {len(template.steps)}")
            
            # Create execution plan
            plan = tool_chain_engine.create_chain_plan(template)
            print(f"   🆔 Chain ID: {plan.chain_id}")
            print(f"   📅 Created: {plan.created_at}")
            
            for step in plan.steps:
                print(f"      Step {step.step_number}: {step.tool_name}")
        else:
            print(f"   ⚠️ No chain pattern detected - would use individual tools")
    
    return True


async def demo_email_simulation():
    """Demonstrate email simulation service."""
    print("\n\n📧 DEMO: Email Simulation Service")
    print("=" * 60)
    
    # Test payoff statement email
    result = await email_service.send_payoff_statement(
        recipient_email="mark.wilson@email.com",
        loan_number="69253358",
        borrower_name="Mark Wilson", 
        payoff_amount=20156.78,
        pdf_filename="payoff_statement_69253358_Mark_Wilson.pdf"
    )
    
    print(f"✅ Email sent successfully:")
    print(f"   📧 To: {result['to_address']}")
    print(f"   📋 Subject: {result['subject']}")
    print(f"   🆔 Message ID: {result['message_id']}")
    print(f"   📎 Has attachment: {result['has_attachment']}")
    print(f"   📅 Sent at: {result['sent_at']}")
    
    # Show email log
    sent_emails = email_service.get_sent_emails(3)
    print(f"\n📋 Recent emails sent: {len(sent_emails)}")
    for i, email in enumerate(sent_emails[-3:], 1):
        print(f"   {i}. To: {email['to_address']} | Subject: {email['subject'][:50]}...")
    
    # Test confirmation workflow
    from src.models.session import ContextData
    context = ContextData(
        current_loan_number="69253358",
        current_borrower_name="Mark Wilson",
        borrower_email="mark.wilson@email.com"
    )
    
    confirmation_msg = await email_service.confirm_email_send("mark.wilson@email.com", context)
    print(f"\n💬 Confirmation message: {confirmation_msg}")
    
    return result


async def demo_data_access_with_emails():
    """Demonstrate data access with email addresses."""
    print("\n\n📊 DEMO: Data Access with Email Addresses")
    print("=" * 60)
    
    # Load sample data
    sample_file = "data/sample_loans.xlsx"
    loans = await loan_data_access.load_loan_data(sample_file)
    
    print(f"✅ Loaded {len(loans)} loan records")
    
    # Show sample loans with email addresses
    print(f"\n📋 Sample loan records with email addresses:")
    for i, loan in enumerate(loans[:5], 1):
        email = getattr(loan, 'email_address', 'No email')
        print(f"   {i}. {loan.loan_number} | {loan.borrower_name} | {email}")
    
    # Test loan search
    test_loan = await loan_data_access.find_loan_by_identifier("Mark Wilson")
    if test_loan:
        print(f"\n🔍 Found loan by name: {test_loan.loan_number}")
        print(f"   📧 Email: {getattr(test_loan, 'email_address', 'No email')}")
        print(f"   💰 Balance: ${test_loan.principal_balance:,.2f}")
    
    return loans


async def demo_manual_tool_chain():
    """Demonstrate manual tool chain execution."""
    print("\n\n⚙️ DEMO: Manual Tool Chain Execution")
    print("=" * 60)
    
    # Initialize the AI orchestrator to register tools with the chain engine
    from src.components.ai_orchestrator import get_ai_orchestrator
    orchestrator = get_ai_orchestrator()
    
    print(f"✅ Registered {len(tool_chain_engine.available_tools)} tools with chain engine")
    for tool_name in tool_chain_engine.available_tools.keys():
        print(f"   🛠️ {tool_name}")
    
    # Create a custom tool chain
    custom_chain = tool_chain_engine.create_custom_chain(
        description="Demo loan processing workflow",
        tool_sequence=["get_loan_info", "calculate_payoff", "generate_pdf"],
        context={"loan_identifier": "69253358"}
    )
    
    print(f"🔗 Created custom chain: {custom_chain.chain_id}")
    print(f"📋 Description: {custom_chain.description}")
    print(f"🛠️ Total steps: {custom_chain.total_steps}")
    
    # Show execution plan
    print(f"\n📅 Execution Plan:")
    for step in custom_chain.steps:
        status_emoji = "⏳" if step.status == ToolStepStatus.PENDING else "✅"
        print(f"   {status_emoji} Step {step.step_number}: {step.tool_name}")
    
    # Note: We won't actually execute this chain since it requires tool implementations
    print(f"\n💡 This chain would execute {custom_chain.total_steps} tools in sequence")
    print(f"   Each step would pass context to the next step")
    print(f"   Progress updates would be sent for real-time UI feedback")
    
    return custom_chain


async def run_enhanced_demo():
    """Run the complete enhanced features demo."""
    print("🚀 MiLA Enhanced Features Demo")
    print("🤖 Machine Intelligence Loan Assistant")
    print("📅 Tool Chaining, Session Management & Email Simulation")
    print("=" * 80)
    
    try:
        # Run all demos
        session = await demo_session_with_context()
        await demo_tool_chain_creation()
        email_result = await demo_email_simulation()
        loans = await demo_data_access_with_emails()
        chain = await demo_manual_tool_chain()
        
        # Summary
        print("\n\n🎉 DEMO SUMMARY")
        print("=" * 60)
        print(f"✅ Session Management: Working ({session.session_id[:8]}...)")
        print(f"✅ Tool Chain Detection: Working ({len(tool_chain_engine.chain_templates)} templates)")
        print(f"✅ Email Simulation: Working ({email_result['message_id'][:8]}...)")
        print(f"✅ Data Access: Working ({len(loans)} loan records)")
        print(f"✅ Chain Creation: Working ({chain.total_steps} steps)")
        
        print(f"\n🎯 Key Features Demonstrated:")
        print(f"   🔄 Session context retention across interactions")
        print(f"   🔗 Automatic tool chain detection and planning")
        print(f"   📧 Email simulation with PDF attachments")
        print(f"   📊 Enhanced data access with email addresses")
        print(f"   ⚙️ Custom tool chain creation and execution")
        
        print(f"\n💡 Next Steps:")
        print(f"   1. Start the FastAPI server: python src/main.py")
        print(f"   2. Open enhanced_chat_ui.html in a browser")
        print(f"   3. Try: 'Process complete payoff for loan 69253358'")
        print(f"   4. Enable debug mode to see tool chaining in action")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_enhanced_demo())
    print(f"\n🏁 Demo {'completed successfully' if success else 'failed'}!")
    sys.exit(0 if success else 1)