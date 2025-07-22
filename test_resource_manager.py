"""
Unit tests for ResourceManager class.

Tests resource registration, cleanup, context manager functionality,
and error handling scenarios.
"""

import pytest
import logging
import io
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from PIL import Image as PILImage
from pdf_config import ResourceManager, ResourceCleanupError


class TestResourceManager:
    """Test suite for ResourceManager class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.logger = logging.getLogger('test_resource_manager')
        self.logger.setLevel(logging.DEBUG)
        
        # Create a string handler to capture log messages
        self.log_stream = io.StringIO()
        handler = logging.StreamHandler(self.log_stream)
        handler.setLevel(logging.DEBUG)
        self.logger.addHandler(handler)
        
        self.resource_manager = ResourceManager(logger=self.logger)
    
    def teardown_method(self):
        """Clean up after each test method."""
        # Clear log handlers
        self.logger.handlers.clear()
    
    def test_context_manager_basic(self):
        """Test basic context manager functionality."""
        with ResourceManager() as rm:
            assert rm._is_active is True
            assert rm.get_resource_count() == 0
        
        assert rm._is_active is False
    
    def test_register_bytesio_resource(self):
        """Test registering and cleaning up BytesIO resources."""
        with ResourceManager(logger=self.logger) as rm:
            # Create a BytesIO resource
            buffer = io.BytesIO(b"test data")
            registered_buffer = rm.register_resource(buffer)
            
            # Should return the same object
            assert registered_buffer is buffer
            assert rm.get_resource_count() == 1
            
            # Check resource summary
            summary = rm.get_resource_summary()
            assert 'BytesIO' in summary
            assert summary['BytesIO'] == 1
        
        # Verify cleanup was logged
        log_output = self.log_stream.getvalue()
        assert "Registered resource: BytesIO" in log_output
        assert "Cleaned up BytesIO using close" in log_output
    
    def test_register_pil_image_resource(self):
        """Test registering and cleaning up PIL Image resources."""
        with ResourceManager(logger=self.logger) as rm:
            # Create a simple PIL Image
            image = PILImage.new('RGB', (100, 100), color='red')
            registered_image = rm.register_resource(image)
            
            assert registered_image is image
            assert rm.get_resource_count() == 1
            
            summary = rm.get_resource_summary()
            assert 'Image' in summary
            assert summary['Image'] == 1
        
        log_output = self.log_stream.getvalue()
        assert "Registered resource: Image" in log_output
        assert "Cleaned up Image using close" in log_output
    
    def test_register_file_handle_resource(self):
        """Test registering and cleaning up file handle resources."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("test content")
            temp_file_path = temp_file.name
        
        try:
            with ResourceManager(logger=self.logger) as rm:
                # Open file and register it
                file_handle = open(temp_file_path, 'r')
                rm.register_resource(file_handle)
                
                assert rm.get_resource_count() == 1
                assert not file_handle.closed
            
            # File should be closed after context exit
            assert file_handle.closed
            
            log_output = self.log_stream.getvalue()
            assert "Registered resource: TextIOWrapper" in log_output
            assert "Cleaned up TextIOWrapper using close" in log_output
        
        finally:
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    def test_register_custom_cleanup_method(self):
        """Test registering resource with custom cleanup method."""
        mock_resource = Mock()
        mock_resource.custom_cleanup = Mock()
        
        with ResourceManager(logger=self.logger) as rm:
            rm.register_resource(
                mock_resource, 
                cleanup_method='custom_cleanup',
                resource_type='MockResource'
            )
            
            assert rm.get_resource_count() == 1
        
        # Verify custom cleanup method was called
        mock_resource.custom_cleanup.assert_called_once()
        
        log_output = self.log_stream.getvalue()
        assert "Registered resource: MockResource with cleanup method: custom_cleanup" in log_output
        assert "Cleaned up MockResource using custom_cleanup" in log_output
    
    def test_register_cleanup_function(self):
        """Test registering and executing custom cleanup functions."""
        cleanup_mock = Mock()
        
        with ResourceManager(logger=self.logger) as rm:
            rm.register_cleanup_function(cleanup_mock, "test cleanup function")
        
        # Verify cleanup function was called
        cleanup_mock.assert_called_once()
        
        log_output = self.log_stream.getvalue()
        assert "Registered cleanup function: test cleanup function" in log_output
        assert "Executed cleanup function: test cleanup function" in log_output
    
    def test_multiple_resources_cleanup_order(self):
        """Test that resources are cleaned up in reverse order."""
        cleanup_order = []
        
        class TestResource:
            def __init__(self, name):
                self.name = name
            
            def close(self):
                cleanup_order.append(self.name)
        
        with ResourceManager() as rm:
            resource1 = TestResource("first")
            resource2 = TestResource("second")
            resource3 = TestResource("third")
            
            rm.register_resource(resource1)
            rm.register_resource(resource2)
            rm.register_resource(resource3)
        
        # Should be cleaned up in reverse order
        assert cleanup_order == ["third", "second", "first"]
    
    def test_cleanup_error_handling(self):
        """Test error handling during resource cleanup."""
        class FailingResource:
            def close(self):
                raise Exception("Cleanup failed!")
        
        failing_resource = FailingResource()
        
        with pytest.raises(ResourceCleanupError):
            with ResourceManager(logger=self.logger) as rm:
                rm.register_resource(failing_resource)
        
        log_output = self.log_stream.getvalue()
        assert "Failed to cleanup FailingResource: Cleanup failed!" in log_output
    
    def test_cleanup_function_error_handling(self):
        """Test error handling for failing cleanup functions."""
        def failing_cleanup():
            raise Exception("Custom cleanup failed!")
        
        with pytest.raises(ResourceCleanupError):
            with ResourceManager(logger=self.logger) as rm:
                rm.register_cleanup_function(failing_cleanup, "failing cleanup")
        
        log_output = self.log_stream.getvalue()
        assert "Failed to execute cleanup function failing cleanup" in log_output
    
    def test_manual_cleanup(self):
        """Test manual cleanup without context manager."""
        rm = ResourceManager(logger=self.logger)
        
        buffer = io.BytesIO(b"test")
        rm.register_resource(buffer)
        
        assert rm.get_resource_count() == 1
        assert not buffer.closed
        
        # Manual cleanup
        rm.cleanup_all()
        
        assert rm.get_resource_count() == 0
        assert buffer.closed
    
    def test_resource_registration_outside_context(self):
        """Test warning when registering resources outside active context."""
        rm = ResourceManager(logger=self.logger)
        
        buffer = io.BytesIO(b"test")
        rm.register_resource(buffer)
        
        log_output = self.log_stream.getvalue()
        assert "ResourceManager not active" in log_output
    
    def test_weak_reference_handling(self):
        """Test handling of resources with weak references."""
        with ResourceManager(logger=self.logger) as rm:
            # Create an object that supports weak references
            buffer = io.BytesIO(b"test")
            rm.register_resource(buffer)
            
            # Delete the reference
            del buffer
            
            # The cleanup should handle the case where weak ref is None
            # This is tested implicitly in the context manager exit
        
        log_output = self.log_stream.getvalue()
        # Should not cause errors
        assert "error" not in log_output.lower()
    
    def test_resource_without_cleanup_method(self):
        """Test handling of resources without appropriate cleanup methods."""
        class NoCleanupResource:
            pass
        
        resource = NoCleanupResource()
        
        with ResourceManager(logger=self.logger) as rm:
            rm.register_resource(resource)
        
        log_output = self.log_stream.getvalue()
        assert "Deleted NoCleanupResource" in log_output
    
    def test_exception_during_context(self):
        """Test resource cleanup when exception occurs in context."""
        buffer = io.BytesIO(b"test")
        
        try:
            with ResourceManager(logger=self.logger) as rm:
                rm.register_resource(buffer)
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Resource should still be cleaned up
        assert buffer.closed
        
        log_output = self.log_stream.getvalue()
        assert "Exiting ResourceManager due to exception: ValueError" in log_output
    
    def test_get_resource_summary_multiple_types(self):
        """Test resource summary with multiple resource types."""
        with ResourceManager() as rm:
            # Register multiple resources of different types
            rm.register_resource(io.BytesIO(b"test1"))
            rm.register_resource(io.BytesIO(b"test2"))
            rm.register_resource(PILImage.new('RGB', (10, 10)))
            
            summary = rm.get_resource_summary()
            
            assert summary['BytesIO'] == 2
            assert summary['Image'] == 1
            assert len(summary) == 2


