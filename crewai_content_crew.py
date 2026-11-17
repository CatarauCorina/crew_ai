"""
CrewAI Content Generation Crew

This module contains the CrewAI implementation of the content generation agents
for press release content creation and quality assurance.
"""

from crewai import Crew, Agent, Task, Process
from crewai.tools import BaseTool
from typing import Dict, List, Any, Optional
import json
import re
from datetime import datetime

from base_agent import BaseAgent
from mongo_interface import MongoInterface
from states import SectionState, FinderState
from config_loader import get_config


class EvidenceResearchTool(BaseTool):
    """Tool for researching and gathering evidence from MongoDB"""
    
    name: str = "evidence_researcher"
    description: str = "Researches and gathers evidence from MongoDB using Atlas Search"
    
    def _run(self, query: str, section_name: str, company: str = "SISCO") -> str:
        """Research evidence for a specific section"""
        try:
            from press_release_writer import build_finder_graph
            
            # Build the finder graph
            finder_app = build_finder_graph()
            
            # Create finder state
            fstate = FinderState(
                company=company,
                topic=query,
                section_name=section_name,
                section_notes="",
                lookback_days=1080,
                top_k=10,
                max_loops=3
            )
            
            # Execute the finder
            result = finder_app.invoke(fstate, config={"recursion_limit": 5})
            
            return json.dumps({
                "evidence": result.get("evidence", []),
                "placeholders": result.get("placeholders", []),
                "sufficient": result.get("sufficient", False),
                "reason": result.get("reason", "")
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "error": str(e),
                "evidence": [],
                "placeholders": [],
                "sufficient": False
            }, indent=2)


class ContentWriterTool(BaseTool):
    """Tool for writing press release content"""
    
    name: str = "content_writer"
    description: str = "Writes high-quality press release content based on evidence and guidelines"
    
    def _run(self, section_name: str, evidence: List[Dict], tone: str, 
             phrase_bank: List[str], placeholders: List[Dict]) -> str:
        """Write content for a specific section"""
        try:
            from press_release_writer import build_section_creator_graph
            
            # Build the creator graph
            creator_app = build_section_creator_graph()
            
            # Create section state
            sstate = SectionState(
                section_name=section_name,
                section_notes="",
                topic="",
                company="SISCO",
                tone=tone,
                phrase_bank=phrase_bank,
                evidence=evidence,
                placeholders=placeholders,
                allow_placeholders=True
            )
            
            # Execute the creator
            result = creator_app.invoke(sstate, config={"recursion_limit": 3})
            
            return json.dumps({
                "draft_md": result.get("draft_md", ""),
                "used_refs": result.get("used_refs", []),
                "warnings": result.get("warnings", []),
                "success": True
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "error": str(e),
                "draft_md": "",
                "used_refs": [],
                "warnings": [f"Error writing content: {str(e)}"],
                "success": False
            }, indent=2)


class QualityAssuranceTool(BaseTool):
    """Tool for quality assurance and content evaluation"""
    
    name: str = "quality_assurance"
    description: str = "Evaluates content quality and provides improvement suggestions"
    
    def _run(self, content: str, section_name: str, tone: str, 
             evidence: List[Dict], placeholders: List[Dict]) -> str:
        """Evaluate content quality"""
        try:
            from press_release_writer import SectionFinalEvaluatorAgent
            
            # Create evaluator agent
            evaluator = SectionFinalEvaluatorAgent()
            
            # Create evaluation payload
            payload = {
                "section_name": section_name,
                "draft_md": content,
                "tone": tone,
                "evidence": evidence,
                "placeholders": placeholders,
                "allow_placeholders": True,
                "phrase_bank": [],
                "section_memory": {}
            }
            
            # Run evaluation
            result = evaluator.run(payload)
            
            return json.dumps({
                "accept": result.get("accept", False),
                "reasons": result.get("reasons", []),
                "needs_revision": result.get("needs_revision", False),
                "revision_instructions": result.get("revision_instructions", []),
                "ask_finder_keywords": result.get("ask_finder_keywords", []),
                "success": True
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "error": str(e),
                "accept": False,
                "reasons": [f"Evaluation error: {str(e)}"],
                "needs_revision": True,
                "success": False
            }, indent=2)


