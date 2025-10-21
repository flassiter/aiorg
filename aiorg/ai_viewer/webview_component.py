"""Webview component for commercial AI models.

This module provides a QWebEngineView-based component for displaying
commercial AI services (Claude, ChatGPT, etc.) in an embedded browser.
"""

import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PyQt6.QtCore import QUrl

logger = logging.getLogger(__name__)


class WebviewComponent(QWidget):
    """Webview component for commercial AI models.

    Provides an embedded browser for accessing commercial AI services
    with persistent cookies and standard desktop user agent.
    """

    def __init__(self, parent=None):
        """Initialize webview with persistent profile.

        Args:
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        logger.info("Initializing WebviewComponent")

        # Create layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Create webview with default persistent profile
        # Default profile automatically persists cookies
        self.webview = QWebEngineView(self)
        self.profile = self.webview.page().profile()

        # Set standard desktop user agent
        user_agent = (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.profile.setHttpUserAgent(user_agent)
        logger.debug(f"Set user agent: {user_agent}")

        # Add webview to layout
        self.layout.addWidget(self.webview)

        logger.info("WebviewComponent initialized successfully")

    def load_url(self, url: str):
        """Load AI model URL in webview.

        Args:
            url: URL to load (e.g., "https://claude.ai/chat")
        """
        logger.info(f"Loading URL: {url}")

        # Convert string to QUrl and load
        qurl = QUrl(url)
        if not qurl.isValid():
            logger.error(f"Invalid URL: {url}")
            return

        self.webview.setUrl(qurl)
        logger.debug(f"URL load initiated: {url}")

    def clear_cache(self):
        """Clear webview cache and cookies.

        Note: This is optional for Phase 1. Clears the browser cache
        and removes stored cookies. Use with caution as this will
        log users out of AI services.
        """
        logger.info("Clearing webview cache and cookies")

        # Clear cache
        self.profile.clearHttpCache()
        logger.debug("HTTP cache cleared")

        # Clear all cookies
        cookie_store = self.profile.cookieStore()
        cookie_store.deleteAllCookies()
        logger.debug("All cookies deleted")

        logger.info("Webview cache and cookies cleared successfully")


# Standalone test mode
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    # Setup logging for test mode
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("Starting WebviewComponent standalone test")

    # Create application
    app = QApplication(sys.argv)

    # Create webview component
    webview = WebviewComponent()
    webview.setWindowTitle("WebviewComponent Test")
    webview.resize(1200, 800)

    # Load test URL (Claude by default)
    test_url = "https://claude.ai/chat"
    logger.info(f"Loading test URL: {test_url}")
    webview.load_url(test_url)

    # Show window
    webview.show()

    logger.info("WebviewComponent test window displayed")

    # Run application
    sys.exit(app.exec())
