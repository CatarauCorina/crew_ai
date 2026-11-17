"""
Test script for CrewAI integration with Gradio app
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

def test_crewai_imports():
    """Test that all CrewAI modules can be imported"""
    try:
        print("🔍 Testing CrewAI imports...")
        
        # Test individual crew imports
        from crewai_structure_crew import StructureAnalysisCrew
        print("✅ StructureAnalysisCrew imported successfully")
        
        from crewai_content_crew import ContentGenerationCrew
        print("✅ ContentGenerationCrew imported successfully")
        
        from crewai_editing_crew import ContentEditingCrew
        print("✅ ContentEditingCrew imported successfully")
        
        from crewai_research_crew import ResearchDataCrew
        print("✅ ResearchDataCrew imported successfully")
        
        from crewai_flow import PressReleaseCrewAI
        print("✅ PressReleaseCrewAI imported successfully")
        
        # Test Gradio app import
        from gradio_app import PressReleaseAgent
        print("✅ PressReleaseAgent imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import error: {str(e)}")
        return False

def test_crewai_initialization():
    """Test that CrewAI agents can be initialized"""
    try:
        print("\n🔍 Testing CrewAI initialization...")
        
        # Test individual crews
        structure_crew = StructureAnalysisCrew()
        print("✅ StructureAnalysisCrew initialized")
        
        content_crew = ContentGenerationCrew()
        print("✅ ContentGenerationCrew initialized")
        
        editing_crew = ContentEditingCrew()
        print("✅ ContentEditingCrew initialized")
        
        research_crew = ResearchDataCrew()
        print("✅ ResearchDataCrew initialized")
        
        # Test main flow
        crewai_agent = PressReleaseCrewAI()
        print("✅ PressReleaseCrewAI initialized")
        
        # Test Gradio agent with CrewAI
        from gradio_app import PressReleaseAgent
        agent = PressReleaseAgent()
        print("✅ PressReleaseAgent with CrewAI initialized")
        
        return True
        
    except Exception as e:
        print(f"❌ Initialization error: {str(e)}")
        return False

def test_crewai_generation():
    """Test CrewAI press release generation"""
    try:
        print("\n🔍 Testing CrewAI generation...")
        
        from gradio_app import PressReleaseAgent
        agent = PressReleaseAgent()
        
        # Test CrewAI generation with progress callback
        def progress_callback(message, percentage):
            print(f"   Progress: {percentage}% - {message}")
        
        result = agent.generate_press_release_with_crewai(
            topic="Q4 2024 Financial Results",
            company="SISCO",
            progress_callback=progress_callback
        )
        
        if result["success"]:
            print("✅ CrewAI generation successful")
            print(f"   - Content length: {len(result['content'])} characters")
            print(f"   - Crew type: {result.get('crew_type', 'unknown')}")
            print(f"   - Content preview: {result['content'][:100]}...")
            return True
        else:
            print(f"❌ CrewAI generation failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Generation error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_gradio_integration():
    """Test that Gradio app can be created with CrewAI"""
    try:
        print("\n🔍 Testing Gradio integration...")
        
        from gradio_app import create_app
        app = create_app()
        print("✅ Gradio app created successfully with CrewAI integration")
        
        # Test that the app has the expected components
        if hasattr(app, 'blocks'):
            print("✅ Gradio app has blocks structure")
        
        return True
        
    except Exception as e:
        print(f"❌ Gradio integration error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting CrewAI Integration Tests\n")
    
    tests = [
        ("Import Test", test_crewai_imports),
        ("Initialization Test", test_crewai_initialization),
        ("Generation Test", test_crewai_generation),
        ("Gradio Integration Test", test_gradio_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print('='*50)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! CrewAI integration is working correctly.")
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
