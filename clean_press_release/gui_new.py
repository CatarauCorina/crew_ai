import gradio as gr
import pandas as pd
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
import uuid
from pathlib import Path
import threading
import time

# Import the improved press release writer
from writer import build_finder_graph, build_section_creator_graph
from structure import build_style_graph
from states import FinderState, SectionState, StyleState
from config_loader import get_config
from content_editor_agent import ContentEditorAgent
from base_agent import BaseAgent
from excel_processor import process_excel_for_ai_enhancement, get_excel_context_for_section
from final_processing_chain import FinalProcessingChainAgent
from mongo_interface import MongoInterface



class ContextForSectionAgent(BaseAgent):
    """Agent for analyzing Excel data and providing context for specific press release sections"""
    
    def __init__(self):
        super().__init__()
        self.config = get_config()
        self.agent_config = self.config.get_context_for_section_config()
        self.model_config = self.config.get_model_config('context_for_section')
    
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze Excel data and provide context for a specific section"""
        try:
            section_name = state.get('section_name', '')
            section_type = state.get('section_type', 'general')
            topic = state.get('topic', '')
            company = state.get('company', '')
            all_data_fields = state.get('all_data_fields', {})
            sample_data = state.get('sample_data', [])
            
            # Prepare the prompt
            system_prompt = self.agent_config.get('system_prompt', '')
            user_prompt_template = self.agent_config.get('user_prompt_template', '')
            
            user_prompt = user_prompt_template.format(
                section_name=section_name,
                section_type=section_type,
                topic=topic,
                company=company,
                all_data_fields=json.dumps(all_data_fields, indent=2),
                sample_data=json.dumps(sample_data, indent=2)
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Get LLM response
            response = self.llm_inference(
                messages=messages,
                model=self.model_config['model'],
                temperature=self.model_config['temperature']
            )
            
            # Parse JSON response
            try:
                context_data = json.loads(response)
            except json.JSONDecodeError as e:
                # Fallback if JSON parsing fails
                context_data = {
                    "relevant_metrics": [],
                    "key_insights": ["Data analysis completed but response format was invalid"],
                    "data_summary": "Data available for analysis",
                    "presentation_suggestions": ["Present data clearly and professionally"],
                    "context_for_ai": response  # Use raw response as fallback
                }
            
            # Update state with results
            state.update({
                'context_analysis': context_data,
                'context_for_ai': context_data.get('context_for_ai', ''),
                'success': True
            })
            
            return state
            
        except Exception as e:
            # Error handling
            state.update({
                'context_analysis': {},
                'context_for_ai': f"Error analyzing data: {str(e)}",
                'success': False,
                'error': str(e)
            })
            return state

class FinalCheckerAgent(BaseAgent):
    """Agent for final quality checking of press release content"""
    
    def __init__(self):
        super().__init__()
        self.config = get_config()
    
    def run(self, state):
        """Check press release content against quality rules"""
        try:
            # Extract content from state
            title = state.get("title", "")
            company = state.get("company", "")
            topic = state.get("topic", "")
            content = state.get("final_content", "")
            
            # Get checker configuration
            checker_config = self.config.get_final_checker_config()
            
            # Generate user prompt
            user_prompt = checker_config["user_prompt_template"].format(
                title=title,
                company=company,
                topic=topic,
                content=content
            )
            
            # Call LLM for quality check
            response = self.llm_inference(
                messages=[
                    {"role": "system", "content": checker_config["system_prompt"]},
                    {"role": "user", "content": user_prompt}
                ],
                model=checker_config["model"],
                temperature=checker_config["temperature"]
            )
            
            # Parse JSON response
            import json
            try:
                check_result = json.loads(response)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                check_result = {
                    "overall_score": 7,
                    "critical_issues": ["Failed to parse quality check response"],
                    "suggestions": ["Review content manually"],
                    "compliance_flags": [],
                    "ready_for_export": False
                }
            
            # Update state with check results
            state["quality_check"] = check_result
            return state
            
        except Exception as e:
            print(f"Error in FinalCheckerAgent: {e}")
            # Fallback check result
            state["quality_check"] = {
                "overall_score": 5,
                "critical_issues": [f"Quality check failed: {str(e)}"],
                "suggestions": ["Manual review required"],
                "compliance_flags": [],
                "ready_for_export": False
            }
            return state

class FactCheckerAgent(BaseAgent):
    """Agent for fact-checking press release content against Excel and MongoDB data"""
    
    def __init__(self):
        super().__init__()
        self.config = get_config()
        self.mongo_interface = MongoInterface()
    
    def run(self, state):
        """Fact-check press release content against available data sources"""
        try:
            # Extract content from state
            title = state.get("title", "")
            company = state.get("company", "")
            topic = state.get("topic", "")
            content = state.get("final_content", "")
            excel_data = state.get("excel_data", {})
            
            # Get MongoDB data for fact checking
            mongo_data = self._get_mongo_data_for_fact_checking(company, topic)
            
            # Get fact checker configuration
            checker_config = self.config.get_fact_checker_config()
            
            # Prepare Excel data summary for fact checking
            excel_summary = self._prepare_excel_data_for_fact_checking(excel_data)
            
            # Generate user prompt
            user_prompt = checker_config["user_prompt_template"].format(
                title=title,
                company=company,
                topic=topic,
                content=content,
                excel_data=excel_summary,
                mongo_data=json.dumps(mongo_data, indent=2, default=str)
            )
            
            # Call LLM for fact checking
            response = self.llm_inference(
                messages=[
                    {"role": "system", "content": checker_config["system_prompt"]},
                    {"role": "user", "content": user_prompt}
                ],
                model=checker_config["model"],
                temperature=checker_config["temperature"]
            )
            
            # Parse JSON response
            import json
            try:
                fact_check_result = json.loads(response)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                fact_check_result = {
                    "verified_claims": [],
                    "unverified_claims": ["Failed to parse fact check response"],
                    "incorrect_claims": [],
                    "suggested_corrections": [],
                    "data_gaps": [],
                    "overall_accuracy": 0
                }
            
            # Update state with fact check results
            state["fact_check"] = fact_check_result
            return state
            
        except Exception as e:
            print(f"Error in FactCheckerAgent: {e}")
            # Fallback fact check result
            state["fact_check"] = {
                "verified_claims": [],
                "unverified_claims": [f"Fact check failed: {str(e)}"],
                "incorrect_claims": [],
                "suggested_corrections": [],
                "data_gaps": [],
                "overall_accuracy": 0
            }
            return state
    
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
            
            # Get company hierarchy
            try:
                company_tree = self.mongo_interface.fetch_company_tree()
                if company in company_tree:
                    mongo_data["company_hierarchy"] = {
                        "subsidiaries": company_tree[company],
                        "parent_companies": self._find_parent_companies(company, company_tree)
                    }
            except Exception as e:
                print(f"Error fetching company hierarchy: {e}")
            
            return mongo_data
            
        except Exception as e:
            print(f"Error getting MongoDB data: {e}")
            return {"company_info": {}, "financial_data": [], "recent_releases": [], "company_hierarchy": {}}
    
    def _find_parent_companies(self, company: str, company_tree: Dict[str, List[tuple]]) -> List[str]:
        """Find parent companies for a given company"""
        parents = []
        for parent, children in company_tree.items():
            for child, _ in children:
                if child.lower() == company.lower():
                    parents.append(parent)
        return parents
    
    def _prepare_excel_data_for_fact_checking(self, excel_data: Dict[str, Any]) -> str:
        """Prepare Excel data summary for fact checking"""
        if not excel_data.get('success', False):
            return "No Excel data available"
        
        summary_parts = []
        
        # Add consolidated metrics
        if excel_data.get('consolidated_metrics'):
            summary_parts.append("CONSOLIDATED METRICS:")
            for metric in excel_data['consolidated_metrics']:
                summary_parts.append(f"- {metric['name']}: {metric['value']} {metric.get('unit', '')}")
        
        # Add raw data sample
        if excel_data.get('raw_data_sample'):
            summary_parts.append("\nRAW DATA SAMPLE:")
            for item in excel_data['raw_data_sample'][:5]:  # Limit to first 5 items
                summary_parts.append(f"- {item}")
        
        # Add insights
        if excel_data.get('insights'):
            summary_parts.append("\nKEY INSIGHTS:")
            for insight in excel_data['insights']:
                summary_parts.append(f"- {insight}")
        
        return "\n".join(summary_parts) if summary_parts else "No Excel data available"

class PressReleaseAgent:
    def __init__(self):
        self.data_dir = Path("press_releases")
        self.data_dir.mkdir(exist_ok=True)
        self.releases_file = self.data_dir / "releases.json"
        self.load_releases()
    
    def load_releases(self):
        """Load existing press releases from JSON file"""
        if self.releases_file.exists():
            with open(self.releases_file, 'r', encoding='utf-8') as f:
                self.releases = json.load(f)
        else:
            # Add some mock data for demonstration
            self.releases = [
                {
                    "id": "demo-1",
                    "title": "Q4 2024 Financial Results",
                    "description": "Strong quarterly performance with record revenue growth",
                    "content": "# Q4 2024 Financial Results\n\n**Date:** January 15, 2025\n\n## Key Highlights\n\n- **Revenue Growth:** 25% year-over-year increase\n- **Net Profit:** $2.3M, up 18% from previous quarter\n- **Customer Acquisition:** 15,000 new customers\n- **Market Expansion:** Launched in 3 new regions\n\n## Detailed Performance\n\nOur Q4 2024 results demonstrate exceptional growth across all key metrics...\n\n---\n\n*This press release was generated using the Press Release Agent.*",
                    "excel_data": [],
                    "created_at": "2025-01-15T10:30:00",
                    "updated_at": "2025-01-15T10:30:00"
                },
                {
                    "id": "demo-2", 
                    "title": "New Product Launch: AI Assistant",
                    "description": "Revolutionary AI-powered assistant for business automation",
                    "content": "# New Product Launch: AI Assistant\n\n**Date:** January 10, 2025\n\n## Product Overview\n\nWe're excited to announce the launch of our revolutionary AI Assistant, designed to transform business automation...\n\n## Key Features\n\n- **Natural Language Processing:** Advanced NLP capabilities\n- **Multi-Platform Integration:** Works across all major platforms\n- **Real-time Analytics:** Comprehensive business insights\n- **Customizable Workflows:** Tailored to your business needs\n\n## Market Impact\n\nThis launch represents a significant milestone in our mission to democratize AI technology...\n\n---\n\n*This press release was generated using the Press Release Agent.*",
                    "excel_data": [],
                    "created_at": "2025-01-10T14:20:00",
                    "updated_at": "2025-01-10T14:20:00"
                }
            ]
            self.save_releases()
    
    def save_releases(self):
        """Save press releases to JSON file"""
        with open(self.releases_file, 'w', encoding='utf-8') as f:
            json.dump(self.releases, f, indent=2, ensure_ascii=False)
    
    def create_release_from_excel(self, excel_file, title: str, description: str = "") -> str:
        """Create a new press release from Excel data"""
        try:
            # Read Excel file
            df = pd.read_excel(excel_file)
            
            # Generate press release content from Excel data
            content = self.generate_press_release_from_data(df, title, description)
            
            # Create release object
            release_id = str(uuid.uuid4())
            release = {
                "id": release_id,
                "title": title,
                "description": description,
                "content": content,
                "excel_data": df.to_dict('records'),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            self.releases.append(release)
            self.save_releases()
            
            return f"✅ Press release '{title}' created successfully! ID: {release_id}"
            
        except Exception as e:
            return f"❌ Error creating press release: {str(e)}"
    
    def generate_press_release_from_data(self, df: pd.DataFrame, title: str, description: str) -> str:
        """Generate press release content from Excel data"""
        content = f"# {title}\n\n"
        
        if description:
            content += f"**Overview:** {description}\n\n"
        
        content += f"**Date:** {datetime.now().strftime('%B %d, %Y')}\n\n"
        
        # Add key metrics or data points from Excel
        if not df.empty:
            content += "## Key Highlights\n\n"
            
            # If there are numeric columns, show summary statistics
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                content += "### Data Summary\n"
                for col in numeric_cols[:5]:  # Limit to first 5 numeric columns
                    if df[col].notna().any():
                        content += f"- **{col}:** {df[col].mean():.2f} (average)\n"
                content += "\n"
            
            # Add table of data if small enough
            if len(df) <= 10:
                content += "### Detailed Data\n\n"
                content += df.to_markdown(index=False)
                content += "\n\n"
        
        content += "---\n\n*This press release was generated using the Press Release Agent.*"
        
        return content
    
    def _extract_data_for_ai_enhancement(self, excel_file_path: str) -> Dict[str, any]:
        """Extract all data fields from Excel file for AI enhancement using comprehensive processor"""
        try:
            # Use the new comprehensive Excel processor
            result = process_excel_for_ai_enhancement(excel_file_path)
            # Add the file path to the result for context generation
            result['excel_file_path'] = excel_file_path
            return result
        except Exception as e:
            print(f"Error processing Excel file with comprehensive processor: {e}")
            # Fallback to basic processing if comprehensive processor fails
            result = self._extract_data_for_ai_enhancement_fallback(excel_file_path)
            result['excel_file_path'] = excel_file_path
            return result
    
    def _extract_data_for_ai_enhancement_fallback(self, excel_file_path: str) -> Dict[str, any]:
        """Fallback method for basic Excel processing"""
        try:
            # Read the first sheet as fallback
            df = pd.read_excel(excel_file_path, sheet_name=0)
            
            extracted_data = {
                "all_data_fields": {},
                "summary_stats": {},
                "raw_data_sample": None
            }
            
            if df.empty:
                return extracted_data
            
            # Extract all columns with their data types and sample values
            for col in df.columns:
                col_data = df[col].dropna()
                if len(col_data) > 0:
                    field_info = {
                        "name": col,
                        "data_type": str(df[col].dtype),
                        "non_null_count": len(col_data),
                        "total_count": len(df),
                        "unique_values": col_data.nunique(),
                        "sample_values": col_data.head(3).tolist()
                    }
                    
                    # Add numeric-specific information
                    if pd.api.types.is_numeric_dtype(df[col]):
                        field_info.update({
                            "is_numeric": True,
                            "current_value": float(col_data.iloc[-1]) if len(col_data) > 0 else None,
                            "average": float(col_data.mean()),
                            "max": float(col_data.max()),
                            "min": float(col_data.min()),
                            "trend": "increasing" if len(col_data) > 1 and col_data.iloc[-1] > col_data.iloc[0] else "decreasing" if len(col_data) > 1 and col_data.iloc[-1] < col_data.iloc[0] else "stable"
                        })
                    else:
                        field_info["is_numeric"] = False
                        # For text columns, get most common values
                        if len(col_data) > 0:
                            value_counts = col_data.value_counts()
                            field_info["most_common_values"] = value_counts.head(3).to_dict()
                    
                    extracted_data["all_data_fields"][col] = field_info
            
            # Extract summary statistics
            extracted_data["summary_stats"] = {
                "total_records": len(df),
                "total_columns": len(df.columns),
                "numeric_columns": len(df.select_dtypes(include=['number']).columns),
                "text_columns": len(df.select_dtypes(include=['object']).columns),
                "date_columns": len(df.select_dtypes(include=['datetime64']).columns),
                "date_range": None
            }
            
            # Try to find date columns
            date_cols = df.select_dtypes(include=['datetime64']).columns
            if len(date_cols) > 0:
                date_col = date_cols[0]
                extracted_data["summary_stats"]["date_range"] = {
                    "start": str(df[date_col].min()),
                    "end": str(df[date_col].max())
                }
            
            # Store a sample of raw data (first 3 rows) for context
            if len(df) > 0:
                sample_df = df.head(3)
                extracted_data["raw_data_sample"] = sample_df.to_dict('records')
            
            return extracted_data
            
        except Exception as e:
            print(f"Error in fallback Excel processing: {e}")
            return {
                "all_data_fields": {},
                "summary_stats": {},
                "raw_data_sample": None
            }
    
    def _format_data_context_for_section(self, extracted_data: Dict[str, any], section_name: str, topic: str = "", company: str = "") -> str:
        """Use Excel processor to format extracted data as context for a specific section"""
        if not extracted_data:
            return ""
        
        try:
            # Check if we have the Excel file path in the extracted data
            excel_file_path = extracted_data.get('excel_file_path')
            if excel_file_path:
                # Use the new Excel processor for context generation
                return get_excel_context_for_section(excel_file_path, section_name, topic, company)
            else:
                # Fallback to the old context agent if no file path available
                return self._format_data_context_for_section_legacy(extracted_data, section_name, topic, company)
                
        except Exception as e:
            print(f"Error in Excel context formatting: {e}")
            # Fallback to basic context if there's an error
            return self._create_fallback_context(extracted_data, section_name)
    
    def _format_data_context_for_section_legacy(self, extracted_data: Dict[str, any], section_name: str, topic: str = "", company: str = "") -> str:
        """Legacy method using ContextForSectionAgent for backward compatibility"""
        try:
            # Initialize the context agent
            context_agent = ContextForSectionAgent()
            
            # Determine section type based on section name
            section_lower = section_name.lower()
            if any(keyword in section_lower for keyword in ['financial', 'revenue', 'profit', 'earnings', 'results']):
                section_type = 'financial'
            elif any(keyword in section_lower for keyword in ['operational', 'operations', 'performance', 'metrics']):
                section_type = 'operational'
            elif any(keyword in section_lower for keyword in ['strategic', 'strategy', 'outlook', 'future']):
                section_type = 'strategic'
            elif any(keyword in section_lower for keyword in ['company', 'about', 'overview', 'profile']):
                section_type = 'company_overview'
            else:
                section_type = 'general'
            
            # Prepare state for the context agent
            state = {
                'section_name': section_name,
                'section_type': section_type,
                'topic': topic,
                'company': company,
                'all_data_fields': extracted_data.get('all_data_fields', {}),
                'sample_data': extracted_data.get('raw_data_sample', [])
            }
            
            # Run the context agent
            result = context_agent.run(state)
            
            if result.get('success', False):
                return result.get('context_for_ai', '')
            else:
                # Fallback to basic context if LLM fails
                return self._create_fallback_context(extracted_data, section_name)
                
        except Exception as e:
            # Fallback to basic context if there's an error
            return self._create_fallback_context(extracted_data, section_name)
    
    def _create_fallback_context(self, extracted_data: Dict[str, any], section_name: str) -> str:
        """Create a basic fallback context if LLM processing fails"""
        context_parts = []
        
        # Add summary statistics
        if extracted_data.get('summary_stats'):
            stats = extracted_data['summary_stats']
            context_parts.append(f"**Data Summary:** {stats['total_records']} records, {stats['numeric_columns']} numeric columns")
            if stats.get('date_range'):
                context_parts.append(f"**Period:** {stats['date_range']['start']} to {stats['date_range']['end']}")
        
        # Add sample data for context if available
        if extracted_data.get('raw_data_sample') and len(extracted_data['raw_data_sample']) > 0:
            context_parts.append("**Sample Data:**")
            sample = extracted_data['raw_data_sample'][0]  # First row as example
            for key, value in sample.items():
                if pd.notna(value):
                    context_parts.append(f"- {key}: {value}")
        
        return "\n".join(context_parts) if context_parts else ""
    
    def _create_excel_evidence(self, extracted_data: Dict[str, any], section_name: str, topic: str, company: str) -> List[Dict[str, Any]]:
        """Convert Excel data into evidence format for SectionCreator"""
        evidence_list = []
        
        if not extracted_data:
            return evidence_list
        
        # Create comprehensive financial evidence from raw data
        raw_data_sample = extracted_data.get('raw_data_sample', [])
        if raw_data_sample and len(raw_data_sample) > 0:
            evidence_text = self._format_comprehensive_financial_evidence(raw_data_sample, section_name)
            if evidence_text:
                evidence_list.append({
                    "ref": "#EXCEL_FINANCIAL_DATA",
                    "source_kind": "excel_data",
                    "press_title": "Excel Data - Financial Metrics",
                    "press_url": "",
                    "doc_url": extracted_data.get('excel_file_path', ''),
                    "text": evidence_text,
                    "created_at": None,
                    "score": 1.0  # Highest priority for financial data
                })
        
        # Create evidence from raw data sample
        if raw_data_sample and len(raw_data_sample) > 0:
            evidence_text = self._format_raw_data_as_evidence(raw_data_sample, section_name)
            if evidence_text:
                evidence_list.append({
                    "ref": "#EXCEL_RAW_DATA",
                    "source_kind": "excel_data",
                    "press_title": "Excel Data - Raw Sample",
                    "press_url": "",
                    "doc_url": extracted_data.get('excel_file_path', ''),
                    "text": evidence_text,
                    "created_at": None,
                    "score": 0.9  # High score for Excel data priority
                })
        
        # Create evidence from consolidated metrics
        consolidated_metrics = extracted_data.get('all_data_fields', {})
        if consolidated_metrics:
            evidence_text = self._format_consolidated_metrics_as_evidence(consolidated_metrics, section_name)
            if evidence_text:
                evidence_list.append({
                    "ref": "#EXCEL_CONSOLIDATED",
                    "source_kind": "excel_data",
                    "press_title": "Excel Data - Consolidated Metrics",
                    "press_url": "",
                    "doc_url": extracted_data.get('excel_file_path', ''),
                    "text": evidence_text,
                    "created_at": None,
                    "score": 0.8  # High score for consolidated data
                })
        
        # Create evidence from insights
        insights = extracted_data.get('insights', {})
        if insights:
            evidence_text = self._format_insights_as_evidence(insights, section_name)
            if evidence_text:
                evidence_list.append({
                    "ref": "#EXCEL_INSIGHTS",
                    "source_kind": "excel_data",
                    "press_title": "Excel Data - Insights",
                    "press_url": "",
                    "doc_url": extracted_data.get('excel_file_path', ''),
                    "text": evidence_text,
                    "created_at": None,
                    "score": 0.7  # High score for insights
                })
        
        return evidence_list
    
    def _format_comprehensive_financial_evidence(self, raw_data_sample: Dict, section_name: str) -> str:
        """Format comprehensive financial evidence from CSV data"""
        if not raw_data_sample:
            return ""
        
        evidence_parts = [f"**Financial Data for {section_name}:**"]
        
        # Extract financial data from the structure
        if isinstance(raw_data_sample, dict):
            for company_key, company_data in raw_data_sample.items():
                if isinstance(company_data, dict) and 'raw_data' in company_data:
                    evidence_parts.append(f"**{company_key} Financial Results:**")
                    
                    # Group data by period
                    q2_data = []
                    h1_data = []
                    
                    for row in company_data['raw_data']:
                        if isinstance(row, dict):
                            period = row.get('Period', '')
                            element = row.get('Element', '')
                            current_q = row.get('Current_Quarter', '')
                            prev_year = row.get('Previous_Year_Same_Quarter', '')
                            yoy_change = row.get('Year_Over_Year_Change', '')
                            prev_q = row.get('Previous_Quarter', '')
                            qoq_change = row.get('Quarter_Over_Quarter_Change', '')
                            unit = row.get('Unit', '')
                            
                            # Clean up values
                            if pd.notna(current_q) and str(current_q) != 'nan':
                                current_q = f"{current_q:.1f}" if isinstance(current_q, (int, float)) else str(current_q)
                            if pd.notna(prev_year) and str(prev_year) != 'nan':
                                prev_year = f"{prev_year:.1f}" if isinstance(prev_year, (int, float)) else str(prev_year)
                            if pd.notna(yoy_change) and str(yoy_change) != 'nan':
                                yoy_change = f"{yoy_change:.2%}" if isinstance(yoy_change, (int, float)) else str(yoy_change)
                            if pd.notna(prev_q) and str(prev_q) != 'nan':
                                prev_q = f"{prev_q:.1f}" if isinstance(prev_q, (int, float)) else str(prev_q)
                            if pd.notna(qoq_change) and str(qoq_change) != 'nan':
                                qoq_change = f"{qoq_change:.2%}" if isinstance(qoq_change, (int, float)) else str(qoq_change)
                            
                            if period == 'Q2 2025':
                                q2_data.append({
                                    'element': element,
                                    'current': current_q,
                                    'prev_year': prev_year,
                                    'yoy': yoy_change,
                                    'prev_q': prev_q,
                                    'qoq': qoq_change,
                                    'unit': unit
                                })
                            elif period == 'H1 2025':
                                h1_data.append({
                                    'element': element,
                                    'current': current_q,
                                    'prev_year': prev_year,
                                    'yoy': yoy_change,
                                    'unit': unit
                                })
                    
                    # Format Q2 2025 data
                    if q2_data:
                        evidence_parts.append("**Q2 2025 Results:**")
                        for item in q2_data:
                            if item['current'] and item['current'] != 'nan':
                                line = f"- {item['element']}: {item['current']} {item['unit']}"
                                if item['prev_year'] and item['prev_year'] != 'nan':
                                    line += f" (vs {item['prev_year']} {item['unit']} in Q2 2024"
                                    if item['yoy'] and item['yoy'] != 'nan':
                                        line += f", {item['yoy']} YoY"
                                    line += ")"
                                if item['prev_q'] and item['prev_q'] != 'nan':
                                    line += f" (vs {item['prev_q']} {item['unit']} in Q1 2025"
                                    if item['qoq'] and item['qoq'] != 'nan':
                                        line += f", {item['qoq']} QoQ"
                                    line += ")"
                                evidence_parts.append(line)
                    
                    # Format H1 2025 data
                    if h1_data:
                        evidence_parts.append("**H1 2025 Results:**")
                        for item in h1_data:
                            if item['current'] and item['current'] != 'nan':
                                line = f"- {item['element']}: {item['current']} {item['unit']}"
                                if item['prev_year'] and item['prev_year'] != 'nan':
                                    line += f" (vs {item['prev_year']} {item['unit']} in H1 2024"
                                    if item['yoy'] and item['yoy'] != 'nan':
                                        line += f", {item['yoy']} YoY"
                                    line += ")"
                                evidence_parts.append(line)
        
        return "\n".join(evidence_parts)
    
    def _format_raw_data_as_evidence(self, raw_data_sample: List[Dict], section_name: str) -> str:
        """Format raw data sample as evidence text"""
        if not raw_data_sample:
            return ""
        
        evidence_parts = [f"**Excel Data Sample for {section_name}:**"]
        
        # Handle different data structures
        if isinstance(raw_data_sample, list):
            # If it's a list of dictionaries (CSV rows)
            for i, row in enumerate(raw_data_sample[:3]):  # First 3 rows
                if isinstance(row, dict):
                    evidence_parts.append(f"Row {i+1}:")
                    for key, value in row.items():
                        if pd.notna(value) and str(value).strip() and str(value) != 'nan':
                            evidence_parts.append(f"  {key}: {value}")
        elif isinstance(raw_data_sample, dict):
            # If it's a dictionary structure (from Excel processor)
            for company_key, company_data in raw_data_sample.items():
                if isinstance(company_data, dict) and 'raw_data' in company_data:
                    evidence_parts.append(f"**{company_key} Data:**")
                    for i, row in enumerate(company_data['raw_data'][:3]):  # First 3 rows
                        if isinstance(row, dict):
                            evidence_parts.append(f"  Row {i+1}:")
                            for key, value in row.items():
                                if pd.notna(value) and str(value).strip() and str(value) != 'nan':
                                    evidence_parts.append(f"    {key}: {value}")
        
        return "\n".join(evidence_parts)
    
    def _format_consolidated_metrics_as_evidence(self, consolidated_metrics: Dict[str, any], section_name: str) -> str:
        """Format consolidated metrics as evidence text"""
        evidence_parts = [f"**Consolidated Financial Data for {section_name}:**"]
        
        # Handle the actual data structure from Excel processor
        if 'other' in consolidated_metrics:
            # This is the structure from your data
            for category, metrics in consolidated_metrics.items():
                if isinstance(metrics, dict):
                    for company_key, company_metrics in metrics.items():
                        if isinstance(company_metrics, dict) and 'values' in company_metrics:
                            evidence_parts.append(f"**{company_key}:**")
                            for metric_name, metric_data in company_metrics.items():
                                if isinstance(metric_data, dict) and 'latest' in metric_data:
                                    unit = metric_data.get('unit', '')
                                    trend = metric_data.get('trend', 'stable')
                                    latest = metric_data.get('latest', 0)
                                    if pd.notna(latest) and str(latest) != 'nan':
                                        evidence_parts.append(f"- {metric_name.replace('_', ' ').title()}: {latest} {unit} (trend: {trend})")
        else:
            # Fallback for other structures
            for metric_name, metric_data in consolidated_metrics.items():
                if isinstance(metric_data, dict) and metric_data.get('current_value') is not None:
                    unit = metric_data.get('unit', '')
                    trend = metric_data.get('trend', 'stable')
                    evidence_parts.append(f"- {metric_name.replace('_', ' ').title()}: {metric_data['current_value']} {unit} (trend: {trend})")
        
        return "\n".join(evidence_parts)
    
    def _format_insights_as_evidence(self, insights: Dict[str, any], section_name: str) -> str:
        """Format insights as evidence text"""
        evidence_parts = [f"**Key Insights for {section_name}:**"]
        
        # Add performance highlights
        highlights = insights.get('performance_highlights', [])
        if highlights:
            evidence_parts.append("Performance Highlights:")
            for highlight in highlights[:3]:  # Top 3 highlights
                evidence_parts.append(f"- {highlight['metric'].replace('_', ' ').title()}: {highlight['best_performer']} leads with {highlight['best_value']}")
        
        # Add trend analysis
        trends = insights.get('trend_analysis', [])
        if trends:
            evidence_parts.append("Trend Analysis:")
            for trend in trends[:2]:  # Top 2 trends
                if trend['increasing_companies']:
                    evidence_parts.append(f"- {trend['metric'].replace('_', ' ').title()}: Growing in {', '.join(trend['increasing_companies'])}")
        
        return "\n".join(evidence_parts)
    
    def get_release_list(self) -> List[Dict]:
        """Get list of all press releases"""
        return sorted(self.releases, key=lambda x: x['created_at'], reverse=True)
    
    def get_release_by_id(self, release_id: str) -> Optional[Dict]:
        """Get a specific press release by ID"""
        for release in self.releases:
            if release['id'] == release_id:
                return release
        return None
    
    def update_release_content(self, release_id: str, new_content: str) -> str:
        """Update press release content"""
        for release in self.releases:
            if release['id'] == release_id:
                release['content'] = new_content
                release['updated_at'] = datetime.now().isoformat()
                self.save_releases()
                return f"✅ Press release updated successfully!"
        return "❌ Release not found!"
    
    def delete_release(self, release_id: str) -> str:
        """Delete a press release"""
        self.releases = [r for r in self.releases if r['id'] != release_id]
        self.save_releases()
        return f"✅ Press release deleted successfully!"
    
    def create_release_from_content(self, content: str, title: str, description: str) -> str:
        """Create a new press release from content"""
        release_id = str(uuid.uuid4())
        new_release = {
            "id": release_id,
            "title": title,
            "description": description,
            "content": content,
            "excel_data": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self.releases.append(new_release)
        self.save_releases()
        return release_id
    
    def generate_press_release_with_ai(self, topic: str, company: str = "SISCO", progress_callback=None, sections_display_callback=None, excel_file=None) -> Dict[str, any]:
        """Generate a press release using the improved AI writer with real-time section updates"""
        try:
            # Process uploaded file data if provided
            extracted_data = None
            if excel_file:
                if progress_callback:
                    progress_callback("📊 Processing uploaded file data...", 5)
                
                try:
                    # Update progress during Excel processing
                    if progress_callback:
                        progress_callback("🔍 Analyzing Excel file structure...", 6)
                    
                    # Extract key data points for AI enhancement using comprehensive processor
                    extracted_data = self._extract_data_for_ai_enhancement(excel_file)
                    
                    # Update progress after Excel processing
                    if progress_callback:
                        progress_callback("📈 Extracting metrics and insights...", 7)
                    
                    if progress_callback:
                        metrics_count = len(extracted_data.get('all_data_fields', {}))
                        progress_callback(f"✅ Processed Excel file with {metrics_count} data fields", 8)
                        
                except Exception as e:
                    if progress_callback:
                        progress_callback(f"⚠️ Warning: Could not process uploaded file: {str(e)}", 8)
                    # Continue without data enhancement
            
            # Build the graphs
            finder_app = build_finder_graph()
            creator_app = build_section_creator_graph()
            style_app = build_style_graph()
            
            # Get structure from style graph
            if progress_callback:
                progress_callback("🔍 Analyzing topic and generating structure...", 10)
            
            config = get_config()
            recursion_limits = config.get_recursion_limits()
            
            # Update progress before style graph
            if progress_callback:
                progress_callback("🎨 Running style analysis and structure generation...", 12)
            
            style_out: StyleState = style_app.invoke({
                "topic": topic,
                "client_id": company,
                "want_document": True,
                "max_docs": 5,
                "lookback_days": 540,
            }, config={"recursion_limit": recursion_limits['style_graph']})
            
            # Update progress after style graph
            if progress_callback:
                progress_callback("📊 Processing structure results...", 15)
            
            structure = style_out.get("structure", {}) or {}
            sections = structure.get("sections", []) or []
            tone = structure.get("tone", "formal, factual, concise")
            phrase_bank = structure.get("phrase_bank", []) or []
            boilerplate = structure.get("boilerplate", "") or ""
            
            if progress_callback:
                progress_callback(f"📋 Generated structure with {len(sections)} sections", 20)
            
            # Cross-section memory
            section_memory: Dict[str, Dict[str, Any]] = {}
            per_section_results: Dict[str, Any] = {}
            assembled_md_parts: List[str] = []
            
            # Process each section with real-time updates
            for i, s in enumerate(sections):
                sec_name = (s.get("name") or "Section").strip()
                sec_notes = s.get("notes", "")
                
                # Initialize section as "working"
                per_section_results[sec_name] = {
                    "status": "working",
                    "content": f"🔄 Working on {sec_name}...",
                    "final_md": "",
                    "draft_md": "",
                    "evidence": [],
                    "citations": []
                }
                
                # Update display to show section is being worked on
                if sections_display_callback:
                    sections_display_callback(per_section_results)
                
                if progress_callback:
                    progress_callback(f"🔍 Finding evidence for: {sec_name}", 20 + (i * 60 // len(sections)))
                
                # Get evidence search parameters from configuration
                config = get_config()
                evidence_params = config.get_evidence_search_params()
                
                print(f"🔍 Starting evidence search for: {sec_name}")
                print(f"   - Topic: {topic}")
                print(f"   - Company: {company}")
                print(f"   - Section notes: {sec_notes}")
                print(f"   - Max loops: {evidence_params['max_loops']}")
                print(f"   - Top K: {evidence_params['top_k']}")
                print(f"   - Lookback days: {evidence_params['lookback_days']}")
                
                # Prepare enhanced section notes with extracted data
                enhanced_notes = sec_notes
                if extracted_data:
                    data_context = self._format_data_context_for_section(extracted_data, sec_name, topic, company)
                    if data_context:
                        enhanced_notes = f"{sec_notes}\n\n**Data Context from uploaded file:**\n{data_context}" if sec_notes else f"**Data Context from uploaded file:**\n{data_context}"
                
                # Finder loop
                fstate: FinderState = {
                    "topic": topic,
                    "company": company,
                    "section_name": sec_name,
                    "section_notes": enhanced_notes,
                    "want_document": True,
                    "lookback_days": evidence_params['lookback_days'],
                    "top_k": evidence_params['top_k'],
                    "max_loops": evidence_params['max_loops'],
                    "allow_placeholders": True,
                    "section_memory": section_memory
                }
                try:
                    fout = finder_app.invoke(fstate, config={"recursion_limit": recursion_limits['finder_graph']})
                except Exception as e:
                    error_msg = f"Evidence search failed for '{sec_name}': {str(e)}"
                    print(f"Finder graph error for section '{sec_name}': {e}")
                    if progress_callback:
                        progress_callback(f"⚠️ {error_msg}", 20 + ((i + 1) * 50 // len(sections)))
                    # Create fallback evidence if finder fails
                    fout = {
                        "evidence": [],
                        "needs_more": False,
                        "finder_request": None,
                        "diagnostics": {"error": str(e)},
                        "placeholders": [{"name": f"{sec_name} Data", "token": f"[{sec_name.upper().replace(' ', '_')}_DATA]", "hint": "data pending"}],
                        "editor_guidance": f"Create {sec_name} content using placeholder for missing data."
                    }
                
                # Get finder evidence
                finder_evidence = fout.get("evidence", [])
                
                # Add Excel data as evidence if available
                excel_evidence = []
                if extracted_data:
                    excel_evidence = self._create_excel_evidence(extracted_data, sec_name, topic, company)
                
                # Combine finder evidence with Excel evidence (Excel evidence first for priority)
                combined_evidence = excel_evidence + finder_evidence
                
                # DEBUG: Print evidence for debugging
                print(f"\n🔍 DEBUG - Evidence for section '{sec_name}':")
                print(f"   - Excel evidence count: {len(excel_evidence)}")
                print(f"   - Finder evidence count: {len(finder_evidence)}")
                print(f"   - Combined evidence count: {len(combined_evidence)}")
                
                if excel_evidence:
                    print(f"   - Excel evidence refs: {[e.get('ref', 'NO_REF') for e in excel_evidence]}")
                    for i, ev in enumerate(excel_evidence):
                        print(f"   - Excel evidence {i+1} text preview: {ev.get('text', 'NO_TEXT')[:200]}...")
                
                # Update section with combined evidence
                per_section_results[sec_name].update({
                    "needs_more": fout.get("needs_more", False),
                    "finder_request": fout.get("finder_request"),
                    "diagnostics": fout.get("diagnostics", {}),
                    "evidence": combined_evidence,
                    "content": f"✍️ Writing {sec_name}...",
                    "status": "writing"
                })
                
                # Update display to show section is being written
                if sections_display_callback:
                    sections_display_callback(per_section_results)
                
                if progress_callback:
                    progress_callback(f"✍️ Writing section: {sec_name}", 20 + ((i + 0.5) * 60 // len(sections)))
                
                # Creator/Evaluator loop
                cstate: SectionState = {
                    "topic": topic,
                    "company": company,
                    "section_name": sec_name,
                    "section_notes": sec_notes,
                    "tone": tone,
                    "phrase_bank": phrase_bank,
                    "boilerplate": boilerplate,
                    "allow_placeholders": True,
                    "evidence": per_section_results[sec_name]["evidence"],
                    "placeholders": fout.get("placeholders", []),
                    "editor_guidance": fout.get("editor_guidance", ""),
                    "max_revisions": 2,
                    "section_memory": section_memory,
                    "writing_style_guidance": f"Use phrases from phrase bank naturally. Maintain {tone} tone throughout. Create comprehensive, detailed content.",
                    "style_consistency_notes": "Ensure consistent use of phrase bank terms and maintain professional tone across all paragraphs."
                }
                
                try:
                    cout = creator_app.invoke(cstate, config={"recursion_limit": recursion_limits['creator_graph']})
                except Exception as e:
                    error_msg = f"Content creation failed for '{sec_name}': {str(e)}"
                    print(f"Creator graph error for section '{sec_name}': {e}")
                    if progress_callback:
                        progress_callback(f"⚠️ {error_msg}", 20 + ((i + 1) * 60 // len(sections)))
                    # Create fallback content if creator fails
                    cout = {
                        "accepted": False,
                        "draft_md": f"[{sec_name.upper().replace(' ', '_')}_CONTENT]",
                        "needs_revision": True,
                        "revision_instructions": [f"Content creation failed: {str(e)}"],
                        "citations": []
                    }
                
                # Handle refinement if needed
                if cout.get("ask_finder_keywords"):
                    add_kw = cout.get("ask_finder_keywords") or []
                    fstate["finder_request"] = {"add_keywords": add_kw}
                    fstate["loops_run"] = 0
                    try:
                        fout2 = finder_app.invoke(fstate)
                        cstate["evidence"] = fout2.get("evidence", [])
                        cout = creator_app.invoke(cstate, config={"recursion_limit": recursion_limits['creator_graph']})
                    except Exception as e:
                        error_msg = f"Refinement failed for '{sec_name}': {str(e)}"
                        print(f"Refinement error for section '{sec_name}': {e}")
                        if progress_callback:
                            progress_callback(f"⚠️ {error_msg}", 20 + ((i + 1) * 60 // len(sections)))
                
                # Save results and update display
                if cout.get("accepted"):
                    final_md = cout.get("final_md", "").strip()
                    section_memory[sec_name] = {"text": final_md, "citations": cout.get("citations", [])}
                    per_section_results[sec_name].update({
                        "final_md": final_md,
                        "citations": cout.get("citations", []),
                        "content": final_md,
                        "status": "completed"
                    })
                    # Clean the content to remove any existing headers
                    cleaned_content = _clean_section_content(final_md, sec_name)
                    assembled_md_parts.append(f"## {sec_name}\n\n{cleaned_content}\n")
                    
                    if progress_callback:
                        progress_callback(f"✅ Completed: {sec_name}", 20 + ((i + 1) * 60 // len(sections)))
                else:
                    draft_md = cout.get("draft_md", "")
                    per_section_results[sec_name].update({
                        "draft_md": draft_md,
                        "needs_revision": cout.get("needs_revision", False),
                        "revision_instructions": cout.get("revision_instructions", []),
                        "content": draft_md,
                        "status": "draft"
                    })
                    # Clean the content to remove any existing headers
                    cleaned_content = _clean_section_content(draft_md, sec_name)
                    assembled_md_parts.append(f"## {sec_name}\n\n{cleaned_content}\n")
                    
                    if progress_callback:
                        progress_callback(f"⚠️ Draft completed: {sec_name}", 20 + ((i + 1) * 60 // len(sections)))
                
                # Update display with final section result
                if sections_display_callback:
                    sections_display_callback(per_section_results)
            
            # Final assembly
            final_markdown = "\n".join(assembled_md_parts).strip()
            
            # Quality check with FinalCheckerAgent
            if progress_callback:
                progress_callback("🔍 Running final quality check...", 95)
            
            try:
                checker_agent = FinalCheckerAgent()
                check_state = {
                    "title": f"{company} - {topic}",
                    "company": company,
                    "topic": topic,
                    "final_content": final_markdown
                }
                checked_state = checker_agent.run(check_state)
                quality_check = checked_state.get("quality_check", {})
            except Exception as e:
                print(f"Quality check failed: {e}")
                quality_check = {
                    "overall_score": 7,
                    "critical_issues": ["Quality check failed"],
                    "suggestions": ["Manual review recommended"],
                    "compliance_flags": [],
                    "ready_for_export": True
                }
            
            # Final Processing Chain (4 stages)
            if progress_callback:
                progress_callback("🔧 Running final processing chain...", 97)
            
            try:
                processing_chain_agent = FinalProcessingChainAgent()
                processing_state = {
                    "title": f"{company} - {topic}",
                    "company": company,
                    "topic": topic,
                    "final_content": final_markdown,
                    "excel_data": extracted_data or {},
                    "progress_callback": progress_callback
                }
                processed_state = processing_chain_agent.run(processing_state)
                final_processed_content = processed_state.get("final_processed_content", final_markdown)
                processing_chain_results = processed_state.get("processing_chain_results", {})
            except Exception as e:
                print(f"Final processing chain failed: {e}")
                final_processed_content = final_markdown
                processing_chain_results = {
                    "error": str(e),
                    "fallback_used": True
                }
            
            if progress_callback:
                progress_callback("🎉 Press release generation completed!", 100)
            
            return {
                "success": True,
                "content": final_processed_content,
                "sections": per_section_results,
                "structure": structure,
                "quality_check": quality_check,
                "processing_chain_results": processing_chain_results,
                "metadata": {
                    "topic": topic,
                    "company": company,
                    "tone": tone,
                    "phrase_bank": phrase_bank,
                    "boilerplate": boilerplate,
                    "generated_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            if progress_callback:
                progress_callback(f"❌ Error: {str(e)}", 100)
            return {
                "success": False,
                "error": str(e),
                "content": "",
                "sections": {},
                "structure": {},
                "metadata": {}
            }
    
    def generate_press_release_with_ai_streaming(self, topic: str, company: str = "SISCO", progress_callback=None, excel_file=None):
        """Generate a press release with streaming updates for real-time UI updates"""
        try:
            # Process uploaded file data if provided
            extracted_data = None
            if excel_file:
                if progress_callback:
                    progress_callback("📊 Processing uploaded file data...", 5)
                
                try:
                    # Update progress during Excel processing
                    if progress_callback:
                        progress_callback("🔍 Analyzing Excel file structure...", 6)
                    
                    # Extract key data points for AI enhancement using comprehensive processor
                    extracted_data = self._extract_data_for_ai_enhancement(excel_file)
                    
                    # Update progress after Excel processing
                    if progress_callback:
                        progress_callback("📈 Extracting metrics and insights...", 7)
                    
                    if progress_callback:
                        metrics_count = len(extracted_data.get('all_data_fields', {}))
                        progress_callback(f"✅ Processed Excel file with {metrics_count} data fields", 8)
                        
                except Exception as e:
                    if progress_callback:
                        progress_callback(f"⚠️ Warning: Could not process uploaded file: {str(e)}", 8)
                    # Continue without data enhancement
            
            # Build the graphs
            finder_app = build_finder_graph()
            creator_app = build_section_creator_graph()
            style_app = build_style_graph()
            
            # Get structure from style graph
            if progress_callback:
                progress_callback("🔍 Analyzing topic and generating structure...", 10)
            
            config = get_config()
            recursion_limits = config.get_recursion_limits()
            
            # Update progress before style graph
            if progress_callback:
                progress_callback("🎨 Running style analysis and structure generation...", 12)
            
            style_out: StyleState = style_app.invoke({
                "topic": topic,
                "client_id": company,
                "want_document": True,
                "max_docs": 5,
                "lookback_days": 540,
            }, config={"recursion_limit": recursion_limits['style_graph']})
            
            # Update progress after style graph
            if progress_callback:
                progress_callback("📊 Processing structure results...", 15)
            
            structure = style_out.get("structure", {}) or {}
            sections = structure.get("sections", []) or []
            tone = structure.get("tone", "formal, factual, concise")
            phrase_bank = structure.get("phrase_bank", []) or []
            boilerplate = structure.get("boilerplate", "") or ""
            
            if progress_callback:
                progress_callback(f"📋 Generated structure with {len(sections)} sections", 20)
            
            # Cross-section memory
            section_memory: Dict[str, Dict[str, Any]] = {}
            per_section_results: Dict[str, Any] = {}
            assembled_md_parts: List[str] = []
            
            # Process each section with real-time updates
            for i, s in enumerate(sections):
                sec_name = (s.get("name") or "Section").strip()
                sec_notes = s.get("notes", "")
                
                # Initialize section as "working"
                per_section_results[sec_name] = {
                    "status": "working",
                    "content": f"🔄 Working on {sec_name}...",
                    "final_md": "",
                    "draft_md": "",
                    "evidence": [],
                    "citations": []
                }
                
                # Yield update to show section is being worked on
                yield {"type": "sections_update", "sections": per_section_results}
                
                if progress_callback:
                    progress_callback(f"🔍 Finding evidence for: {sec_name}", 20 + (i * 60 // len(sections)))
                
                # Get evidence search parameters from configuration
                config = get_config()
                evidence_params = config.get_evidence_search_params()
                
                # Prepare enhanced section notes with extracted data
                enhanced_notes = sec_notes
                if extracted_data:
                    data_context = self._format_data_context_for_section(extracted_data, sec_name, topic, company)
                    if data_context:
                        enhanced_notes = f"{sec_notes}\n\n**Data Context from uploaded file:**\n{data_context}" if sec_notes else f"**Data Context from uploaded file:**\n{data_context}"
                
                # Finder loop
                fstate: FinderState = {
                    "topic": topic,
                    "company": company,
                    "section_name": sec_name,
                    "section_notes": enhanced_notes,
                    "want_document": True,
                    "lookback_days": evidence_params['lookback_days'],
                    "top_k": evidence_params['top_k'],
                    "max_loops": evidence_params['max_loops'],
                    "allow_placeholders": True,
                    "section_memory": section_memory
                }
                try:
                    fout = finder_app.invoke(fstate, config={"recursion_limit": recursion_limits['finder_graph']})
                except Exception as e:
                    error_msg = f"Evidence search failed for '{sec_name}': {str(e)}"
                    print(f"Finder graph error for section '{sec_name}': {e}")
                    if progress_callback:
                        progress_callback(f"⚠️ {error_msg}", 20 + ((i + 1) * 50 // len(sections)))
                    # Create fallback evidence if finder fails
                    fout = {
                        "evidence": [],
                        "needs_more": False,
                        "finder_request": None,
                        "diagnostics": {"error": str(e)},
                        "placeholders": [{"name": f"{sec_name} Data", "token": f"[{sec_name.upper().replace(' ', '_')}_DATA]", "hint": "data pending"}],
                        "editor_guidance": f"Create {sec_name} content using placeholder for missing data."
                    }
                
                # Get finder evidence
                finder_evidence = fout.get("evidence", [])
                
                # Add Excel data as evidence if available
                excel_evidence = []
                if extracted_data:
                    excel_evidence = self._create_excel_evidence(extracted_data, sec_name, topic, company)
                
                # Combine finder evidence with Excel evidence (Excel evidence first for priority)
                combined_evidence = excel_evidence + finder_evidence
                
                # DEBUG: Print evidence for debugging
                print(f"\n🔍 DEBUG - Evidence for section '{sec_name}':")
                print(f"   - Excel evidence count: {len(excel_evidence)}")
                print(f"   - Finder evidence count: {len(finder_evidence)}")
                print(f"   - Combined evidence count: {len(combined_evidence)}")
                
                if excel_evidence:
                    print(f"   - Excel evidence refs: {[e.get('ref', 'NO_REF') for e in excel_evidence]}")
                    for i, ev in enumerate(excel_evidence):
                        print(f"   - Excel evidence {i+1} text preview: {ev.get('text', 'NO_TEXT')[:200]}...")
                
                # Update section with combined evidence
                per_section_results[sec_name].update({
                    "needs_more": fout.get("needs_more", False),
                    "finder_request": fout.get("finder_request"),
                    "diagnostics": fout.get("diagnostics", {}),
                    "evidence": combined_evidence,
                    "content": f"✍️ Writing {sec_name}...",
                    "status": "writing"
                })
                
                # Yield update to show section is being written
                yield {"type": "sections_update", "sections": per_section_results}
                
                if progress_callback:
                    progress_callback(f"✍️ Writing section: {sec_name}", 20 + ((i + 0.5) * 60 // len(sections)))
                
                # Creator/Evaluator loop
                cstate: SectionState = {
                    "topic": topic,
                    "company": company,
                    "section_name": sec_name,
                    "section_notes": sec_notes,
                    "tone": tone,
                    "phrase_bank": phrase_bank,
                    "boilerplate": boilerplate,
                    "allow_placeholders": True,
                    "evidence": per_section_results[sec_name]["evidence"],
                    "placeholders": fout.get("placeholders", []),
                    "editor_guidance": fout.get("editor_guidance", ""),
                    "max_revisions": 2,
                    "section_memory": section_memory,
                    "writing_style_guidance": f"Use phrases from phrase bank naturally. Maintain {tone} tone throughout. Create comprehensive, detailed content.",
                    "style_consistency_notes": "Ensure consistent use of phrase bank terms and maintain professional tone across all paragraphs."
                }
                
                try:
                    cout = creator_app.invoke(cstate, config={"recursion_limit": recursion_limits['creator_graph']})
                except Exception as e:
                    error_msg = f"Content creation failed for '{sec_name}': {str(e)}"
                    print(f"Creator graph error for section '{sec_name}': {e}")
                    if progress_callback:
                        progress_callback(f"⚠️ {error_msg}", 20 + ((i + 1) * 60 // len(sections)))
                    # Create fallback content if creator fails
                    cout = {
                        "accepted": False,
                        "draft_md": f"[{sec_name.upper().replace(' ', '_')}_CONTENT]",
                        "needs_revision": True,
                        "revision_instructions": [f"Content creation failed: {str(e)}"],
                        "citations": []
                    }
                
                # Handle refinement if needed
                if cout.get("ask_finder_keywords"):
                    add_kw = cout.get("ask_finder_keywords") or []
                    fstate["finder_request"] = {"add_keywords": add_kw}
                    fstate["loops_run"] = 0
                    try:
                        fout2 = finder_app.invoke(fstate)
                        cstate["evidence"] = fout2.get("evidence", [])
                        cout = creator_app.invoke(cstate, config={"recursion_limit": recursion_limits['creator_graph']})
                    except Exception as e:
                        error_msg = f"Refinement failed for '{sec_name}': {str(e)}"
                        print(f"Refinement error for section '{sec_name}': {e}")
                        if progress_callback:
                            progress_callback(f"⚠️ {error_msg}", 20 + ((i + 1) * 60 // len(sections)))
                
                # Save results and update display
                if cout.get("accepted"):
                    final_md = cout.get("final_md", "").strip()
                    section_memory[sec_name] = {"text": final_md, "citations": cout.get("citations", [])}
                    per_section_results[sec_name].update({
                        "final_md": final_md,
                        "citations": cout.get("citations", []),
                        "content": final_md,
                        "status": "completed"
                    })
                    # Clean the content to remove any existing headers
                    cleaned_content = _clean_section_content(final_md, sec_name)
                    assembled_md_parts.append(f"## {sec_name}\n\n{cleaned_content}\n")
                    
                    if progress_callback:
                        progress_callback(f"✅ Completed: {sec_name}", 20 + ((i + 1) * 60 // len(sections)))
                else:
                    draft_md = cout.get("draft_md", "")
                    per_section_results[sec_name].update({
                        "draft_md": draft_md,
                        "needs_revision": cout.get("needs_revision", False),
                        "revision_instructions": cout.get("revision_instructions", []),
                        "content": draft_md,
                        "status": "draft"
                    })
                    # Clean the content to remove any existing headers
                    cleaned_content = _clean_section_content(draft_md, sec_name)
                    assembled_md_parts.append(f"## {sec_name}\n\n{cleaned_content}\n")
                    
                    if progress_callback:
                        progress_callback(f"⚠️ Draft completed: {sec_name}", 20 + ((i + 1) * 60 // len(sections)))
                
                # Yield update with final section result
                yield {"type": "sections_update", "sections": per_section_results}
            
            # Final assembly
            final_markdown = "\n".join(assembled_md_parts).strip()
            
            # Quality check with FinalCheckerAgent
            if progress_callback:
                progress_callback("🔍 Running final quality check...", 95)
            
            try:
                checker_agent = FinalCheckerAgent()
                check_state = {
                    "title": f"{company} - {topic}",
                    "company": company,
                    "topic": topic,
                    "final_content": final_markdown
                }
                checked_state = checker_agent.run(check_state)
                quality_check = checked_state.get("quality_check", {})
            except Exception as e:
                print(f"Quality check failed: {e}")
                quality_check = {
                    "overall_score": 7,
                    "critical_issues": ["Quality check failed"],
                    "suggestions": ["Manual review recommended"],
                    "compliance_flags": [],
                    "ready_for_export": True
                }
            
            # Final Processing Chain (4 stages)
            if progress_callback:
                progress_callback("🔧 Running final processing chain...", 97)
            
            try:
                processing_chain_agent = FinalProcessingChainAgent()
                processing_state = {
                    "title": f"{company} - {topic}",
                    "company": company,
                    "topic": topic,
                    "final_content": final_markdown,
                    "excel_data": extracted_data or {},
                    "progress_callback": progress_callback
                }
                processed_state = processing_chain_agent.run(processing_state)
                final_processed_content = processed_state.get("final_processed_content", final_markdown)
                processing_chain_results = processed_state.get("processing_chain_results", {})
            except Exception as e:
                print(f"Final processing chain failed: {e}")
                final_processed_content = final_markdown
                processing_chain_results = {
                    "error": str(e),
                    "fallback_used": True
                }
            
            if progress_callback:
                progress_callback("🎉 Press release generation completed!", 100)
            
            # Yield final result
            yield {
                "type": "final_result",
                "result": {
                    "success": True,
                    "content": final_processed_content,
                    "sections": per_section_results,
                    "structure": structure,
                    "quality_check": quality_check,
                    "processing_chain_results": processing_chain_results,
                    "metadata": {
                        "topic": topic,
                        "company": company,
                        "tone": tone,
                        "phrase_bank": phrase_bank,
                        "boilerplate": boilerplate,
                        "generated_at": datetime.now().isoformat()
                    }
                }
            }
            
        except Exception as e:
            if progress_callback:
                progress_callback(f"❌ Error: {str(e)}", 100)
            yield {
                "type": "final_result",
                "result": {
                    "success": False,
                    "error": str(e),
                    "content": "",
                    "sections": {},
                    "structure": {},
                    "metadata": {}
                }
            }

# Helper function to clean section content and remove duplicate headers
def _clean_section_content(content: str, section_name: str) -> str:
    """Clean section content by removing duplicate headers and improving formatting"""
    if not content:
        return content
    
    # Remove any existing headers that match the section name
    lines = content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Skip lines that are just the section name as a header
        if line.strip().startswith('#') and section_name.lower() in line.lower():
            continue
        # Skip lines that are just the section name without headers
        if line.strip().lower() == section_name.lower():
            continue
        cleaned_lines.append(line)
    
    # Join lines and clean up extra whitespace
    cleaned_content = '\n'.join(cleaned_lines).strip()
    
    # Remove multiple consecutive newlines
    import re
    cleaned_content = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_content)
    
    return cleaned_content

# Initialize the agent
agent = PressReleaseAgent()

# Custom CSS for ultra-modern styling
custom_css = """
/* Ultra-modern dark theme with glassmorphism */
.gradio-container {
    background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
    min-height: 100vh;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* Glassmorphism cards */
.card {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    padding: 30px;
    margin: 20px 0;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
    /* backdrop-filter: blur(20px); */ /* Removed to prevent overlay effect */
    border: 1px solid rgba(255, 255, 255, 0.2);
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.card:hover {
    transform: translateY(-5px);
    box-shadow: 0 30px 60px rgba(0, 0, 0, 0.4);
    border-color: rgba(255, 255, 255, 0.2);
}

/* Modern button styling */
.btn-primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: none;
    border-radius: 50px;
    padding: 16px 32px;
    color: white;
    font-weight: 600;
    font-size: 16px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.btn-primary::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
    transition: left 0.5s;
}

.btn-primary:hover::before {
    left: 100%;
}

.btn-primary:hover {
    transform: translateY(-3px) scale(1.05);
    box-shadow: 0 15px 35px rgba(102, 126, 234, 0.4);
}

/* Ultra-modern input styling */
input, textarea, select {
    background: rgba(255, 255, 255, 0.95);
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-radius: 15px;
    padding: 16px 20px;
    color: #333 !important;
    font-size: 16px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    backdrop-filter: blur(10px);
}

/* Specific Gradio textarea styling */
.gr-textarea textarea {
    background: rgba(255, 255, 255, 0.95) !important;
    color: #333 !important;
    border: 2px solid rgba(255, 255, 255, 0.3) !important;
}

.gr-textarea textarea::placeholder {
    color: rgba(51, 51, 51, 0.6) !important;
}

/* Specific Gradio input styling */
.gr-textbox input {
    background: rgba(255, 255, 255, 0.95) !important;
    color: #333 !important;
    border: 2px solid rgba(255, 255, 255, 0.3) !important;
}

.gr-textbox input::placeholder {
    color: rgba(51, 51, 51, 0.6) !important;
}

input::placeholder, textarea::placeholder {
    color: rgba(51, 51, 51, 0.6);
}

input:focus, textarea:focus, select:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.2);
    background: rgba(255, 255, 255, 1);
    transform: translateY(-2px);
}

