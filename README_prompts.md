# Press Release Generation System - Prompts Configuration

This system now uses a YAML configuration file (`prompts_config.yaml`) to manage all prompts and instructions, making them much easier to modify and maintain.

## Quick Start

### 1. Modify Prompts
Edit `prompts_config.yaml` to change any prompts or instructions:

```yaml
section_creator:
  system_prompt: |
    You are an expert press-release section writer...
    # Modify this prompt as needed
```

### 2. Reload Configuration
The system automatically loads the configuration on startup. To reload during development:

```python
from config_loader import reload_config
reload_config()
```

## Configuration Structure

### Section Creator Agent
- `system_prompt`: Main system instructions for the section writer
- `user_prompt`: User prompt template with rules and guidelines
- `model`: LLM model to use (default: "gpt-4o-mini")
- `temperature`: Creativity level (0.0-1.0, default: 0.4)

### Section Evaluator Agent
- `system_prompt`: Instructions for evaluating section quality
- `model`: LLM model to use
- `temperature`: Evaluation strictness (default: 0.0)

### Evidence Approver Agent
- `system_prompt`: Instructions for validating evidence
- `user_prompt_template`: Template for evidence validation prompts
- `model`: LLM model to use
- `temperature`: Validation strictness (default: 0.0)

### Structure Generator
- `historical_analyzer`: Configuration for analyzing historical patterns
- `section_discovery`: Configuration for discovering sections
- `structure_proposer`: Configuration for proposing structures
- `template_generator`: Configuration for generating templates

### General Configuration
- `recursion_limits`: Maximum recursion for different graphs
- `evidence_search`: Parameters for evidence search
- `content_processing`: Content processing parameters

### Error Handling
- `fallback_placeholders`: Configuration for fallback behavior
- `content_cleaning`: Configuration for content cleaning

## Example Modifications

### Change Section Creator Temperature
```yaml
section_creator:
  temperature: 0.7  # More creative
```

### Modify System Prompt
```yaml
section_creator:
  system_prompt: |
    You are an expert press-release section writer specializing in comprehensive, detailed content.
    Write ONLY the requested SECTION in Markdown using the EVIDENCE provided.
    # Add your custom instructions here...
```

### Adjust Recursion Limits
```yaml
general:
  recursion_limits:
    style_graph: 15
    creator_graph: 8
    finder_graph: 3
```

### Change Evidence Search Parameters
```yaml
general:
  evidence_search:
    lookback_days: 365
    top_k: 10
    max_loops: 3
```

## Benefits

1. **Easy Modification**: Change prompts without touching code
2. **Version Control**: Track prompt changes in git
3. **A/B Testing**: Easily test different prompt variations
4. **Maintenance**: Centralized configuration management
5. **Documentation**: Prompts are self-documenting in YAML
6. **Flexibility**: Easy to add new configuration options

## File Structure

```
├── prompts_config.yaml      # Main configuration file
├── config_loader.py         # Configuration loader utility
├── press_release_writer.py  # Updated to use configuration
├── gradio_app.py           # Updated to use configuration
└── README_prompts.md       # This documentation
```

## Usage in Code

```python
from config_loader import get_config

# Get configuration
config = get_config()

# Get a specific prompt
system_prompt = config.get_prompt('section_creator', 'system_prompt')

# Get model configuration
model_config = config.get_model_config('section_creator')
model = model_config['model']
temperature = model_config['temperature']

# Get general configuration
recursion_limits = config.get_recursion_limits()
evidence_params = config.get_evidence_search_params()
```

## Best Practices

1. **Backup**: Always backup your configuration before making changes
2. **Test**: Test changes in a development environment first
3. **Document**: Document any custom modifications
4. **Version Control**: Commit configuration changes to git
5. **Incremental**: Make small, incremental changes rather than large overhauls

