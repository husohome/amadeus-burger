"""
Amadeus Burger - An experimental AGI prototype
"""

# Re-export Settings for clean imports
from .constants.settings import Settings
from .constants.literals import *

__all__ = [
    "Settings",
    "DBClientTypes",
    "CompressorTypes",
]

__version__ = "0.1.0"
