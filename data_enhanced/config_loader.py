"""
Configuration loader for press release generation system.
Loads prompts and configuration from YAML file.
"""

import yaml
import os
from typing import Dict, Any, Optional, List
from pathlib import Path

class ConfigLoader:
    """Loads and manages configuration from YAML file"""
    
    def __init__(self, config_path: str = "prompts_config.yaml"):
        self.config_path = Path(config_path)
        self._config: Optional[Dict[str, Any]] = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as file:
            self._config = yaml.safe_load(file)
    
    def reload_config(self):
        """Reload configuration from file"""
        self._load_config()
    
    def get_section_creator_config(self) -> Dict[str, Any]:
        """Get section creator agent configuration"""
        return self._config.get('section_creator', {})
    
    def get_section_evaluator_config(self) -> Dict[str, Any]:
        """Get section evaluator agent configuration"""
        return self._config.get('section_evaluator', {})
    
    def get_evidence_approver_config(self) -> Dict[str, Any]:
        """Get evidence approver agent configuration"""
        return self._config.get('evidence_approver', {})
    
    def get_structure_generator_config(self) -> Dict[str, Any]:
        """Get structure generator configuration"""
        return self._config.get('structure_generator', {})
    
    def get_type_classifier_config(self) -> Dict[str, Any]:
        """Get type classifier configuration"""
        return self._config.get('type_classifier', {})
    
    def get_context_for_section_config(self) -> Dict[str, Any]:
        """Get context for section agent configuration"""
        return self._config.get('context_for_section', {})
    
    def get_excel_processor_config(self) -> Dict[str, Any]:
        """Get Excel processor configuration"""
        return self._config.get('excel_processor', {})
    
    def get_final_checker_config(self) -> Dict[str, Any]:
        """Get final checker configuration"""
        return self._config.get('final_checker', {})
    
    def get_fact_checker_config(self) -> Dict[str, Any]:
        """Get fact checker configuration"""
        return self._config.get('fact_checker', {})
    
    def get_final_processing_chain_config(self) -> Dict[str, Any]:
        """Get final processing chain configuration"""
        return self._config.get('final_processing_chain', {})
    
    def get_content_finder_config(self) -> Dict[str, Any]:
        """Get content finder configuration"""
        return self._config.get('content_finder', {})
    
    def get_section_terms(self) -> Dict[str, List[str]]:
        """Get section-specific search terms"""
        content_finder_config = self.get_content_finder_config()
        return content_finder_config.get('section_terms', {})
    
    def get_general_config(self) -> Dict[str, Any]:
        """Get general configuration"""
        return self._config.get('general', {})
    
    def get_error_handling_config(self) -> Dict[str, Any]:
        """Get error handling configuration"""
        return self._config.get('error_handling', {})
    
    def get_prompt(self, agent_type: str, prompt_type: str) -> str:
        """Get a specific prompt from configuration"""
        agent_config = self._config.get(agent_type, {})
        return agent_config.get(prompt_type, "")
    
    def get_model_config(self, agent_type: str) -> Dict[str, Any]:
        """Get model configuration for an agent"""
        agent_config = self._config.get(agent_type, {})
        return {
            'model': agent_config.get('model', 'gpt-4o-mini'),
            'temperature': agent_config.get('temperature', 0.0)
        }
    
    def get_recursion_limits(self) -> Dict[str, int]:
        """Get recursion limits for different graphs"""
        general_config = self.get_general_config()
        return general_config.get('recursion_limits', {
            'style_graph': 10,
            'creator_graph': 5,
            'finder_graph': 5  # Increased to match config file
        })
    
    def get_evidence_search_params(self) -> Dict[str, Any]:
        """Get evidence search parameters"""
        general_config = self.get_general_config()
        return general_config.get('evidence_search', {
            'lookback_days': 540,
            'top_k': 6,
            'max_loops': 2
        })
    
    def get_content_processing_params(self) -> Dict[str, Any]:
        """Get content processing parameters"""
        general_config = self.get_general_config()
        return general_config.get('content_processing', {
            'max_revisions': 2,
            'min_confidence': 0.6,
            'require_evidence': True
        })
    
    def get_fallback_config(self) -> Dict[str, Any]:
        """Get fallback configuration"""
        error_config = self.get_error_handling_config()
        return error_config.get('fallback_placeholders', {
            'enabled': True,
            'default_placeholder': '[DATA_PENDING]',
            'max_retry_attempts': 2
        })
    
    def get_content_cleaning_config(self) -> Dict[str, Any]:
        """Get content cleaning configuration"""
        error_config = self.get_error_handling_config()
        return error_config.get('content_cleaning', {
            'remove_duplicate_headers': True,
            'normalize_whitespace': True,
            'remove_empty_lines': True
        })

# Global configuration instance
config = ConfigLoader()

def get_config() -> ConfigLoader:
    """Get the global configuration instance"""
    return config

def reload_config():
    """Reload the global configuration"""
    global config
    config.reload_config()
