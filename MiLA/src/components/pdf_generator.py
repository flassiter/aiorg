"""
PDF generation component for creating loan payoff statements.
"""
import logging
import os
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus.flowables import HRFlowable

from ..models.pdf_data import PayoffData

logger = logging.getLogger(__name__)


class PDFGenerationError(Exception):
    """Custom exception for PDF generation errors"""
    pass


class PDFGenerator:
    """
    PDF generation service for creating loan payoff statements.
    """
    
    def __init__(self, output_directory: str = "output"):
        """
        Initialize PDF generator with output directory.
        
        Args:
            output_directory: Directory to store generated PDF files
        """
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(exist_ok=True)
        logger.info(f"PDF Generator initialized with output directory: {self.output_directory}")
    
    def generate_unique_filename(self, borrower_name: str, loan_number: str) -> str:
        """
        Generate a unique filename for the PDF.
        
        Args:
            borrower_name: Name of the borrower
            loan_number: Loan number
            
        Returns:
            Unique filename for the PDF
        """
        # Clean borrower name for filename
        clean_name = "".join(c for c in borrower_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        clean_name = clean_name.replace(' ', '_')
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Add unique identifier to prevent collisions
        unique_id = str(uuid.uuid4())[:8]
        
        filename = f"payoff_statement_{loan_number}_{clean_name}_{timestamp}_{unique_id}.pdf"
        return filename
    
    def create_payoff_pdf(self, payoff_data: PayoffData, output_path: Optional[str] = None) -> str:
        """
        Create a payoff statement PDF from PayoffData.
        
        Args:
            payoff_data: PayoffData object containing all required information
            output_path: Optional specific output path for the PDF
            
        Returns:
            Path to the generated PDF file
            
        Raises:
            PDFGenerationError: If PDF generation fails
        """
        try:
            # Generate filename if not provided
            if output_path is None:
                filename = self.generate_unique_filename(payoff_data.borrower_name, payoff_data.loan_number)
                output_path = self.output_directory / filename
            else:
                output_path = Path(output_path)
            
            logger.info(f"Generating PDF for loan {payoff_data.loan_number}, borrower {payoff_data.borrower_name}")
            
            # Create PDF document
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            # Build PDF content
            story = self._build_pdf_content(payoff_data)
            
            # Generate the PDF
            doc.build(story)
            
            logger.info(f"PDF generated successfully: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to generate PDF: {str(e)}")
            raise PDFGenerationError(f"PDF generation failed: {str(e)}")
    
    def generate_payoff_statement(self, loan_record, payoff_data, statement_date: Optional[date] = None) -> str:
        """
        Generate a payoff statement PDF from loan record and payoff calculation.
        
        Args:
            loan_record: LoanRecord object
            payoff_data: PayoffCalculation or PayoffResult object
            statement_date: Optional statement date (defaults to today)
            
        Returns:
            Path to the generated PDF file
        """
        # Convert to PayoffData model
        pdf_data = PayoffData.from_loan_and_payoff(loan_record, payoff_data, statement_date)
        
        # Generate PDF
        return self.create_payoff_pdf(pdf_data)
    
    def _build_pdf_content(self, payoff_data: PayoffData) -> list:
        """
        Build the content for the PDF document.
        
        Args:
            payoff_data: PayoffData object containing statement information
            
        Returns:
            List of ReportLab flowables for the PDF
        """
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.darkblue,
            alignment=1  # Center alignment
        )
        
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.darkblue
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=6
        )
        
        # Company header
        story.append(Paragraph("MiLA Loan Services", title_style))
        story.append(Paragraph("Loan Payoff Statement", header_style))
        story.append(Spacer(1, 20))
        
        # Statement information
        story.append(Paragraph("Statement Information", header_style))
        
        # Create statement info table
        statement_data = [
            ['Statement Date:', payoff_data.statement_date.strftime('%B %d, %Y')],
            ['Good Through Date:', payoff_data.payoff_good_through_date.strftime('%B %d, %Y')],
        ]
        
        statement_table = Table(statement_data, colWidths=[2*inch, 3*inch])
        statement_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(statement_table)
        story.append(Spacer(1, 20))
        
        # Borrower information
        story.append(Paragraph("Borrower Information", header_style))
        
        borrower_data = [
            ['Borrower Name:', payoff_data.borrower_name],
            ['Loan Number:', payoff_data.loan_number],
        ]
        
        borrower_table = Table(borrower_data, colWidths=[2*inch, 3*inch])
        borrower_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(borrower_table)
        story.append(Spacer(1, 20))
        
        # Payment breakdown
        story.append(Paragraph("Payment Breakdown", header_style))
        
        # Format currency values
        principal_str = f"${payoff_data.principal_balance:,.2f}"
        interest_str = f"${payoff_data.accrued_interest:,.2f}"
        total_str = f"${payoff_data.total_payoff_amount:,.2f}"
        
        breakdown_data = [
            ['Description', 'Amount'],
            ['Principal Balance', principal_str],
            ['Accrued Interest', interest_str],
            ['', ''],  # Separator row
            ['Total Payoff Amount', total_str],
        ]
        
        breakdown_table = Table(breakdown_data, colWidths=[3*inch, 2*inch])
        breakdown_table.setStyle(TableStyle([
            # Header row
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            
            # Total row
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 14),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightblue),
            
            # Borders
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
            
            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(breakdown_table)
        story.append(Spacer(1, 30))
        
        # Important notice
        story.append(HRFlowable(width="100%", thickness=1, color=colors.black))
        story.append(Spacer(1, 12))
        
        notice_text = f"""
        <b>IMPORTANT NOTICE:</b><br/>
        This payoff amount is valid through <b>{payoff_data.payoff_good_through_date.strftime('%B %d, %Y')}</b>. 
        After this date, additional interest may accrue and a new payoff statement will be required.
        Please remit payment to MiLA Loan Services with your loan number <b>{payoff_data.loan_number}</b> 
        as the reference.
        """
        
        notice_style = ParagraphStyle(
            'Notice',
            parent=styles['Normal'],
            fontSize=11,
            leading=14,
            spaceAfter=12,
            borderWidth=1,
            borderColor=colors.grey,
            borderPadding=12,
            backColor=colors.lightgrey
        )
        
        story.append(Paragraph(notice_text, notice_style))
        
        # Footer
        story.append(Spacer(1, 30))
        footer_text = f"Generated on {date.today().strftime('%B %d, %Y')} | MiLA Loan Services"
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            alignment=1  # Center alignment
        )
        story.append(Paragraph(footer_text, footer_style))
        
        return story
    
    def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up PDF files older than specified age.
        
        Args:
            max_age_hours: Maximum age of files to keep in hours
            
        Returns:
            Number of files deleted
        """
        deleted_count = 0
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        try:
            for pdf_file in self.output_directory.glob("*.pdf"):
                file_time = datetime.fromtimestamp(pdf_file.stat().st_mtime)
                if file_time < cutoff_time:
                    pdf_file.unlink()
                    deleted_count += 1
                    logger.info(f"Deleted old PDF file: {pdf_file}")
                    
        except Exception as e:
            logger.warning(f"Error during file cleanup: {str(e)}")
        
        logger.info(f"Cleanup completed. Deleted {deleted_count} old PDF files.")
        return deleted_count
    
    def get_file_path(self, filename: str) -> Optional[Path]:
        """
        Get the full path for a filename in the output directory.
        
        Args:
            filename: Name of the PDF file
            
        Returns:
            Path object if file exists, None otherwise
        """
        file_path = self.output_directory / filename
        return file_path if file_path.exists() else None


# Global PDF generator instance
pdf_generator = PDFGenerator()