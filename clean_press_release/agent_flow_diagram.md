# Agent Flow Diagram

This Mermaid diagram represents the actual agent flow in `gui_new.py` implementation.

```mermaid
flowchart TD
    subgraph "Main Orchestrator"
        PressReleaseAgent["PressReleaseAgent<br/>(Main Orchestrator)"]
    end
    
    subgraph "Structure Generation"
        TypeClassifierAgent["TypeClassifierAgent"]
        SectionDiscoveryAgent["SectionDiscoveryAgent"]
        HistoricalStructureAnalyzerAgent["HistoricalStructureAnalyzerAgent"]
        StructureProposerAgent["StructureProposerAgent"]
    end
    
    subgraph "Per-Section Processing"
        ContentFinderAgent["ContentFinderAgent"]
        EvidenceApproverAgent["EvidenceApproverAgent"]
        SectionCreatorAgent["SectionCreatorAgent"]
        SectionFinalEvaluatorAgent["SectionFinalEvaluatorAgent"]
        ContextForSectionAgent["ContextForSectionAgent<br/>(Excel Data)"]
    end
    
    subgraph "Final Processing"
        FinalCheckerAgent["FinalCheckerAgent<br/>(Quality Check)"]
        FinalProcessingChainAgent["FinalProcessingChainAgent<br/>(4-Stage Processing)"]
    end
    
    subgraph "Processing Chain Details"
        PlaceholderCleaner["Placeholder Cleaner"]
        FactExtractor["Fact Extractor"]
        FactChecker["Fact Checker"]
        FinalFormatter["Final Formatter"]
    end
    
    %% Main flow
    PressReleaseAgent --> TypeClassifierAgent
    PressReleaseAgent --> SectionDiscoveryAgent
    PressReleaseAgent --> HistoricalStructureAnalyzerAgent
    PressReleaseAgent --> StructureProposerAgent
    
    %% Per-section loop
    PressReleaseAgent --> ContentFinderAgent
    ContentFinderAgent --> EvidenceApproverAgent
    EvidenceApproverAgent --> SectionCreatorAgent
    SectionCreatorAgent --> SectionFinalEvaluatorAgent
    SectionFinalEvaluatorAgent --> SectionCreatorAgent
    ContextForSectionAgent --> SectionCreatorAgent
    
    %% Final processing
    PressReleaseAgent --> FinalCheckerAgent
    PressReleaseAgent --> FinalProcessingChainAgent
    FinalProcessingChainAgent --> PlaceholderCleaner
    PlaceholderCleaner --> FactExtractor
    FactExtractor --> FactChecker
    FactChecker --> FinalFormatter
    
    %% Styling
    style PressReleaseAgent fill:#ff9800,color:#fff
    style TypeClassifierAgent fill:#4caf50,color:#fff
    style SectionDiscoveryAgent fill:#4caf50,color:#fff
    style HistoricalStructureAnalyzerAgent fill:#4caf50,color:#fff
    style StructureProposerAgent fill:#4caf50,color:#fff
    style ContentFinderAgent fill:#2196f3,color:#fff
    style EvidenceApproverAgent fill:#9c27b0,color:#fff
    style SectionCreatorAgent fill:#f44336,color:#fff
    style SectionFinalEvaluatorAgent fill:#ff5722,color:#fff
    style ContextForSectionAgent fill:#795548,color:#fff
    style FinalCheckerAgent fill:#607d8b,color:#fff
    style FinalProcessingChainAgent fill:#3f51b5,color:#fff
    style PlaceholderCleaner fill:#e91e63,color:#fff
    style FactExtractor fill:#e91e63,color:#fff
    style FactChecker fill:#e91e63,color:#fff
    style FinalFormatter fill:#e91e63,color:#fff
```

## Key Components

### Main Orchestrator
- **PressReleaseAgent**: Central control point for the entire process

### Structure Generation
- **TypeClassifierAgent**: Classifies the type of press release
- **SectionDiscoveryAgent**: Discovers relevant sections from historical data
- **HistoricalStructureAnalyzerAgent**: Analyzes successful structure patterns
- **StructureProposerAgent**: Proposes final template and structure

### Per-Section Processing
- **ContentFinderAgent**: Retrieves evidence for each section
- **EvidenceApproverAgent**: Validates evidence sufficiency
- **SectionCreatorAgent**: Creates content using evidence
- **SectionFinalEvaluatorAgent**: Evaluates and can send back for revision
- **ContextForSectionAgent**: Integrates Excel data as evidence

### Final Processing
- **FinalCheckerAgent**: Quality check of final content
- **FinalProcessingChainAgent**: 4-stage processing chain
  - **Placeholder Cleaner**: Ensures placeholder consistency
  - **Fact Extractor**: Extracts factual claims
  - **Fact Checker**: Validates facts against data
  - **Final Formatter**: Final formatting and cleanup

## Flow Description

1. **Structure Generation**: Multiple agents work in parallel to analyze and propose structure
2. **Per-Section Processing**: Each section goes through finder → creator → evaluator loop with Excel data integration
3. **Final Processing**: Quality check and 4-stage processing chain
4. **Feedback Loops**: Section evaluator can send back to section creator for revisions

This diagram accurately represents the complex agent interactions in the `gui_new.py` implementation.


