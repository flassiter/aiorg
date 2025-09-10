"""
Generate sample loan data Excel file for testing.
"""
import random
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pandas as pd


def generate_sample_loans(count: int = 20) -> list:
    """
    Generate sample loan data.
    
    Args:
        count: Number of loan records to generate
        
    Returns:
        List of loan data dictionaries
    """
    # Sample borrower names
    first_names = [
        "John", "Jane", "Michael", "Sarah", "David", "Lisa", "Robert", "Emily",
        "William", "Ashley", "James", "Jessica", "Christopher", "Amanda", "Daniel",
        "Michelle", "Matthew", "Stephanie", "Anthony", "Jennifer", "Mark", "Angela",
        "Donald", "Brenda", "Steven", "Emma", "Paul", "Olivia", "Andrew", "Kimberly"
    ]
    
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
        "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
        "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
        "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson"
    ]
    
    loans = []
    used_loan_numbers = set()
    
    for i in range(count):
        # Generate unique loan number
        while True:
            loan_number = str(random.randint(100000, 99999999))
            if loan_number not in used_loan_numbers:
                used_loan_numbers.add(loan_number)
                break
        
        # Generate borrower name
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        borrower_name = f"{first_name} {last_name}"
        
        # Generate principal balance ($500 - $50,000)
        principal_balance = Decimal(str(random.randint(500, 50000)))
        
        # Generate interest rate (3.5% - 18.0%)
        interest_rate = Decimal(str(round(random.uniform(3.5, 18.0), 2)))
        
        # Generate last payment date (30-365 days ago)
        days_ago = random.randint(30, 365)
        last_payment_date = date.today() - timedelta(days=days_ago)
        
        loan_data = {
            "Loan Number": loan_number,
            "Borrower Name": borrower_name,
            "Principal Balance": float(principal_balance),
            "Annual Interest Rate": float(interest_rate),
            "Last Payment Date": last_payment_date
        }
        
        loans.append(loan_data)
    
    return loans


def create_sample_excel_file(output_path: str, loan_count: int = 20):
    """
    Create sample loan data Excel file.
    
    Args:
        output_path: Path for the output Excel file
        loan_count: Number of loan records to generate
    """
    # Generate sample data
    loans = generate_sample_loans(loan_count)
    
    # Create DataFrame
    df = pd.DataFrame(loans)
    
    # Ensure proper data types
    df["Loan Number"] = df["Loan Number"].astype(str)
    df["Principal Balance"] = df["Principal Balance"].astype(float)
    df["Annual Interest Rate"] = df["Annual Interest Rate"].astype(float)
    df["Last Payment Date"] = pd.to_datetime(df["Last Payment Date"])
    
    # Create output directory if it doesn't exist
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Save to Excel
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Loans', index=False)
        
        # Format the worksheet
        worksheet = writer.sheets['Loans']
        
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    print(f"Sample loan data file created: {output_path}")
    print(f"Generated {len(loans)} loan records")
    
    # Print summary statistics
    df_summary = df.describe()
    print("\nSummary Statistics:")
    print(f"Principal Balance range: ${df['Principal Balance'].min():.2f} - ${df['Principal Balance'].max():.2f}")
    print(f"Interest Rate range: {df['Annual Interest Rate'].min():.2f}% - {df['Annual Interest Rate'].max():.2f}%")
    print(f"Date range: {df['Last Payment Date'].min().date()} to {df['Last Payment Date'].max().date()}")


if __name__ == "__main__":
    # Create sample data file
    data_dir = Path(__file__).parent / "data"
    output_file = data_dir / "sample_loans.xlsx"
    
    create_sample_excel_file(str(output_file), 20)