/* Header styling */
.header {
    text-align: center;
    color: white;
    margin-bottom: 50px;
    position: relative;
}

.header h1 {
    font-size: 3.5em;
    margin: 0;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 800;
    letter-spacing: -2px;
}

.header p {
    font-size: 1.3em;
    opacity: 0.8;
    margin: 20px 0;
    font-weight: 300;
}

/* Tab styling */
.tab-nav {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 15px;
    padding: 8px;
    margin-bottom: 30px;
    backdrop-filter: blur(20px);
}

.tab-nav button {
    background: transparent;
    border: none;
    color: rgba(255, 255, 255, 0.7);
    padding: 12px 24px;
    border-radius: 10px;
    transition: all 0.3s ease;
    font-weight: 500;
}

.tab-nav button.active {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
}

/* Document viewer styling */
.document-viewer {
    background: white;
    border-radius: 20px;
    padding: 30px;
    max-height: none;
    overflow-y: visible;
    border: 1px solid rgba(0, 0, 0, 0.1);
    color: #333;
    line-height: 1.8;
}

/* Final result specific styling */
#final-result {
    background: white !important;
    color: #333 !important;
    padding: 30px !important;
    border-radius: 15px !important;
    border: 1px solid #ddd !important;
    max-height: none !important;
    overflow-y: visible !important;
}

