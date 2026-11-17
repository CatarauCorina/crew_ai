"""
CrewAI Flow Orchestrator

This module contains the main CrewAI flow that orchestrates all crews
for the complete press release generation process.
"""

from crewai import Crew, Agent, Task, Process
from typing import Dict, List, Any, Optional
import json
from datetime import datetime

from crewai_structure_crew import StructureAnalysisCrew
from crewai_content_crew import ContentGenerationCrew
from crewai_editing_crew import ContentEditingCrew
from crewai_research_crew import ResearchDataCrew


class PressReleaseFlow:
    """Main CrewAI flow for press release generation"""
    
    def __init__(self):
        # Initialize all crews
        self.structure_crew = StructureAnalysisCrew()
        self.content_crew = ContentGenerationCrew()
        self.editing_crew = ContentEditingCrew()
        self.research_crew = ResearchDataCrew()
    
    def _create_flow(self) -> Crew:
        """Create the main CrewAI crew"""
        # Create a simple crew that orchestrates all the individual crews
        return Crew(
            agents=[
                # We'll use the individual crews directly
            ],
            tasks=[
                # We'll call the individual crews directly
            ],
            process=Process.sequential,
            verbose=True,
            memory=True,
            planning=True
        )
    
    def generate_press_release(self, topic: str, company: str = "SISCO", 
                              requirements: Dict[str, Any] = None,
                              user_feedback: str = None) -> Dict[str, Any]:
        """Generate a complete press release using all crews"""
        try:
            # Step 1: Structure Analysis
            structure_result = self.structure_crew.run_analysis(topic, company)
            
            # Step 2: Research & Evidence
            research_result = self.research_crew.research_data(
                query=topic,
                section_name="general"
            )
            
            # Step 3: Content Generation
            content_result = self.content_crew.generate_content(
                section_name="Complete Press Release",
                topic=topic,
                tone="professional",
                phrase_bank=[],
                company=company
            )
            
            return {
                "success": True,
                "result": {
                    "structure": structure_result,
                    "research": research_result,
                    "content": content_result
                },
                "flow_type": "press_release_generation",
                "topic": topic,
                "company": company,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "flow_type": "press_release_generation",
                "timestamp": datetime.now().isoformat()
            }
    
    def edit_press_release(self, current_content: str, user_request: str,
                          target_tone: str = "professional") -> Dict[str, Any]:
        """Edit an existing press release using the editing crew"""
        try:
            # Use only the editing crew for content modification
            result = self.editing_crew.edit_content(
                user_request=user_request,
                current_content=current_content,
                target_tone=target_tone
            )
            
            return {
                "success": True,
                "result": result,
                "flow_type": "content_editing",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "flow_type": "content_editing",
                "timestamp": datetime.now().isoformat()
            }
    
    def research_evidence(self, query: str, section_name: str) -> Dict[str, Any]:
        """Research evidence for a specific section"""
        try:
            result = self.research_crew.research_data(
                query=query,
                section_name=section_name
            )
            
            return {
                "success": True,
                "result": result,
                "flow_type": "evidence_research",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "flow_type": "evidence_research",
                "timestamp": datetime.now().isoformat()
            }


class PressReleaseCrewAI:
    """Main class for CrewAI-based press release generation"""
    
    def __init__(self):
        self.flow = PressReleaseFlow()
    
    def generate_with_ai(self, topic: str, company: str = "SISCO", 
                        progress_callback=None) -> Dict[str, Any]:
        """Generate press release using CrewAI with progress updates"""
        try:
            if progress_callback:
                progress_callback("🚀 Starting CrewAI press release generation...", 10)
            
            # Step 1: Structure Analysis
            if progress_callback:
                progress_callback("🔍 Analyzing content type and structure...", 20)
            
            structure_result = self.flow.structure_crew.run_analysis(topic, company)
            
            if progress_callback:
                progress_callback("📋 Structure analysis complete", 40)
            
            # Step 2: Research & Evidence
            if progress_callback:
                progress_callback("🔍 Researching evidence and data...", 60)
            
            research_result = self.flow.research_crew.research_data(
                query=topic,
                section_name="general"
            )
            
            if progress_callback:
                progress_callback("📊 Evidence research complete", 80)
            
            # Step 3: Content Generation
            if progress_callback:
                progress_callback("✍️ Generating content sections...", 90)
            
            # Generate content using CrewAI content crew
            content_result = self.flow.content_crew.generate_content(
                section_name="Complete Press Release",
                topic=topic,
                tone="professional",
                phrase_bank=[],
                company=company
            )
            
            if progress_callback:
                progress_callback("✅ Press release generation complete!", 100)
            
            # Extract content from CrewAI output
            if hasattr(content_result, 'raw'):
                content_text = str(content_result.raw)
            elif hasattr(content_result, 'result'):
                content_text = str(content_result.result)
            else:
                content_text = str(content_result)
            
            return {
                "success": True,
                "content": content_text,
                "sections": {"Complete Press Release": {"content": content_text, "status": "completed"}},
                "placeholders": [],
                "structure_analysis": structure_result,
                "research_data": research_result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            if progress_callback:
                progress_callback(f"❌ Error: {str(e)}", 0)
            
            return {
                "success": False,
                "error": str(e),
                "content": "",
                "sections": [],
                "placeholders": []
            }
    
    def edit_content(self, user_request: str, current_content: str) -> Dict[str, Any]:
        """Edit content based on user request"""
        return self.flow.edit_press_release(current_content, user_request)
    
    def research_evidence(self, query: str, section_name: str) -> Dict[str, Any]:
        """Research evidence for a specific section"""
        return self.flow.research_evidence(query, section_name)


# Example usage and testing
if __name__ == "__main__":
    # Test the complete flow
    crewai_press_release = PressReleaseCrewAI()
    
    # Test press release generation
    result = crewai_press_release.generate_with_ai(
        topic="Q4 2024 Financial Results",
        company="SISCO"
    )
    
    print("CrewAI Press Release Generation Result:")
    print(json.dumps(result, indent=2))
    
    # Test content editing
    if result["success"]:
        edit_result = crewai_press_release.edit_content(
            user_request="Make the tone more formal and professional",
            current_content=result["content"]
        )
        
        print("\nCrewAI Content Editing Result:")
        print(json.dumps(edit_result, indent=2))
