# llm_integration.py
import os
import json
from typing import Dict, Optional, Literal, Any, List
from abc import ABC, abstractmethod

class BaseLLMController(ABC):
    """Base class for LLM controllers"""
    @abstractmethod
    def get_completion(self, prompt: str, response_format: Optional[dict] = None, temperature: float = 0.7) -> str:
        """Get completion from LLM"""
        pass

class OpenAIController(BaseLLMController):
    """OpenAI API controller for LLM interactions"""
    def __init__(self, model: str = "gpt-4o-mini", api_key: Optional[str] = None):
        try:
            from openai import OpenAI
            self.model = model
            if api_key is None:
                api_key = os.getenv('OPENAI_API_KEY')
            if api_key is None:
                raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
            self.client = OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("OpenAI package not found. Install it with: pip install openai")
    
    def get_completion(self, prompt: str, response_format: Optional[dict] = None, temperature: float = 0.7) -> str:
        """Get completion from OpenAI"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
        
        # Set up parameters
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1000
        }
        
        # Add response format if provided
        if response_format:
            # Add system message to guide JSON response
            if response_format.get("type") == "json_schema":
                messages[0]["content"] = "You must respond with a JSON object following the provided schema."
            params["response_format"] = response_format
        
        # Get completion
        response = self.client.chat.completions.create(**params)
        return response.choices[0].message.content

class MockLLMController(BaseLLMController):
    """Mock LLM controller for testing or when no LLM is available"""
    def __init__(self):
        pass
    
    def _generate_empty_response(self, response_format: Optional[dict] = None) -> str:
        """Generate an empty response based on the format"""
        if not response_format or response_format.get("type") != "json_schema":
            return ""
            
        schema = response_format.get("json_schema", {}).get("schema", {})
        result = {}
        
        if "properties" in schema:
            for prop_name, prop_schema in schema["properties"].items():
                prop_type = prop_schema.get("type", "string")
                if prop_type == "array":
                    result[prop_name] = []
                elif prop_type == "string":
                    result[prop_name] = ""
                elif prop_type == "object":
                    result[prop_name] = {}
                elif prop_type == "number":
                    result[prop_name] = 0
                elif prop_type == "boolean":
                    result[prop_name] = False
        
        return json.dumps(result)
    
    def get_completion(self, prompt: str, response_format: Optional[dict] = None, temperature: float = 0.7) -> str:
        """Return empty or mock response"""
        if response_format:
            return self._generate_empty_response(response_format)
        return ""

class LLMController:
    """Main LLM controller that handles different backends"""
    def __init__(self, 
                 backend: Literal["openai", "mock"] = "mock",
                 model: str = "gpt-4o-mini", 
                 api_key: Optional[str] = None):
        if backend == "openai" and os.getenv('OPENAI_API_KEY'):
            try:
                self.llm = OpenAIController(model, api_key)
            except (ImportError, ValueError) as e:
                print(f"Falling back to mock LLM controller: {str(e)}")
                self.llm = MockLLMController()
        else:
            self.llm = MockLLMController()

    def analyze_content(self, content: str) -> Dict:
        """Analyze content to extract keywords, context, and tags"""
        prompt = """Generate a structured analysis of the following content by:
            1. Identifying the most salient keywords (focus on nouns, verbs, and key concepts)
            2. Extracting core themes and contextual elements
            3. Creating relevant categorical tags

            Format the response as a JSON object:
            {
                "keywords": [
                    // several specific, distinct keywords that capture key concepts
                    // Order from most to least important
                    // At least three keywords, but don't be too redundant
                ],
                "context": 
                    // one sentence summarizing the main topic/domain
                ,
                "tags": [
                    // several broad categories/themes for classification
                    // At least three tags, but don't be too redundant
                ]
            }

            Content for analysis:
            """ + content
            
        try:
            response_format = {
                "type": "json_schema", 
                "json_schema": {
                    "name": "response",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "keywords": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "context": {"type": "string"},
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["keywords", "context", "tags"]
                    }
                }
            }
            
            response = self.llm.get_completion(prompt, response_format)
            
            try:
                analysis = json.loads(response)
                return analysis
            except json.JSONDecodeError:
                # Return default values if JSON parsing fails
                return {
                    "keywords": [],
                    "context": "General",
                    "tags": []
                }
                
        except Exception as e:
            print(f"Error analyzing content: {str(e)}")
            return {
                "keywords": [],
                "context": "General",
                "tags": []
            }
            
    def find_connections(self, note_content: str, related_notes: List[Dict]) -> Dict:
        """Find connections between note and related notes"""
        if not related_notes:
            return {
                "suggested_connections": [],
                "importance_score": 1.0
            }
            
        related_notes_text = "\n\n".join([
            f"Note {i+1}:\nTitle: {note.get('title', 'Untitled')}\nContent: {note.get('content', '')}"
            for i, note in enumerate(related_notes)
        ])
        
        prompt = f"""Analyze the relationships between a new note and existing notes in a knowledge base.
        
        New Note:
        {note_content}
        
        Existing Related Notes:
        {related_notes_text}
        
        Please identify:
        1. Which existing notes should be connected to the new note (by index number)
        2. An importance score for this new note on a scale of 0.0 to 2.0, where:
           - 0.0-0.5: Low importance, auxiliary information
           - 0.5-1.0: Average importance, useful but not critical
           - 1.0-1.5: High importance, key information
           - 1.5-2.0: Critical importance, foundational knowledge
        
        Return your analysis as JSON:
        {
            "suggested_connections": [1, 3],  // indices of notes that should be connected
            "importance_score": 1.2  // your assigned importance score
        }
        """
        
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "suggested_connections": {
                            "type": "array",
                            "items": {"type": "integer"}
                        },
                        "importance_score": {"type": "number"}
                    },
                    "required": ["suggested_connections", "importance_score"]
                }
            }
        }
        
        try:
            response = self.llm.get_completion(prompt, response_format)
            analysis = json.loads(response)
            return analysis
        except Exception as e:
            print(f"Error finding connections: {str(e)}")
            return {
                "suggested_connections": [],
                "importance_score": 1.0
            }