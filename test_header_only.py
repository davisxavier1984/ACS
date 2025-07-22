#!/usr/bin/env python3
"""
Focused test for header generation only.

This test verifies that the improved header generation works correctly
without dependencies on chart generation or other components.
"""

import sys
import os
import logging
import pandas as pd
from io import BytesIO

# Add current directory to path
sys.path.append('.')

from pdf_generator import PDFGenerator
from pdf_config import PDFConfig, ResourceManager
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

def test_header_only():
    """Test only the header generation functionality."""
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)
    
    logger.info("Starting header-only test...")
    
    # Create test data
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
        
        logger.info("Testing header generation...")
        
        # Create a PDF with only header
        with ResourceManager() as rm:
            buffer = BytesIO()
            test_canvas = canvas.Canvas(buffer, pagesize=A4)
            
            generator._canvas = test_canvas
            generator._resource_manager = rm
            
            # Generate header
            final_y = generator._create_header()
            
            logger.info(f"Header generated successfully, final Y position: {final_y}")
            
            # Add some text to verify positioning
            test_canvas.setFont("Helvetica", 12)
            test_canvas.drawString(40, final_y - 20, "Content would start here...")
            
            # Save the PDF
            test_canvas.save()
            
            # Get PDF data
            pdf_data = buffer.getvalue()
            
            # Save test PDF
            with open('test_header_only.pdf', 'wb') as f:
                f.write(pdf_data)
            
            logger.info(f"Header-only PDF saved! Size: {len(pdf_data)} bytes")
            
            # Basic validation
            assert len(pdf_data) > 1000, "PDF seems too small"
            assert pdf_data.startswith(b'%PDF'), "Invalid PDF header"
            
            logger.info("Header-only test validation passed!")
        
        # Test all header sub-methods individually
        logger.info("Testing individual header methods...")
        
        with ResourceManager() as rm:
            buffer2 = BytesIO()
            test_canvas2 = canvas.Canvas(buffer2, pagesize=A4)
            
            generator._canvas = test_canvas2
            generator._resource_manager = rm
            
            current_y = generator.config.page_height - generator.config.margin
            
            # Test logo loading
            logo_width, logo_x = generator._load_and_add_logo(current_y, 60, 120)
            logger.info(f"✓ Logo loading: width={logo_width}, x={logo_x}")
            
            # Test header content
            text_x = generator.config.margin + logo_width + 20 if logo_width > 0 else generator.config.margin
            available_width = generator.config.content_width - (logo_width + 20 if logo_width > 0 else 0)
            
            content_y = generator._add_header_content(text_x, current_y, available_width)
            logger.info(f"✓ Header content: final Y={content_y}")
            
            # Test separator
            generator._add_header_separator(content_y - 15)
            logger.info("✓ Header separator added")
            
            # Test fallback logo
            generator._create_logo_fallback(300, 400)
            logger.info("✓ Logo fallback created")
            
            test_canvas2.save()
        
        logger.info("All individual header methods tested successfully!")
        
        return True
        
    except Exception as e:
        logger.error(f"Header-only test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_header_only()
    if success:
        print("\n✅ Header-only test passed!")
        print("Check 'test_header_only.pdf' to see the result")
        sys.exit(0)
    else:
        print("\n❌ Header-only test failed!")
        sys.exit(1)