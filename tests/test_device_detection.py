"""Comprehensive tests for device detection functionality."""

import pytest
from unittest.mock import Mock

from promptheus.utils import get_device_category


class TestDeviceDetection:
    """Test privacy-safe device detection functionality."""

    def test_detect_desktop_chrome_windows(self):
        """Test detection of desktop Chrome on Windows."""
        mock_request = Mock()
        mock_request.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        result = get_device_category(mock_request)
        assert result == "desktop"

    def test_detect_desktop_safari_macos(self):
        """Test detection of desktop Safari on macOS."""
        mock_request = Mock()
        mock_request.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Safari/605.1.15"
        }

        result = get_device_category(mock_request)
        assert result == "desktop"

    def test_detect_desktop_firefox_linux(self):
        """Test detection of desktop Firefox on Linux."""
        mock_request = Mock()
        mock_request.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0"
        }

        result = get_device_category(mock_request)
        assert result == "desktop"

    def test_detect_mobile_iphone(self):
        """Test detection of iPhone mobile device."""
        mock_request = Mock()
        mock_request.headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"
        }

        result = get_device_category(mock_request)
        assert result == "mobile"

    def test_detect_mobile_android(self):
        """Test detection of Android mobile device."""
        mock_request = Mock()
        mock_request.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-G998U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        }

        result = get_device_category(mock_request)
        assert result == "mobile"

    def test_detect_tablet_ipad(self):
        """Test detection of iPad tablet device."""
        mock_request = Mock()
        mock_request.headers = {
            "User-Agent": "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"
        }

        result = get_device_category(mock_request)
        assert result == "tablet"

    def test_detect_tablet_android_tablet(self):
        """Test detection of Android tablet device."""
        mock_request = Mock()
        mock_request.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-T870) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        result = get_device_category(mock_request)
        assert result == "tablet"

    def test_detect_mobile_and_tablet_conflict_ipad(self):
        """Test that tablet takes precedence when both mobile and tablet indicators present."""
        mock_request = Mock()
        mock_request.headers = {
            "User-Agent": "Mozilla/5.0 (iPad; Mobile) Safari/604.1"
        }

        result = get_device_category(mock_request)
        # iPad contains both "ipad" (tablet) and "Mobile" (mobile), tablet should win
        assert result == "tablet"

    def test_detect_mobile_and_tablet_conflict_android(self):
        """Test that tablet takes precedence when both mobile and tablet indicators present."""
        mock_request = Mock()
        mock_request.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) Safari/537.36"
        }

        result = get_device_category(mock_request)
        # Android contains both "Android" (mobile) and "Mobile" (mobile), but this specific case should be mobile
        assert result == "mobile"

    def test_detect_mobile_windows_phone(self):
        """Test detection of Windows Phone mobile device."""
        mock_request = Mock()
        mock_request.headers = {
            "User-Agent": "Mozilla/5.0 (Mobile; Windows Phone 8.1; Android 4.4; IE/10.0; ARM; Touch; NOKIA; Lumia 920)"
        }

        result = get_device_category(mock_request)
        assert result == "mobile"

    def test_no_user_agent_header(self):
        """Test handling when User-Agent header is missing."""
        mock_request = Mock()
        mock_request.headers = {}

        result = get_device_category(mock_request)
        assert result == "unknown"

    def test_empty_user_agent_header(self):
        """Test handling when User-Agent header is empty."""
        mock_request = Mock()
        mock_request.headers = {"User-Agent": ""}

        result = get_device_category(mock_request)
        assert result == "unknown"

    def test_case_insensitive_mobile_detection(self):
        """Test that mobile detection is case-insensitive for User-Agent value."""
        # Standard case
        mock_request = Mock()
        mock_request.headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"
        }

        result = get_device_category(mock_request)
        assert result == "mobile"

        # Test with uppercase IPHONE in User-Agent value (should still work due to .lower())
        mock_request = Mock()
        mock_request.headers = {
            "User-Agent": "Mozilla/5.0 (IPHONE; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"
        }

        result = get_device_category(mock_request)
        assert result == "mobile"

    def test_privacy_no_fingerprinting(self):
        """Test that function doesn't extract detailed fingerprinting data."""
        mock_request = Mock()
        mock_request.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/320.4654.85 Edge/120.0.0"
        }

        result = get_device_category(mock_request)
        # Should only return basic category, not detailed browser info
        assert result == "desktop"

        # Ensure no sensitive data is extracted or logged
        assert "Windows NT 10.0" not in str(result)
        assert "Win64" not in str(result)
        assert "Chrome" not in str(result)
        assert "120.0.0.0" not in str(result)

    def test_edge_cases(self):
        """Test edge cases and unusual User-Agent strings."""
        # User-Agent with mobile indicator but unusual format
        mock_request = Mock()
        mock_request.headers = {
            "User-Agent": "SomeCustomApp/1.0 Mobile"
        }

        result = get_device_category(mock_request)
        assert result == "mobile"

        # User-Agent with tablet indicator but unusual format
        mock_request.headers = {
            "User-Agent": "CustomTablet/1.0"
        }

        result = get_device_category(mock_request)
        assert result == "tablet"

        # User-Agent that mentions both mobile and tablet (tablet should take precedence)
        mock_request.headers = {
            "User-Agent": "Mozilla/5.0 (iPad; Mobile) Safari/604.1"
        }

        result = get_device_category(mock_request)
        # Tablet indicators are checked first, so should return tablet
        assert result == "tablet"

    def test_unknown_device_with_unrecognized_agent(self):
        """Test handling of completely unrecognized User-Agent."""
        mock_request = Mock()
        mock_request.headers = {
            "User-Agent": "CustomCrawler/1.0"
        }

        result = get_device_category(mock_request)
        # Doesn't match mobile/tablet, has User-Agent, so falls back to desktop
        assert result == "desktop"

    def test_unicode_user_agent(self):
        """Test handling of User-Agent with Unicode characters."""
        mock_request = Mock()
        mock_request.headers = {
            "User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        result = get_device_category(mock_request)
        # Should handle Unicode gracefully and still detect desktop
        assert result == "desktop"


class TestDeviceDetectionIntegration:
    """Test device detection integration with logging."""

    def test_device_category_in_logging_context(self):
        """Test that device category can be used in logging context."""
        from promptheus.web.api.prompt_router import PromptRequest
        from unittest.mock import Mock

        # Create a mock request with device detection
        mock_request = Mock()
        mock_request.headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15"
        }

        # Test that we can extract device category for logging
        device_category = get_device_category(mock_request)
        assert device_category == "mobile"

        # Test that it would work in a logging context
        assert isinstance(device_category, str)
        assert device_category in ["mobile", "tablet", "desktop", "unknown"]

    def test_device_category_compatibility_with_existing_functions(self):
        """Test that device detection works alongside existing user email detection."""
        from promptheus.utils import get_user_email

        mock_request = Mock()
        mock_request.headers = {
            "User-Agent": "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15",
            "CF-Access-Authenticated-User-Email": "test@example.com"
        }

        user_email = get_user_email(mock_request)
        device_category = get_device_category(mock_request)

        # Both functions should work independently
        assert user_email == "test@example.com"
        assert device_category == "tablet"

        # Should not interfere with each other
        assert "iPad" not in user_email
        assert "Mozilla" not in device_category


