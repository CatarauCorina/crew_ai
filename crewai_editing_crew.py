"""
CrewAI Content Editing Crew

This module contains the CrewAI implementation of the content editing agents
for press release content modification and improvement.
"""

from crewai import Crew, Agent, Task, Process
from crewai.tools import BaseTool
from typing import Dict, List, Any, Optional
import json
import re
from datetime import datetime

from content_editor_agent import ContentEditorAgent
from config_loader import get_config


class ContentEditorTool(BaseTool):
    """Tool for editing press release content based on user requests"""
    
    name: str = "content_editor"
    description: str = "Edits press release content based on user requests and feedback"
    
    def _run(self, user_request: str, current_content: str, chat_history: List = None) -> str:
        """Edit content based on user request"""
        try:
            # Use the existing ContentEditorAgent
            editor = ContentEditorAgent()
            
            # Process the request
            result = editor.run(
                user_request=user_request,
                current_content=current_content,
                chat_history=chat_history or []
            )
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            return json.dumps({
                "modified_content": current_content,
                "explanation": f"Error processing request: {str(e)}",
                "success": False,
                "suggestions": ["Please try rephrasing your request"]
            }, indent=2)


class StyleConsultantTool(BaseTool):
    """Tool for providing style and tone consultation"""
    
    name: str = "style_consultant"
    description: str = "Provides style and tone consultation for press release content"
    
    def _run(self, content: str, target_tone: str, current_tone: str = None) -> str:
        """Analyze and suggest style improvements"""
        try:
            # Analyze current tone and style
            analysis = self._analyze_tone_and_style(content)
            
            # Generate style recommendations
            recommendations = self._generate_style_recommendations(
                content, target_tone, analysis
            )
            
            return json.dumps({
                "current_tone": analysis.get("tone", "unknown"),
                "target_tone": target_tone,
                "style_analysis": analysis,
                "recommendations": recommendations,
                "success": True
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "error": str(e),
                "success": False
            }, indent=2)
    
    def _analyze_tone_and_style(self, content: str) -> Dict[str, Any]:
        """Analyze the tone and style of the content"""
        analysis = {
            "tone": "neutral",
            "formality": "medium",
            "sentence_length": "medium",
            "vocabulary": "standard",
            "structure": "good"
        }
        
        # Analyze sentence length
        sentences = re.split(r'[.!?]+', content)
        avg_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        
        if avg_length < 10:
            analysis["sentence_length"] = "short"
        elif avg_length > 20:
            analysis["sentence_length"] = "long"
        
        # Analyze formality
        formal_words = ["utilize", "implement", "facilitate", "comprehensive", "strategic"]
        informal_words = ["use", "do", "help", "big", "plan"]
        
        formal_count = sum(1 for word in formal_words if word.lower() in content.lower())
        informal_count = sum(1 for word in informal_words if word.lower() in content.lower())
        
        if formal_count > informal_count:
            analysis["formality"] = "high"
        elif informal_count > formal_count:
            analysis["formality"] = "low"
        
        return analysis
    
    def _generate_style_recommendations(self, content: str, target_tone: str, 
                                      analysis: Dict[str, Any]) -> List[str]:
        """Generate style recommendations"""
        recommendations = []
        
        if target_tone == "formal" and analysis["formality"] != "high":
            recommendations.append("Use more formal vocabulary and sentence structures")
        
        if target_tone == "casual" and analysis["formality"] != "low":
            recommendations.append("Use more conversational language and shorter sentences")
        
        if analysis["sentence_length"] == "long":
            recommendations.append("Consider breaking up long sentences for better readability")
        
        if analysis["sentence_length"] == "short":
            recommendations.append("Consider combining some short sentences for better flow")
        
        return recommendations


class FinalReviewerTool(BaseTool):
    """Tool for final content review and approval"""
    
    name: str = "final_reviewer"
    description: str = "Performs final review and approval of press release content"
    
    def _run(self, content: str, requirements: Dict[str, Any]) -> str:
        """Perform final review of content"""
        try:
            review_results = {
                "approved": True,
                "issues": [],
                "suggestions": [],
                "quality_score": 8.0,
                "compliance": True
            }
            
            # Check content length
            word_count = len(content.split())
            if word_count < requirements.get("min_words", 100):
                review_results["issues"].append("Content is too short")
                review_results["approved"] = False
            elif word_count > requirements.get("max_words", 2000):
                review_results["issues"].append("Content is too long")
                review_results["suggestions"].append("Consider shortening the content")
            
            # Check for placeholders
            placeholder_pattern = r'\[([A-Z_]+)\]'
            placeholders = re.findall(placeholder_pattern, content)
            if placeholders:
                review_results["suggestions"].append(f"Consider filling {len(placeholders)} placeholder(s)")
            
            # Check for required sections
            required_sections = requirements.get("required_sections", [])
            for section in required_sections:
                if section.lower() not in content.lower():
                    review_results["issues"].append(f"Missing required section: {section}")
                    review_results["approved"] = False
            
            # Calculate quality score
            quality_factors = {
                "length_appropriate": 1.0 if 100 <= word_count <= 2000 else 0.5,
                "no_placeholders": 1.0 if not placeholders else 0.7,
                "has_quotes": 1.0 if "said" in content.lower() or "commented" in content.lower() else 0.8,
                "proper_structure": 1.0 if len(content.split('\n\n')) > 2 else 0.6
            }
            
            review_results["quality_score"] = sum(quality_factors.values()) / len(quality_factors) * 10
            
            return json.dumps(review_results, indent=2)
            
        except Exception as e:
            return json.dumps({
                "error": str(e),
                "approved": False,
                "success": False
            }, indent=2)


