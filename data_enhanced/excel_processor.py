"""
Comprehensive Excel Processing Module for Press Release Generation
Handles complex Excel files with multiple sheets, different company structures,
and varying column names under the SISCO umbrella.
"""

import pandas as pd
import json
import os
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import numpy as np
from datetime import datetime
import re

from base_agent import BaseAgent
from config_loader import get_config


class ExcelStructureAnalyzer(BaseAgent):
    """LLM-based Excel structure analyzer for complex multi-sheet files"""
    
    def __init__(self):
        super().__init__()
        self.config = get_config()
        self.agent_config = self.config.get_excel_processor_config()
        self.model_config = self.config.get_model_config('excel_processor')
    
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze Excel file structure and normalize data"""
        try:
            excel_file_path = state.get('excel_file_path', '')
            if not excel_file_path or not os.path.exists(excel_file_path):
                state.update({'success': False, 'error': 'Excel file not found'})
                return state
            
            # Read all sheets
            all_sheets = self._read_all_sheets(excel_file_path)
            
            # Analyze structure
            structure_analysis = self._analyze_excel_structure(all_sheets)
            
            # Normalize and consolidate data
            normalized_data = self._normalize_excel_data(all_sheets, structure_analysis)
            
            # Generate insights
            insights = self._generate_data_insights(normalized_data, structure_analysis)
            
            state.update({
                'success': True,
                'all_sheets': all_sheets,
                'structure_analysis': structure_analysis,
                'normalized_data': normalized_data,
                'insights': insights,
                'processed_at': datetime.now().isoformat()
            })
            
            return state
            
        except Exception as e:
            state.update({
                'success': False,
                'error': str(e),
                'processed_at': datetime.now().isoformat()
            })
            return state
    
    def _read_all_sheets(self, excel_file_path: str) -> Dict[str, pd.DataFrame]:
        """Read all sheets from Excel file"""
        try:
            excel_file = pd.ExcelFile(excel_file_path)
            all_sheets = {}
            
            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(excel_file_path, sheet_name=sheet_name)
                    # Clean the dataframe
                    df = self._clean_dataframe(df)
                    all_sheets[sheet_name] = df
                except Exception as e:
                    print(f"Warning: Could not read sheet '{sheet_name}': {e}")
                    continue
            
            return all_sheets
        except Exception as e:
            raise Exception(f"Error reading Excel file: {e}")
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize dataframe"""
        # Remove completely empty rows and columns
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        # Reset index
        df = df.reset_index(drop=True)
        
        # Clean column names
        df.columns = [str(col).strip() for col in df.columns]
        
        # Remove rows where all values are NaN
        df = df.dropna(how='all')
        
        return df
    
    def _analyze_excel_structure(self, all_sheets: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Use LLM to analyze Excel structure and identify patterns"""
        try:
            # Prepare structure data for LLM analysis
            structure_data = {}
            for sheet_name, df in all_sheets.items():
                structure_data[sheet_name] = {
                    'shape': df.shape,
                    'columns': list(df.columns),
                    'sample_data': df.head(3).to_dict('records'),
                    'data_types': df.dtypes.to_dict(),
                    'has_numeric_data': len(df.select_dtypes(include=[np.number]).columns) > 0
                }
            
            # Prepare LLM prompt
            system_prompt = self.agent_config.get('structure_analyzer', {}).get('system_prompt', '')
            user_prompt_template = self.agent_config.get('structure_analyzer', {}).get('user_prompt_template', '')
            
            user_prompt = user_prompt_template.format(
                structure_data=json.dumps(structure_data, indent=2, default=str)
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Get LLM analysis
            response = self.llm_inference(
                messages=messages,
                model=self.model_config['model'],
                temperature=self.model_config['temperature']
            )
            
            # Parse response
            try:
                analysis = json.loads(response)
            except json.JSONDecodeError:
                # Fallback analysis
                analysis = self._create_fallback_analysis(all_sheets)
            
            return analysis
            
        except Exception as e:
            print(f"Error in structure analysis: {e}")
            return self._create_fallback_analysis(all_sheets)
    
    def _create_fallback_analysis(self, all_sheets: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Create fallback analysis when LLM fails"""
        analysis = {
            'sheet_types': {},
            'common_metrics': [],
            'company_entities': [],
            'data_consolidation_strategy': 'merge_all',
            'normalization_rules': {}
        }
        
        for sheet_name, df in all_sheets.items():
            # Basic analysis
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            text_cols = df.select_dtypes(include=['object']).columns.tolist()
            
            analysis['sheet_types'][sheet_name] = {
                'type': 'financial' if any('revenue' in col.lower() or 'profit' in col.lower() for col in df.columns) else 'general',
                'numeric_columns': numeric_cols,
                'text_columns': text_cols,
                'row_count': len(df)
            }
            
            # Extract potential metrics
            for col in numeric_cols:
                if any(keyword in col.lower() for keyword in ['revenue', 'profit', 'margin', 'ebitda', 'cash', 'debt']):
                    analysis['common_metrics'].append(col)
        
        return analysis
    
    def _normalize_excel_data(self, all_sheets: Dict[str, pd.DataFrame], structure_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and consolidate data from all sheets"""
        try:
            normalized_data = {
                'consolidated_metrics': {},
                'company_data': {},
                'time_series_data': {},
                'summary_statistics': {}
            }
            
            # Process each sheet
            for sheet_name, df in all_sheets.items():
                # Extract company name from sheet name
                company_name = self._extract_company_name(sheet_name)
                
                # Process metrics
                metrics = self._extract_metrics_from_sheet(df, sheet_name)
                normalized_data['company_data'][company_name] = {
                    'sheet_name': sheet_name,
                    'metrics': metrics,
                    'raw_data': df.to_dict('records')
                }
                
                # Consolidate common metrics
                for metric_name, metric_data in metrics.items():
                    if metric_name not in normalized_data['consolidated_metrics']:
                        normalized_data['consolidated_metrics'][metric_name] = {}
                    normalized_data['consolidated_metrics'][metric_name][company_name] = metric_data
            
            # Generate summary statistics
            normalized_data['summary_statistics'] = self._generate_summary_statistics(normalized_data)
            
            return normalized_data
            
        except Exception as e:
            print(f"Error normalizing data: {e}")
            return {'consolidated_metrics': {}, 'company_data': {}, 'time_series_data': {}, 'summary_statistics': {}}
    
    def _extract_company_name(self, sheet_name: str) -> str:
        """Extract company name from sheet name"""
        # Remove common prefixes/suffixes
        name = sheet_name.replace('Financial Performance', '').replace('Performance', '').strip()
        
        # Clean up the name
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name if name else 'Unknown Company'
    
    def _extract_metrics_from_sheet(self, df: pd.DataFrame, sheet_name: str) -> Dict[str, Any]:
        """Extract financial metrics from a sheet"""
        metrics = {}
        
        # Look for common financial metrics
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                col_lower = col.lower()
                
                # Identify metric type
                metric_type = self._identify_metric_type(col_lower)
                
                if metric_type:
                    # Extract values
                    values = df[col].dropna().tolist()
                    if values:
                        metrics[metric_type] = {
                            'values': values,
                            'latest': values[-1] if values else None,
                            'previous': values[-2] if len(values) > 1 else None,
                            'trend': self._calculate_trend(values),
                            'column_name': col,
                            'unit': self._extract_unit(col)
                        }
        
        return metrics
    
    def _identify_metric_type(self, column_name: str) -> Optional[str]:
        """Use LLM to identify the type of financial metric from column name"""
        try:
            # Prepare the prompt for metric type identification
            system_prompt = self.agent_config.get('metric_identifier', {}).get('system_prompt', '')
            user_prompt_template = self.agent_config.get('metric_identifier', {}).get('user_prompt_template', '')
            
            user_prompt = user_prompt_template.format(column_name=column_name)
            
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
                result = json.loads(response)
                return result.get('metric_type')
            except json.JSONDecodeError:
                # Fallback to basic keyword matching if LLM fails
                return self._identify_metric_type_fallback(column_name)
                
        except Exception as e:
            print(f"Error in LLM metric identification: {e}")
            # Fallback to basic keyword matching
            return self._identify_metric_type_fallback(column_name)
    
    @staticmethod
    def _identify_metric_type_fallback(column_name: str) -> Optional[str]:
        """Fallback method for basic metric type identification"""
        column_name = column_name.lower()
        
        # Revenue metrics
        if any(keyword in column_name for keyword in ['revenue', 'sales', 'income']):
            return 'revenue'
        
        # Profit metrics
        if any(keyword in column_name for keyword in ['profit', 'earnings']):
            if 'operating' in column_name:
                return 'operating_profit'
            elif 'net' in column_name:
                return 'net_profit'
            else:
                return 'profit'
        
        # EBITDA
        if 'ebitda' in column_name:
            return 'ebitda'
        
        # Cash flow
        if any(keyword in column_name for keyword in ['cash flow', 'cashflow']):
            return 'cash_flow'
        
        # Margins
        if 'margin' in column_name:
            if 'gross' in column_name:
                return 'gross_margin'
            elif 'operating' in column_name:
                return 'operating_margin'
            elif 'net' in column_name:
                return 'net_margin'
            else:
                return 'margin'
        
        # Debt
        if 'debt' in column_name:
            return 'debt'
        
        # EPS
        if 'eps' in column_name:
            return 'eps'
        
        # Dividend
        if 'dividend' in column_name:
            return 'dividend'
        
        # ROACE
        if 'roace' in column_name:
            return 'roace'
        
        return None
    
    def _extract_unit(self, column_name: str) -> str:
        """Use LLM to extract unit from column name"""
        try:
            # Prepare the prompt for unit extraction
            system_prompt = self.agent_config.get('unit_extractor', {}).get('system_prompt', '')
            user_prompt_template = self.agent_config.get('unit_extractor', {}).get('user_prompt_template', '')
            
            user_prompt = user_prompt_template.format(column_name=column_name)
            
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
                result = json.loads(response)
                return result.get('unit', 'Units')
            except json.JSONDecodeError:
                # Fallback to basic keyword matching if LLM fails
                return self._extract_unit_fallback(column_name)
                
        except Exception as e:
            print(f"Error in LLM unit extraction: {e}")
            # Fallback to basic keyword matching
            return self._extract_unit_fallback(column_name)
    
    @staticmethod
    def _extract_unit_fallback(column_name: str) -> str:
        """Fallback method for basic unit extraction"""
        column_name = column_name.lower()
        
        if 'gbp' in column_name:
            return 'GBP'
        elif 'inr' in column_name:
            return 'INR'
        elif 'sar' in column_name:
            return 'SAR'
        elif 'usd' in column_name:
            return 'USD'
        elif '%' in column_name:
            return '%'
        elif 'mn' in column_name or 'million' in column_name:
            return 'Million'
        elif 'bn' in column_name or 'billion' in column_name:
            return 'Billion'
        elif 'k' in column_name or 'thousand' in column_name:
            return 'Thousand'
        else:
            return 'Units'
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend from values"""
        if len(values) < 2:
            return 'stable'
        
        latest = values[-1]
        previous = values[-2]
        
        if latest > previous * 1.05:  # 5% increase
            return 'increasing'
        elif latest < previous * 0.95:  # 5% decrease
            return 'decreasing'
        else:
            return 'stable'
    
    def _generate_summary_statistics(self, normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics from normalized data"""
        summary = {
            'total_companies': len(normalized_data['company_data']),
            'total_metrics': len(normalized_data['consolidated_metrics']),
            'metric_summary': {},
            'company_summary': {}
        }
        
        # Summarize each metric across companies
        for metric_name, companies_data in normalized_data['consolidated_metrics'].items():
            all_values = []
            for company, data in companies_data.items():
                if data.get('values'):
                    all_values.extend(data['values'])
            
            if all_values:
                summary['metric_summary'][metric_name] = {
                    'count': len(all_values),
                    'average': np.mean(all_values),
                    'min': np.min(all_values),
                    'max': np.max(all_values),
                    'companies_with_data': len(companies_data)
                }
        
        # Summarize each company
        for company, data in normalized_data['company_data'].items():
            summary['company_summary'][company] = {
                'metrics_count': len(data['metrics']),
                'has_revenue': 'revenue' in data['metrics'],
                'has_profit': any('profit' in metric for metric in data['metrics'].keys()),
                'data_quality': 'high' if len(data['metrics']) > 5 else 'medium' if len(data['metrics']) > 2 else 'low'
            }
        
        return summary
    
    def _generate_data_insights(self, normalized_data: Dict[str, Any], structure_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights from the processed data"""
        insights = {
            'key_findings': [],
            'performance_highlights': [],
            'trend_analysis': [],
            'recommendations': []
        }
        
        # Analyze performance across companies
        for metric_name, companies_data in normalized_data['consolidated_metrics'].items():
            if len(companies_data) > 1:
                # Find best and worst performers
                performance_data = []
                for company, data in companies_data.items():
                    if data.get('latest') is not None:
                        performance_data.append((company, data['latest']))
                
                if performance_data:
                    performance_data.sort(key=lambda x: x[1], reverse=True)
                    best_company, best_value = performance_data[0]
                    worst_company, worst_value = performance_data[-1]
                    
                    insights['performance_highlights'].append({
                        'metric': metric_name,
                        'best_performer': best_company,
                        'best_value': best_value,
                        'worst_performer': worst_company,
                        'worst_value': worst_value
                    })
        
        # Analyze trends
        for metric_name, companies_data in normalized_data['consolidated_metrics'].items():
            increasing_companies = []
            decreasing_companies = []
            
            for company, data in companies_data.items():
                if data.get('trend') == 'increasing':
                    increasing_companies.append(company)
                elif data.get('trend') == 'decreasing':
                    decreasing_companies.append(company)
            
            if increasing_companies or decreasing_companies:
                insights['trend_analysis'].append({
                    'metric': metric_name,
                    'increasing_companies': increasing_companies,
                    'decreasing_companies': decreasing_companies
                })
        
        return insights


class ExcelProcessor:
    """Main Excel processing class that coordinates all processing"""
    
    def __init__(self):
        self.analyzer = ExcelStructureAnalyzer()
    
    def process_excel_file(self, excel_file_path: str) -> Dict[str, Any]:
        """Process an Excel file and return comprehensive analysis"""
        state = {'excel_file_path': excel_file_path}
        result = self.analyzer.run(state)
        return result
    
    def get_context_for_section(self, processed_data: Dict[str, Any], section_name: str, topic: str = "", company: str = "") -> str:
        """Get context for a specific press release section using LLM with Excel data and company hierarchy"""
        if not processed_data.get('success', False):
            return ""
        
        try:
            # Get company hierarchy from MongoDB
            company_hierarchy = self._get_company_hierarchy(company)
            
            # Prepare data for LLM
            excel_data_summary = self._prepare_excel_data_summary(processed_data)
            
            # Use LLM to generate section-specific context
            context = self._generate_llm_context(
                section_name, topic, company, excel_data_summary, company_hierarchy
            )
            
            return context
            
        except Exception as e:
            print(f"Error generating LLM-based section context: {e}")
            # Fallback to basic context
            return self._create_basic_context(processed_data, section_name)
    
    def _get_company_hierarchy(self, company: str) -> Dict[str, Any]:
        """Get full company hierarchy from MongoDB (all levels)"""
        try:
            from mongo_interface import MongoInterface
            mi = MongoInterface()
            
            # Get company tree structure
            company_tree = mi.fetch_company_tree()
            
            # Find the company in the hierarchy
            hierarchy_info = {
                "company": company,
                "subsidiaries": [],
                "parent_companies": [],
                "full_hierarchy": {},
                "ownership_structure": {}
            }
            
            # Get all subsidiaries (recursive - all levels down)
            all_subsidiaries = self._get_all_subsidiaries(company, company_tree)
            hierarchy_info["subsidiaries"] = all_subsidiaries
            
            # Get all parent companies (recursive - all levels up)
            all_parents = self._get_all_parents(company, company_tree)
            hierarchy_info["parent_companies"] = all_parents
            
            # Build full hierarchy tree
            hierarchy_info["full_hierarchy"] = self._build_hierarchy_tree(company, company_tree)
            
            return hierarchy_info
            
        except Exception as e:
            print(f"Error fetching company hierarchy: {e}")
            return {"company": company, "subsidiaries": [], "parent_companies": [], "full_hierarchy": {}, "ownership_structure": {}}
    
    def _get_all_subsidiaries(self, company: str, company_tree: Dict[str, List[tuple]]) -> List[Dict[str, Any]]:
        """Recursively get all subsidiaries at all levels"""
        subsidiaries = []
        visited = set()
        
        def _collect_subsidiaries(current_company: str, level: int = 0):
            if current_company in visited or level > 10:  # Prevent infinite loops
                return
            
            visited.add(current_company)
            
            if current_company in company_tree:
                for child, percent in company_tree[current_company]:
                    subsidiaries.append({
                        "name": child,
                        "ownership_percent": percent,
                        "level": level + 1,
                        "parent": current_company
                    })
                    # Recursively get subsidiaries of this subsidiary
                    _collect_subsidiaries(child, level + 1)
        
        _collect_subsidiaries(company)
        return subsidiaries
    
    def _get_all_parents(self, company: str, company_tree: Dict[str, List[tuple]]) -> List[Dict[str, Any]]:
        """Recursively get all parent companies at all levels"""
        parents = []
        visited = set()
        
        def _collect_parents(current_company: str, level: int = 0):
            if current_company in visited or level > 10:  # Prevent infinite loops
                return
            
            visited.add(current_company)
            
            # Find all parents of current company
            for parent, children in company_tree.items():
                for child, percent in children:
                    if child == current_company:
                        parents.append({
                            "name": parent,
                            "ownership_percent": percent,
                            "level": level + 1,
                            "child": current_company
                        })
                        # Recursively get parents of this parent
                        _collect_parents(parent, level + 1)
        
        _collect_parents(company)
        return parents
    
    def _build_hierarchy_tree(self, company: str, company_tree: Dict[str, List[tuple]]) -> Dict[str, Any]:
        """Build a complete hierarchy tree structure"""
        def _build_tree(current_company: str, visited: set = None) -> Dict[str, Any]:
            if visited is None:
                visited = set()
            
            if current_company in visited:
                return {"name": current_company, "subsidiaries": [], "circular_reference": True}
            
            visited.add(current_company)
            
            tree = {
                "name": current_company,
                "subsidiaries": [],
                "is_root": current_company == company
            }
            
            if current_company in company_tree:
                for child, percent in company_tree[current_company]:
                    child_tree = _build_tree(child, visited.copy())
                    child_tree["ownership_percent"] = percent
                    tree["subsidiaries"].append(child_tree)
            
            return tree
        
        return _build_tree(company)
    
    def _prepare_excel_data_summary(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare Excel data in a format suitable for LLM processing"""
        summary = {
            "company_data": {},
            "insights": processed_data.get('insights', {}),
            "raw_data_sample": processed_data.get('raw_data_sample', [])
        }
        
        # Simplify company data for LLM
        if processed_data.get('company_data'):
            for company_name, data in processed_data['company_data'].items():
                if data.get('metrics'):
                    summary["company_data"][company_name] = {
                        "metrics": data['metrics'],
                        "performance_trends": data.get('performance_trends', {})
                    }
        
        return summary
    
    def _generate_llm_context(self, section_name: str, topic: str, company: str, 
                            excel_data: Dict[str, Any], company_hierarchy: Dict[str, Any]) -> str:
        """Use LLM to generate section-specific context"""
        try:
            from config_loader import get_config
            config = get_config()
            
            # Get LLM configuration
            llm_config = config.get_excel_processor_config().get('section_context_generator', {})
            model = llm_config.get('model', 'gpt-4o-mini')
            temperature = llm_config.get('temperature', 0.2)
            
            # Prepare system prompt
            system_prompt = llm_config.get('system_prompt', self._get_default_system_prompt())
            
            # Prepare user prompt
            user_prompt = self._prepare_user_prompt(section_name, topic, company, excel_data, company_hierarchy)
            
            # Use the existing LLM infrastructure
            analyzer = ExcelStructureAnalyzer()
            
            response = analyzer.llm_inference(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=model,
                temperature=temperature
            )
            
            return response.strip()
            
        except Exception as e:
            print(f"Error in LLM context generation: {e}")
            return self._create_basic_context(excel_data, section_name)
    
    def _get_default_system_prompt(self) -> str:
        """Default system prompt for section context generation"""
        return """You are an expert at analyzing financial and operational data to provide relevant context for press release sections.

Your task is to:
1. Analyze Excel data and company hierarchy information
2. Generate section-specific context that highlights the most relevant information
3. Focus on metrics, trends, and insights that are most important for the specific section type
4. Include company hierarchy context when relevant (subsidiaries, ownership structure)
5. Provide clear, structured context that will help write compelling press release content

Return only the context text, formatted with clear headers and bullet points."""
    
    def _prepare_user_prompt(self, section_name: str, topic: str, company: str, 
                           excel_data: Dict[str, Any], company_hierarchy: Dict[str, Any]) -> str:
        """Prepare user prompt for LLM"""
        import json
        
        prompt = f"""Generate context for the press release section: "{section_name}"

Topic: {topic}
Company: {company}

Excel Data Available:
{json.dumps(excel_data, indent=2, default=str)}

Company Hierarchy:
{json.dumps(company_hierarchy, indent=2, default=str)}

Please provide relevant context for this section, focusing on:
- The most important metrics and data points for this section type
- Company performance highlights
- Subsidiary performance (if relevant)
- Trends and insights that would be valuable for press release content
- Any ownership structure context that's relevant

Format the response with clear headers and bullet points for easy reading."""
        
        return prompt
    
    def _create_basic_context(self, processed_data: Dict[str, Any], section_name: str) -> str:
        """Fallback method to create basic context without LLM"""
        context_parts = [f"**{section_name} Data:**"]
        
        if processed_data.get('company_data'):
            for company_name, data in processed_data['company_data'].items():
                if data.get('metrics'):
                    context_parts.append(f"\n**{company_name}:**")
                    for metric_name, metric_data in data['metrics'].items():
                        if metric_data.get('latest') is not None:
                            unit = metric_data.get('unit', '')
                            trend = metric_data.get('trend', 'stable')
                            context_parts.append(f"- {metric_name.replace('_', ' ').title()}: {metric_data['latest']} {unit} (trend: {trend})")
        
        return "\n".join(context_parts) if context_parts else ""


# Utility functions for integration
def process_excel_for_ai_enhancement(excel_file_path: str) -> Dict[str, Any]:
    """Process Excel file and return data suitable for AI enhancement"""
    processor = ExcelProcessor()
    result = processor.process_excel_file(excel_file_path)
    
    if result.get('success', False):
        # Convert to format expected by existing AI enhancement
        return {
            'all_data_fields': result.get('normalized_data', {}).get('consolidated_metrics', {}),
            'summary_stats': result.get('normalized_data', {}).get('summary_statistics', {}),
            'raw_data_sample': result.get('normalized_data', {}).get('company_data', {}),
            'insights': result.get('insights', {}),
            'structure_analysis': result.get('structure_analysis', {})
        }
    else:
        return {
            'all_data_fields': {},
            'summary_stats': {},
            'raw_data_sample': {},
            'insights': {},
            'structure_analysis': {}
        }


def get_excel_context_for_section(excel_file_path: str, section_name: str, topic: str = "", company: str = "") -> str:
    """Get context for a specific section from Excel file"""
    processor = ExcelProcessor()
    processed_data = processor.process_excel_file(excel_file_path)
    return processor.get_context_for_section(processed_data, section_name, topic, company)