#final-result h1, #final-result h2, #final-result h3, #final-result h4 {
    color: #2c3e50 !important;
    margin-top: 20px !important;
    margin-bottom: 10px !important;
}

#final-result p {
    color: #333 !important;
    margin-bottom: 15px !important;
    line-height: 1.6 !important;
}

#final-result blockquote {
    background: #f8f9fa !important;
    border-left: 4px solid #667eea !important;
    padding: 15px !important;
    margin: 20px 0 !important;
    color: #555 !important;
}

/* Prompt area styling */
.prompt-area {
    background: rgba(255, 255, 255, 0.03);
    border-radius: 20px;
    padding: 25px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(20px);
    color: white;
}

/* Status messages */
.status-success {
    color: #4ade80;
    font-weight: 600;
    background: rgba(74, 222, 128, 0.1);
    padding: 12px 20px;
    border-radius: 10px;
    border: 1px solid rgba(74, 222, 128, 0.2);
}

/* Progress bar improvements for better visibility */
.progress-text {
    color: #ffffff !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5) !important;
}

/* Progress bar container styling */
.progress-container {
    background: rgba(255, 255, 255, 0.05) !important;
    border-radius: 10px !important;
    padding: 10px !important;
    margin: 10px 0 !important;
}

.status-error {
    color: #f87171;
    font-weight: 600;
    background: rgba(248, 113, 113, 0.1);
    padding: 12px 20px;
    border-radius: 10px;
    border: 1px solid rgba(248, 113, 113, 0.2);
}