class ContentEditingCrew:
    """CrewAI crew for content editing and improvement"""
    
    def __init__(self):
        self.config = get_config()
        
        # Initialize tools
        self.content_editor_tool = ContentEditorTool()
        self.style_consultant_tool = StyleConsultantTool()
        self.final_reviewer_tool = FinalReviewerTool()
        
        # Create agents
        self.content_editor = Agent(
            role="Content Editor",
            goal="Edit and modify press release content based on user requests and feedback",
            backstory="""You are an expert content editor specializing in press release content. 
            You excel at understanding user requests and making precise, effective modifications 
            to content while maintaining quality and consistency.""",
            tools=[self.content_editor_tool],
            verbose=True,
            allow_delegation=False
        )
        
        self.style_consultant = Agent(
            role="Style Consultant",
            goal="Provide style and tone consultation to improve content effectiveness",
            backstory="""You are a style and tone expert with deep knowledge of press release 
            best practices. You specialize in analyzing content style and providing specific 
            recommendations for improvement.""",
            tools=[self.style_consultant_tool],
            verbose=True,
            allow_delegation=False
        )
        
        self.final_reviewer = Agent(
            role="Final Reviewer",
            goal="Perform final review and approval of press release content",
            backstory="""You are a meticulous final reviewer with expertise in press release 
            standards and requirements. You ensure all content meets publication standards 
            and quality requirements before final approval.""",
            tools=[self.final_reviewer_tool],
            verbose=True,
            allow_delegation=False
        )

    def create_crew(self) -> Crew:
        """Create and return the Content Editing Crew"""
        return Crew(
            agents=[
                self.content_editor,
                self.style_consultant,
                self.final_reviewer
            ],
            tasks=[
                self.edit_content_task(),
                self.style_consultation_task(),
                self.final_review_task()
            ],
            process=Process.sequential,
            verbose=True,
            memory=True,
            planning=True
        )

    def edit_content_task(self) -> Task:
        """Task for editing content based on user requests"""
        return Task(
            description="""Edit the press release content based on the user's specific request. 
            Consider the following types of requests:
            - Tone changes (formal, casual, professional, friendly)
            - Content additions (more details, new sections, quotes)
            - Content removal (unnecessary sections, redundant information)
            - Structural changes (reorganizing sections, improving flow)
            - Style improvements (better headlines, clearer language)
            - Length adjustments (making content shorter or longer)
            
            Ensure all changes maintain content quality and consistency.""",
            expected_output="""A JSON object containing:
            - modified_content: The updated content
            - explanation: Clear explanation of changes made
            - success: Boolean indicating success
            - suggestions: Additional improvement suggestions
            - change_summary: Summary of specific changes made""",
            agent=self.content_editor,
            tools=[self.content_editor_tool]
        )

    def style_consultation_task(self) -> Task:
        """Task for style consultation"""
        return Task(
            description="""Analyze the content style and provide consultation on:
            - Current tone and style characteristics
            - Alignment with target tone
            - Style consistency throughout content
            - Areas for improvement
            - Specific recommendations for enhancement
            
            Focus on making the content more effective and engaging.""",
            expected_output="""A JSON object containing:
            - current_tone: Analysis of current tone
            - target_tone: Target tone for the content
            - style_analysis: Detailed style analysis
            - recommendations: Specific style recommendations
            - improvement_areas: Areas that need improvement
            - consistency_check: Consistency analysis results""",
            agent=self.style_consultant,
            tools=[self.style_consultant_tool],
            context=[self.edit_content_task()]
        )

    def final_review_task(self) -> Task:
        """Task for final review and approval"""
        return Task(
            description="""Perform a comprehensive final review of the edited content. Check:
            - Content quality and completeness
            - Compliance with press release standards
            - Length and format requirements
            - Required elements present
            - Overall effectiveness and impact
            - Readiness for publication
            
            Provide final approval or specific requirements for completion.""",
            expected_output="""A JSON object containing:
            - approved: Boolean indicating final approval
            - issues: List of any remaining issues
            - suggestions: Final improvement suggestions
            - quality_score: Overall quality score (1-10)
            - compliance: Compliance status
            - publication_ready: Boolean indicating if ready for publication""",
            agent=self.final_reviewer,
            tools=[self.final_reviewer_tool],
            context=[self.edit_content_task(), self.style_consultation_task()]
        )

    def edit_content(self, user_request: str, current_content: str, 
                    target_tone: str = "professional", 
                    requirements: Dict[str, Any] = None) -> Dict[str, Any]:
        """Edit content based on user request"""
        crew = self.create_crew()
        
        # Set inputs for the crew
        inputs = {
            "user_request": user_request,
            "current_content": current_content,
            "target_tone": target_tone,
            "requirements": requirements or {}
        }
        
        # Execute the crew
        result = crew.kickoff(inputs=inputs)
        
        return {
            "success": True,
            "result": result,
            "crew_type": "content_editing",
            "timestamp": datetime.now().isoformat()
        }


# Example usage
if __name__ == "__main__":
    # Test the Content Editing Crew
    crew = ContentEditingCrew()
    
    # Edit content for a sample request
    result = crew.edit_content(
        user_request="Make the tone more formal and professional",
        current_content="# Q4 Results\n\nWe did great this quarter!",
        target_tone="formal",
        requirements={"min_words": 100, "max_words": 2000}
    )
    
    print("Content Editing Result:")
    print(json.dumps(result, indent=2))

