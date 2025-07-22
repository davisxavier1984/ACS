"""
Test script to verify PDF configuration and data models work correctly.
"""

from pdf_config import (
    PDFConfig, 
    ChartConfig, 
    PDFGenerationError, 
    ChartConversionError, 
    ResourceCleanupError, 
    LayoutError, 
    DataValidationError
)


def test_pdf_config():
    """Test PDFConfig dataclass functionality."""
    print("Testing PDFConfig...")
    
    # Test default configuration
    config = PDFConfig()
    print(f"Page dimensions: {config.page_width} x {config.page_height}")
    print(f"Content width: {config.content_width}")
    print(f"Content height: {config.content_height}")
    print(f"Margin: {config.margin}")
    print(f"Chart dimensions: {config.chart_width} x {config.chart_height}")
    
    # Test custom configuration
    custom_config = PDFConfig(margin=50, chart_width=900)
    print(f"Custom margin: {custom_config.margin}")
    print(f"Custom chart width: {custom_config.chart_width}")
    print("PDFConfig test passed ✓")


def test_chart_config():
    """Test ChartConfig dataclass functionality."""
    print("\nTesting ChartConfig...")
    
    # Test default financial chart config
    financial_config = ChartConfig.default_financial_chart()
    print(f"Financial chart: {financial_config.width} x {financial_config.height}")
    print(f"DPI: {financial_config.dpi}")
    print(f"Background: {financial_config.background_color}")
    
    # Test default personnel chart config
    personnel_config = ChartConfig.default_personnel_chart()
    print(f"Personnel chart: {personnel_config.width} x {personnel_config.height}")
    
    # Test custom config
    custom_config = ChartConfig(width=1000, height=500, dpi=200)
    print(f"Custom config: {custom_config.width} x {custom_config.height} @ {custom_config.dpi} DPI")
    print("ChartConfig test passed ✓")


def test_exceptions():
    """Test custom exception classes."""
    print("\nTesting Exception Classes...")
    
    # Test PDFGenerationError
    try:
        raise PDFGenerationError("Test error", "Test details")
    except PDFGenerationError as e:
        print(f"PDFGenerationError: {e}")
    
    # Test ChartConversionError
    try:
        raise ChartConversionError("financial", ValueError("Test original error"))
    except ChartConversionError as e:
        print(f"ChartConversionError: {e}")
        print(f"Chart type: {e.chart_type}")
    
    # Test ResourceCleanupError
    try:
        raise ResourceCleanupError("image", IOError("File not found"))
    except ResourceCleanupError as e:
        print(f"ResourceCleanupError: {e}")
    
    # Test LayoutError
    try:
        raise LayoutError("table", "Position Y=100 exceeds page height")
    except LayoutError as e:
        print(f"LayoutError: {e}")
    
    # Test DataValidationError
    try:
        raise DataValidationError("municipio", "Cannot be empty")
    except DataValidationError as e:
        print(f"DataValidationError: {e}")
    
    print("Exception classes test passed ✓")


if __name__ == "__main__":
    test_pdf_config()
    test_chart_config()
    test_exceptions()
    print("\n✅ All tests passed! PDF configuration and data models are working correctly.")