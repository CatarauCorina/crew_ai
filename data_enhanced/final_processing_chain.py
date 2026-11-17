"""
Final Processing Chain Agent
Handles the 4-stage final processing of press release documents:
1. Placeholder Cleaner
2. Fact Extractor  
3. Fact Verifier
4. Final Formatter
"""

import json
import tempfile
import os
from typing import Dict, Any
from base_agent import BaseAgent
from config_loader import ConfigLoader
from mongo_interface import MongoInterface

try:
    import pypandoc
    PYPANDOC_AVAILABLE = True
except ImportError:
    PYPANDOC_AVAILABLE = False


class FinalProcessingChainAgent(BaseAgent):
    """Agent that processes documents through a 4-stage final processing chain"""
    
    def __init__(self):
        super().__init__()
        self.config_loader = ConfigLoader()
        self.mongo_interface = MongoInterface()
    
    def _convert_markdown_to_document(self, markdown_content: str) -> str:
        """Convert markdown content to clean document format using pypandoc"""
        try:
            # Check if pypandoc is available
            if not PYPANDOC_AVAILABLE:
                print("pypandoc not available, using fallback")
                return self._clean_markdown_fallback(markdown_content)
            
            # Convert markdown to plain text using pypandoc
            converted_content = pypandoc.convert_text(
                markdown_content,
                'plain',
                format='markdown',
                extra_args=[
                    '--wrap=none',
                    '--columns=1000'
                ]
            )
            
            return converted_content.strip()
                    
        except Exception as e:
            print(f"Error in pypandoc conversion: {e}")
            # Fallback to basic markdown cleaning
            return self._clean_markdown_fallback(markdown_content)
    
    def _clean_markdown_fallback(self, markdown_content: str) -> str:
        """Fallback method to clean markdown when pandoc is not available"""
        lines = markdown_content.strip().split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                cleaned_lines.append('')
                continue
                
            # Handle headers - convert to clean format with proper spacing
            if line.startswith('### '):
                # Level 3 header
                header_text = line[4:].strip()
                cleaned_lines.append('')
                cleaned_lines.append(header_text)
                cleaned_lines.append('')
            elif line.startswith('## '):
                # Level 2 header  
                header_text = line[3:].strip()
                cleaned_lines.append('')
                cleaned_lines.append(header_text)
                cleaned_lines.append('')
            elif line.startswith('# '):
                # Level 1 header
                header_text = line[2:].strip()
                cleaned_lines.append('')
                cleaned_lines.append(header_text)
                cleaned_lines.append('')
            elif line.startswith('- ') or line.startswith('* '):
                # Convert markdown list items to proper bullet points
                list_text = line[2:].strip()
                cleaned_lines.append(f'• {list_text}')
            elif line.startswith('1. ') or line.startswith('2. ') or line.startswith('3. ') or line.startswith('4. ') or line.startswith('5. '):
                # Keep numbered lists as-is
                cleaned_lines.append(line)
            else:
                # Regular paragraph text
                # Convert bold/italic markers
                text = line
                text = text.replace('**', '')  # Remove bold markers
                text = text.replace('*', '')   # Remove italic markers
                cleaned_lines.append(text)
        
        # Clean up multiple consecutive empty lines
        final_lines = []
        prev_empty = False
        for line in cleaned_lines:
            if line == '':
                if not prev_empty:
                    final_lines.append('')
                prev_empty = True
            else:
                final_lines.append(line)
                prev_empty = False
        
        return '\n'.join(final_lines)
    
    def run(self, state):
        """Process document through the 4-stage final processing chain"""
        try:
            # Extract content from state
            title = state.get("title", "")
            company = state.get("company", "")
            topic = state.get("topic", "")
            content = state.get("final_content", "")
            excel_data = state.get("excel_data", {})
            
            # Get processing chain configuration
            chain_config = self.config_loader.get_final_processing_chain_config()
            
            # Stage 1: Placeholder Cleaner
            if state.get("progress_callback"):
                state["progress_callback"]("🧹 Stage 1: Cleaning placeholders and repetitions...", 98)
            
            cleaned_content = self._run_placeholder_cleaner(
                content, title, company, chain_config["placeholder_cleaner"]
            )
            
            # Stage 2: Fact Extractor
            if state.get("progress_callback"):
                state["progress_callback"]("🔍 Stage 2: Extracting facts from document...", 98.5)
            
            extracted_facts = self._run_fact_extractor(
                cleaned_content, title, company, topic, chain_config["fact_extractor"]
            )
            
            # Stage 3: Fact Verifier
            if state.get("progress_callback"):
                state["progress_callback"]("✅ Stage 3: Verifying facts against data sources...", 99)
            
            verified_content = self._run_fact_verifier(
                cleaned_content, extracted_facts, title, company, topic, 
                excel_data, chain_config["fact_verifier"]
            )
            
            # Stage 4: Final Formatter
            if state.get("progress_callback"):
                state["progress_callback"]("📝 Stage 4: Final formatting and validation...", 99.5)
            
            final_content = self._run_final_formatter(
                verified_content, title, company, chain_config["final_formatter"]
            )
            
            # Update state with final processed content
            state["final_processed_content"] = final_content
            state["processing_chain_results"] = {
                "cleaned_content": cleaned_content,
                "extracted_facts": extracted_facts,
                "verified_content": verified_content,
                "final_content": final_content
            }
            
            return state
            
        except Exception as e:
            print(f"Error in FinalProcessingChainAgent: {e}")
            # Fallback: return original content
            state["final_processed_content"] = state.get("final_content", "")
            state["processing_chain_results"] = {
                "error": str(e),
                "fallback_used": True
            }
            return state
    
    def _run_placeholder_cleaner(self, content: str, title: str, company: str, config: Dict[str, Any]) -> str:
        """Stage 1: Clean placeholders and remove repetitions"""
        try:
            # Handle both direct config and nested config structures
            if "user_prompt_template" in config:
                user_prompt = config["user_prompt_template"].format(
                    title=title,
                    company=company,
                    content=content
                )
            else:
                # Fallback if config structure is different
                user_prompt = f"Clean this press release document for placeholder consistency and repetitions:\n\nTITLE: {title}\nCOMPANY: {company}\n\nDOCUMENT:\n{content}\n\nReturn the cleaned document with consistent placeholders and no repetitions."
            
            response = self.llm_inference(
                messages=[
                    {"role": "system", "content": config.get("system_prompt", "You are a document cleaner that ensures placeholder consistency and removes repetitions.")},
                    {"role": "user", "content": user_prompt}
                ],
                model=config.get("model", "gpt-4o-mini"),
                temperature=config.get("temperature", 0.1)
            )
            
            # Convert markdown to clean document format using pandoc
            cleaned_response = self._convert_markdown_to_document(response.strip())
            
            return cleaned_response
            
        except Exception as e:
            print(f"Error in placeholder cleaner: {e}")
            return content
    
    def _run_fact_extractor(self, content: str, title: str, company: str, topic: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 2: Extract facts from document"""
        try:
            # Handle both direct config and nested config structures
            if "user_prompt_template" in config:
                user_prompt = config["user_prompt_template"].format(
                    title=title,
                    company=company,
                    topic=topic,
                    content=content
                )
            else:
                # Fallback if config structure is different
                user_prompt = f"Extract all factual claims from this press release:\n\nTITLE: {title}\nCOMPANY: {company}\nTOPIC: {topic}\n\nDOCUMENT:\n{content}\n\nReturn JSON with extracted facts."
            
            response = self.llm_inference(
                messages=[
                    {"role": "system", "content": config.get("system_prompt", "You are a fact extraction agent that identifies specific factual claims from documents.")},
                    {"role": "user", "content": user_prompt}
                ],
                model=config.get("model", "gpt-4o-mini"),
                temperature=config.get("temperature", 0.1)
            )
            
            # Parse JSON response
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {"extracted_facts": [], "fact_categories": {}, "verification_priority": "medium"}
                
        except Exception as e:
            print(f"Error in fact extractor: {e}")
            return {"extracted_facts": [], "fact_categories": {}, "verification_priority": "medium"}
    
    def _run_fact_verifier(self, content: str, extracted_facts: Dict[str, Any], title: str, 
                          company: str, topic: str, excel_data: Dict[str, Any], config: Dict[str, Any]) -> str:
        """Stage 3: Verify facts and replace incorrect ones with placeholders"""
        try:
            # Get MongoDB data
            mongo_data = self._get_mongo_data_for_fact_checking(company, topic)
            excel_summary = self._prepare_excel_data_for_fact_checking(excel_data)
            
            # Handle both direct config and nested config structures
            if "user_prompt_template" in config:
                user_prompt = config["user_prompt_template"].format(
                    title=title,
                    company=company,
                    topic=topic,
                    content=content,
                    extracted_facts=json.dumps(extracted_facts, indent=2, default=str),
                    excel_data=excel_summary,
                    mongo_data=json.dumps(mongo_data, indent=2, default=str)
                )
            else:
                # Fallback if config structure is different
                user_prompt = f"Verify these facts against available data:\n\nTITLE: {title}\nCOMPANY: {company}\nTOPIC: {topic}\n\nDOCUMENT:\n{content}\n\nEXTRACTED FACTS:\n{json.dumps(extracted_facts, indent=2, default=str)}\n\nMONGO DATA:\n{json.dumps(mongo_data, indent=2, default=str)}\n\nEXCEL DATA:\n{excel_summary}\n\nReturn JSON with verification results."
            
            response = self.llm_inference(
                messages=[
                    {"role": "system", "content": config.get("system_prompt", "You are a document processing agent.")},
                    {"role": "user", "content": user_prompt}
                ],
                model=config.get("model", "gpt-4o-mini"),
                temperature=config.get("temperature", 0.1)
            )
            
            # Parse JSON response
            try:
                result = json.loads(response)
                verified_doc = result.get("verified_document", content)
                
                # Convert markdown to clean document format using pandoc
                cleaned_doc = self._convert_markdown_to_document(verified_doc.strip())
                
                return cleaned_doc
            except json.JSONDecodeError:
                return content
                
        except Exception as e:
            print(f"Error in fact verifier: {e}")
            return content
    
    def _run_final_formatter(self, content: str, title: str, company: str, config: Dict[str, Any]) -> str:
        """Stage 4: Final formatting and validation"""
        try:
            # Handle both direct config and nested config structures
            if "user_prompt_template" in config:
                user_prompt = config["user_prompt_template"].format(
                    title=title,
                    company=company,
                    content=content
                )
            else:
                # Fallback if config structure is different
                user_prompt = f"Format this press release for final publication:\n\nTITLE: {title}\nCOMPANY: {company}\n\nDOCUMENT:\n{content}\n\nReturn the final formatted document."
            
            response = self.llm_inference(
                messages=[
                    {"role": "system", "content": config.get("system_prompt", "You are a document processing agent.")},
                    {"role": "user", "content": user_prompt}
                ],
                model=config.get("model", "gpt-4o-mini"),
                temperature=config.get("temperature", 0.1)
            )
            
            # Convert markdown to clean document format using pandoc
            cleaned_response = self._convert_markdown_to_document(response.strip())
            
            return cleaned_response
            
        except Exception as e:
            print(f"Error in final formatter: {e}")
            return content
    
    def _get_mongo_data_for_fact_checking(self, company: str, topic: str) -> Dict[str, Any]:
        """Get relevant MongoDB data for fact checking"""
        try:
            mongo_data = {
                "company_info": {},
                "financial_data": [],
                "recent_releases": [],
                "company_hierarchy": {}
            }
            
            # Get company information
            try:
                company_docs = list(self.mongo_interface.db.Companies.find({"Name": {"$regex": company, "$options": "i"}}))
                if company_docs:
                    mongo_data["company_info"] = company_docs[0]
            except Exception as e:
                print(f"Error fetching company info: {e}")
            
            # Get recent press releases for context
            try:
                recent_releases = list(self.mongo_interface.db.PressRelease.find(
                    {"ClientID": {"$regex": company, "$options": "i"}}
                ).sort("CreatedAt", -1).limit(5))
                mongo_data["recent_releases"] = recent_releases
            except Exception as e:
                print(f"Error fetching recent releases: {e}")
            
            return mongo_data
            
        except Exception as e:
            print(f"Error getting MongoDB data: {e}")
            return {"company_info": {}, "financial_data": [], "recent_releases": [], "company_hierarchy": {}}
    
    def _prepare_excel_data_for_fact_checking(self, excel_data: Dict[str, Any]) -> str:
        """Prepare Excel data summary for fact checking with detailed financial data"""
        if not excel_data.get('success', False):
            return "No Excel data available"
        
        summary_parts = []
        
        # Add consolidated metrics with detailed information
        if excel_data.get('consolidated_metrics'):
            summary_parts.append("EXCEL FINANCIAL DATA (AUTHORITATIVE):")
            for metric in excel_data['consolidated_metrics']:
                summary_parts.append(f"- {metric['name']}: {metric['value']} {metric.get('unit', '')}")
                if metric.get('trend'):
                    summary_parts.append(f"  Trend: {metric['trend']}")
                if metric.get('significance'):
                    summary_parts.append(f"  Note: {metric['significance']}")
        
        # Add raw data sample with more context
        if excel_data.get('raw_data_sample'):
            summary_parts.append("\nEXCEL RAW DATA (VERIFIED VALUES):")
            for item in excel_data['raw_data_sample'][:10]:  # Show more items
                if isinstance(item, dict):
                    # Format dictionary items nicely
                    item_str = ", ".join([f"{k}: {v}" for k, v in item.items()])
                    summary_parts.append(f"- {item_str}")
                else:
                    summary_parts.append(f"- {item}")
        
        # Add insights with context
        if excel_data.get('insights'):
            summary_parts.append("\nEXCEL-DERIVED INSIGHTS:")
            for insight in excel_data['insights']:
                summary_parts.append(f"- {insight}")
        
        # Add company hierarchy if available
        if excel_data.get('company_hierarchy'):
            summary_parts.append("\nCOMPANY HIERARCHY (FROM EXCEL):")
            hierarchy = excel_data['company_hierarchy']
            if isinstance(hierarchy, dict):
                for key, value in hierarchy.items():
                    summary_parts.append(f"- {key}: {value}")
        
        # Add data quality information
        if excel_data.get('data_quality'):
            summary_parts.append("\nEXCEL DATA QUALITY:")
            quality = excel_data['data_quality']
            summary_parts.append(f"- Completeness: {quality.get('completeness', 'Unknown')}")
            summary_parts.append(f"- Consistency: {quality.get('consistency', 'Unknown')}")
            summary_parts.append(f"- Reliability: {quality.get('reliability', 'Unknown')}")
        
        summary_parts.append("\nIMPORTANT: Excel data is authoritative and should be preserved. Only replace with placeholders if Excel data is clearly missing or incorrect.")
        
        return "\n".join(summary_parts) if summary_parts else "No Excel data available"

