# Press Release Generation System - Agent Architecture

## 🏗️ System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           PRESS RELEASE GENERATION SYSTEM                        │
│                                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐            │
│  │   GRADIO UI     │    │   YAML CONFIG   │    │   MONGODB       │            │
│  │   (5 Steps)     │    │   (Prompts)     │    │   (Data Store)  │            │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘            │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 🔄 Complete Workflow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                USER WORKFLOW                                    │
│                                                                                 │
│  Step 1: Data Upload → Step 2: Configuration → Step 3: Review →                │
│  Step 4: Generation → Step 5: Chat & Edit → Finalize                          │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 🤖 Agent Architecture

### 1. Structure Generation Phase
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           STRUCTURE GENERATION AGENTS                           │
│                                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐            │
│  │ TypeClassifier  │    │ SectionDiscovery│    │ StructureProposer│            │
│  │     Agent       │    │     Agent       │    │     Agent       │            │
│  │                 │    │                 │    │                 │            │
│  │ • Classifies    │    │ • Discovers     │    │ • Proposes      │            │
│  │   content type  │    │   sections      │    │   structure     │            │
│  │ • Determines    │    │ • Analyzes      │    │ • Creates       │            │
│  │   approach      │    │   patterns      │    │   templates     │            │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘            │
│           │                       │                       │                   │
│           └───────────────────────┼───────────────────────┘                   │
│                                   │                                           │
│  ┌─────────────────────────────────▼─────────────────────────────────┐        │
│  │                HistoricalStructureAnalyzerAgent                   │        │
│  │                                                                   │        │
│  │ • Analyzes past MongoDB documents                                 │        │
│  │ • Uses Atlas Search (default + vector indexes)                   │        │
│  │ • Extracts patterns, tone, and phrases                           │        │
│  │ • Builds phrase bank and style guidelines                        │        │
│  └───────────────────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2. Content Generation Phase
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           CONTENT GENERATION AGENTS                             │
│                                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐            │
│  │   Evidence      │    │   Section       │    │   Section       │            │
│  │   Approver      │    │   Creator       │    │   Evaluator     │            │
│  │   Agent         │    │   Agent         │    │   Agent         │            │
│  │                 │    │                 │    │                 │            │
│  │ • Validates     │    │ • Writes        │    │ • Evaluates     │            │
│  │   evidence      │    │   sections      │    │   quality       │            │
│  │ • Creates       │    │ • Uses evidence │    │ • Provides      │            │
│  │   placeholders  │    │ • Applies tone  │    │   feedback      │            │
│  │ • Manages       │    │ • Follows style │    │ • Suggests      │            │
│  │   fallbacks     │    │   guidelines    │    │   improvements  │            │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘            │
│           │                       │                       │                   │
│           └───────────────────────┼───────────────────────┘                   │
│                                   │                                           │
│  ┌─────────────────────────────────▼─────────────────────────────────┐        │
│  │                    Content Finder Graph                          │        │
│  │                                                                   │        │
│  │ • Searches MongoDB with Atlas Search                             │        │
│  │ • Uses vector similarity search                                  │        │
│  │ • Builds comprehensive queries                                   │        │
│  │ • Deduplicates evidence                                          │        │
│  └───────────────────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 3. Content Editing Phase
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            CONTENT EDITING AGENTS                               │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐            │
│  │                    ContentEditorAgent                          │            │
│  │                                                                 │            │
│  │ • Processes chat requests                                       │            │
│  │ • Analyzes request types (tone, structure, content, etc.)      │            │
│  │ • Modifies content intelligently                                │            │
│  │ • Validates changes                                             │            │
│  │ • Provides suggestions                                          │            │
│  │ • Manages placeholders                                          │            │
│  └─────────────────────────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 🔄 Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                DATA FLOW                                        │
│                                                                                 │
│  MongoDB → Atlas Search → Evidence → Agents → Content → Validation → Final     │
│     │           │           │         │         │          │           │        │
│     │           │           │         │         │          │           │        │
│  ┌──▼──┐    ┌───▼───┐   ┌───▼───┐  ┌──▼──┐  ┌──▼──┐   ┌───▼───┐  ┌───▼───┐   │
│  │Data │    │Search │   │Filter │  │LLM  │  │Mark │   │Quality│  │Press  │   │
│  │Store│    │Query  │   │Dedup  │  │Proc │  │down │   │Check  │  │Release│   │
│  └─────┘    └───────┘   └───────┘  └─────┘  └─────┘   └───────┘  └───────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 🎯 Agent Responsibilities

### Structure Generation Agents
| Agent | Purpose | Input | Output |
|-------|---------|-------|--------|
| **TypeClassifierAgent** | Classify content type | Topic, company | Content type classification |
| **SectionDiscoveryAgent** | Discover sections | Content type, patterns | Section list |
| **StructureProposerAgent** | Propose structure | Sections, patterns | Structure template |
| **HistoricalStructureAnalyzerAgent** | Analyze past documents | MongoDB queries | Patterns, tone, phrases |