class ContentValidatorTool(BaseTool):
    """Tool for validating content against requirements"""
    
    name: str = "content_validator"
    description: str = "Validates content against press release requirements and standards"
    
    def _run(self, content: str, section_name: str, requirements: Dict) -> str:
        """Validate content against requirements"""
        issues = []
        suggestions = []
        
        # Check content length
        if len(content.strip()) < 50:
            issues.append("Content is too short")
            suggestions.append("Add more details and context")
        elif len(content.strip()) > 2000:
            issues.append("Content is too long")
            suggestions.append("Consider making it more concise")
        
        # Check for placeholders
        placeholder_pattern = r'\[([A-Z_]+)\]'
        placeholders = re.findall(placeholder_pattern, content)
        if placeholders:
            suggestions.append(f"Consider filling {len(placeholders)} placeholder(s)")
        
        # Check for required elements based on section
        if section_name.lower() in ['headline', 'title']:
            if len(content.strip()) > 100:
                issues.append("Headline is too long")
                suggestions.append("Keep headlines under 100 characters")
        
        # Check for quotes in quote sections
        if 'quote' in section_name.lower() and 'said' not in content.lower():
            suggestions.append("Consider adding a quote from a key stakeholder")
        
        return json.dumps({
            "valid": len(issues) == 0,
            "issues": issues,
            "suggestions": suggestions,
            "placeholders_found": placeholders,
            "word_count": len(content.split()),
            "character_count": len(content)
        }, indent=2)


