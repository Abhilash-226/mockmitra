#!/usr/bin/env python3
"""
PYQ Extraction Script
Extracts questions from PDF exam papers using Gemini Vision AI.

Usage:
    python extract.py ts_eamcet 2020-1.pdf     # Extract specific paper
    python extract.py ts_eamcet --all          # Extract all papers
    python extract.py ts_eamcet --list         # List available PDFs
    python extract.py --exams                  # List configured exams
"""
import sys
import argparse
from pathlib import Path

# Add parent dir and backend dir to path for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from pyq_extractor import GeminiExtractor, get_exam_config
from pyq_extractor.config import list_available_exams


def main():
    parser = argparse.ArgumentParser(
        description="Extract questions from PYQ PDFs using Gemini Vision",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python extract.py ts_eamcet 2020-1.pdf     # Extract specific paper
    python extract.py ts_eamcet --all          # Extract all non-extracted papers
    python extract.py ts_eamcet --list         # List available PDFs
    python extract.py --exams                  # List configured exams
        """
    )
    
    parser.add_argument('exam_code', nargs='?', help='Exam code (e.g., ts_eamcet)')
    parser.add_argument('pdf', nargs='?', help='PDF filename to extract')
    parser.add_argument('--all', action='store_true', help='Extract all non-extracted papers')
    parser.add_argument('--list', action='store_true', help='List available PDFs')
    parser.add_argument('--exams', action='store_true', help='List configured exams')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between pages (default: 2.0s)')
    
    args = parser.parse_args()
    
    # List configured exams
    if args.exams:
        print("Configured exams:")
        for code in list_available_exams():
            config = get_exam_config(code)
            print(f"  {code}: {config.name}")
        return
    
    # Need exam code for other operations
    if not args.exam_code:
        parser.print_help()
        return
    
    # Get exam config
    try:
        config = get_exam_config(args.exam_code)
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    extractor = GeminiExtractor(config)
    
    # List available PDFs
    if args.list:
        print(f"\nAvailable PDFs for {config.name}:")
        pdfs = extractor.list_available_pdfs()
        extracted = extractor.list_extracted()
        
        for pdf in pdfs:
            paper_id = pdf.replace('.pdf', '')
            status = "✓ extracted" if f"{config.code}_{paper_id.replace('-', '_')}" in str(extracted) else "  pending"
            print(f"  {pdf} {status}")
        
        print(f"\nTotal: {len(pdfs)} PDFs, {len(extracted)} extracted")
        return
    
    # Extract all
    if args.all:
        pdfs = extractor.list_available_pdfs()
        extracted = set(extractor.list_extracted())
        
        to_extract = []
        for pdf in pdfs:
            parts = pdf.replace('.pdf', '').split('-')
            year = parts[0]
            shift = parts[1] if len(parts) > 1 else '1'
            paper_id = f"{config.code}_{year}_{shift}"
            if paper_id not in extracted:
                to_extract.append(pdf)
        
        if not to_extract:
            print("All papers already extracted!")
            return
        
        print(f"Extracting {len(to_extract)} papers...")
        for pdf in to_extract:
            try:
                extractor.extract_and_save(pdf)
            except Exception as e:
                print(f"Failed to extract {pdf}: {e}")
        return
    
    # Extract specific PDF
    if args.pdf:
        try:
            extractor.extract_and_save(args.pdf)
            print("\nExtraction complete!")
        except Exception as e:
            print(f"Error: {e}")
        return
    
    # No action specified
    parser.print_help()


if __name__ == '__main__':
    main()
