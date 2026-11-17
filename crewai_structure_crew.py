"""
CrewAI Structure Analysis Crew

This module contains the CrewAI implementation of the structure generation agents
for press release analysis and template creation.
"""

from crewai import Crew, Agent, Task, Process
from crewai.tools import BaseTool
from typing import Dict, List, Any, Optional
import json
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

from base_agent import BaseAgent
from mongo_interface import MongoInterface
from states import StyleState
from config_loader import get_config


class ContentTypeAnalysisTool(BaseTool):
    """Tool for analyzing and classifying press release content type"""
    
    name: str = "content_type_analyzer"
    description: str = "Analyzes press release topics and classifies them into appropriate content types"
    
    def _run(self, topic: str, company: str = "SISCO") -> str:
        """Analyze content type based on topic and company"""
        config = get_config()
        model_config = config.get_model_config('type_classifier')
        
        # Use the existing TypeClassifierAgent logic
        from press_release_structure_generator import TypeClassifierAgent
        agent = TypeClassifierAgent()
        
        # Create a mock state for the agent
        state = {
            "topic": topic,
            "company": company,
            "buckets": [
                "Financial & Capital",
                "Deals & Corporate Actions", 
                "Operations, Products & Projects",
                "Governance & People",
                "Regulatory, Compliance & Legal",
                "ESG, Sustainability & Community"
            ]
        }
        
        result = agent.run(state)
        return json.dumps(result, indent=2)


class SectionDiscoveryTool(BaseTool):
    """Tool for discovering and recommending sections for press releases"""
    
    name: str = "section_discovery"
    description: str = "Discovers and recommends sections for press releases based on content type"
    
    def _run(self, content_type: str, topic: str, company: str = "SISCO") -> str:
        """Discover sections based on content type and topic"""
        config = get_config()
        model_config = config.get_model_config('structure_generator.section_discovery')
        
        # Use the existing SectionDiscoveryAgent logic
        from press_release_structure_generator import SectionDiscoveryAgent
        agent = SectionDiscoveryAgent()
        
        state = {
            "content_type": content_type,
            "topic": topic,
            "company": company,
            "buckets": [
                "Financial & Capital",
                "Deals & Corporate Actions",
                "Operations, Products & Projects", 
                "Governance & People",
                "Regulatory, Compliance & Legal",
                "ESG, Sustainability & Community"
            ]
        }
        
        result = agent.run(state)
        return json.dumps(result, indent=2)


class StructureDesignTool(BaseTool):
    """Tool for designing press release structure and templates"""
    
    name: str = "structure_designer"
    description: str = "Designs optimal press release structure and templates"
    
    def _run(self, sections: List[Dict], content_type: str, topic: str) -> str:
        """Design structure based on sections and content type"""
        config = get_config()
        model_config = config.get_model_config('structure_generator.structure_proposer')
        
        # Use the existing StructureProposerAgent logic
        from press_release_structure_generator import StructureProposerAgent
        agent = StructureProposerAgent()
        
        state = {
            "sections": sections,
            "content_type": content_type,
            "topic": topic,
            "company": "SISCO"
        }
        
        result = agent.run(state)
        return json.dumps(result, indent=2)


class HistoricalAnalysisTool(BaseTool):
    """Tool for analyzing historical patterns and extracting best practices"""
    
    name: str = "historical_analyzer"
    description: str = "Analyzes historical press release patterns and extracts best practices"
    
    def _run(self, content_type: str, company: str = "SISCO") -> str:
        """Analyze historical patterns for the given content type"""
        config = get_config()
        model_config = config.get_model_config('structure_generator.historical_analyzer')
        
        # Use the existing HistoricalStructureAnalyzerAgent logic
        from press_release_structure_generator import HistoricalStructureAnalyzerAgent
        agent = HistoricalStructureAnalyzerAgent()
        
        state = {
            "content_type": content_type,
            "company": company,
            "lookback_days": 1080  # 3 years
        }
        
        result = agent.run(state)
        return json.dumps(result, indent=2)


