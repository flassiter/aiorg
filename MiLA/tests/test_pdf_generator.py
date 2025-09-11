"""
Tests for PDF generation functionality.
"""
import os
import tempfile
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest

from src.components.pdf_generator import PDFGenerator, PDFGenerationError
from src.models.loan import LoanRecord
from src.models.payoff import PayoffCalculation
from src.models.pdf_data import PayoffData


class TestPDFGenerator:
    """Test cases for PDFGenerator class."""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def pdf_generator(self, temp_output_dir):
        """Create a PDFGenerator instance with temporary output directory."""
        return PDFGenerator(output_directory=temp_output_dir)
    
    @pytest.fixture
    def sample_loan_record(self):
        """Create a sample loan record for testing."""
        return LoanRecord(
            loan_number="123456",
            borrower_name="John Doe",
            principal_balance=Decimal("15000.00"),
            annual_interest_rate=Decimal("5.50"),
            last_payment_date=date(2024, 1, 1)
        )
    
    @pytest.fixture
    def sample_payoff_calculation(self):
        """Create a sample payoff calculation for testing."""
        return PayoffCalculation(
            loan_number="123456",
            principal_balance=Decimal("15000.00"),
            interest_accrued=Decimal("123.45"),
            total_payoff=Decimal("15123.45"),
            calculation_date=date.today(),
            days_since_payment=30
        )
    
    @pytest.fixture
    def sample_payoff_data(self):
        """Create sample PayoffData for testing."""
        return PayoffData(
            borrower_name="John Doe",
            loan_number="123456",
            statement_date=date.today(),
            principal_balance=Decimal("15000.00"),
            accrued_interest=Decimal("123.45"),
            total_payoff_amount=Decimal("15123.45"),
            payoff_good_through_date=date.today() + timedelta(days=10)
        )
    
    def test_pdf_generator_initialization(self, temp_output_dir):
        """Test PDF generator initialization."""
        generator = PDFGenerator(output_directory=temp_output_dir)
        
        assert generator.output_directory == Path(temp_output_dir)
        assert generator.output_directory.exists()
        assert generator.output_directory.is_dir()
    
    def test_generate_unique_filename(self, pdf_generator):
        """Test unique filename generation."""
        borrower_name = "John Doe"
        loan_number = "123456"
        
        filename1 = pdf_generator.generate_unique_filename(borrower_name, loan_number)
        filename2 = pdf_generator.generate_unique_filename(borrower_name, loan_number)
        
        # Filenames should be unique
        assert filename1 != filename2
        
        # Filenames should contain expected components
        assert "123456" in filename1
        assert "John_Doe" in filename1
        assert filename1.endswith(".pdf")
        
        # Test with special characters in name
        special_name = "María José-Smith"
        filename3 = pdf_generator.generate_unique_filename(special_name, loan_number)
        assert filename3.endswith(".pdf")
        assert "123456" in filename3
    
    def test_create_payoff_pdf_success(self, pdf_generator, sample_payoff_data):
        """Test successful PDF creation."""
        pdf_path = pdf_generator.create_payoff_pdf(sample_payoff_data)
        
        # Check that file was created
        assert os.path.exists(pdf_path)
        assert pdf_path.endswith(".pdf")
        
        # Check file size (should be non-zero)
        file_size = os.path.getsize(pdf_path)
        assert file_size > 0
        
        # Filename should contain loan number and borrower name
        filename = Path(pdf_path).name
        assert "123456" in filename
        assert "John_Doe" in filename
    
    def test_create_payoff_pdf_with_custom_path(self, pdf_generator, sample_payoff_data, temp_output_dir):
        """Test PDF creation with custom output path."""
        custom_path = os.path.join(temp_output_dir, "custom_payoff.pdf")
        
        pdf_path = pdf_generator.create_payoff_pdf(sample_payoff_data, custom_path)
        
        assert pdf_path == custom_path
        assert os.path.exists(custom_path)
        
        # Check file content
        file_size = os.path.getsize(custom_path)
        assert file_size > 0
    
    def test_generate_payoff_statement(self, pdf_generator, sample_loan_record, sample_payoff_calculation):
        """Test payoff statement generation from loan record and calculation."""
        statement_date = date.today()
        
        pdf_path = pdf_generator.generate_payoff_statement(
            sample_loan_record, 
            sample_payoff_calculation, 
            statement_date
        )
        
        # Check that file was created
        assert os.path.exists(pdf_path)
        assert pdf_path.endswith(".pdf")
        
        # Check file size
        file_size = os.path.getsize(pdf_path)
        assert file_size > 0
    
    def test_pdf_creation_error_handling(self, pdf_generator):
        """Test error handling during PDF creation."""
        # Test with invalid PayoffData - empty borrower name should raise validation error
        with pytest.raises(Exception):
            PayoffData(
                borrower_name="",  # Invalid empty name
                loan_number="123456",
                statement_date=date.today(),
                principal_balance=Decimal("15000.00"),
                accrued_interest=Decimal("123.45"),
                total_payoff_amount=Decimal("15123.45"),
                payoff_good_through_date=date.today() + timedelta(days=10)
            )
    
    def test_get_file_path_existing_file(self, pdf_generator, sample_payoff_data):
        """Test getting file path for existing file."""
        # Create a PDF first
        pdf_path = pdf_generator.create_payoff_pdf(sample_payoff_data)
        filename = Path(pdf_path).name
        
        # Test getting the file path
        retrieved_path = pdf_generator.get_file_path(filename)
        
        assert retrieved_path is not None
        assert retrieved_path.exists()
        assert str(retrieved_path) == pdf_path
    
    def test_get_file_path_nonexistent_file(self, pdf_generator):
        """Test getting file path for non-existent file."""
        nonexistent_filename = "nonexistent_file.pdf"
        
        file_path = pdf_generator.get_file_path(nonexistent_filename)
        
        assert file_path is None
    
    def test_cleanup_old_files(self, pdf_generator, sample_payoff_data):
        """Test cleanup of old files."""
        # Create a PDF file
        pdf_path = pdf_generator.create_payoff_pdf(sample_payoff_data)
        
        # Verify file exists
        assert os.path.exists(pdf_path)
        
        # Test cleanup with max_age_hours=0 (should delete all files)
        deleted_count = pdf_generator.cleanup_old_files(max_age_hours=0)
        
        # File should be deleted
        assert deleted_count >= 1
        assert not os.path.exists(pdf_path)
    
    def test_cleanup_old_files_preserves_new_files(self, pdf_generator, sample_payoff_data):
        """Test that cleanup preserves new files."""
        # Create a PDF file
        pdf_path = pdf_generator.create_payoff_pdf(sample_payoff_data)
        
        # Verify file exists
        assert os.path.exists(pdf_path)
        
        # Test cleanup with max_age_hours=24 (should preserve new files)
        deleted_count = pdf_generator.cleanup_old_files(max_age_hours=24)
        
        # File should still exist (it's new)
        assert os.path.exists(pdf_path)
    
    def test_pdf_content_validation(self, pdf_generator, sample_payoff_data):
        """Test that PDF contains expected content structure."""
        pdf_path = pdf_generator.create_payoff_pdf(sample_payoff_data)
        
        # Check file properties
        assert os.path.exists(pdf_path)
        
        # Check that the file is a valid PDF (basic check)
        with open(pdf_path, 'rb') as f:
            header = f.read(4)
            assert header == b'%PDF'  # PDF files start with %PDF
    
    @patch('src.components.pdf_generator.SimpleDocTemplate')
    def test_pdf_generation_error_handling(self, mock_doc, pdf_generator, sample_payoff_data):
        """Test error handling when PDF generation fails."""
        # Mock SimpleDocTemplate to raise an exception
        mock_doc.side_effect = Exception("PDF generation failed")
        
        with pytest.raises(PDFGenerationError) as exc_info:
            pdf_generator.create_payoff_pdf(sample_payoff_data)
        
        assert "PDF generation failed" in str(exc_info.value)