/* File upload styling */
.upload-area {
    border: 2px dashed rgba(255, 255, 255, 0.3);
    border-radius: 20px;
    padding: 40px;
    text-align: center;
    transition: all 0.3s ease;
    background: rgba(255, 255, 255, 0.02);
}

.upload-area:hover {
    border-color: #667eea;
    background: rgba(102, 126, 234, 0.05);
}

/* Dropdown styling */
select {
    background: rgba(255, 255, 255, 0.95);
    color: #333;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-radius: 15px;
    padding: 16px 20px;
    backdrop-filter: blur(10px);
}

select option {
    background: #fff;
    color: #333;
}

/* Scrollbar styling */
::-webkit-scrollbar {
    width: 8px;
}

::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 10px;
}

::-webkit-scrollbar-thumb {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 10px;
}

::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%);
}

/* Animation keyframes */
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(30px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.card {
    animation: fadeInUp 0.6s ease-out;
}

/* Step progress indicator */
.step-progress {
    display: flex;
    justify-content: center;
    align-items: center;
    margin: 30px 0;
    gap: 20px;
}

.step-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 20px;
    border-radius: 25px;
    background: rgba(255, 255, 255, 0.05);
    border: 2px solid rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.5);
    transition: all 0.3s ease;
}

.step-item.active {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-color: #667eea;
    color: white;
    box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
}

