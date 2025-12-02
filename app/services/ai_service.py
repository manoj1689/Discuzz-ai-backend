"""
AI service for context profile generation and delegate responses.
"""

import json
from typing import List, Optional

import httpx

from app.core.config import settings
from app.schemas.post import ContextProfile, InterviewMessage
from app.core.exceptions import DiscuzzException


class AIService:
    """Service for AI-powered features."""
    
    def __init__(self):
        self.openai_api_key = settings.openai_api_key
        self.gemini_api_key = settings.gemini_api_key
    
    async def generate_interview_questions(self, draft: str) -> List[str]:
        """
        Generate interview questions for a draft post.
        Uses OpenAI GPT-4.
        """
        if not self.openai_api_key:
            # Return fallback questions if no API key
            return [
                "What is your main goal with this post?",
                "Who exactly are you speaking to?",
                "What assumptions are you making that you haven't said out loud?",
            ]
        
        prompt = f"""
        You are an insightful editor for Discuzz.ai. The user wants to post the following draft:

        "{draft}"

        Your goal:
        - Extract the user's hidden context.
        - Generate 3 short, sharp, leading questions that uncover:
          1. Their underlying intent or goal.
          2. The unspoken assumptions they are making.
          3. The emotional tone or nuance they want to convey.

        Format:
        Return ONLY a JSON array of 3 strings.
        """
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"}
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise DiscuzzException("Failed to generate interview questions")
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            result = json.loads(content)
            
            # Handle different response formats
            if isinstance(result, list):
                return result[:3]
            elif isinstance(result, dict) and "questions" in result:
                return result["questions"][:3]
            else:
                raise DiscuzzException("Unexpected AI response format")
    
    async def generate_context_profile(
        self,
        draft: str,
        interview_history: List[InterviewMessage]
    ) -> ContextProfile:
        """
        Generate a context profile from draft and interview.
        Uses Google Gemini.
        """
        if not self.gemini_api_key:
            # Return fallback profile if no API key
            return ContextProfile(
                intent="To share an opinion.",
                tone="Neutral",
                assumptions="None explicitly stated.",
                audience="General public",
                coreArgument=draft[:100] if draft else ""
            )
        
        conversation_text = "\n".join([
            f"{m.role.upper()}: {m.content}"
            for m in interview_history
        ])
        
        prompt = f"""
        Analyze the following draft and interview transcript to create a structured Context Profile.
        
        Draft: "{draft}"
        
        Interview Transcript:
        {conversation_text}

        Return a JSON object with these exact fields:
        - intent: The primary goal of the post
        - tone: The emotional nuance
        - assumptions: Underlying premises
        - audience: Target demographic
        - coreArgument: The central thesis in one sentence
        """
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_api_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "responseMimeType": "application/json"
                    }
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise DiscuzzException("Failed to generate context profile")
            
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            profile_data = json.loads(text)
            
            return ContextProfile(**profile_data)
    
    async def generate_delegate_response(
        self,
        original_post: str,
        profile: ContextProfile,
        user_query: str,
        chat_history: List[InterviewMessage]
    ) -> str:
        """
        Generate an AI delegate response to a reader's question.
        Uses OpenAI GPT-4.
        """
        if not self.openai_api_key:
            return "I am unable to respond at this moment."
        
        history_text = "\n".join([
            f"{'Reader' if m.role == 'user' else 'Author Delegate'}: {m.content}"
            for m in chat_history[-5:]  # Last 5 messages
        ])
        
        system_instruction = f"""
        You are the AI Delegate for the author of this post.
        
        Original Post: "{original_post}"
        
        Author's Context Profile (The "Truth"):
        - Intent: {profile.intent}
        - Tone: {profile.tone}
        - Assumptions: {profile.assumptions}
        - Core Argument: {profile.core_argument}
        
        Your Task:
        Respond to the Reader's query effectively.
        1. STRICTLY adhere to the Author's tone and logic.
        2. Do NOT invent new facts outside the context; if unsure, pivot back to the core argument.
        3. Defend the author's viewpoint using the provided assumptions.
        4. Keep it concise (under 280 characters if possible, max 500).
        5. Do not start with "As the author..." just speak directly.
        """
        
        user_content = f"""
        Previous Chat:
        {history_text}

        Reader: {user_query}
        """
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": user_content}
                    ],
                    "max_tokens": 300
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                return "I am unable to respond at this moment."
            
            data = response.json()
            return data["choices"][0]["message"]["content"]


# Singleton instance
ai_service = AIService()
