import os
import requests
import json
import re
from dotenv import load_dotenv

# Ensure .env is loaded from root
load_dotenv(os.path.join(os.getcwd(), '.env'))
load_dotenv()

class SarvamNarrator:
    """
    Handles BharatData reporting using the Sarvam-M model.
    Optimized for professional data analysis with multilingual support.
    """
    
    ENDPOINT = "https://api.sarvam.ai/v1/chat/completions"
    MODEL = "sarvam-m"
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("SARVAM_API_KEY")
        if not self.api_key:
            raise ValueError("SARVAM_API_KEY not found in environment or arguments.")
            
    def generate_narrative(self, quality_data: dict, context_info: dict = None) -> str:
        """
        Generates a professional data analysis narrative based on the quality report.
        """
        
        # Prepare the context string for the AI
        stats_summary = json.dumps(quality_data, indent=2)
        
        system_prompt = (
            "You are the Senior Data Strategy & Quality Architect for BharatData, India's premier unified data infrastructure. "
            "Task: Generate an exhaustive, deep-dive Technical Audit Narrative of the latest ingestion phase. "
            "Constraints: "
            "1. NO internal thoughts, NO self-references, NO preambles. "
            "2. EXCLUSIVE Focus on technical metrics, data integrity, and strategic coverage. "
            "3. Structure the report with 5+ detailed sections using '###' headers. "
            "4. IMPORTANT: Use Markdown Tables (`| Header |`) to compare critical metrics (e.g., Raw vs Ingested). "
            "Sections Required: "
            "### I. Ingestion Pipeline Architecture Performance: [Deep analysis of the specific source handling] "
            "### II. Data Integrity & Parity Metrics: [Using a table to show extraction vs loading results] "
            "### III. Normalization & Transformation Logic: [Analysis of Geographic/Type mapping accuracy] "
            "### IV. Deduplication Efficiency & Conflict Resolution: [Detailed breakdown of hash-based filtering] "
            "### V. Strategic Impact & Registry Coverage: [Analysis of this dataset's role in the BharatData ecosystem] "
            "Maintain an authoritative, high-density, and elite technical tone."
        )
        
        user_prompt = (
            f"AUDIT DATA:\n{stats_summary}\n\n"
            "Generate an EXHAUSTIVE, 'Pro-Max' technical audit. "
            "For EACH of the 5 specified sections: "
            "1. Provide a High-Density Data Table comparing processed vs expected metrics. "
            "2. Provide 3-4 Detailed Paragraphs of technical analysis (Root Cause Analysis, Normalization Efficiency, and Strategic Recommendations). "
            "3. Use authoritative, elite technical language (e.g., 'Parity Validation', 'Hash-Collision Mitigation', 'Registry Synchronicity'). "
            "Return ONLY the analytical content. No preambles."
        )
        
        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 2000,
            "reasoning_effort": "medium"
        }
        
        try:
            response = requests.post(self.ENDPOINT, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Post-processing: Remove any potential <think> tags if reasoning_effort fails
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
            return content
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                return "❌ Error: Invalid Sarvam API Key. Please check your credentials."
            return f"❌ AI Analysis Error: {str(e)}"
        except Exception as e:
            return f"❌ Narrative generation failed: {str(e)}"

if __name__ == "__main__":
    # Test with mockup data if key is available
    test_json = {
        "overall_health": "88%",
        "total_records": 50541,
        "anomalies": ["Missing district mapping for 5 entries in Bihar"],
        "confidence_avg": 0.94
    }
    
    try:
        narrator = SarvamNarrator()
        print("--- Sarvam-M Narrative Test ---")
        print(narrator.generate_narrative(test_json))
    except Exception as e:
        print(f"Test failed: {e}")
