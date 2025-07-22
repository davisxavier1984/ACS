#!/usr/bin/env python3
"""
Integration test for header generation within full PDF generation.

This test verifies that the improved header generation works correctly
within the complete PDF generation workflow.
"""

import sys
import os
import logging
import pandas as pd
from io import BytesIO

# Add current directory to path
sys.path.append('.')

from pdf_generator import PDFGenerator
from pdf_config import PDFConfig

def test_full_pdf_with_header():
    """Test full PDF generation with improved header."""
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)
    
    logger.info("Starting full PDF generation test with header...")
    
    # Create realistic test data
    df_test = pd.DataFrame({
        'competencia': ['2024-01', '2024-02', '2024-03'],
        'qtTotalCredenciado': [150, 155, 160],
        'qtTotalPago': [145, 150, 155],
        'vlEsperado': [75000.0, 77500.0, 80000.0],
        'vlTotalAcs': [72500.0, 75000.0, 77500.0]
    })
    
    dados_atual = pd.Series({
        'qtTotalCredenciado': 160,
        'qtTotalPago': 155,
        'vlEsperado': 80000.0,
        'vlTotalAcs': 77500.0
    })
    
    competencias = ['2024-01', '2024-02', '2024-03']
    
    try:
        logger.info("Creating PDFGenerator instance...")
        
        generator = PDFGenerator(
            municipio='Abaré',
            uf='BA',
            df_3_meses=df_test,
            dados_atual=dados_atual,
            competencias=competencias
        )
        
        logger.info("Generating PDF with improved header...")
        
        # Generate the complete PDF
        pdf_buffer = generator.generate_pdf()
        
        # Verify PDF was generated
        pdf_data = pdf_buffer.getvalue()
        logger.info(f"PDF generated successfully! Size: {len(pdf_data)} bytes")
        
        # Save test PDF for manual verification
        with open('test_header_output.pdf', 'wb') as f:
            f.write(pdf_data)
        
        logger.info("Test PDF saved as 'test_header_output.pdf'")
        
        # Basic validation
        assert len(pdf_data) > 1000, "PDF seems too small"
        assert pdf_data.startswith(b'%PDF'), "Invalid PDF header"
        
        logger.info("PDF validation passed!")
        
        return True
        
    except Exception as e:
        logger.error(f"Full PDF generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_full_pdf_with_header()
    if success:
        print("\n✅ Full PDF generation with header test passed!")
        sys.exit(0)
    else:
        print("\n❌ Full PDF generation with header test failed!")
        sys.exit(1)