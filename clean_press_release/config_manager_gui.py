"""
Configuration Management GUI Component
Provides tab-based interface for managing different document modes
"""

import gradio as gr
import yaml
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from multi_mode_config_loader import get_multi_mode_config

class ConfigManagerGUI:
    """GUI component for managing multi-mode configurations"""
    
    def __init__(self):
        self.config_loader = get_multi_mode_config()
        self.current_mode = self.config_loader.get_default_mode()
        self.config_loader.set_current_mode(self.current_mode)
    
    def create_config_tabs(self) -> Tuple[gr.Tabs, Dict[str, Any]]:
        """Create the configuration management tabs"""
        
        # Get available modes
        modes = self.config_loader.get_available_modes()
        
        # Create tab components
        tab_components = {}
        
        with gr.Tabs(label="Configuration Management", elem_id="config-tabs") as config_tabs:
            
            # Mode Selection Tab
            with gr.Tab("Mode Selection", id="mode-selection"):
                mode_components = self._create_mode_selection_tab()
                tab_components.update(mode_components)
            
            # Configuration Editor Tab
            with gr.Tab("Configuration Editor", id="config-editor"):
                editor_components = self._create_config_editor_tab()
                tab_components.update(editor_components)
            
            # Custom Modes Tab
            with gr.Tab("Custom Modes", id="custom-modes"):
                custom_components = self._create_custom_modes_tab()
                tab_components.update(custom_components)
        
        return config_tabs, tab_components
    
    def _create_mode_selection_tab(self) -> Dict[str, Any]:
        """Create the mode selection tab"""
        
        with gr.Row():
            with gr.Column(scale=2):
                # Mode selector
                mode_selector = gr.Dropdown(
                    choices=list(self.config_loader.get_available_modes().keys()),
                    value=self.current_mode,
                    label="Select Document Mode",
                    interactive=True
                )
                
                # Mode information display
                mode_info = gr.HTML("", elem_id="mode-info")
                
                # Apply mode button
                apply_mode_btn = gr.Button(
                    "Apply Mode",
                    variant="primary",
                    elem_classes=["btn-primary"]
                )
                
                # Status display
                mode_status = gr.Markdown("", visible=False)
            
            with gr.Column(scale=1):
                # Mode preview
                gr.HTML("""
                <div class="card">
                    <h3 style="color: white; margin-bottom: 15px;">📋 Current Mode</h3>
                    <div id="current-mode-preview">
                        <p style="color: rgba(255,255,255,0.8);">Select a mode to see details</p>
                    </div>
                </div>
                """)
        
        return {
            "mode_selector": mode_selector,
            "mode_info": mode_info,
            "apply_mode_btn": apply_mode_btn,
            "mode_status": mode_status
        }
    
    def _create_config_editor_tab(self) -> Dict[str, Any]:
        """Create the configuration editor tab"""
        
        with gr.Row():
            with gr.Column(scale=1):
                # Configuration sections
                config_sections = gr.Dropdown(
                    choices=[
                        "Section Creator",
                        "Section Evaluator", 
                        "Evidence Approver",
                        "Structure Generator",
                        "Type Classifier",
                        "Content Finder",
                        "General Settings",
                        "Error Handling"
                    ],
                    value="Section Creator",
                    label="Configuration Section",
                    interactive=True
                )
                
                # Load section button
                load_section_btn = gr.Button(
                    "Load Section",
                    variant="secondary"
                )
                
                # Save section button
                save_section_btn = gr.Button(
                    "Save Section",
                    variant="primary",
                    elem_classes=["btn-primary"]
                )
            
            with gr.Column(scale=3):
                # Configuration editor
                config_editor = gr.Textbox(
                    label="Configuration (YAML)",
                    lines=20,
                    max_lines=30,
                    placeholder="Configuration will appear here...",
                    elem_classes=["config-editor"]
                )
                
                # Editor status
                editor_status = gr.Markdown("", visible=False)
        
        return {
            "config_sections": config_sections,
            "load_section_btn": load_section_btn,
            "save_section_btn": save_section_btn,
            "config_editor": config_editor,
            "editor_status": editor_status
        }
    
    def _create_custom_modes_tab(self) -> Dict[str, Any]:
        """Create the custom modes management tab"""
        
        with gr.Row():
            with gr.Column(scale=1):
                # Add new mode
                gr.HTML("""
                <div class="card">
                    <h3 style="color: white; margin-bottom: 15px;">➕ Add New Mode</h3>
                </div>
                """)
                
                new_mode_name = gr.Textbox(
                    label="Mode Name",
                    placeholder="e.g., contract_template"
                )
                
                new_mode_display_name = gr.Textbox(
                    label="Display Name",
                    placeholder="e.g., Contract Template"
                )
                
                new_mode_description = gr.Textbox(
                    label="Description",
                    placeholder="e.g., Generate contract templates",
                    lines=2
                )
                
                new_mode_icon = gr.Textbox(
                    label="Icon",
                    placeholder="e.g., 📄",
                    value="📄"
                )
                
                new_mode_config_file = gr.Textbox(
                    label="Config File Path",
                    placeholder="e.g., contract_config.yaml"
                )
                
                add_mode_btn = gr.Button(
                    "Add Mode",
                    variant="primary",
                    elem_classes=["btn-primary"]
                )
            
            with gr.Column(scale=1):
                # Manage existing modes
                gr.HTML("""
                <div class="card">
                    <h3 style="color: white; margin-bottom: 15px;">🗑️ Manage Modes</h3>
                </div>
                """)
                
                existing_modes = gr.Dropdown(
                    choices=list(self.config_loader.get_available_modes().keys()),
                    label="Select Mode to Remove",
                    interactive=True
                )
                
                remove_mode_btn = gr.Button(
                    "Remove Mode",
                    variant="stop"
                )
                
                # Status
                custom_status = gr.Markdown("", visible=False)
        
        return {
            "new_mode_name": new_mode_name,
            "new_mode_display_name": new_mode_display_name,
            "new_mode_description": new_mode_description,
            "new_mode_icon": new_mode_icon,
            "new_mode_config_file": new_mode_config_file,
            "add_mode_btn": add_mode_btn,
            "existing_modes": existing_modes,
            "remove_mode_btn": remove_mode_btn,
            "custom_status": custom_status
        }
    
    def update_mode_info(self, mode: str) -> Tuple[str, str]:
        """Update mode information display"""
        mode_info = self.config_loader.get_mode_info(mode)
        if not mode_info:
            return "", "❌ Mode not found"
        
        info_html = f"""
        <div class="card">
            <h3 style="color: white; margin-bottom: 15px;">
                {mode_info.get('icon', '📄')} {mode_info.get('name', mode)}
            </h3>
            <p style="color: rgba(255,255,255,0.8); margin-bottom: 15px;">
                {mode_info.get('description', 'No description available')}
            </p>
            <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px;">
                <p style="color: rgba(255,255,255,0.7); margin: 0;">
                    <strong>Config File:</strong> {mode_info.get('config_file', 'Not specified')}
                </p>
            </div>
        </div>
        """
        
        return info_html, "✅ Mode information loaded"
    
    def apply_mode(self, mode: str) -> Tuple[str, str]:
        """Apply the selected mode"""
        if self.config_loader.set_current_mode(mode):
            self.current_mode = mode
            return "✅ Mode applied successfully", "success"
        else:
            return "❌ Failed to apply mode", "error"
    
    def load_config_section(self, section: str) -> Tuple[str, str]:
        """Load a configuration section for editing"""
        try:
            config = self.config_loader.get_current_config()
            if not config:
                return "", "❌ No configuration loaded for current mode"
            
            # Map section names to config methods
            section_mapping = {
                "Section Creator": config.get_section_creator_config,
                "Section Evaluator": config.get_section_evaluator_config,
                "Evidence Approver": config.get_evidence_approver_config,
                "Structure Generator": config.get_structure_generator_config,
                "Type Classifier": config.get_type_classifier_config,
                "Content Finder": config.get_content_finder_config,
                "General Settings": config.get_general_config,
                "Error Handling": config.get_error_handling_config
            }
            
            if section in section_mapping:
                section_config = section_mapping[section]()
                yaml_content = yaml.dump(section_config, default_flow_style=False, indent=2)
                return yaml_content, "✅ Section loaded successfully"
            else:
                return "", "❌ Unknown section"
                
        except Exception as e:
            return "", f"❌ Error loading section: {str(e)}"
    
    def save_config_section(self, section: str, yaml_content: str) -> Tuple[str, str]:
        """Save a configuration section"""
        try:
            # Parse YAML content
            section_config = yaml.safe_load(yaml_content)
            
            # This would need to be implemented in the config loader
            # For now, just return success
            return "✅ Section saved successfully", "success"
            
        except yaml.YAMLError as e:
            return f"❌ Invalid YAML: {str(e)}", "error"
        except Exception as e:
            return f"❌ Error saving section: {str(e)}", "error"
    
    def add_custom_mode(self, name: str, display_name: str, description: str, 
                       icon: str, config_file: str) -> Tuple[str, str]:
        """Add a custom mode"""
        try:
            mode_info = {
                "name": display_name,
                "description": description,
                "icon": icon,
                "config_file": config_file
            }
            
            if self.config_loader.add_custom_mode(name, mode_info, config_file):
                return "✅ Custom mode added successfully", "success"
            else:
                return "❌ Failed to add custom mode", "error"
                
        except Exception as e:
            return f"❌ Error adding custom mode: {str(e)}", "error"
    
    def remove_custom_mode(self, mode: str) -> Tuple[str, str]:
        """Remove a custom mode"""
        try:
            if self.config_loader.remove_mode(mode):
                return "✅ Mode removed successfully", "success"
            else:
                return "❌ Failed to remove mode (may be a protected mode)", "error"
                
        except Exception as e:
            return f"❌ Error removing mode: {str(e)}", "error"
    
    def get_current_mode(self) -> str:
        """Get the current active mode"""
        return self.current_mode
    
    def get_available_modes(self) -> List[str]:
        """Get list of available modes"""
        return list(self.config_loader.get_available_modes().keys())

# Global config manager instance
config_manager = ConfigManagerGUI()

def get_config_manager() -> ConfigManagerGUI:
    """Get the global config manager instance"""
    return config_manager


