from abc import ABC, abstractmethod
from typing import Dict, Any, List
import os
import json
from openai import OpenAI
from datetime import datetime
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class BaseAgent(ABC):
    def __init__(self):
        self.history = []
        use_core42_client = os.getenv('USE_CORE_42_CLIENT', "False") == "True"

        if use_core42_client:
            self.client = OpenAI(
                base_url="https://api.core42.ai/v1",
                api_key=os.getenv("CORE42_KEY"),
                default_headers={"api-key": os.getenv("CORE42_KEY")},
                default_query={"api-version": "2024-11-01-preview"}
            )
        else:
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def llm_inference(
        self,
        messages: list[dict],
        model: str = "gpt-4o",
        temperature: float = 0.2,
        top_p: float = 0.2
    ) -> str:
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            top_p=top_p
        )
        return response.choices[0].message.content

    @abstractmethod
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        pass
