"""
UI Components for Jarvis 2.0
Modular components extracted from jarvis_ui.py for better maintainability.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List

from PyQt6.QtCore import QSize


class UIState(Enum):
    """UI state enumeration for different modes"""
    STARTUP = "startup"
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    RESPONDING = "responding"
    LEARNING = "learning"
    VOICE_REGISTRATION = "voice_registration"
    VOICE_AUTHENTICATION = "voice_authentication"
    ERROR = "error"


class ConversationMode(Enum):
    """Conversation mode enumeration"""
    WAKE_WORD = "wake_word"
    CONTINUOUS = "continuous"
    SESSION_BASED = "session_based"
    HYBRID = "hybrid"


class ScreenSize(Enum):
    """Screen size categories for responsive design"""
    MOBILE = "mobile"      # < 800px
    COMPACT = "compact"    # 800-1200px
    STANDARD = "standard"  # 1200-1600px
    EXTENDED = "extended"  # > 1600px


# Theme color definitions
class ThemeColors:
    """Color palette for the UI"""
    
    # Iron Man HUD Theme (Default)
    IRONMAN = {
        'primary': '#00FFFF',       # Cyan
        'secondary': '#008888',      # Dark cyan
        'accent': '#00E5FF',         # Bright cyan
        'background': 'rgba(0, 10, 20, 80)',
        'text': '#FFFFFF',
        'success': '#00FF00',
        'warning': '#FFAA00',
        'error': '#FF0000',
        'glow': 'rgba(0, 255, 255, 150)',
    }
    
    # Alternative themes for future expansion
    MIDNIGHT = {
        'primary': '#7B68EE',
        'secondary': '#483D8B',
        'accent': '#9370DB',
        'background': 'rgba(20, 10, 30, 80)',
        'text': '#FFFFFF',
        'success': '#32CD32',
        'warning': '#FFD700',
        'error': '#DC143C',
        'glow': 'rgba(123, 104, 238, 150)',
    }
    
    EMBER = {
        'primary': '#FF6B35',
        'secondary': '#9E2A00',
        'accent': '#FF9F1C',
        'background': 'rgba(30, 10, 5, 80)',
        'text': '#FFFFFF',
        'success': '#7CB518',
        'warning': '#FFD700',
        'error': '#FF0000',
        'glow': 'rgba(255, 107, 53, 150)',
    }


@dataclass
class ResponsiveConfig:
    """Configuration for responsive layout"""
    breakpoints: Dict[str, int] = None
    scale_factors: Dict[str, float] = None
    component_visibility: Dict[str, List[str]] = None
    
    def __post_init__(self):
        if self.breakpoints is None:
            self.breakpoints = {
                ScreenSize.MOBILE.value: 800,
                ScreenSize.COMPACT.value: 1200,
                ScreenSize.STANDARD.value: 1600
            }
        
        if self.scale_factors is None:
            self.scale_factors = {
                ScreenSize.MOBILE.value: 0.8,
                ScreenSize.COMPACT.value: 1.0,
                ScreenSize.STANDARD.value: 1.2,
                ScreenSize.EXTENDED.value: 1.4
            }
        
        if self.component_visibility is None:
            self.component_visibility = {
                ScreenSize.MOBILE.value: ["essential", "status"],
                ScreenSize.COMPACT.value: ["essential", "status", "conversation"],
                ScreenSize.STANDARD.value: ["essential", "status", "conversation", "learning"],
                ScreenSize.EXTENDED.value: ["essential", "status", "conversation", "learning", "analytics"]
            }


class ResponsiveLayout:
    """Manages responsive layout adaptation"""
    
    def __init__(self, config: ResponsiveConfig = None):
        self.config = config or ResponsiveConfig()
        self.current_size = ScreenSize.STANDARD
        self.scale_factor = 1.0
        self.screen_size = QSize(1200, 800)
    
    def update_screen_size(self, size: QSize) -> ScreenSize:
        """Update screen size and return current size category"""
        self.screen_size = size
        width = size.width()
        
        if width < self.config.breakpoints[ScreenSize.MOBILE.value]:
            self.current_size = ScreenSize.MOBILE
        elif width < self.config.breakpoints[ScreenSize.COMPACT.value]:
            self.current_size = ScreenSize.COMPACT
        elif width < self.config.breakpoints[ScreenSize.STANDARD.value]:
            self.current_size = ScreenSize.STANDARD
        else:
            self.current_size = ScreenSize.EXTENDED
        
        self.scale_factor = self.config.scale_factors[self.current_size.value]
        return self.current_size
    
    def get_component_visibility(self) -> List[str]:
        """Get visible components for current screen size"""
        return self.config.component_visibility[self.current_size.value]
    
    def calculate_font_size(self, base_size: int) -> int:
        """Calculate responsive font size"""
        return int(base_size * self.scale_factor)
    
    def calculate_spacing(self, base_spacing: int) -> int:
        """Calculate responsive spacing"""
        return int(base_spacing * self.scale_factor)


# Font configuration with fallbacks
TECH_FONT_FAMILY = "'Orbitron', 'Segoe UI', 'Arial', sans-serif"
TECH_FONT_FALLBACK = "Segoe UI"


def get_theme_stylesheet(theme: Dict[str, str] = None) -> str:
    """Generate a complete stylesheet from a theme dictionary"""
    if theme is None:
        theme = ThemeColors.IRONMAN
    
    return f"""
        QWidget {{
            background-color: transparent;
            color: {theme['primary']};
            font-family: {TECH_FONT_FAMILY};
        }}
        
        QFrame {{
            background-color: {theme['background']};
            border: none;
        }}
        
        QLabel {{
            color: {theme['primary']};
            font-weight: normal;
            letter-spacing: 1px;
        }}
        
        QPushButton {{
            background-color: transparent;
            border: 1px solid rgba(0, 255, 255, 50);
            border-radius: 2px;
            color: {theme['primary']};
            font-family: {TECH_FONT_FAMILY};
            font-size: 11px;
            padding: 10px;
            text-transform: uppercase;
        }}
        
        QPushButton:hover {{
            background-color: rgba(0, 255, 255, 20);
            border: 1px solid {theme['primary']};
        }}
        
        QPushButton:pressed {{
            background-color: rgba(0, 255, 255, 50);
            border: 2px solid {theme['primary']};
            color: {theme['text']};
        }}
        
        QPushButton:disabled {{
            color: rgba(0, 255, 255, 80);
            border: 1px solid rgba(0, 255, 255, 20);
        }}
        
        QScrollBar:vertical {{
            border: none;
            background: rgba(0,0,0,0);
            width: 4px;
        }}
        
        QScrollBar::handle:vertical {{
            background: {theme['primary']};
            min-height: 20px;
        }}
        
        QProgressBar {{
            border: 1px solid rgba(0, 255, 255, 50);
            background-color: transparent;
            height: 6px;
        }}
        
        QProgressBar::chunk {{
            background-color: {theme['primary']};
        }}
    """