class StructureAnalysisCrew:
    """CrewAI crew for structure analysis and template generation"""
    
    def __init__(self):
        self.config = get_config()
        self.mi = MongoInterface()
        
        # Initialize tools
        self.content_type_tool = ContentTypeAnalysisTool()
        self.section_discovery_tool = SectionDiscoveryTool()
        self.structure_design_tool = StructureDesignTool()
        self.historical_analysis_tool = HistoricalAnalysisTool()
        
        # Create agents
        self.content_type_analyst = Agent(
            role="Content Type Analyst",
            goal="Analyze and classify press release content type based on topic and company context",
            backstory="""You are an expert in press release content classification with deep knowledge 
            of different types of corporate communications. You excel at analyzing topics and determining 
            the most appropriate content type for press releases, considering factors like audience, 
            purpose, and industry standards.""",
            tools=[self.content_type_tool],
            verbose=True,
            allow_delegation=False
        )
        
        self.section_discovery_specialist = Agent(
            role="Section Discovery Specialist",
            goal="Discover and recommend the most effective sections for press releases based on content type",
            backstory="""You are a specialist in press release structure and content organization. 
            You have extensive experience in determining which sections are most effective for different 
            types of press releases, considering audience engagement and information hierarchy.""",
            tools=[self.section_discovery_tool],
            verbose=True,
            allow_delegation=False
        )
        
        self.structure_architect = Agent(
            role="Structure Architect", 
            goal="Design optimal press release structure and templates based on sections and historical patterns",
            backstory="""You are an expert in press release architecture and template design. You excel 
            at creating comprehensive structure templates that include tone guidelines, phrase banks, 
            and detailed section specifications for maximum effectiveness.""",
            tools=[self.structure_design_tool],
            verbose=True,
            allow_delegation=False
        )
        
        self.historical_analyst = Agent(
            role="Historical Pattern Analyst",
            goal="Analyze historical press release patterns and extract best practices for content type",
            backstory="""You are an expert in analyzing historical data and extracting actionable insights. 
            You specialize in identifying successful patterns, tone preferences, and structural elements 
            from past press releases to inform current template creation.""",
            tools=[self.historical_analysis_tool],
            verbose=True,
            allow_delegation=False
        )

    def create_crew(self) -> Crew:
        """Create and return the Structure Analysis Crew"""
        return Crew(
            agents=[
                self.content_type_analyst,
                self.section_discovery_specialist,
                self.structure_architect,
                self.historical_analyst
            ],
            tasks=[
                self.analyze_content_type_task(),
                self.discover_sections_task(),
                self.analyze_historical_patterns_task(),
                self.design_structure_task()
            ],
            process=Process.sequential,
            verbose=True,
            memory=True,
            planning=True
        )

    def analyze_content_type_task(self) -> Task:
        """Task for analyzing content type"""
        return Task(
            description="""Analyze the provided topic and company to determine the most appropriate 
            content type for the press release. Consider factors like:
            - The nature of the announcement
            - Target audience
            - Industry context
            - Communication purpose
            
            Return a detailed classification with reasoning and recommendations.""",
            expected_output="""A JSON object containing:
            - content_type: The classified content type
            - confidence: Confidence level (0-1)
            - reasoning: Detailed explanation of the classification
            - recommendations: Suggestions for content approach
            - target_audience: Primary and secondary audiences""",
            agent=self.content_type_analyst,
            tools=[self.content_type_tool]
        )

    def discover_sections_task(self) -> Task:
        """Task for discovering sections"""
        return Task(
            description="""Based on the content type analysis, discover and recommend the most 
            effective sections for this press release. Consider:
            - Industry best practices
            - Audience expectations
            - Information hierarchy
            - Engagement factors
            
            Provide detailed section recommendations with descriptions and importance rankings.""",
            expected_output="""A JSON object containing:
            - sections: List of recommended sections with:
              - name: Section name
              - notes: Description and purpose
              - importance: Priority level (1-5)
              - order: Suggested sequence
            - rationale: Explanation for section choices
            - optional_sections: Additional sections to consider""",
            agent=self.section_discovery_specialist,
            tools=[self.section_discovery_tool],
            context=[self.analyze_content_type_task()]
        )

    def analyze_historical_patterns_task(self) -> Task:
        """Task for analyzing historical patterns"""
        return Task(
            description="""Analyze historical press release patterns for the identified content type. 
            Extract insights about:
            - Successful structural patterns
            - Tone and style preferences
            - Common phrases and terminology
            - Section effectiveness
            - Audience engagement factors
            
            Focus on patterns that have proven successful in similar contexts.""",
            expected_output="""A JSON object containing:
            - patterns: Identified successful patterns
            - tone_preferences: Historical tone analysis
            - phrase_bank: Common effective phrases
            - structural_insights: Key structural findings
            - best_practices: Extracted best practices
            - sample_count: Number of documents analyzed""",
            agent=self.historical_analyst,
            tools=[self.historical_analysis_tool],
            context=[self.analyze_content_type_task()]
        )

    def design_structure_task(self) -> Task:
        """Task for designing the final structure"""
        return Task(
            description="""Design the complete press release structure template based on:
            - Content type analysis
            - Section recommendations
            - Historical pattern insights
            
            Create a comprehensive template that includes:
            - Detailed section specifications
            - Tone guidelines
            - Phrase bank
            - Boilerplate content
            - Style recommendations
            
            Ensure the template is optimized for the specific content type and audience.""",
            expected_output="""A JSON object containing:
            - template: Complete structure template with:
              - sections: Detailed section specifications
              - tone: Tone guidelines and examples
              - phrase_bank: Curated phrase collection
              - boilerplate: Company boilerplate
              - style_guide: Writing style recommendations
            - rationale: Explanation of design decisions
            - customization_notes: Areas for customization
            - quality_metrics: Success indicators""",
            agent=self.structure_architect,
            tools=[self.structure_design_tool],
            context=[
                self.analyze_content_type_task(),
                self.discover_sections_task(),
                self.analyze_historical_patterns_task()
            ]
        )

    def run_analysis(self, topic: str, company: str = "SISCO") -> Dict[str, Any]:
        """Run the complete structure analysis process"""
        crew = self.create_crew()
        
        # Set inputs for the crew
        inputs = {
            "topic": topic,
            "company": company
        }
        
        # Execute the crew
        result = crew.kickoff(inputs=inputs)
        
        return {
            "success": True,
            "result": result,
            "crew_type": "structure_analysis",
            "timestamp": datetime.now().isoformat()
        }


# Example usage
if __name__ == "__main__":
    # Test the Structure Analysis Crew
    crew = StructureAnalysisCrew()
    
    # Run analysis for a sample topic
    result = crew.run_analysis(
        topic="Q4 2024 Financial Results",
        company="SISCO"
    )
    
    print("Structure Analysis Result:")
    print(json.dumps(result, indent=2))

