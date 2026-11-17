"""
Simple test for CrewAI integration
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

def test_basic_crewai():
    """Test basic CrewAI functionality"""
    try:
        print("🔍 Testing basic CrewAI functionality...")
        
        # Test CrewAI import
        from crewai import Crew, Agent, Task, Process
        print("✅ CrewAI basic imports successful")
        
        # Test our custom crews
        from crewai_structure_crew import StructureAnalysisCrew
        print("✅ StructureAnalysisCrew imported")
        
        from crewai_content_crew import ContentGenerationCrew
        print("✅ ContentGenerationCrew imported")
        
        from crewai_editing_crew import ContentEditingCrew
        print("✅ ContentEditingCrew imported")
        
        from crewai_research_crew import ResearchDataCrew
        print("✅ ResearchDataCrew imported")
        
        # Test initialization
        structure_crew = StructureAnalysisCrew()
        print("✅ StructureAnalysisCrew initialized")
        
        content_crew = ContentGenerationCrew()
        print("✅ ContentGenerationCrew initialized")
        
        editing_crew = ContentEditingCrew()
        print("✅ ContentEditingCrew initialized")
        
        research_crew = ResearchDataCrew()
        print("✅ ResearchDataCrew initialized")
        
        # Test Gradio integration
        from gradio_app import PressReleaseAgent
        agent = PressReleaseAgent()
        print("✅ PressReleaseAgent with CrewAI initialized")
        
        print("\n🎉 All basic tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_generation():
    """Test simple press release generation"""
    try:
        print("\n🔍 Testing simple generation...")
        
        from gradio_app import PressReleaseAgent
        agent = PressReleaseAgent()
        
        # Test with a simple topic
        result = agent.generate_press_release_with_crewai(
            topic="Test Press Release",
            company="Test Company"
        )
        
        if result["success"]:
            print("✅ Simple generation successful")
            print(f"   - Content length: {len(result['content'])} characters")
            print(f"   - Crew type: {result.get('crew_type', 'unknown')}")
            return True
        else:
            print(f"❌ Simple generation failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Generation error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Simple CrewAI Tests\n")
    
    # Test basic functionality
    basic_success = test_basic_crewai()
    
    if basic_success:
        # Test simple generation
        generation_success = test_simple_generation()
        
        if generation_success:
            print("\n🎉 All tests passed! CrewAI integration is working.")
        else:
            print("\n⚠️ Basic tests passed but generation failed.")
    else:
        print("\n❌ Basic tests failed.")
    
    sys.exit(0 if basic_success else 1)

