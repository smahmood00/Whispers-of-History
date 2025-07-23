import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseComponent:
    """Base class for all pipeline components"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize base component
        
        Args:
            output_dir: Optional custom output directory
        """
        from .config import OUTPUT_DIR
        self.output_dir = output_dir or OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def get_timestamp(self) -> str:
        """Get current timestamp string"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def save_output(self, content: str, filename: str) -> Path:
        """Save content to output file
        
        Args:
            content: Content to save
            filename: Name of the file
            
        Returns:
            Path to saved file
        """
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Saved output to: {filepath}")
        return filepath
    
    def save_json(self, data: Dict[str, Any], filename: str) -> Path:
        """Save JSON data to output file
        
        Args:
            data: Data to save as JSON
            filename: Name of the file
            
        Returns:
            Path to saved file
        """
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved JSON to: {filepath}")
        return filepath
    
    def load_json(self, filepath: Path) -> Dict[str, Any]:
        """Load JSON data from file
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            Loaded JSON data
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def test(self) -> bool:
        """Test component functionality
        
        Returns:
            True if test passes, False otherwise
        """
        logger.info(f"[{self.__class__.__name__}] Running tests...")
        return True
    
    def cleanup(self) -> None:
        """Cleanup any resources"""
        pass 