#!/usr/bin/env python3
"""
Test script for header generation functionality.

This script tests the improved header generation with logo handling,
fallback support, and consistent styling.
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

def test_header_generation():
    """Test the header generation functionality."""
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)
    
    logger.info("Starting header generation test...")
    
    # Create test data
    df_test = pd.DataFrame({
        'competencia': ['2024-01', '2024-02', '2024-03'],
        'qtTotalCredenciado': [100, 105, 110],
        'qtTotalPago': [95, 100, 105],
        'vlEsperado': [50000.0, 52500.0, 55000.0],
        'vlTotalAcs': [47500.0, 50000.0, 52250.0]
    })
    
    dados_atual = pd.Series({
        'qtTotalCredenciado': 110,
        'qtTotalPago': 105,
        'vlEsperado': 55000.0,
        'vlTotalAcs': 52250.0
    })
    
    competencias = ['2024-01', '2024-02', '2024-03']
    
    try:
        # Test with logo present
        logger.info("Testing header generation with logo...")
        
        generator = PDFGenerator(
            municipio='São Paulo',
            uf='SP',
            df_3_meses=df_test,
            dados_atual=dados_atual,
            competencias=competencias
        )
        
        # Test individual header methods
        logger.info("Testing logo loading method...")
        
        # Create a mock canvas and resource manager for testing
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        
        with ResourceManager() as rm:
            buffer = BytesIO()
            test_canvas = canvas.Canvas(buffer, pagesize=A4)
            
            generator._canvas = test_canvas
            generator._resource_manager = rm
            
            # Test logo loading
            current_y = generator.config.page_height - generator.config.margin
            logo_width, logo_x = generator._load_and_add_logo(current_y, 60, 120)
            
            logger.info(f"Logo loading result: width={logo_width}, x={logo_x}")
            
            # Test header content
            text_x = generator.config.margin + logo_width + 20 if logo_width > 0 else generator.config.margin
            available_width = generator.config.content_width - (logo_width + 20 if logo_width > 0 else 0)
            
            final_y = generator._add_header_content(text_x, current_y, available_width)
            logger.info(f"Header content added, final Y: {final_y}")
            
            # Test separator
            generator._add_header_separator(final_y - 15)
            logger.info("Header separator added successfully")
            
            test_canvas.save()
        
        logger.info("Header generation test completed successfully!")
        
        # Test fallback scenario (temporarily rename logo)
        logger.info("Testing fallback scenario...")
        
        logo_exists = os.path.exists('logo.png')
        if logo_exists:
            os.rename('logo.png', 'logo.png.backup')
        
        try:
            with ResourceManager() as rm:
                buffer2 = BytesIO()
                test_canvas2 = canvas.Canvas(buffer2, pagesize=A4)
                
                generator._canvas = test_canvas2
                generator._resource_manager = rm
                
                # Test logo loading without logo file
                logo_width2, logo_x2 = generator._load_and_add_logo(current_y, 60, 120)
                logger.info(f"Fallback logo result: width={logo_width2}, x={logo_x2}")
                
                test_canvas2.save()
                
        finally:
            # Restore logo if it existed
            if logo_exists:
                os.rename('logo.png.backup', 'logo.png')
        
        logger.info("Fallback test completed successfully!")
        
        return True
        
    except Exception as e:
        logger.error(f"Header generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_header_generation()
    if success:
        print("\n✅ All header generation tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Header generation tests failed!")
        sys.exit(1)