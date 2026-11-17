"""
Multi-Mode Configuration Loader for Document Generation System.
Supports multiple document types with tab-based configuration management.
"""

import yaml
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from config_loader import ConfigLoader

class MultiModeConfigLoader:
    """Loads and manages configuration for multiple document modes"""
    
    def __init__(self, modes_config_path: str = "config_modes.yaml"):
        self.modes_config_path = Path(modes_config_path)
        self._modes_config: Optional[Dict[str, Any]] = None
        self._mode_configs: Dict[str, ConfigLoader] = {}
        self._current_mode: str = "press_release"
        self._load_modes_config()
        self._load_all_mode_configs()
    
    def _load_modes_config(self):
        """Load the modes configuration file"""
        if not self.modes_config_path.exists():
            raise FileNotFoundError(f"Modes configuration file not found: {self.modes_config_path}")
        
        with open(self.modes_config_path, 'r', encoding='utf-8') as file:
            self._modes_config = yaml.safe_load(file)
    
    def _load_all_mode_configs(self):
        """Load all mode-specific configuration files"""
        modes = self._modes_config.get('document_modes', {})
        for mode_key, mode_info in modes.items():
            config_file = mode_info.get('config_file')
            if config_file and Path(config_file).exists():
                try:
                    self._mode_configs[mode_key] = ConfigLoader(config_file)
                except Exception as e:
                    print(f"Warning: Could not load config for mode {mode_key}: {e}")
    
    def get_available_modes(self) -> Dict[str, Dict[str, Any]]:
        """Get all available document modes"""
        return self._modes_config.get('document_modes', {})
    
    def get_current_mode(self) -> str:
        """Get the current active mode"""
        return self._current_mode
    
    def set_current_mode(self, mode: str) -> bool:
        """Set the current active mode"""
        if mode in self._mode_configs:
            self._current_mode = mode
            return True
        return False
    
    def get_default_mode(self) -> str:
        """Get the default mode"""
        return self._modes_config.get('default_mode', 'press_release')
    
    def get_mode_info(self, mode: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific mode"""
        modes = self.get_available_modes()
        return modes.get(mode)
    
    def get_current_config(self) -> Optional[ConfigLoader]:
        """Get the configuration for the current mode"""
        return self._mode_configs.get(self._current_mode)
    
    def get_mode_config(self, mode: str) -> Optional[ConfigLoader]:
        """Get the configuration for a specific mode"""
        return self._mode_configs.get(mode)
    
    def reload_mode_config(self, mode: str) -> bool:
        """Reload configuration for a specific mode"""
        if mode in self._mode_configs:
            try:
                self._mode_configs[mode].reload_config()
                return True
            except Exception as e:
                print(f"Error reloading config for mode {mode}: {e}")
                return False
        return False
    
    def reload_all_configs(self):
        """Reload all mode configurations"""
        for mode in self._mode_configs:
            self.reload_mode_config(mode)
    
    def add_custom_mode(self, mode_key: str, mode_info: Dict[str, Any], config_file: str) -> bool:
        """Add a custom mode with its configuration"""
        try:
            if Path(config_file).exists():
                self._mode_configs[mode_key] = ConfigLoader(config_file)
                # Update modes config
                if 'document_modes' not in self._modes_config:
                    self._modes_config['document_modes'] = {}
                self._modes_config['document_modes'][mode_key] = mode_info
                return True
        except Exception as e:
            print(f"Error adding custom mode {mode_key}: {e}")
        return False
    
    def remove_mode(self, mode_key: str) -> bool:
        """Remove a mode (except default modes)"""
        if mode_key in ['press_release', 'rfp']:  # Protect default modes
            return False
        
        if mode_key in self._mode_configs:
            del self._mode_configs[mode_key]
            if 'document_modes' in self._modes_config and mode_key in self._modes_config['document_modes']:
                del self._modes_config['document_modes'][mode_key]
            return True
        return False
    
    def save_modes_config(self):
        """Save the modes configuration to file"""
        with open(self.modes_config_path, 'w', encoding='utf-8') as file:
            yaml.dump(self._modes_config, file, default_flow_style=False, indent=2)
    
    # Delegate methods to current config
    def get_section_creator_config(self) -> Dict[str, Any]:
        """Get section creator agent configuration for current mode"""
        config = self.get_current_config()
        return config.get_section_creator_config() if config else {}
    
    def get_section_evaluator_config(self) -> Dict[str, Any]:
        """Get section evaluator agent configuration for current mode"""
        config = self.get_current_config()
        return config.get_section_evaluator_config() if config else {}
    
    def get_evidence_approver_config(self) -> Dict[str, Any]:
        """Get evidence approver agent configuration for current mode"""
        config = self.get_current_config()
        return config.get_evidence_approver_config() if config else {}
    
    def get_structure_generator_config(self) -> Dict[str, Any]:
        """Get structure generator configuration for current mode"""
        config = self.get_current_config()
        return config.get_structure_generator_config() if config else {}
    
    def get_type_classifier_config(self) -> Dict[str, Any]:
        """Get type classifier configuration for current mode"""
        config = self.get_current_config()
        return config.get_type_classifier_config() if config else {}
    
    def get_content_finder_config(self) -> Dict[str, Any]:
        """Get content finder configuration for current mode"""
        config = self.get_current_config()
        return config.get_content_finder_config() if config else {}
    
    def get_section_terms(self) -> Dict[str, List[str]]:
        """Get section-specific search terms for current mode"""
        config = self.get_current_config()
        return config.get_section_terms() if config else {}
    
    def get_general_config(self) -> Dict[str, Any]:
        """Get general configuration for current mode"""
        config = self.get_current_config()
        return config.get_general_config() if config else {}
    
    def get_error_handling_config(self) -> Dict[str, Any]:
        """Get error handling configuration for current mode"""
        config = self.get_current_config()
        return config.get_error_handling_config() if config else {}
    
    def get_prompt(self, agent_type: str, prompt_type: str) -> str:
        """Get a specific prompt from current mode configuration"""
        config = self.get_current_config()
        return config.get_prompt(agent_type, prompt_type) if config else ""
    
    def get_model_config(self, agent_type: str) -> Dict[str, Any]:
        """Get model configuration for an agent in current mode"""
        config = self.get_current_config()
        return config.get_model_config(agent_type) if config else {}
    
    def get_recursion_limits(self) -> Dict[str, int]:
        """Get recursion limits for different graphs in current mode"""
        config = self.get_current_config()
        return config.get_recursion_limits() if config else {}
    
    def get_evidence_search_params(self) -> Dict[str, Any]:
        """Get evidence search parameters for current mode"""
        config = self.get_current_config()
        return config.get_evidence_search_params() if config else {}
    
    def get_content_processing_params(self) -> Dict[str, Any]:
        """Get content processing parameters for current mode"""
        config = self.get_current_config()
        return config.get_content_processing_params() if config else {}
    
    def get_fallback_config(self) -> Dict[str, Any]:
        """Get fallback configuration for current mode"""
        config = self.get_current_config()
        return config.get_fallback_config() if config else {}
    
    def get_content_cleaning_config(self) -> Dict[str, Any]:
        """Get content cleaning configuration for current mode"""
        config = self.get_current_config()
        return config.get_content_cleaning_config() if config else {}

# Global multi-mode configuration instance
multi_mode_config = MultiModeConfigLoader()

def get_multi_mode_config() -> MultiModeConfigLoader:
    """Get the global multi-mode configuration instance"""
    return multi_mode_config

def get_config() -> MultiModeConfigLoader:
    """Get the global multi-mode configuration instance (alias for compatibility)"""
    return multi_mode_config

def reload_config():
    """Reload all configurations"""
    global multi_mode_config
    multi_mode_config.reload_all_configs()


