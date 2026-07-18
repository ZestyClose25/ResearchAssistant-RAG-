import json
from dotenv import load_dotenv

from groq import Groq

load_dotenv()

class QueryProcessor:
    def __init__(self, client:Groq, model_name:str):
        print("[DEBUG] Initializing Query processor LLM....")
        self.client = client
        self.model_name=model_name

    def rewrite_query(self, raw_query: str, chat_history:str = "") -> dict:
        print("[DEBUG] Re-writing query......")
        system_prompt = """
        You are an expert search query optimizer for a Vector+BM25 Hybrid Database.
        Given a user's conversational query and the chat history, your job is to rewrite the query into two exact strings for database retrieval.
        And also check for any typos and spelling corrections and change it accordingly.

        Rules:
        1. semantic_query: A complete, standalone question optimized for dense vector meaning. Resolve all pronouns (it, they, them) based on the context.
        2. bm25_keywords: A comma-separated list of 3 to 7 highly specific nouns, acronyms, or proper names for exact keyword matching.

        You must output ONLY raw JSON. No markdown formatting, no conversational text.
        Format: {"semantic_query": "...", "bm25_keywords": "..."}
        """

        user_prompt = f"Chat history: {chat_history}\n New query: {raw_query}"

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role":"system", "content":system_prompt},
                    {"role":"user", "content":user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            llm_output = response.choices[0].message.content
            optimized_queries = json.loads(llm_output)
            return optimized_queries

        except Exception as e:
            print(f"[ERROR] Error occurred while rewriting query: {e}")
            return {"semantic_query": raw_query, "bm25_keywords": ""}