### Content Generation Agents
| Agent | Purpose | Input | Output |
|-------|---------|-------|--------|
| **EvidenceApproverAgent** | Validate evidence | Evidence, section info | Approval/rejection + placeholders |
| **SectionCreatorAgent** | Write sections | Evidence, tone, style | Markdown content |
| **SectionFinalEvaluatorAgent** | Evaluate quality | Content, criteria | Quality assessment + feedback |

### Content Editing Agents
| Agent | Purpose | Input | Output |
|-------|---------|-------|--------|
| **ContentEditorAgent** | Edit content | User request, current content | Modified content + explanation |

## 🔧 Configuration System

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            YAML CONFIGURATION                                   │
│                                                                                 │
│  prompts_config.yaml                                                           │
│  ├── section_creator (system_prompt, user_prompt, model, temperature)          │
│  ├── section_evaluator (system_prompt, model, temperature)                     │
│  ├── evidence_approver (system_prompt, user_prompt_template, model)            │
│  ├── content_editor (system_prompt, user_prompt, model, temperature)           │
│  ├── type_classifier (system_prompt, model, temperature)                       │
│  ├── structure_generator                                                       │
│  │   ├── historical_analyzer (system_prompt, model, temperature)               │
│  │   ├── section_discovery (system_prompt, model, temperature)                 │
│  │   └── structure_proposer (system_prompt, model, temperature)                │
│  ├── content_finder                                                           │
│  │   └── section_terms (financial, operational, company_info, etc.)           │
│  └── general (recursion_limits, evidence_search, content_processing)          │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 🚀 LangGraph Workflows

### 1. Style Graph (Structure Generation)
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              STYLE GRAPH                                        │
│                                                                                 │
│  TypeClassifier → SectionDiscovery → StructureProposer → HistoricalAnalyzer    │
│       │                │                  │                    │               │
│       └────────────────┼──────────────────┼────────────────────┘               │
│                        │                  │                                    │
│                        ▼                  ▼                                    │
│                 [Structure Template with Tone, Phrase Bank, Sections]          │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2. Creator Graph (Content Generation)
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CREATOR GRAPH                                      │
│                                                                                 │
│  For each section:                                                             │
│                                                                                 │
│  EvidenceApprover → SectionCreator → SectionEvaluator                          │
│        │                │                │                                     │
│        ▼                ▼                ▼                                     │
│  [Approved] → [Draft Content] → [Final Content]                                │
│     │              │                │                                          │
│     └──────────────┼────────────────┘                                          │
│                    │                                                           │
│                    ▼                                                           │
│              [Assembled Press Release]                                         │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 3. Finder Graph (Evidence Gathering)
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FINDER GRAPH                                       │
│                                                                                 │
│  Query Building → Atlas Search → Evidence Filtering → Deduplication            │
│       │              │                │                    │                   │
│       ▼              ▼                ▼                    ▼                   │
│  [Search Terms] → [MongoDB] → [Raw Evidence] → [Clean Evidence]                │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 🎨 User Interface Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              GRADIO UI FLOW                                     │
│                                                                                 │
│  Step 1: Data Upload (Optional)                                                │
│  ├── Excel file upload                                                         │
│  └── Skip to AI generation                                                     │
│                                                                                 │
│  Step 2: Configuration                                                         │
│  ├── Title, description, tone                                                  │
│  ├── Company, topic (for AI)                                                   │
│  └── AI options                                                                │
│                                                                                 │
│  Step 3: Review & Generate                                                     │
│  ├── Review configuration                                                      │
│  └── Start generation                                                          │
│                                                                                 │
│  Step 4: Generation Progress                                                   │
│  ├── Real-time section updates                                                 │
│  ├── Progress tracking                                                         │
│  └── Final result display                                                      │
│                                                                                 │
│  Step 5: Chat & Edit                                                           │
│  ├── Chat with AI editor                                                       │
│  ├── Download placeholders CSV                                                 │
│  ├── Upload filled CSV                                                         │
│  └── Finalize press release                                                    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 🔄 Error Handling & Fallbacks

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            ERROR HANDLING                                       │
│                                                                                 │
│  Evidence Not Found → Placeholder Creation → Content Generation                │
│       │                      │                        │                        │
│       ▼                      ▼                        ▼                        │
│  [No Evidence] → [Dynamic Placeholders] → [Content with Placeholders]          │
│                                                                                 │
│  Agent Failures → Fallback Responses → User Guidance                           │
│       │                │                    │                                   │
│       ▼                ▼                    ▼                                   │
│  [Error] → [Graceful Degradation] → [Helpful Messages]                         │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 📊 Key Features

- **🤖 AI-Powered**: Uses GPT-4o-mini for all content generation and editing
- **📚 Data-Driven**: Learns from historical MongoDB documents
- **🔍 Smart Search**: Uses Atlas Search with vector similarity
- **💬 Interactive**: Real-time chat interface for content editing
- **📋 Placeholder Management**: CSV-based placeholder system
- **⚙️ Configurable**: YAML-based prompt and parameter management
- **🔄 Iterative**: Multi-step refinement with quality evaluation
- **🎯 Context-Aware**: Maintains conversation history and context

