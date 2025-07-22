"""
Demonstration script for ResourceManager usage.

Shows practical examples of how to use ResourceManager for proper
resource cleanup in PDF generation scenarios.
"""

import io
import logging
from PIL import Image as PILImage
from pdf_config import ResourceManager

# Set up logging to see ResourceManager operations
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def demo_basic_usage():
    """Demonstrate basic ResourceManager usage."""
    print("=== Basic ResourceManager Usage ===")
    
    with ResourceManager(logger=logger) as rm:
        # Create and register various resources
        buffer1 = io.BytesIO(b"Sample PDF data")
        buffer2 = io.BytesIO(b"Chart image data")
        image = PILImage.new('RGB', (200, 100), color='red')
        
        # Register resources for automatic cleanup
        rm.register_resource(buffer1, resource_type="PDF Buffer")
        rm.register_resource(buffer2, resource_type="Chart Buffer")
        rm.register_resource(image, resource_type="Chart Image")
        
        print(f"Registered {rm.get_resource_count()} resources")
        print(f"Resource summary: {rm.get_resource_summary()}")
        
        # Simulate some work with the resources
        buffer1.write(b"Additional PDF content")
        print(f"Buffer1 size: {len(buffer1.getvalue())} bytes")
        print(f"Image size: {image.size}")
    
    print("Resources automatically cleaned up on context exit\n")


def demo_custom_cleanup():
    """Demonstrate custom cleanup functions."""
    print("=== Custom Cleanup Functions ===")
    
    cleanup_log = []
    
    def custom_cleanup_1():
        cleanup_log.append("Custom cleanup 1 executed")
        print("Performing custom cleanup task 1")
    
    def custom_cleanup_2():
        cleanup_log.append("Custom cleanup 2 executed")
        print("Performing custom cleanup task 2")
    
    with ResourceManager(logger=logger) as rm:
        # Register custom cleanup functions
        rm.register_cleanup_function(custom_cleanup_1, "Task 1 cleanup")
        rm.register_cleanup_function(custom_cleanup_2, "Task 2 cleanup")
        
        # Also register some regular resources
        buffer = io.BytesIO(b"test data")
        rm.register_resource(buffer)
        
        print("Registered custom cleanup functions and resources")
    
    print(f"Cleanup log: {cleanup_log}")
    print("Custom cleanup functions executed before resource cleanup\n")


def demo_error_handling():
    """Demonstrate error handling during cleanup."""
    print("=== Error Handling Demo ===")
    
    class ProblematicResource:
        def close(self):
            raise Exception("Simulated cleanup error!")
    
    try:
        with ResourceManager(logger=logger) as rm:
            # Register a resource that will fail during cleanup
            problematic = ProblematicResource()
            rm.register_resource(problematic, resource_type="Problematic Resource")
            
            # Also register a good resource
            good_buffer = io.BytesIO(b"good data")
            rm.register_resource(good_buffer, resource_type="Good Buffer")
            
            print("Registered resources including one that will fail cleanup")
    
    except Exception as e:
        print(f"Caught cleanup error: {type(e).__name__}: {e}")
    
    print("Error handling completed - good resources still cleaned up\n")


def demo_manual_cleanup():
    """Demonstrate manual cleanup without context manager."""
    print("=== Manual Cleanup Demo ===")
    
    rm = ResourceManager(logger=logger)
    
    # Create and register resources
    buffer1 = io.BytesIO(b"manual cleanup test 1")
    buffer2 = io.BytesIO(b"manual cleanup test 2")
    
    rm.register_resource(buffer1)
    rm.register_resource(buffer2)
    
    print(f"Registered {rm.get_resource_count()} resources manually")
    print(f"Buffer1 closed: {buffer1.closed}")
    print(f"Buffer2 closed: {buffer2.closed}")
    
    # Manual cleanup
    rm.cleanup_all()
    
    print(f"After manual cleanup:")
    print(f"Buffer1 closed: {buffer1.closed}")
    print(f"Buffer2 closed: {buffer2.closed}")
    print(f"Remaining resources: {rm.get_resource_count()}\n")


def demo_pdf_generation_scenario():
    """Demonstrate ResourceManager in a PDF generation scenario."""
    print("=== PDF Generation Scenario ===")
    
    def simulate_pdf_generation():
        """Simulate a PDF generation process with proper resource management."""
        with ResourceManager(logger=logger) as rm:
            # Simulate creating chart images
            chart1 = PILImage.new('RGB', (400, 300), color='blue')
            chart2 = PILImage.new('RGB', (400, 300), color='green')
            
            # Register chart images
            rm.register_resource(chart1, resource_type="Financial Chart")
            rm.register_resource(chart2, resource_type="Personnel Chart")
            
            # Simulate creating PDF buffer
            pdf_buffer = io.BytesIO()
            rm.register_resource(pdf_buffer, resource_type="PDF Output Buffer")
            
            # Simulate chart conversion to bytes
            chart1_bytes = io.BytesIO()
            chart2_bytes = io.BytesIO()
            
            # Save charts to bytes (simulate conversion)
            chart1.save(chart1_bytes, format='PNG')
            chart2.save(chart2_bytes, format='PNG')
            
            # Register the byte buffers
            rm.register_resource(chart1_bytes, resource_type="Chart1 Bytes")
            rm.register_resource(chart2_bytes, resource_type="Chart2 Bytes")
            
            # Simulate PDF content creation
            pdf_content = b"PDF Header\n"
            pdf_content += b"Chart 1 data: " + chart1_bytes.getvalue()[:50] + b"...\n"
            pdf_content += b"Chart 2 data: " + chart2_bytes.getvalue()[:50] + b"...\n"
            pdf_content += b"PDF Footer\n"
            
            pdf_buffer.write(pdf_content)
            
            print(f"Generated PDF with {len(pdf_content)} bytes")
            print(f"Used {rm.get_resource_count()} resources")
            print(f"Resource breakdown: {rm.get_resource_summary()}")
            
            return pdf_buffer.getvalue()
    
    # Generate PDF with automatic resource cleanup
    pdf_data = simulate_pdf_generation()
    print(f"Final PDF size: {len(pdf_data)} bytes")
    print("All resources automatically cleaned up\n")


if __name__ == "__main__":
    print("ResourceManager Demonstration\n")
    
    demo_basic_usage()
    demo_custom_cleanup()
    demo_error_handling()
    demo_manual_cleanup()
    demo_pdf_generation_scenario()
    
    print("=== Demo Complete ===")
    print("ResourceManager provides:")
    print("- Automatic resource cleanup with context managers")
    print("- Support for custom cleanup functions")
    print("- Robust error handling during cleanup")
    print("- Manual cleanup when needed")
    print("- Comprehensive logging for debugging")