class ContentGenerationCrew:
    """CrewAI crew for content generation and quality assurance"""
    
    def __init__(self):
        self.config = get_config()
        self.mi = MongoInterface()
        
        # Initialize tools
        self.evidence_research_tool = EvidenceResearchTool()
        self.content_writer_tool = ContentWriterTool()
        self.quality_assurance_tool = QualityAssuranceTool()
        self.content_validator_tool = ContentValidatorTool()
        
        # Create agents
        self.evidence_researcher = Agent(
            role="Evidence Research Specialist",
            goal="Research and gather comprehensive evidence from MongoDB for press release content",
            backstory="""You are an expert researcher specializing in corporate communications and 
            press release content. You excel at finding relevant, accurate, and compelling evidence 
            from historical documents and databases to support press release content.""",
            tools=[self.evidence_research_tool],
            verbose=True,
            allow_delegation=False
        )
        
        self.content_writer = Agent(
            role="Content Writer",
            goal="Write high-quality, engaging press release content based on evidence and guidelines",
            backstory="""You are a skilled press release writer with extensive experience in corporate 
            communications. You excel at crafting compelling, accurate, and well-structured content 
            that effectively communicates key messages to target audiences.""",
            tools=[self.content_writer_tool],
            verbose=True,
            allow_delegation=False
        )
        
        self.quality_assurance_editor = Agent(
            role="Quality Assurance Editor",
            goal="Evaluate content quality and ensure it meets press release standards",
            backstory="""You are a meticulous editor specializing in press release quality assurance. 
            You have a keen eye for detail and excel at identifying areas for improvement in content 
            structure, clarity, and effectiveness.""",
            tools=[self.quality_assurance_tool],
            verbose=True,
            allow_delegation=False
        )
        
        self.content_validator = Agent(
            role="Content Validator",
            goal="Validate content against requirements and standards",
            backstory="""You are an expert in press release standards and requirements. You specialize 
            in ensuring content meets all necessary criteria for publication and effectiveness.""",
            tools=[self.content_validator_tool],
            verbose=True,
            allow_delegation=False
        )

    def create_crew(self) -> Crew:
        """Create and return the Content Generation Crew"""
        return Crew(
            agents=[
                self.evidence_researcher,
                self.content_writer,
                self.quality_assurance_editor,
                self.content_validator
            ],
            tasks=[
                self.research_evidence_task(),
                self.write_content_task(),
                self.quality_assurance_task(),
                self.validate_content_task()
            ],
            process=Process.sequential,
            verbose=True,
            memory=True,
            planning=True
        )

    def research_evidence_task(self) -> Task:
        """Task for researching evidence"""
        return Task(
            description="""Research and gather comprehensive evidence for the press release section. 
            Use MongoDB and Atlas Search to find relevant information including:
            - Historical data and metrics
            - Company information and context
            - Industry trends and benchmarks
            - Quotes and statements
            - Supporting details and facts
            
            Ensure evidence is accurate, relevant, and compelling.""",
            expected_output="""A JSON object containing:
            - evidence: List of relevant evidence items with sources
            - placeholders: List of placeholders for missing data
            - sufficient: Boolean indicating if evidence is sufficient
            - reason: Explanation of evidence quality
            - search_terms: Terms used in the search""",
            agent=self.evidence_researcher,
            tools=[self.evidence_research_tool]
        )

    def write_content_task(self) -> Task:
        """Task for writing content"""
        return Task(
            description="""Write high-quality press release content for the specified section based on:
            - Research evidence gathered
            - Tone and style guidelines
            - Phrase bank and terminology
            - Section requirements and purpose
            
            Ensure content is:
            - Accurate and factual
            - Engaging and compelling
            - Well-structured and clear
            - Appropriate for target audience
            - Consistent with company voice""",
            expected_output="""A JSON object containing:
            - draft_md: Complete markdown content for the section
            - used_refs: List of evidence references used
            - warnings: Any warnings or concerns
            - success: Boolean indicating success
            - word_count: Approximate word count""",
            agent=self.content_writer,
            tools=[self.content_writer_tool],
            context=[self.research_evidence_task()]
        )

    def quality_assurance_task(self) -> Task:
        """Task for quality assurance"""
        return Task(
            description="""Evaluate the written content for quality and effectiveness. Check for:
            - Content accuracy and completeness
            - Writing quality and clarity
            - Tone consistency
            - Structure and flow
            - Audience appropriateness
            - Press release standards compliance
            
            Provide detailed feedback and improvement suggestions.""",
            expected_output="""A JSON object containing:
            - accept: Boolean indicating if content is acceptable
            - reasons: List of reasons for acceptance/rejection
            - needs_revision: Boolean indicating if revision is needed
            - revision_instructions: Specific improvement suggestions
            - ask_finder_keywords: Additional search terms if needed
            - quality_score: Overall quality score (1-10)""",
            agent=self.quality_assurance_editor,
            tools=[self.quality_assurance_tool],
            context=[self.write_content_task()]
        )

    def validate_content_task(self) -> Task:
        """Task for content validation"""
        return Task(
            description="""Validate the content against press release requirements and standards. Check:
            - Length and format requirements
            - Required elements present
            - Placeholder usage appropriateness
            - Compliance with guidelines
            - Technical specifications
            
            Ensure content meets all necessary criteria for publication.""",
            expected_output="""A JSON object containing:
            - valid: Boolean indicating if content is valid
            - issues: List of validation issues found
            - suggestions: List of improvement suggestions
            - placeholders_found: List of placeholders in content
            - word_count: Final word count
            - character_count: Final character count""",
            agent=self.content_validator,
            tools=[self.content_validator_tool],
            context=[self.write_content_task(), self.quality_assurance_task()]
        )

    def generate_content(self, section_name: str, topic: str, tone: str, 
                        phrase_bank: List[str], company: str = "SISCO") -> Dict[str, Any]:
        """Generate content for a specific section"""
        crew = self.create_crew()
        
        # Set inputs for the crew
        inputs = {
            "section_name": section_name,
            "topic": topic,
            "tone": tone,
            "phrase_bank": phrase_bank,
            "company": company
        }
        
        # Execute the crew
        result = crew.kickoff(inputs=inputs)
        
        return {
            "success": True,
            "result": result,
            "crew_type": "content_generation",
            "section_name": section_name,
            "timestamp": datetime.now().isoformat()
        }


# Example usage
if __name__ == "__main__":
    # Test the Content Generation Crew
    crew = ContentGenerationCrew()
    
    # Generate content for a sample section
    result = crew.generate_content(
        section_name="Financial Highlights",
        topic="Q4 2024 Financial Results",
        tone="formal, factual, concise",
        phrase_bank=["strong performance", "record growth", "strategic initiatives"],
        company="SISCO"
    )
    
    print("Content Generation Result:")
    print(json.dumps(result, indent=2))