class TestPayoffData:
    """Test cases for PayoffData model."""
    
    def test_payoff_data_validation(self):
        """Test PayoffData validation."""
        # Valid data
        valid_data = PayoffData(
            borrower_name="John Doe",
            loan_number="123456",
            statement_date=date.today(),
            principal_balance=Decimal("15000.00"),
            accrued_interest=Decimal("123.45"),
            total_payoff_amount=Decimal("15123.45"),
            payoff_good_through_date=date.today() + timedelta(days=10)
        )
        
        assert valid_data.borrower_name == "John Doe"
        assert valid_data.loan_number == "123456"
        assert valid_data.total_payoff_amount == Decimal("15123.45")
    
    def test_payoff_data_validation_errors(self):
        """Test PayoffData validation errors."""
        with pytest.raises(ValueError):
            # Empty borrower name
            PayoffData(
                borrower_name="",
                loan_number="123456",
                statement_date=date.today(),
                principal_balance=Decimal("15000.00"),
                accrued_interest=Decimal("123.45"),
                total_payoff_amount=Decimal("15123.45"),
                payoff_good_through_date=date.today() + timedelta(days=10)
            )
        
        with pytest.raises(ValueError):
            # Invalid loan number
            PayoffData(
                borrower_name="John Doe",
                loan_number="abc123",  # Contains letters
                statement_date=date.today(),
                principal_balance=Decimal("15000.00"),
                accrued_interest=Decimal("123.45"),
                total_payoff_amount=Decimal("15123.45"),
                payoff_good_through_date=date.today() + timedelta(days=10)
            )
        
        with pytest.raises(ValueError):
            # Good through date before statement date
            PayoffData(
                borrower_name="John Doe",
                loan_number="123456",
                statement_date=date.today(),
                principal_balance=Decimal("15000.00"),
                accrued_interest=Decimal("123.45"),
                total_payoff_amount=Decimal("15123.45"),
                payoff_good_through_date=date.today() - timedelta(days=1)
            )
    
    def test_from_loan_and_payoff(self):
        """Test PayoffData creation from loan record and payoff calculation."""
        loan_record = LoanRecord(
            loan_number="123456",
            borrower_name="Jane Smith",
            principal_balance=Decimal("20000.00"),
            annual_interest_rate=Decimal("4.75"),
            last_payment_date=date(2024, 1, 15)
        )
        
        payoff_calculation = PayoffCalculation(
            loan_number="123456",
            principal_balance=Decimal("20000.00"),
            interest_accrued=Decimal("200.00"),
            total_payoff=Decimal("20200.00"),
            calculation_date=date.today(),
            days_since_payment=45
        )
        
        statement_date = date.today()
        payoff_data = PayoffData.from_loan_and_payoff(
            loan_record, payoff_calculation, statement_date
        )
        
        assert payoff_data.borrower_name == "Jane Smith"
        assert payoff_data.loan_number == "123456"
        assert payoff_data.principal_balance == Decimal("20000.00")
        assert payoff_data.accrued_interest == Decimal("200.00")
        assert payoff_data.total_payoff_amount == Decimal("20200.00")
        assert payoff_data.statement_date == statement_date
        assert payoff_data.payoff_good_through_date == statement_date + timedelta(days=10)


# Integration test (if needed)
@pytest.mark.integration
class TestPDFGenerationIntegration:
    """Integration tests for PDF generation."""
    
    def test_full_pdf_generation_workflow(self):
        """Test complete PDF generation workflow."""
        # This would test the full workflow from API endpoint to PDF file
        # Would require setting up test data, making API calls, etc.
        pass