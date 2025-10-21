"""
AIOrg - Main Application Entry Point

A desktop application for interacting with multiple AI models
and organizing notes in markdown format.
"""

import logging
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMainWindow, QSplitter
from PyQt6.QtCore import Qt

from ai_viewer.config import load_config, get_default_config
from ai_viewer.viewer import AIViewerWidget
from organizer.organizer import OrganizerWidget
from organizer.database import NoteDatabase


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure logging system for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture everything at root level

    # File handler - always DEBUG, full format
    file_handler = logging.FileHandler(log_dir / "aiorg.log")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Console handler - configurable level, simpler format
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(getattr(logging, log_level))
    console_formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    logging.info("Logging system initialized")


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, config: dict):
        """
        Initialize main window.

        Args:
            config: Application configuration dictionary
        """
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Component references
        self.database = None
        self.ai_viewer = None
        self.organizer = None
        self.splitter = None

        self.logger.info("Initializing main window")

        # Create components
        self.create_components()

        # Setup UI
        self.setup_ui()

        self.logger.info("Main window initialized successfully")

    def create_components(self):
        """Initialize database, AI viewer, and organizer components."""
        self.logger.info("Creating application components")

        try:
            # Get database path from config
            db_path = self.config["settings"]["database_path"]
            self.logger.debug(f"Initializing database at: {db_path}")

            # Create database instance
            self.database = NoteDatabase(db_path)
            self.logger.info("Database initialized successfully")

            # Create AI viewer widget
            self.logger.debug("Creating AI viewer widget")
            self.ai_viewer = AIViewerWidget(config=self.config, parent=self)
            self.logger.info("AI viewer widget created")

            # Create organizer widget
            self.logger.debug("Creating organizer widget")
            self.organizer = OrganizerWidget(database=self.database, parent=self)
            self.logger.info("Organizer widget created")

            self.logger.info("All components created successfully")

        except Exception as e:
            self.logger.critical(f"Failed to create components: {e}", exc_info=True)
            raise

    def setup_ui(self) -> None:
        """Create main window layout with QSplitter."""
        self.logger.debug("Setting up main window UI")

        # Get window settings from config
        settings = self.config["settings"]
        self.setWindowTitle("AIOrg")
        self.resize(settings["window_width"], settings["window_height"])

        self.logger.debug(
            f"Window size set to: {settings['window_width']}x{settings['window_height']}"
        )

        # Create horizontal splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Add AI viewer to left pane
        self.splitter.addWidget(self.ai_viewer)

        # Add organizer to right pane
        self.splitter.addWidget(self.organizer)

        # Set minimum widths
        self.ai_viewer.setMinimumWidth(400)
        self.organizer.setMinimumWidth(300)

        self.logger.debug("Set minimum widths: AI viewer=400px, Organizer=300px")

        # Apply split ratio from config
        split_ratio = settings.get("split_ratio", 0.5)
        total_width = settings["window_width"]
        left_width = int(total_width * split_ratio)
        right_width = total_width - left_width

        self.splitter.setSizes([left_width, right_width])

        self.logger.debug(
            f"Applied split ratio {split_ratio}: left={left_width}px, right={right_width}px"
        )

        # Set splitter as central widget
        self.setCentralWidget(self.splitter)

        # Make splitter handle more visible
        self.splitter.setHandleWidth(5)

        self.logger.info("Main window UI setup complete")

    def closeEvent(self, event):
        """Handle application shutdown."""
        self.logger.info("Application shutdown initiated")

        try:
            # Close database connection
            if self.database:
                self.logger.debug("Closing database connection")
                self.database.close()
                self.logger.info("Database connection closed successfully")

            self.logger.info("Application closed successfully")
            event.accept()

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}", exc_info=True)
            # Accept event anyway to allow application to close
            event.accept()


def main():
    """Application entry point."""
    # Initialize logging with default level (will be updated after config loads)
    setup_logging()

    logger = logging.getLogger(__name__)
    logger.info("Starting AIOrg application")

    # Load configuration
    try:
        config = load_config("config.toml")
        logger.info("Configuration loaded successfully")

        # Update logging level based on config
        log_level = config["settings"].get("log_level", "INFO")
        for handler in logging.getLogger().handlers:
            if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stderr:
                handler.setLevel(getattr(logging, log_level))
                logger.debug(f"Console log level set to {log_level}")

    except FileNotFoundError:
        logger.warning("config.toml not found, using default configuration")
        config = get_default_config()
    except ValueError as e:
        logger.error(f"Invalid configuration: {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Failed to load configuration: {e}", exc_info=True)
        sys.exit(1)

    # Create Qt application
    app = QApplication(sys.argv)

    # Create and show main window
    window = MainWindow(config)
    window.show()

    logger.info("Application started successfully")
    logger.debug(f"Loaded {len(config.get('ai_models', []))} AI models")

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