class TestResourceManagerIntegration:
    """Integration tests for ResourceManager with real resources."""
    
    def test_real_image_file_cleanup(self):
        """Test cleanup of real image file resources."""
        # Create a temporary image file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Create a simple image and save it
            image = PILImage.new('RGB', (100, 100), color='blue')
            image.save(temp_path)
            
            with ResourceManager() as rm:
                # Load and register the image
                loaded_image = PILImage.open(temp_path)
                rm.register_resource(loaded_image)
                
                # Verify image is loaded
                assert loaded_image.size == (100, 100)
                # PIL Images don't have a 'closed' attribute, but we can check if it's still accessible
                assert loaded_image.format == 'PNG'
            
            # After cleanup, the image should still be accessible but resources should be freed
            # PIL Images don't have a direct way to check if they're "closed" like file objects
            # The cleanup mainly ensures proper resource management
            assert loaded_image.size == (100, 100)  # Image data should still be accessible
        
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_multiple_buffers_memory_cleanup(self):
        """Test cleanup of multiple BytesIO buffers."""
        buffers = []
        
        with ResourceManager() as rm:
            # Create multiple buffers with data
            for i in range(10):
                buffer = io.BytesIO(f"test data {i}".encode())
                buffers.append(buffer)
                rm.register_resource(buffer)
            
            assert rm.get_resource_count() == 10
            
            # All buffers should be open
            for buffer in buffers:
                assert not buffer.closed
        
        # All buffers should be closed after cleanup
        for buffer in buffers:
            assert buffer.closed


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v'])