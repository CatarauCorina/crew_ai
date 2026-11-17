"""
Content Editor Agent for Press Release Editing

This module contains the ContentEditorAgent class that handles intelligent
editing of press release content based on user chat requests.
"""

import json
from typing import Dict, List, Optional
from base_agent import BaseAgent
from config_loader import get_config


class ContentEditorAgent(BaseAgent):
    """
    AI agent that processes chat requests and modifies press release content.
    Handles various types of editing requests like tone changes, content additions,
    structural modifications, and style improvements.
    """
    
    def __init__(self, model: str = None):
        super().__init__()
        config = get_config()
        model_config = config.get_model_config('content_editor')
        self.model = model or model_config['model']

    def run(self, user_request: str, current_content: str, chat_history: list = None) -> dict:
        """
        Process a user's editing request and return modified content.
        
        Args:
            user_request: The user's editing request
            current_content: Current press release content
            chat_history: Previous chat messages for context
            
        Returns:
            dict with keys: modified_content, explanation, success, suggestions
        """
        config = get_config()
        system_prompt = config.get_prompt('content_editor', 'system_prompt')
        
        # Build context from chat history
        context = ""
        if chat_history:
            context = "Previous conversation:\n"
            for msg in chat_history[-3:]:  # Last 3 messages for context
                if isinstance(msg, list) and len(msg) >= 2:
                    user_msg, ai_msg = msg[0], msg[1]
                    context += f"User: {user_msg}\n"
                    if ai_msg:
                        context += f"AI: {ai_msg}\n"
            context += "\n"
        
        user_prompt = config.get_prompt('content_editor', 'user_prompt').format(
            user_request=user_request,
            current_content=current_content,
            context=context
        )
        
        model_config = config.get_model_config('content_editor')
        raw = self.llm_inference(
            messages=[{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}],
            model=self.model, temperature=model_config['temperature']
        )
        
        try:
            result = json.loads(raw)
            return result
        except json.JSONDecodeError:
            return {
                "modified_content": current_content,
                "explanation": "I understand your request, but I encountered an error processing it. Please try rephrasing your request.",
                "success": False,
                "suggestions": ["Try being more specific about what you want to change", "Check if your request is clear and actionable"]
            }

    def analyze_request_type(self, user_request: str) -> str:
        """
        Analyze the type of editing request to provide better responses.
        
        Returns:
            str: Type of request (tone_change, content_addition, structural_change, style_improvement, etc.)
        """
        request_lower = user_request.lower()
        
        if any(word in request_lower for word in ['tone', 'formal', 'casual', 'professional', 'friendly']):
            return 'tone_change'
        elif any(word in request_lower for word in ['add', 'include', 'insert', 'more details', 'expand']):
            return 'content_addition'
        elif any(word in request_lower for word in ['remove', 'delete', 'cut', 'omit']):
            return 'content_removal'
        elif any(word in request_lower for word in ['structure', 'reorganize', 'reorder', 'move']):
            return 'structural_change'
        elif any(word in request_lower for word in ['headline', 'title', 'heading']):
            return 'headline_change'
        elif any(word in request_lower for word in ['shorter', 'longer', 'length', 'concise', 'detailed']):
            return 'length_adjustment'
        else:
            return 'general_edit'

    def extract_placeholders(self, content: str) -> List[str]:
        """
        Extract all placeholders from the content.
        
        Returns:
            List[str]: List of placeholder tokens found in the content
        """
        import re
        placeholder_pattern = r'\[([A-Z_]+)\]'
        return re.findall(placeholder_pattern, content)

    def validate_content(self, content: str) -> Dict[str, any]:
        """
        Validate the modified content for common issues.
        
        Returns:
            Dict[str, any]: Validation results with warnings and suggestions
        """
        issues = []
        suggestions = []
        
        # Check for broken placeholders
        import re
        broken_placeholders = re.findall(r'\[[^\]]*[^A-Z_][^\]]*\]', content)
        if broken_placeholders:
            issues.append(f"Broken placeholders found: {broken_placeholders}")
            suggestions.append("Ensure placeholders follow the format [UPPERCASE_WITH_UNDERSCORES]")
        
        # Check for very short content
        if len(content.strip()) < 100:
            issues.append("Content is very short")
            suggestions.append("Consider adding more details or expanding sections")
        
        # Check for missing sections
        expected_sections = ['headline', 'summary', 'body', 'contact']
        content_lower = content.lower()
        missing_sections = [section for section in expected_sections if section not in content_lower]
        if missing_sections:
            issues.append(f"Missing common sections: {missing_sections}")
            suggestions.append("Consider adding missing sections for a complete press release")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "suggestions": suggestions
        }

    def get_editing_suggestions(self, content: str) -> List[str]:
        """
        Generate general editing suggestions for the content.
        
        Returns:
            List[str]: List of improvement suggestions
        """
        suggestions = []
        
        # Check content length
        if len(content.strip()) < 500:
            suggestions.append("Consider expanding the content with more details")
        elif len(content.strip()) > 2000:
            suggestions.append("Consider making the content more concise")
        
        # Check for placeholders
        placeholders = self.extract_placeholders(content)
        if placeholders:
            suggestions.append(f"Consider filling in the {len(placeholders)} placeholder(s) with actual values")
        
        # Check for quotes
        if 'said' not in content.lower() and 'commented' not in content.lower():
            suggestions.append("Consider adding quotes from key stakeholders")
        
        # Check for contact information
        if 'contact' not in content.lower() and 'email' not in content.lower():
            suggestions.append("Consider adding contact information for media inquiries")
        
        return suggestions

    def format_response(self, result: Dict[str, any]) -> str:
        """
        Format the agent's response for display in the chat interface.
        
        Args:
            result: The result dictionary from the agent
            
        Returns:
            str: Formatted response string
        """
        if result.get("success", False):
            response = f"✅ **Changes Applied Successfully!**\n\n{result['explanation']}"
            
            if result.get("suggestions"):
                response += f"\n\n**Additional Suggestions:**\n" + "\n".join([f"• {s}" for s in result["suggestions"]])
        else:
            response = f"❌ **Unable to process request**\n\n{result.get('explanation', 'Please try rephrasing your request.')}"
            
            if result.get("suggestions"):
                response += f"\n\n**Suggestions:**\n" + "\n".join([f"• {s}" for s in result["suggestions"]])
        
        return response
