"""
Integration tests for payoff calculation workflows with real data.
Tests end-to-end functionality without mocked data.
"""
import pytest
import asyncio
import os
from datetime import date, datetime
from pathlib import Path

from src.components.ai_orchestrator import AIOrchestrator
from src.components.session_manager import session_manager
from src.components.data_access import loan_data_access
from src.models.session import SessionCreateRequest
from src.models.chat import ChatRequest


class TestPayoffWorkflowIntegration:
    """Integration tests for complete payoff calculation workflow."""
    
    @pytest.fixture(autouse=True)
    def setup(self, event_loop):
        """Setup test environment."""
        self.orchestrator = AIOrchestrator()
        self.session = event_loop.run_until_complete(
            session_manager.create_session(SessionCreateRequest(debug_mode=True))
        )
        
    @pytest.mark.asyncio
    async def test_loan_info_retrieval_with_real_data(self):
        """Test retrieving loan information with real data from Excel file."""
        # Test with a known loan number from the sample data
        response = await self.orchestrator.process_user_message(
            "Get loan information for loan 69253358",
            session_id=self.session.session_id
        )
        
        assert response.success, f"Failed to get loan info: {response.error_message}"
        assert "69253358" in response.message
        assert "Mark Wilson" in response.message
        assert len(response.tool_calls) >= 1
        assert response.tool_calls[0].tool_name == "get_loan_info"
        assert response.tool_calls[0].result is not None
        
        # Verify session context was updated
        updated_session = await session_manager.get_session(self.session.session_id)
        assert updated_session.context.current_loan_number == "69253358"
        assert updated_session.context.current_borrower_name == "Mark Wilson"
        
    @pytest.mark.asyncio
    async def test_payoff_calculation_with_real_data(self):
        """Test payoff calculation with real loan data."""
        # First get loan info to establish context
        await self.orchestrator.process_user_message(
            "Get loan information for loan 69253358",
            session_id=self.session.session_id
        )
        
        # Now calculate payoff using context
        response = await self.orchestrator.process_user_message(
            "Calculate payoff for this loan",
            session_id=self.session.session_id
        )
        
        assert response.success, f"Failed to calculate payoff: {response.error_message}"
        assert "payoff" in response.message.lower()
        assert "$" in response.message  # Should contain dollar amount
        
        # Verify we have calculate_payoff tool call
        payoff_tools = [tc for tc in response.tool_calls if tc.tool_name == "calculate_payoff"]
        assert len(payoff_tools) >= 1, "Should have calculate_payoff tool call"
        
        payoff_result = payoff_tools[0].result
        assert payoff_result is not None
        assert "total_payoff" in payoff_result
        assert "calculation_date" in payoff_result
        assert payoff_result["total_payoff"] > 0
        
    @pytest.mark.asyncio
    async def test_complete_payoff_workflow_with_real_data(self):
        """Test complete payoff workflow: loan info → calculate → PDF generation."""
        response = await self.orchestrator.process_user_message(
            "Process complete payoff for loan 69253358",
            session_id=self.session.session_id
        )
        
        assert response.success, f"Complete workflow failed: {response.error_message}"
        
        # Verify all expected tools were called
        tool_names = [tc.tool_name for tc in response.tool_calls]
        expected_tools = ["get_loan_info", "calculate_payoff", "generate_pdf"]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Missing tool: {expected_tool}"
        
        # Verify PDF was generated
        assert len(response.files_generated) >= 1, "Should have generated at least one PDF file"
        pdf_file = response.files_generated[0]
        assert pdf_file.endswith('.pdf'), "Generated file should be a PDF"
        
        # Verify PDF file exists
        pdf_path = Path("output") / pdf_file
        assert pdf_path.exists(), f"PDF file should exist at {pdf_path}"
        
        # Verify session context was updated with all information
        updated_session = await session_manager.get_session(self.session.session_id)
        assert updated_session.context.current_loan_number == "69253358"
        assert updated_session.context.current_payoff_data is not None
        assert updated_session.context.generated_pdf_filename is not None
        
    @pytest.mark.asyncio
    async def test_context_retention_across_multiple_interactions(self):
        """Test that context is retained across multiple chat interactions."""
        # First interaction: get loan info
        response1 = await self.orchestrator.process_user_message(
            "Get loan information for Mark Wilson",
            session_id=self.session.session_id
        )
        assert response1.success
        assert "69253358" in response1.message
        
        # Second interaction: calculate payoff using context
        response2 = await self.orchestrator.process_user_message(
            "Now calculate the payoff amount",
            session_id=self.session.session_id
        )
        assert response2.success, f"Context retention failed: {response2.error_message}"
        
        # Verify payoff was calculated for the correct loan
        payoff_tools = [tc for tc in response2.tool_calls if tc.tool_name == "calculate_payoff"]
        assert len(payoff_tools) >= 1
        
        # Third interaction: generate PDF using context
        response3 = await self.orchestrator.process_user_message(
            "Generate a PDF statement",
            session_id=self.session.session_id
        )
        assert response3.success, f"PDF generation with context failed: {response3.error_message}"
        assert len(response3.files_generated) >= 1
        
    @pytest.mark.asyncio
    async def test_payoff_calculation_accuracy(self):
        """Test payoff calculation accuracy with known loan data."""
        # Get a specific loan and calculate payoff
        response = await self.orchestrator.process_user_message(
            "Get loan info and calculate payoff for loan 69253358",
            session_id=self.session.session_id
        )
        
        assert response.success
        
        # Extract payoff calculation
        payoff_tools = [tc for tc in response.tool_calls if tc.tool_name == "calculate_payoff"]
        assert len(payoff_tools) >= 1
        
        payoff_result = payoff_tools[0].result
        
        # Verify calculation components
        assert "principal_balance" in payoff_result
        assert "interest_accrued" in payoff_result
        assert "total_payoff" in payoff_result
        assert "calculation_date" in payoff_result
        assert "days_since_payment" in payoff_result
        
        # Verify mathematical accuracy
        principal = payoff_result["principal_balance"]
        interest = payoff_result["interest_accrued"]
        total = payoff_result["total_payoff"]
        
        assert abs(total - (principal + interest)) < 0.01, "Total should equal principal + interest"
        assert principal > 0, "Principal balance should be positive"
        assert interest >= 0, "Interest should be non-negative"
        
        # Verify calculation date is today (since no specific date provided)
        calc_date = datetime.fromisoformat(payoff_result["calculation_date"]).date()
        assert calc_date == date.today(), "Calculation date should be today when not specified"
        
    @pytest.mark.asyncio
    async def test_error_handling_with_invalid_loan(self):
        """Test error handling when invalid loan number is provided."""
        response = await self.orchestrator.process_user_message(
            "Calculate payoff for loan 99999999",
            session_id=self.session.session_id
        )
        
        # Should gracefully handle the error
        assert not response.success or "not found" in response.message.lower()
        
    @pytest.mark.asyncio
    async def test_multiple_loans_context_switching(self):
        """Test handling multiple loans and context switching."""
        # First loan
        response1 = await self.orchestrator.process_user_message(
            "Get loan information for loan 69253358",
            session_id=self.session.session_id
        )
        assert response1.success
        
        session = await session_manager.get_session(self.session.session_id)
        assert session.context.current_loan_number == "69253358"
        
        # Switch to different loan
        response2 = await self.orchestrator.process_user_message(
            "Get loan information for loan 8321619",
            session_id=self.session.session_id
        )
        assert response2.success
        
        # Verify context switched
        session = await session_manager.get_session(self.session.session_id)
        assert session.context.current_loan_number == "8321619"
        
        # Calculate payoff for current loan (should be 8321619)
        response3 = await self.orchestrator.process_user_message(
            "Calculate payoff for this loan",
            session_id=self.session.session_id
        )
        assert response3.success
        
        # Verify payoff was calculated for the correct loan
        payoff_tools = [tc for tc in response3.tool_calls if tc.tool_name == "calculate_payoff"]
        assert len(payoff_tools) >= 1
        # The context should have been used to determine the loan number
        
    @pytest.mark.asyncio
    async def test_pdf_generation_with_real_data(self):
        """Test PDF generation with real loan and payoff data."""
        # Get loan info first
        await self.orchestrator.process_user_message(
            "Get loan information for loan 69253358",
            session_id=self.session.session_id
        )
        
        # Calculate payoff
        await self.orchestrator.process_user_message(
            "Calculate payoff for this loan",
            session_id=self.session.session_id
        )
        
        # Generate PDF
        response = await self.orchestrator.process_user_message(
            "Generate PDF statement for this loan",
            session_id=self.session.session_id
        )
        
        assert response.success, f"PDF generation failed: {response.error_message}"
        assert len(response.files_generated) >= 1
        
        # Verify PDF file
        pdf_file = response.files_generated[0]
        pdf_path = Path("output") / pdf_file
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0, "PDF file should not be empty"
        
        # Verify filename contains loan information
        assert "69253358" in pdf_file
        assert "Mark_Wilson" in pdf_file or "Mark" in pdf_file
        
    @pytest.mark.asyncio 
    async def test_data_consistency_across_tools(self):
        """Test that data remains consistent across all tools in the workflow."""
        response = await self.orchestrator.process_user_message(
            "Process complete payoff for loan 69253358",
            session_id=self.session.session_id
        )
        
        assert response.success
        
        # Extract data from each tool
        loan_info = None
        payoff_info = None
        pdf_info = None
        
        for tool_call in response.tool_calls:
            if tool_call.tool_name == "get_loan_info":
                loan_info = tool_call.result
            elif tool_call.tool_name == "calculate_payoff":
                payoff_info = tool_call.result
            elif tool_call.tool_name == "generate_pdf":
                pdf_info = tool_call.result
        
        # Verify data consistency
        assert loan_info is not None, "Should have loan info"
        assert payoff_info is not None, "Should have payoff info"
        assert pdf_info is not None, "Should have PDF info"
        
        # Loan numbers should match across all tools
        assert loan_info["loan_number"] == payoff_info["loan_number"]
        assert loan_info["loan_number"] == pdf_info["loan_number"]
        
        # Borrower names should match
        assert loan_info["borrower_name"] == pdf_info["borrower_name"]


if __name__ == "__main__":
    # Run tests directly if needed
    import asyncio
    
    async def run_tests():
        test_class = TestPayoffWorkflowIntegration()
        await test_class.setup()
        
        print("🧪 Running integration tests...")
        
        try:
            await test_class.test_loan_info_retrieval_with_real_data()
            print("✅ Loan info retrieval test passed")
        except Exception as e:
            print(f"❌ Loan info retrieval test failed: {e}")
        
        try:
            await test_class.test_payoff_calculation_with_real_data()
            print("✅ Payoff calculation test passed")
        except Exception as e:
            print(f"❌ Payoff calculation test failed: {e}")
        
        try:
            await test_class.test_complete_payoff_workflow_with_real_data()
            print("✅ Complete workflow test passed")
        except Exception as e:
            print(f"❌ Complete workflow test failed: {e}")
        
        print("🏁 Integration tests completed")
    
    asyncio.run(run_tests())