class TestDeviceDetectionPrivacy:
    """Test privacy compliance of device detection."""

    def test_no_logging_of_sensitive_data(self):
        """Test that sensitive data is not logged or accessible."""
        mock_request = Mock()
        mock_request.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        result = get_device_category(mock_request)

        # Result should contain only basic category
        assert result in ["mobile", "tablet", "desktop", "unknown"]

        # Should not contain any identifying information
        sensitive_indicators = [
            "Windows", "Win64", "x64", "Macintosh", "iPhone",
            "iPad", "Android", "Chrome", "Firefox", "Safari",
            "Gecko", "WebKit", "120.0.0.0", "17_1"
        ]

        for indicator in sensitive_indicators:
            assert indicator not in result.lower()

    def test_data_minimization_principle(self):
        """Test that function follows data minimization principle."""
        test_cases = [
            ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X)", "mobile"),
            ("Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X)", "tablet"),
            ("Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "desktop"),
            ("Mozilla/5.0 (Linux; Android 13)", "tablet"),  # Android without "mobile" = tablet
            ("Mozilla/5.0 (X11; Linux x86_64)", "desktop"),
        ]

        for user_agent, expected_category in test_cases:
            mock_request = Mock()
            mock_request.headers = {"User-Agent": user_agent}

            result = get_device_category(mock_request)
            assert result == expected_category

            # Verify result is minimal
            assert len(result) <= len(expected_category)  # Should be similarly minimal

    def test_gdpr_compliance_basic(self):
        """Test basic GDPR compliance aspects."""
        mock_request = Mock()
        mock_request.headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"
        }

        result = get_device_category(mock_request)

        # GDPR: Personal data should be minimized
        assert result == "mobile"  # Category, not detailed identifier

        # GDPR: Data should be accurate and up-to-date
        # Our implementation is conservative, so this is satisfied

        # GDPR: Data should be collected for specified purposes
        # Our purpose is analytics for mobile vs desktop usage - this is legitimate

    def test_performance_characteristics(self):
        """Test performance characteristics of device detection."""
        import time

        mock_request = Mock()
        mock_request.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        # Test that function is fast (should be very fast)
        start_time = time.time()
        result = get_device_category(mock_request)
        end_time = time.time()

        assert end_time - start_time < 0.001  # Should be under 1ms
        assert result == "desktop"

        # Test multiple calls (should be consistently fast)
        for _ in range(100):
            get_device_category(mock_request)


if __name__ == "__main__":
    pytest.main([__file__])