.step-item.completed {
    background: rgba(74, 222, 128, 0.1);
    border-color: #4ade80;
    color: #4ade80;
}

.step-number {
    width: 30px;
    height: 30px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    background: rgba(255, 255, 255, 0.1);
}

.step-item.active .step-number {
    background: rgba(255, 255, 255, 0.2);
}

.step-item.completed .step-number {
    background: #4ade80;
    color: white;
}

/* Knowledge library styling */
.knowledge-panel {
    position: sticky;
    top: 20px;
    max-height: calc(100vh - 40px);
    overflow-y: auto;
}

/* Step navigation buttons */
.step-nav {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 30px;
    gap: 20px;
}

.step-nav .btn-primary {
    flex: 1;
    max-width: 200px;
}

/* Responsive design */
@media (max-width: 768px) {
    .header h1 {
        font-size: 2.5em;
    }
    
    .card {
        padding: 20px;
        margin: 10px 0;
    }
    
    .btn-primary {
        padding: 14px 28px;
        font-size: 14px;
    }
    
    .step-progress {
        flex-direction: column;
        gap: 10px;
    }
    
    .step-item {
        width: 100%;
        justify-content: center;
    }
}
"""

def create_release_interface():
    """Create the ultra-modern interface for creating new releases"""
    with gr.Row():
        with gr.Column(scale=1):
            # Modern header with icon
            gr.HTML("""
            <div class="card" style="text-align: center; margin-bottom: 30px;">
                <div style="font-size: 3em; margin-bottom: 15px;">📊</div>
                <h2 style="margin: 0; color: white; font-weight: 600;">Upload Excel Data</h2>
                <p style="margin: 10px 0 0 0; color: rgba(255,255,255,0.7);">Transform your data into compelling press releases</p>
            </div>
            """)
            
            # Modern file upload area
            excel_file = gr.File(
                label="",
                file_types=[".xlsx", ".xls"],
                height=120,
                elem_classes=["upload-area"]
            )
            
            # Modern input fields
            title_input = gr.Textbox(
                label="Press Release Title",
                placeholder="Enter a compelling title for your press release...",
                lines=1,
                value=""
            )
            
            description_input = gr.Textbox(
                label="Description (Optional)",
                placeholder="Brief description of the press release...",
                lines=3,
                value=""
            )
            
            # Modern button with animation
            create_btn = gr.Button(
                "🚀 Generate Press Release", 
                variant="primary", 
                elem_classes=["btn-primary"],
                scale=1
            )
            
            # Status area
            create_status = gr.Markdown("", elem_classes=["status-success"], visible=False)

    return excel_file, title_input, description_input, create_btn, create_status

def view_releases_interface():
    """Create the ultra-modern interface for viewing past releases"""
    with gr.Row():
        with gr.Column(scale=1):
            # Modern header
            gr.HTML("""
            <div class="card" style="text-align: center; margin-bottom: 30px;">
                <div style="font-size: 3em; margin-bottom: 15px;">📰</div>
                <h2 style="margin: 0; color: white; font-weight: 600;">Past Press Releases</h2>
                <p style="margin: 10px 0 0 0; color: rgba(255,255,255,0.7);">Browse and manage your previous releases</p>
            </div>
            """)
            
            # Modern controls
            with gr.Row():
                refresh_btn = gr.Button(
                    "🔄 Refresh", 
                    variant="secondary",
                    scale=1
                )
                releases_dropdown = gr.Dropdown(
                    label="Select a Release",
                    choices=[],
                    interactive=True,
                    scale=3
                )
            
            view_btn = gr.Button(
                "👁️ View Release", 
                variant="primary", 
                elem_classes=["btn-primary"],
                scale=1
            )
            
            # Release details with modern styling
            release_title = gr.Markdown("", visible=False, elem_classes=["card"])
            release_date = gr.Markdown("", visible=False, elem_classes=["card"])
            release_content = gr.Markdown("", elem_classes=["document-viewer"], visible=False)
            
            # Modern action buttons
            with gr.Row():
                edit_btn = gr.Button(
                    "✏️ Edit", 
                    variant="secondary", 
                    visible=False,
                    scale=1
                )
                delete_btn = gr.Button(
                    "🗑️ Delete", 
                    variant="stop", 
                    visible=False,
                    scale=1
                )

    return (refresh_btn, releases_dropdown, view_btn, release_title, release_date, 
            release_content, edit_btn, delete_btn)

def edit_interface():
    """Create the ultra-modern interface for editing releases"""
    with gr.Row():
        with gr.Column(scale=1):
            # Modern header
            gr.HTML("""
            <div class="card" style="text-align: center; margin-bottom: 30px;">
                <div style="font-size: 3em; margin-bottom: 15px;">✏️</div>
                <h2 style="margin: 0; color: white; font-weight: 600;">Edit Press Release</h2>
                <p style="margin: 10px 0 0 0; color: rgba(255,255,255,0.7);">Refine and perfect your content</p>
            </div>
            """)
            
            # Modern text editor
            edit_content = gr.Textbox(
                label="Press Release Content",
                placeholder="Edit your press release content here...",
                lines=25,
                elem_classes=["prompt-area"],
                value=""
            )
            
            # Modern action buttons
            with gr.Row():
                save_btn = gr.Button(
                    "💾 Save Changes", 
                    variant="primary", 
                    elem_classes=["btn-primary"],
                    scale=1
                )
                cancel_btn = gr.Button(
                    "❌ Cancel", 
                    variant="secondary",
                    scale=1
                )
            
            # Status area
            edit_status = gr.Markdown("", elem_classes=["status-success"], visible=False)

    return edit_content, save_btn, cancel_btn, edit_status

# Event handlers with enhanced functionality
def create_release(excel_file, title, description):
    """Handle creating a new press release with enhanced feedback"""
    if not excel_file or not title:
        return gr.Markdown("❌ Please provide both an Excel file and a title.", visible=True)
    
    # Simulate processing with enhanced feedback
    result = agent.create_release_from_excel(excel_file, title, description)
    
    # Return with enhanced styling
    if "✅" in result:
        return gr.Markdown(f"""
        <div style="background: rgba(74, 222, 128, 0.1); border: 1px solid rgba(74, 222, 128, 0.3); 
                    border-radius: 15px; padding: 20px; color: #4ade80;">
            <h3 style="margin: 0 0 10px 0; color: #4ade80;">🎉 Success!</h3>
            <p style="margin: 0;">{result}</p>
        </div>
        """, visible=True)
    else:
        return gr.Markdown(f"""
        <div style="background: rgba(248, 113, 113, 0.1); border: 1px solid rgba(248, 113, 113, 0.3); 
                    border-radius: 15px; padding: 20px; color: #f87171;">
            <h3 style="margin: 0 0 10px 0; color: #f87171;">⚠️ Error</h3>
            <p style="margin: 0;">{result}</p>
        </div>
        """, visible=True)

def generate_ai_press_release(generation_mode, excel_file, title, description, company, topic):
    """Generate press release using AI with real-time progress updates"""
    try:
        if generation_mode == "ai":
            if not topic:
                return (
                    gr.Column(visible=False),  # step1
                    gr.Column(visible=False),  # step2
                    gr.Column(visible=True),   # step3
                    gr.Column(visible=False),  # step4
                    gr.Column(visible=False),  # step5
                    3,  # current_step
                    {},  # wizard_data
                    gr.Markdown("❌ Please provide a topic for AI generation.", visible=True),
                    gr.HTML("", visible=False),
                    gr.Markdown("", visible=False),
                    gr.Markdown("", visible=False)  # current_content_display
                )
            
            # Create progress bar for this function
            # progress = gr.Progress()  # Commented out to remove overlay
            
            # Progress callback function that updates the UI
            def progress_callback(message, percentage):
                # Use a single, clear progress display with better visibility
                # progress(percentage / 100, desc=f"🔄 {message}")  # Commented out to remove overlay
                pass
                # Yield control to allow UI updates
                import time
                time.sleep(0.1)
            
            # Switch to generation view immediately
            yield (
                gr.Column(visible=False),  # step1
                gr.Column(visible=False),  # step2
                gr.Column(visible=False),  # step3
                gr.Column(visible=True),   # step4
                gr.Column(visible=False),  # step5
                4,  # current_step
                {},  # wizard_data
                gr.Markdown("🔄 Starting generation...", visible=True),
                gr.HTML("<div class='card'><h3 style='color: white; margin-bottom: 20px;'>📋 Preparing Generation...</h3><p>Initializing AI generation process...</p></div>", visible=True),
                gr.Markdown("", visible=False),
                gr.Markdown("", visible=False)  # current_content_display
            )
            
            # Generate with AI using generator for real-time updates
            result = None
            try:
                for update in agent.generate_press_release_with_ai_streaming(topic, company, progress_callback, excel_file):
                    if update["type"] == "sections_update":
                        # Create sections display HTML
                        sections_html = "<div class='card'><h3 style='color: white; margin-bottom: 20px;'>📋 Generating Sections...</h3>"
                        for section_name, section_data in update["sections"].items():
                            status_icon = "🔄" if section_data.get("status") == "working" else "✍️" if section_data.get("status") == "writing" else "✅" if section_data.get("status") == "completed" else "⚠️"
                            content = section_data.get('content', 'Working...')
                            sections_html += f"""
                            <div style='margin-bottom: 15px; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 10px; border: 1px solid rgba(255,255,255,0.2);'>
                                <h4 style='color: #667eea; margin: 0 0 10px 0;'>{status_icon} {section_name}</h4>
                                <div style='color: rgba(255,255,255,0.9); font-size: 0.9em; line-height: 1.4; white-space: pre-wrap;'>
                                    {content}
                                </div>
                            </div>
                            """
                        sections_html += "</div>"
                        
                        # Yield the update
                        yield (
                            gr.Column(visible=False),  # step1
                            gr.Column(visible=False),  # step2
                            gr.Column(visible=False),  # step3
                            gr.Column(visible=True),   # step4
                            gr.Column(visible=False),  # step5
                            4,  # current_step
                            {},  # wizard_data
                            gr.Markdown("🔄 Generating sections...", visible=True),
                            gr.HTML(sections_html, visible=True),
                            gr.Markdown("", visible=False),
                            gr.Markdown("", visible=False)  # current_content_display
                        )
                    elif update["type"] == "final_result":
                        result = update["result"]
                        break
            except Exception as streaming_error:
                # Handle streaming errors with proper frontend feedback
                error_message = f"❌ Generation failed: {str(streaming_error)}"
                if progress_callback:
                    progress_callback(error_message, 100)
                
                # Yield error state to frontend
                yield (
                    gr.Column(visible=False),  # step1
                    gr.Column(visible=False),  # step2
                    gr.Column(visible=True),   # step3
                    gr.Column(visible=False),  # step4
                    gr.Column(visible=False),  # step5
                    3,  # current_step
                    {},  # wizard_data
                    gr.Markdown(error_message, visible=True),
                    gr.HTML("", visible=False),
                    gr.Markdown("", visible=False),
                    gr.Markdown("", visible=False)  # current_content_display
                )
                return
            
            if result["success"]:
                # Create sections display with full text
                sections_html = "<div class='card'><h3 style='color: white; margin-bottom: 20px;'>📋 Generated Sections</h3>"
                for section_name, section_data in result["sections"].items():
                    status = "✅" if section_data.get("final_md") else "⚠️"
                    content = section_data.get('final_md', section_data.get('draft_md', 'No content generated'))
                    sections_html += f"""
                    <div style='margin-bottom: 20px; padding: 20px; background: rgba(255,255,255,0.1); border-radius: 10px; border: 1px solid rgba(255,255,255,0.2);'>
                        <h4 style='color: #667eea; margin: 0 0 15px 0; font-size: 1.2em;'>{status} {section_name}</h4>
                        <div style='color: rgba(255,255,255,0.9); font-size: 1em; line-height: 1.6; white-space: pre-wrap;'>
                            {content}
                        </div>
                    </div>
                    """
                sections_html += "</div>"
                
                # Use final processed content from processing chain
                final_content = result.get("content", "")
                processing_results = result.get("processing_chain_results", {})
                
                # Create processing chain summary
                processing_summary = ""
                if processing_results and not processing_results.get("fallback_used", False):
                    processing_summary = """
                    <div class='card' style='margin-bottom: 20px;'>
                        <h3 style='color: #4ade80; margin-bottom: 15px;'>🔧 Final Processing Chain Completed</h3>
                        <div style='color: rgba(255,255,255,0.9); font-size: 0.9em; line-height: 1.6;'>
                            <p><strong>✅ Stage 1:</strong> Placeholder consistency and repetition removal</p>
                            <p><strong>✅ Stage 2:</strong> Fact extraction and categorization</p>
                            <p><strong>✅ Stage 3:</strong> Fact verification against data sources</p>
                            <p><strong>✅ Stage 4:</strong> Final formatting and validation</p>
                        </div>
                    </div>
                    """
                
                yield (
                    gr.Column(visible=False),  # step1
                    gr.Column(visible=False),  # step2
                    gr.Column(visible=False),  # step3
                    gr.Column(visible=False),  # step4
                    gr.Column(visible=True),   # step5
                    5,  # current_step
                    {"content": final_content, "placeholders": result.get("placeholders", [])},  # wizard_data
                    gr.Markdown("🎉 AI Press release generated and processed successfully!", visible=True),
                    gr.HTML(processing_summary + sections_html, visible=True),
                    gr.Markdown(final_content, visible=True, elem_id="final-result"),
                    gr.Markdown(final_content, visible=True, elem_id="current-content")  # current_content_display
                )
            else:
                return (
                    gr.Column(visible=False),  # step1
                    gr.Column(visible=False),  # step2
                    gr.Column(visible=True),   # step3
                    gr.Column(visible=False),  # step4
                    gr.Column(visible=False),  # step5
                    3,  # current_step
                    {},  # wizard_data
                    gr.Markdown(f"❌ Error: {result.get('error', 'Unknown error')}", visible=True),
                    gr.HTML("", visible=False),
                    gr.Markdown("", visible=False),
                    gr.Markdown("", visible=False)  # current_content_display
                )
        else:
            # Traditional Excel generation
            if not excel_file or not title:
                return (
                    gr.Column(visible=False),  # step1
                    gr.Column(visible=False),  # step2
                    gr.Column(visible=True),   # step3
                    gr.Column(visible=False),  # step4
                    gr.Column(visible=False),  # step5
                    3,  # current_step
                    {},  # wizard_data
                    gr.Markdown("❌ Please provide both an Excel file and a title.", visible=True),
                    gr.HTML("", visible=False),
                    gr.Markdown("", visible=False),
                    gr.Markdown("", visible=False)  # current_content_display
                )
            
            result = agent.create_release_from_excel(excel_file, title, description)
            
            if "✅" in result:
                return (
                    gr.Column(visible=False),  # step1
                    gr.Column(visible=False),  # step2
                    gr.Column(visible=False),  # step3
                    gr.Column(visible=True),   # step4
                    gr.Column(visible=False),  # step5
                    4,  # current_step
                    {},  # wizard_data
                    gr.Markdown(f"🎉 Success! {result}", visible=True),
                    gr.HTML("", visible=False),
                    gr.Markdown("", visible=False),
                    gr.Markdown("", visible=False)  # current_content_display
                )
            else:
                return (
                    gr.Column(visible=False),  # step1
                    gr.Column(visible=False),  # step2
                    gr.Column(visible=True),   # step3
                    gr.Column(visible=False),  # step4
                    gr.Column(visible=False),  # step5
                    3,  # current_step
                    {},  # wizard_data
                    gr.Markdown(f"❌ Error: {result}", visible=True),
                    gr.HTML("", visible=False),
                    gr.Markdown("", visible=False),
                    gr.Markdown("", visible=False)  # current_content_display
                )
                
    except Exception as e:
        return (
            gr.Column(visible=False),  # step1
            gr.Column(visible=False),  # step2
            gr.Column(visible=True),   # step3
            gr.Column(visible=False),  # step4
            gr.Column(visible=False),  # step5
            3,  # current_step
            {},  # wizard_data
            gr.Markdown(f"❌ Unexpected error: {str(e)}", visible=True),
            gr.HTML("", visible=False),
            gr.Markdown("", visible=False),
            gr.Markdown("", visible=False)  # current_content_display
        )

def refresh_releases():
    """Refresh the releases dropdown"""
    releases = agent.get_release_list()
    choices = [(f"{r['title']} ({r['created_at'][:10]})", r['id']) for r in releases]
    return gr.Dropdown(choices=choices)

def view_release(release_id):
    """View a specific release"""
    if not release_id:
        return (gr.Markdown("", visible=False), gr.Markdown("", visible=False), 
                gr.Markdown("", visible=False), gr.Button(visible=False), gr.Button(visible=False))
    
    release = agent.get_release_by_id(release_id)
    if not release:
        return (gr.Markdown("❌ Release not found", visible=True), gr.Markdown("", visible=False), 
                gr.Markdown("", visible=False), gr.Button(visible=False), gr.Button(visible=False))
    
    title_md = f"## {release['title']}"
    date_md = f"**Created:** {release['created_at'][:10]} | **Updated:** {release['updated_at'][:10]}"
    
    return (gr.Markdown(title_md, visible=True), gr.Markdown(date_md, visible=True), 
            gr.Markdown(release['content'], visible=True), gr.Button(visible=True), gr.Button(visible=True))

def load_release_for_edit(release_id):
    """Load release content for editing"""
    if not release_id:
        return ""
    
    release = agent.get_release_by_id(release_id)
    if not release:
        return ""
    
    return release['content']

def save_release_changes(release_id, new_content):
    """Save changes to a release"""
    if not release_id:
        return "❌ No release selected."
    
    return agent.update_release_content(release_id, new_content)

# Step 5 helper functions
def go_back_to_step_4():
    """Navigate back to step 4 (generation)"""
    return (
        gr.Column(visible=False),  # step1
        gr.Column(visible=False),  # step2
        gr.Column(visible=False),  # step3
        gr.Column(visible=True),   # step4
        gr.Column(visible=False),  # step5
        4,  # current_step
        {}  # wizard_data
    )

def handle_chat_request(chat_input, chat_history, wizard_data):
    """Handle chat requests for content changes using ContentEditorAgent"""
    if not chat_input.strip():
        return chat_history, "", wizard_data
    
    # Add user message to chat history
    chat_history.append([chat_input, None])
    
    # Get current content from wizard_data
    current_content = wizard_data.get("content", "")
    
    try:
        # Create the agent
        editor_agent = ContentEditorAgent()
        
        # Process the request
        result = editor_agent.run(
            user_request=chat_input,
            current_content=current_content,
            chat_history=chat_history[:-1]  # Exclude the current message
        )
        
        if result.get("success", False):
            # Update the content in wizard_data
            wizard_data["content"] = result["modified_content"]
            
            # Create AI response
            ai_response = f"✅ **Changes Applied Successfully!**\n\n{result['explanation']}"
            
            if result.get("suggestions"):
                ai_response += f"\n\n**Additional Suggestions:**\n" + "\n".join([f"• {s}" for s in result["suggestions"]])
        else:
            ai_response = f"❌ **Unable to process request**\n\n{result.get('explanation', 'Please try rephrasing your request.')}"
            
            if result.get("suggestions"):
                ai_response += f"\n\n**Suggestions:**\n" + "\n".join([f"• {s}" for s in result["suggestions"]])
        
        # Add AI response to chat history
        chat_history[-1][1] = ai_response
        
    except Exception as e:
        # Fallback response if agent fails
        ai_response = f"❌ **Error processing request**\n\nI encountered an error while processing your request: {str(e)}\n\nPlease try rephrasing your request or contact support if the issue persists."
        chat_history[-1][1] = ai_response
    
    return chat_history, "", wizard_data

def clear_chat():
    """Clear the chat interface"""
    return [], ""

def download_placeholders_csv(wizard_data):
    """Download CSV with all placeholders found in the content"""
    import csv
    import tempfile
    import re
    
    content = wizard_data.get("content", "")
    placeholders = wizard_data.get("placeholders", [])
    
    # Extract placeholders from content using regex
    placeholder_pattern = r'\[([A-Z_]+)\]'
    found_placeholders = re.findall(placeholder_pattern, content)
    
    # Create CSV data
    csv_data = []
    for placeholder in found_placeholders:
        csv_data.append({
            'placeholder': f'[{placeholder}]',
            'value': '',
            'description': f'Value for {placeholder}',
            'section': 'To be determined'
        })
    
    # Add any additional placeholders from wizard_data
    for placeholder in placeholders:
        if isinstance(placeholder, dict):
            csv_data.append({
                'placeholder': placeholder.get('token', ''),
                'value': '',
                'description': placeholder.get('name', ''),
                'section': placeholder.get('hint', '')
            })
    
    # Create temporary CSV file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
    writer = csv.DictWriter(temp_file, fieldnames=['placeholder', 'value', 'description', 'section'])
    writer.writeheader()
    writer.writerows(csv_data)
    temp_file.close()
    
    return temp_file.name

def apply_placeholder_updates(csv_file, wizard_data):
    """Apply placeholder updates from uploaded CSV"""
    if not csv_file:
        return wizard_data.get("content", ""), wizard_data
    
    try:
        import pandas as pd
        
        # Read CSV file
        df = pd.read_csv(csv_file)
        
        # Get current content
        content = wizard_data.get("content", "")
        original_content = content
        
        # Replace placeholders with values
        replacements_made = 0
        for _, row in df.iterrows():
            placeholder = row['placeholder']
            value = str(row['value']) if pd.notna(row['value']) and str(row['value']).strip() else placeholder
            
            if placeholder in content and value != placeholder:
                content = content.replace(placeholder, value)
                replacements_made += 1
        
        # Update wizard_data
        wizard_data["content"] = content
        
        # Create feedback message
        if replacements_made > 0:
            feedback = f"✅ **Successfully updated {replacements_made} placeholder(s)!**\n\nThe content has been updated with the values from your CSV file."
        else:
            feedback = "⚠️ **No changes made**\n\nNo placeholder values were found or updated. Please check that your CSV contains valid placeholder values."
        
        return content, wizard_data
        
    except Exception as e:
        return f"❌ **Error applying placeholder updates**\n\n{str(e)}", wizard_data

def finalize_press_release(wizard_data):
    """Finalize the press release and save it"""
    content = wizard_data.get("content", "")
    
    if not content:
        return (
            gr.Column(visible=True),   # step1
            gr.Column(visible=False),  # step2
            gr.Column(visible=False),  # step3
            gr.Column(visible=False),  # step4
            gr.Column(visible=False),  # step5
            1,  # current_step
            {}  # wizard_data
        )
    
    # Save the press release (you can enhance this to save to database)
    release_id = agent.create_release_from_content(content, "AI Generated Press Release", "Generated using AI")
    
    return (
        gr.Column(visible=True),   # step1
        gr.Column(visible=False),  # step2
        gr.Column(visible=False),  # step3
        gr.Column(visible=False),  # step4
        gr.Column(visible=False),  # step5
        1,  # current_step
        {}  # wizard_data
    )

def delete_release(release_id):
    """Delete a release"""
    if not release_id:
        return "❌ No release selected."
    
    result = agent.delete_release(release_id)
    return result

# Step-by-step wizard interface
def create_step_wizard():
    """Create a step-by-step wizard interface"""
    
    # Step 1: Data Upload (Optional)
    with gr.Column(visible=True, elem_id="step-1") as step1:
        gr.HTML("""
        <div class="card" style="text-align: center; margin-bottom: 30px;">
            <div style="font-size: 3em; margin-bottom: 15px;">📊</div>
            <h2 style="margin: 0; color: white; font-weight: 600;">Step 1: Upload Your Data (Optional)</h2>
            <p style="margin: 10px 0 0 0; color: rgba(255,255,255,0.7);">Upload Excel data or skip to use AI generation</p>
        </div>
        """)
        
        # Generation mode selection
        initial_mode = gr.Radio(
            choices=[
                ("🤖 AI-Powered Generation (Recommended)", "ai"),
                ("📊 From Excel Data (Traditional)", "excel")
            ],
            value="ai",
            label="Choose Generation Method",
            elem_classes=["card"]
        )
        
        # Excel upload (conditional)
        with gr.Column(visible=False) as excel_upload_section:
            excel_file = gr.File(
                label="Upload Excel File",
                file_types=[".xlsx", ".xls"],
                height=120,
                elem_classes=["upload-area"]
            )
        
        # Skip option for AI generation
        with gr.Row():
            skip_btn = gr.Button(
                "🚀 Skip & Use AI Generation", 
                variant="primary", 
                elem_classes=["btn-primary"],
                scale=1
            )
            next_btn_1 = gr.Button(
                "Next Step →", 
                variant="secondary",
                scale=1
            )
    
    # Step 2: Content Configuration
    with gr.Column(visible=False, elem_id="step-2") as step2:
        gr.HTML("""
        <div class="card" style="text-align: center; margin-bottom: 30px;">
            <div style="font-size: 3em; margin-bottom: 15px;">✏️</div>
            <h2 style="margin: 0; color: white; font-weight: 600;">Step 2: Configure Content</h2>
            <p style="margin: 10px 0 0 0; color: rgba(255,255,255,0.7);">Define your press release details</p>
        </div>
        """)
        
        title_input = gr.Textbox(
            label="Press Release Title",
            placeholder="Enter a compelling title for your press release...",
            lines=1,
            value=""
        )
        
        description_input = gr.Textbox(
            label="Description (Optional)",
            placeholder="Brief description of the press release...",
            lines=3,
            value=""
        )
        
        tone_dropdown = gr.Dropdown(
            label="Tone of Voice",
            choices=["Professional", "Casual", "Formal", "Enthusiastic", "Technical"],
            value="Professional"
        )
        
        with gr.Row():
            prev_btn_2 = gr.Button("← Previous", variant="secondary", scale=1)
            next_btn_2 = gr.Button("Next Step →", variant="primary", elem_classes=["btn-primary"], scale=1)
    
    # Step 3: Review & Generate
    with gr.Column(visible=False, elem_id="step-3") as step3:
        gr.HTML("""
        <div class="card" style="text-align: center; margin-bottom: 30px;">
            <div style="font-size: 3em; margin-bottom: 15px;">🎯</div>
            <h2 style="margin: 0; color: white; font-weight: 600;">Step 3: Review & Generate</h2>
            <p style="margin: 10px 0 0 0; color: rgba(255,255,255,0.7);">Review your settings and generate the press release</p>
        </div>
        """)
        
        review_content = gr.Markdown("", elem_classes=["card"])
        
        # AI Generation Options
        with gr.Row():
            with gr.Column():
                gr.HTML("""
                <div class="card" style="margin-bottom: 20px;">
                    <h3 style="color: white; margin-bottom: 15px;">🤖 AI Generation Options</h3>
                    <p style="color: rgba(255,255,255,0.8); margin-bottom: 15px;">Choose how to generate your press release:</p>
                </div>
                """)
                
                generation_mode = gr.Radio(
                    choices=[
                        ("📊 From Excel Data (Traditional)", "excel"),
                        ("🤖 AI-Powered Generation (Advanced)", "ai")
                    ],
                    value="ai",
                    label="Generation Method",
                    elem_classes=["card"]
                )
                
                # AI-specific options
                with gr.Column(visible=True) as ai_options:
                    company_input = gr.Textbox(
                        label="Company Name",
                        placeholder="Enter company name (e.g., SISCO)",
                        value="SISCO",
                        lines=1
                    )
                    
                    topic_input = gr.Textbox(
                        label="Press Release Topic",
                        placeholder="Describe what you want to announce...",
                        lines=3
                    )
        
        with gr.Row():
            prev_btn_3 = gr.Button("← Previous", variant="secondary", scale=1)
            generate_btn = gr.Button("🚀 Generate Press Release", variant="primary", elem_classes=["btn-primary"], scale=1)
        
        # Progress tracking
        # progress_bar = gr.Progress()  # Commented out to remove overlay
        progress_status = gr.Markdown("", elem_classes=["status-success"], visible=False)
        
        # Real-time section display
        sections_display = gr.HTML("", visible=False)
        
        # Final result
        final_result = gr.Markdown("", elem_classes=["document-viewer"], visible=False)
        
        create_status = gr.Markdown("", elem_classes=["status-success"], visible=False)
    
    # Step 4: Generation Progress (New Screen)
    with gr.Column(visible=False, elem_id="step-4") as step4:
        gr.HTML("""
        <div class="card" style="text-align: center; margin-bottom: 30px;">
            <div style="font-size: 3em; margin-bottom: 15px;">⚡</div>
            <h2 style="margin: 0; color: white; font-weight: 600;">Generating Your Press Release</h2>
            <p style="margin: 10px 0 0 0; color: rgba(255,255,255,0.7);">AI is creating your content section by section</p>
        </div>
        """)
        
        # Progress tracking
        # progress_bar_gen = gr.Progress()  # Commented out to remove overlay
        progress_status_gen = gr.Markdown("", elem_classes=["status-success"], visible=False)
        
        # Real-time section display
        sections_display_gen = gr.HTML("", visible=False)
        
        # Final result with better styling
        final_result_gen = gr.Markdown("", elem_classes=["document-viewer"], visible=False, 
                                      elem_id="final-result")
        
        # Back button
        back_to_config_btn = gr.Button("← Back to Configuration", variant="secondary", scale=1)
    
    # Step 5: Chat & Edit (New Step)
    with gr.Column(visible=False, elem_id="step-5") as step5:
        gr.HTML("""
        <div class="card" style="text-align: center; margin-bottom: 30px;">
            <div style="font-size: 3em; margin-bottom: 15px;">💬</div>
            <h2 style="margin: 0; color: white; font-weight: 600;">Review & Edit Your Press Release</h2>
            <p style="margin: 10px 0 0 0; color: rgba(255,255,255,0.7);">Chat with AI to make changes or download placeholders to fill manually</p>
        </div>
        """)
        
        # Current content display
        current_content_display = gr.Markdown("", elem_classes=["document-viewer"], visible=True, 
                                            elem_id="current-content")
        
        # Chat interface for change requests
        chat_interface = gr.Chatbot(
            label="💬 Chat with AI Editor",
            height=400,
            show_label=True,
            container=True,
            bubble_full_width=False,
            show_copy_button=True
        )
        
        # Chat input
        chat_input = gr.Textbox(
            label="Type your change request here...",
            placeholder="e.g., 'Make the headline more exciting', 'Add more details about revenue growth', 'Change the tone to be more formal'",
            lines=2,
            max_lines=4
        )
        
        # Chat controls
        with gr.Row():
            send_chat_btn = gr.Button("Send Request", variant="primary", scale=1)
            clear_chat_btn = gr.Button("Clear Chat", variant="secondary", scale=1)
        
        # Placeholder management section
        gr.HTML("""
        <div class="card" style="margin-top: 30px;">
            <h3 style="color: white; margin-bottom: 15px;">📊 Placeholder Management</h3>
            <p style="color: rgba(255,255,255,0.7); margin-bottom: 20px;">
                Download a CSV with all placeholders found in your press release, fill in the values, and upload to update the content.
            </p>
        </div>
        """)
        
        with gr.Row():
            download_placeholders_btn = gr.Button("📥 Download Placeholders CSV", variant="secondary", scale=1)
            placeholder_csv_upload = gr.File(
                label="📤 Upload Filled Placeholders CSV",
                file_types=[".csv"],
                scale=1
            )
        
        # Apply placeholder updates
        apply_placeholders_btn = gr.Button("🔄 Apply Placeholder Updates", variant="primary", scale=1)
        
        # Final actions
        with gr.Row():
            back_to_generation_btn = gr.Button("← Back to Generation", variant="secondary", scale=1)
            finalize_btn = gr.Button("✅ Finalize Press Release", variant="primary", scale=1)
    
    return (step1, step2, step3, step4, step5, excel_file, title_input, description_input, tone_dropdown, 
            next_btn_1, next_btn_2, prev_btn_2, prev_btn_3, generate_btn, review_content, create_status,
            generation_mode, company_input, topic_input, ai_options, progress_bar, progress_status, 
            sections_display, final_result, initial_mode, excel_upload_section, skip_btn,
            progress_bar_gen, progress_status_gen, sections_display_gen, final_result_gen, back_to_config_btn,
            current_content_display, chat_interface, chat_input, send_chat_btn, clear_chat_btn,
            download_placeholders_btn, placeholder_csv_upload, apply_placeholders_btn, 
            back_to_generation_btn, finalize_btn)

# Knowledge Library Component
def create_knowledge_library():
    """Create a hidden knowledge library panel"""
    
    knowledge_content = gr.HTML("""
    <div class="card" style="max-height: 500px; overflow-y: auto;">
        <h3 style="color: white; margin-bottom: 20px;">📚 Knowledge Library</h3>
        
        <div style="margin-bottom: 25px;">
            <h4 style="color: #667eea; margin-bottom: 10px;">Press Release Best Practices</h4>
            <ul style="color: rgba(255,255,255,0.8); line-height: 1.6;">
                <li>Start with a compelling headline that captures attention</li>
                <li>Include the 5 W's: Who, What, When, Where, Why</li>
                <li>Use active voice and strong verbs</li>
                <li>Keep paragraphs short and scannable</li>
                <li>Include quotes from key stakeholders</li>
                <li>End with a clear call-to-action</li>
            </ul>
        </div>
        
        <div style="margin-bottom: 25px;">
            <h4 style="color: #667eea; margin-bottom: 10px;">Tone Guidelines</h4>
            <ul style="color: rgba(255,255,255,0.8); line-height: 1.6;">
                <li><strong>Professional:</strong> Formal, authoritative, business-focused</li>
                <li><strong>Casual:</strong> Friendly, approachable, conversational</li>
                <li><strong>Formal:</strong> Traditional, respectful, corporate</li>
                <li><strong>Enthusiastic:</strong> Energetic, exciting, optimistic</li>
                <li><strong>Technical:</strong> Precise, detailed, industry-specific</li>
            </ul>
        </div>
        
        <div style="margin-bottom: 25px;">
            <h4 style="color: #667eea; margin-bottom: 10px;">Structure Template</h4>
            <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; color: rgba(255,255,255,0.8);">
                <p><strong>1. Headline:</strong> Clear, compelling, under 10 words</p>
                <p><strong>2. Subheadline:</strong> Supporting details, 15-20 words</p>
                <p><strong>3. Lead Paragraph:</strong> Most important information</p>
                <p><strong>4. Body:</strong> Supporting details and quotes</p>
                <p><strong>5. Boilerplate:</strong> Company information</p>
                <p><strong>6. Contact Info:</strong> Media contact details</p>
            </div>
        </div>
        
        <div style="margin-bottom: 25px;">
            <h4 style="color: #667eea; margin-bottom: 10px;">Excel Data Tips</h4>
            <ul style="color: rgba(255,255,255,0.8); line-height: 1.6;">
                <li>Ensure column headers are descriptive</li>
                <li>Use consistent data formats</li>
                <li>Include numerical data for key metrics</li>
                <li>Add context in separate columns</li>
                <li>Remove empty rows and columns</li>
            </ul>
        </div>
    </div>
    """)
    
    return knowledge_content

# Create the main Gradio interface
def create_app():
    with gr.Blocks(css=custom_css, title="Press Release Agent", theme=gr.themes.Soft()) as app:
        # Ultra-modern header
        gr.HTML("""
        <div class="header">
            <div style="display: flex; align-items: center; justify-content: center; margin-bottom: 20px;">
                <div style="display: flex; align-items: center;">
                    <div style="font-size: 4em; margin-right: 20px; animation: pulse 2s infinite;">🚀</div>
                    <div>
                        <h1>Press Release Agent</h1>
                        <p>Create professional press releases step by step</p>
                    </div>
                </div>
            </div>
        </div>
        
        <style>
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        </style>
        """)
        
        # # Step indicator (simplified)
        step_indicator = gr.HTML("""
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="display: flex; justify-content: center; gap: 20px; align-items: center;">
                <div class="step-item active" id="step-indicator-1">
                    <div class="step-number">1</div>
                    <div class="step-label">Upload Data</div>
                </div>
                <div class="step-connector"></div>
                <div class="step-item" id="step-indicator-2">
                    <div class="step-number">2</div>
                    <div class="step-label">Configure</div>
                </div>
                <div class="step-connector"></div>
                <div class="step-item" id="step-indicator-3">
                    <div class="step-number">3</div>
                    <div class="step-label">Generate</div>
                </div>
                <div class="step-connector"></div>
                <div class="step-item" id="step-indicator-4">
                    <div class="step-number">4</div>
                    <div class="step-label">Results</div>
                </div>
            </div>
        </div>
        """)
        
        # Main content area
        with gr.Row():
            # Left side - Step wizard
            with gr.Column(scale=3):
                # Step wizard
                (step1, step2, step3, step4, step5, excel_file, title_input, description_input, tone_dropdown, 
                 next_btn_1, next_btn_2, prev_btn_2, prev_btn_3, generate_btn, review_content, create_status,
                 generation_mode, company_input, topic_input, ai_options, progress_bar, progress_status,
                 sections_display, final_result, initial_mode, excel_upload_section, skip_btn,
                 progress_bar_gen, progress_status_gen, sections_display_gen, final_result_gen, back_to_config_btn,
                 current_content_display, chat_interface, chat_input, send_chat_btn, clear_chat_btn,
                 download_placeholders_btn, placeholder_csv_upload, apply_placeholders_btn, 
                 back_to_generation_btn, finalize_btn) = create_step_wizard()
            
            # Right side - Knowledge library (always visible but collapsible)
            # with gr.Column(scale=1, visible=True, elem_id="knowledge-panel", elem_classes=["knowledge-panel"]) as knowledge_panel:
            #     # Collapsible header
            #     gr.HTML("""
            #     <div class="card" style="text-align: center; margin-bottom: 20px; cursor: pointer;" id="knowledge-header">
            #         <h3 style="margin: 0; color: white; font-weight: 600;">📚 Knowledge Library</h3>
            #         <p style="margin: 5px 0 0 0; color: rgba(255,255,255,0.7); font-size: 0.9em;">Click to expand/collapse</p>
            #     </div>
            #     """)
                
            #     # Collapsible content
            #     with gr.Column(visible=True, elem_id="knowledge-content"):
            #         knowledge_content = create_knowledge_library()
        
        # State management
        current_step = gr.State(1)
        wizard_data = gr.State({})
        knowledge_visible = gr.State(False)
        
        # Step navigation functions
        def update_step_indicator(step_num):
            """Update the step indicator HTML"""
            html = f"""
            <div style="text-align: center; margin-bottom: 30px;">
                <div style="display: flex; justify-content: center; gap: 20px; align-items: center;">
                    <div class="step-item {'active' if step_num >= 1 else ''}" id="step-indicator-1">
                        <div class="step-number">1</div>
                        <div class="step-label">Upload Data</div>
                    </div>
                    <div class="step-connector"></div>
                    <div class="step-item {'active' if step_num >= 2 else ''}" id="step-indicator-2">
                        <div class="step-number">2</div>
                        <div class="step-label">Configure</div>
                    </div>
                    <div class="step-connector"></div>
                    <div class="step-item {'active' if step_num >= 3 else ''}" id="step-indicator-3">
                        <div class="step-number">3</div>
                        <div class="step-label">Generate</div>
                    </div>
                    <div class="step-connector"></div>
                    <div class="step-item {'active' if step_num >= 4 else ''}" id="step-indicator-4">
                        <div class="step-number">4</div>
                        <div class="step-label">Results</div>
                    </div>
                </div>
            </div>
            """
            return gr.HTML(html)
        
        def go_to_step_2(excel_file):
            # Allow proceeding without Excel file for AI generation
            return (
                gr.Column(visible=False),  # step1
                gr.Column(visible=True),   # step2
                gr.Column(visible=False),  # step3
                gr.Column(visible=False),  # step4
                2,  # current_step
                {"excel_file": excel_file},  # wizard_data
                update_step_indicator(2)  # step_indicator
            )
        
        def go_to_step_3(title, description, tone, data):
            if title or data.get('mode') == 'ai':
                new_data = data.copy()
                new_data.update({
                    "title": title,
                    "description": description,
                    "tone": tone
                })
                
                # Create review content based on mode
                mode = data.get('mode', 'excel')
                if mode == 'ai':
                    review_text = f"""
                    ## Review Your AI Generation Configuration
                    
                    **Mode:** 🤖 AI-Powered Generation
                    **Title:** {title or 'Will be generated from topic'}
                    **Description:** {description or 'Will be generated from topic'}
                    **Tone:** {tone}
                    
                    Ready to generate your press release with AI?
                    """
                else:
                    review_text = f"""
                    ## Review Your Configuration
                    
                    **Mode:** 📊 Excel Data Generation
                    **Title:** {title}
                    **Description:** {description}
                    **Tone:** {tone}
                    **File:** {data.get('excel_file', 'No file uploaded')}
                    
                    Ready to generate your press release?
                    """
                
                return (
                    gr.Column(visible=False),  # step1
                    gr.Column(visible=False),  # step2
                    gr.Column(visible=True),   # step3
                    gr.Column(visible=False),  # step4
                    3,  # current_step
                    new_data,  # wizard_data
                    gr.Markdown(review_text),  # review_content
                    update_step_indicator(3)  # step_indicator

                )
            else:
                return (
                    gr.Column(visible=False),  # step1
                    gr.Column(visible=True),   # step2
                    gr.Column(visible=False),  # step3
                    gr.Column(visible=False),  # step4
                    2,  # current_step
                    data,  # wizard_data
                    gr.Markdown(""),  # review_content
                    update_step_indicator(3)  # step_indicator

                )
        
        def go_back_to_step_1():
            return (
                gr.Column(visible=True),   # step1
                gr.Column(visible=False),  # step2
                gr.Column(visible=False),  # step3
                gr.Column(visible=False),  # step4
                1,  # current_step
                {}  # wizard_data
            )
        
        def go_back_to_step_2(data):
            return (
                gr.Column(visible=False),  # step1
                gr.Column(visible=True),   # step2
                gr.Column(visible=False),  # step3
                gr.Column(visible=False),  # step4
                2,  # current_step
                data  # wizard_data
            )
        
        def go_to_step_4():
            return (
                gr.Column(visible=False),  # step1
                gr.Column(visible=False),  # step2
                gr.Column(visible=False),  # step3
                gr.Column(visible=True),   # step4
                4,  # current_step
                {},  # wizard_data
                update_step_indicator(4)  # step_indicator

            )
        
        def go_back_to_step_3():
            return (
                gr.Column(visible=False),  # step1
                gr.Column(visible=False),  # step2
                gr.Column(visible=True),   # step3
                gr.Column(visible=False),  # step4
                3,  # current_step
                {}  # wizard_data

            )
        
        # Knowledge library toggle function
        def toggle_knowledge_library(visible):
            return not visible, gr.Column(visible=not visible)
        
        # Add a hidden button for knowledge toggle (as backup)
        knowledge_toggle_btn = gr.Button("Toggle Knowledge", visible=False)
        
        # Mode selection handler
        def toggle_excel_upload(mode):
            if mode == "excel":
                return gr.Column(visible=True)
            else:
                return gr.Column(visible=False)
        
        # Skip to step 2 function
        def skip_to_step_2():
            return (
                gr.Column(visible=False),  # step1
                gr.Column(visible=True),   # step2
                gr.Column(visible=False),  # step3
                2,  # current_step
                {"excel_file": None, "mode": "ai"}  # wizard_data
            )
        
        # Event handlers
        initial_mode.change(
            toggle_excel_upload,
            inputs=[initial_mode],
            outputs=[excel_upload_section]
        )
        
        skip_btn.click(
            skip_to_step_2,
            outputs=[step1, step2, step3, step4, current_step, wizard_data]
        )
        
        next_btn_1.click(
            go_to_step_2,
            inputs=[excel_file],
            outputs=[step1, step2, step3, step4, current_step, wizard_data, step_indicator]
        )
        
        next_btn_2.click(
            go_to_step_3,
            inputs=[title_input, description_input, tone_dropdown, wizard_data],
            outputs=[step1, step2, step3, step4, current_step, wizard_data, review_content,step_indicator]
        )
        
        prev_btn_2.click(
            go_back_to_step_1,
            outputs=[step1, step2, step3, step4, current_step, wizard_data]
        )
        
        prev_btn_3.click(
            go_back_to_step_2,
            inputs=[wizard_data],
            outputs=[step1, step2, step3, step4, current_step, wizard_data]
        )
        
        generate_btn.click(
            generate_ai_press_release,
            inputs=[generation_mode, excel_file, title_input, description_input, company_input, topic_input],
            outputs=[step1, step2, step3, step4, step5, current_step, wizard_data, progress_status_gen, sections_display_gen, final_result_gen, current_content_display]
        )
        
        back_to_config_btn.click(
            go_back_to_step_3,
            outputs=[step1, step2, step3, step4, current_step, wizard_data]
        )
        
        # Step 5 event handlers
        back_to_generation_btn.click(
            go_back_to_step_4,
            outputs=[step1, step2, step3, step4, step5, current_step, wizard_data]
        )
        
        send_chat_btn.click(
            handle_chat_request,
            inputs=[chat_input, chat_interface, wizard_data],
            outputs=[chat_interface, chat_input, current_content_display, wizard_data]
        )
        
        chat_input.submit(
            handle_chat_request,
            inputs=[chat_input, chat_interface, wizard_data],
            outputs=[chat_interface, chat_input, current_content_display, wizard_data]
        )
        
        clear_chat_btn.click(
            clear_chat,
            outputs=[chat_interface, chat_input]
        )
        
        download_placeholders_btn.click(
            download_placeholders_csv,
            inputs=[wizard_data],
            outputs=[gr.File()]
        )
        
        apply_placeholders_btn.click(
            apply_placeholder_updates,
            inputs=[placeholder_csv_upload, wizard_data],
            outputs=[current_content_display, wizard_data]
        )
        
        finalize_btn.click(
            finalize_press_release,
            inputs=[wizard_data],
            outputs=[step1, step2, step3, step4, step5, current_step, wizard_data]
        )
        
        # Knowledge library toggle event
        # knowledge_toggle_btn.click(
        #     toggle_knowledge_library,
        #     inputs=[knowledge_visible],
        #     outputs=[knowledge_visible, knowledge_panel]
        # )
        
        # Modern footer with animations
        gr.HTML("""
        <div style="text-align: center; margin-top: 50px; color: white; opacity: 0.8;">
            <div style="display: flex; align-items: center; justify-content: center; gap: 20px;">
                <div style="animation: float 3s ease-in-out infinite;">✨</div>
                <p style="margin: 0; font-size: 1.1em;">Press Release Agent - Step by Step Professional PR Management</p>
                <div style="animation: float 3s ease-in-out infinite reverse;">✨</div>
            </div>
        </div>
        
        <style>
        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }
        </style>
        """)
        
        # Add JavaScript for enhanced interactivity
        app.load(
            fn=None,
            inputs=[],
            outputs=[],
            js="""
            // Simple collapsible knowledge library
            function setupKnowledgeToggle() {
                const knowledgeHeader = document.getElementById('knowledge-header');
                const knowledgeContent = document.getElementById('knowledge-content');
                
                if (knowledgeHeader && knowledgeContent) {
                    knowledgeContent.style.display = 'block';
                    
                    knowledgeHeader.addEventListener('click', function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                        
                        const isHidden = knowledgeContent.style.display === 'none';
                        
                        if (isHidden) {
                            knowledgeContent.style.display = 'block';
                            knowledgeHeader.querySelector('p').textContent = 'Click to expand/collapse';
                        } else {
                            knowledgeContent.style.display = 'none';
                            knowledgeHeader.querySelector('p').textContent = 'Click to expand/collapse';
                        }
                    });
                    
                    console.log('Knowledge library setup complete');
                } else {
                    console.log('Knowledge elements not found, retrying...');
                    setTimeout(setupKnowledgeToggle, 1000);
                }
            }
            
            function updateStepProgress(step) {
                const indicators = document.querySelectorAll('.step-item');
                indicators.forEach(function(indicator, index) {
                    indicator.classList.remove('active', 'completed');
                    if (index + 1 < step) {
                        indicator.classList.add('completed');
                    } else if (index + 1 === step) {
                        indicator.classList.add('active');
                    }
                });
            }
            
            function initializeApp() {
                setupKnowledgeToggle();
                updateStepProgress(1);
                console.log('Press Release Agent initialized');
            }
            
            // Initialize when ready
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', initializeApp);
            } else {
                initializeApp();
            }
            
            // Retry after delay
            setTimeout(initializeApp, 2000);
            """
        )
    
    return app

# Launch the application
if __name__ == "__main__":
    app = create_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
