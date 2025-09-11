"""
Color utilities for terminal output.
"""

class Colors:
    """ANSI color codes for terminal output."""
    
    # Regular colors
    BLACK = '\033[0;30m'
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    BLUE = '\033[0;34m'
    MAGENTA = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[0;37m'
    
    # Bold colors
    BOLD_BLACK = '\033[1;30m'
    BOLD_RED = '\033[1;31m'
    BOLD_GREEN = '\033[1;32m'
    BOLD_YELLOW = '\033[1;33m'
    BOLD_BLUE = '\033[1;34m'
    BOLD_MAGENTA = '\033[1;35m'
    BOLD_CYAN = '\033[1;36m'
    BOLD_WHITE = '\033[1;37m'
    
    # Reset
    RESET = '\033[0m'
    
    @staticmethod
    def colorize(text: str, color: str) -> str:
        """Apply color to text."""
        return f"{color}{text}{Colors.RESET}"
    
    @staticmethod
    def success(text: str) -> str:
        """Format text as success message."""
        return Colors.colorize(text, Colors.GREEN)
    
    @staticmethod
    def error(text: str) -> str:
        """Format text as error message."""
        return Colors.colorize(text, Colors.RED)
    
    @staticmethod
    def warning(text: str) -> str:
        """Format text as warning message."""
        return Colors.colorize(text, Colors.YELLOW)
    
    @staticmethod
    def info(text: str) -> str:
        """Format text as info message."""
        return Colors.colorize(text, Colors.BLUE)
    
    @staticmethod
    def bold(text: str) -> str:
        """Format text as bold."""
        return Colors.colorize(text, Colors.BOLD_WHITE)
