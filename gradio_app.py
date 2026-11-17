import gradio as gr
import pandas as pd
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import uuid
from pathlib import Path

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
    background: rgba(255, 255, 255, 0.05);
    border-radius: 20px;
    padding: 30px;
    margin: 20px 0;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.1);
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
    background: rgba(255, 255, 255, 0.05);
    border: 2px solid rgba(255, 255, 255, 0.1);
    border-radius: 15px;
    padding: 16px 20px;
    color: white;
    font-size: 16px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    backdrop-filter: blur(10px);
}

input::placeholder, textarea::placeholder {
    color: rgba(255, 255, 255, 0.5);
}

input:focus, textarea:focus, select:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.2);
    background: rgba(255, 255, 255, 0.08);
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
    background: rgba(255, 255, 255, 0.03);
    border-radius: 20px;
    padding: 30px;
    max-height: 600px;
    overflow-y: auto;
    border: 1px solid rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(20px);
    color: white;
    line-height: 1.8;
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
    background: rgba(255, 255, 255, 0.05);
    color: white;
    border: 2px solid rgba(255, 255, 255, 0.1);
    border-radius: 15px;
    padding: 16px 20px;
    backdrop-filter: blur(10px);
}

select option {
    background: #1a1a2e;
    color: white;
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

def delete_release(release_id):
    """Delete a release"""
    if not release_id:
        return "❌ No release selected."
    
    result = agent.delete_release(release_id)
    return result

# Step-by-step wizard interface
def create_step_wizard():
    """Create a step-by-step wizard interface"""
    
    # Step 1: Data Upload
    with gr.Column(visible=True, elem_id="step-1") as step1:
        gr.HTML("""
        <div class="card" style="text-align: center; margin-bottom: 30px;">
            <div style="font-size: 3em; margin-bottom: 15px;">📊</div>
            <h2 style="margin: 0; color: white; font-weight: 600;">Step 1: Upload Your Data</h2>
            <p style="margin: 10px 0 0 0; color: rgba(255,255,255,0.7);">Upload your Excel file to get started</p>
        </div>
        """)
        
        excel_file = gr.File(
            label="",
            file_types=[".xlsx", ".xls"],
            height=120,
            elem_classes=["upload-area"]
        )
        
        next_btn_1 = gr.Button(
            "Next Step →", 
            variant="primary", 
            elem_classes=["btn-primary"],
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
        
        with gr.Row():
            prev_btn_3 = gr.Button("← Previous", variant="secondary", scale=1)
            generate_btn = gr.Button("🚀 Generate Press Release", variant="primary", elem_classes=["btn-primary"], scale=1)
        
        create_status = gr.Markdown("", elem_classes=["status-success"], visible=False)
    
    return (step1, step2, step3, excel_file, title_input, description_input, tone_dropdown, 
            next_btn_1, next_btn_2, prev_btn_2, prev_btn_3, generate_btn, review_content, create_status)

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
        
        # Step progress indicator
        gr.HTML("""
        <div class="step-progress">
            <div class="step-item active" id="step-indicator-1">
                <div class="step-number">1</div>
                <span>Upload Data</span>
            </div>
            <div class="step-item" id="step-indicator-2">
                <div class="step-number">2</div>
                <span>Configure</span>
            </div>
            <div class="step-item" id="step-indicator-3">
                <div class="step-number">3</div>
                <span>Generate</span>
            </div>
        </div>
        """)
        
        # Main content area
        with gr.Row():
            # Left side - Step wizard
            with gr.Column(scale=3):
                # Step wizard
                (step1, step2, step3, excel_file, title_input, description_input, tone_dropdown, 
                 next_btn_1, next_btn_2, prev_btn_2, prev_btn_3, generate_btn, review_content, create_status) = create_step_wizard()
            
            # Right side - Knowledge library (always visible but collapsible)
            with gr.Column(scale=1, visible=True, elem_id="knowledge-panel", elem_classes=["knowledge-panel"]) as knowledge_panel:
                # Collapsible header
                gr.HTML("""
                <div class="card" style="text-align: center; margin-bottom: 20px; cursor: pointer;" id="knowledge-header">
                    <h3 style="margin: 0; color: white; font-weight: 600;">📚 Knowledge Library</h3>
                    <p style="margin: 5px 0 0 0; color: rgba(255,255,255,0.7); font-size: 0.9em;">Click to expand/collapse</p>
                </div>
                """)
                
                # Collapsible content
                with gr.Column(visible=True, elem_id="knowledge-content"):
                    knowledge_content = create_knowledge_library()
        
        # State management
        current_step = gr.State(1)
        wizard_data = gr.State({})
        knowledge_visible = gr.State(False)
        
        # Step navigation functions
        def go_to_step_2(excel_file):
            if excel_file:
                return (
                    gr.Column(visible=False),  # step1
                    gr.Column(visible=True),   # step2
                    gr.Column(visible=False),  # step3
                    2,  # current_step
                    {"excel_file": excel_file}  # wizard_data
                )
            else:
                return (
                    gr.Column(visible=True),   # step1
                    gr.Column(visible=False),  # step2
                    gr.Column(visible=False),  # step3
                    1,  # current_step
                    {}  # wizard_data
                )
        
        def go_to_step_3(title, description, tone, data):
            if title:
                new_data = data.copy()
                new_data.update({
                    "title": title,
                    "description": description,
                    "tone": tone
                })
                
                # Create review content
                review_text = f"""
                ## Review Your Configuration
                
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
                    3,  # current_step
                    new_data,  # wizard_data
                    gr.Markdown(review_text)  # review_content
                )
            else:
                return (
                    gr.Column(visible=False),  # step1
                    gr.Column(visible=True),   # step2
                    gr.Column(visible=False),  # step3
                    2,  # current_step
                    data,  # wizard_data
                    gr.Markdown("")  # review_content
                )
        
        def go_back_to_step_1():
            return (
                gr.Column(visible=True),   # step1
                gr.Column(visible=False),  # step2
                gr.Column(visible=False),  # step3
                1,  # current_step
                {}  # wizard_data
            )
        
        def go_back_to_step_2(data):
            return (
                gr.Column(visible=False),  # step1
                gr.Column(visible=True),   # step2
                gr.Column(visible=False),  # step3
                2,  # current_step
                data  # wizard_data
            )
        
        # Knowledge library toggle function
        def toggle_knowledge_library(visible):
            return not visible, gr.Column(visible=not visible)
        
        # Add a hidden button for knowledge toggle (as backup)
        knowledge_toggle_btn = gr.Button("Toggle Knowledge", visible=False)
        
        # Event handlers
        next_btn_1.click(
            go_to_step_2,
            inputs=[excel_file],
            outputs=[step1, step2, step3, current_step, wizard_data]
        )
        
        next_btn_2.click(
            go_to_step_3,
            inputs=[title_input, description_input, tone_dropdown, wizard_data],
            outputs=[step1, step2, step3, current_step, wizard_data, review_content]
        )
        
        prev_btn_2.click(
            go_back_to_step_1,
            outputs=[step1, step2, step3, current_step, wizard_data]
        )
        
        prev_btn_3.click(
            go_back_to_step_2,
            inputs=[wizard_data],
            outputs=[step1, step2, step3, current_step, wizard_data]
        )
        
        generate_btn.click(
            create_release,
            inputs=[gr.State(), title_input, description_input],
            outputs=[create_status]
        ).then(
            lambda: gr.Markdown(visible=True),
            outputs=[create_status]
        )
        
        # Knowledge library toggle event
        knowledge_toggle_btn.click(
            toggle_knowledge_library,
            inputs=[knowledge_visible],
            outputs=[knowledge_visible, knowledge_panel]
        )
        
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
