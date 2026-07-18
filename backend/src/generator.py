from groq import Groq
from typing import List, Dict, Any

class Generator:
    def __init__(self, client:Groq, model_name:str):
        print("[DEBUG] Initializing Generator LLM....")
        self.client = client
        self.model_name = model_name

    def format_context(self, retrieved_chunks: List[Dict[str, Any]]) -> str:
        context_string = ""
        for i, match in enumerate(retrieved_chunks):
            # Include the source metadata so the LLM can cite it if needed
            source = match['metadata'].get('source', f'Document {i + 1}')
            context_string += f"\n--- Source: {source} ---\n"
            context_string += f"{match['chunk']}\n"

        return context_string

    def generate(self, original_query:str, retrieved_chunks: List[Dict[str, Any]]) -> str:
        print("[DEBUG] Synthesizing final output.....")

        context = self.format_context(retrieved_chunks)

        # system_prompt = """
        # You are an expert, highly accurate research assistant.
        # You will be provided with a user's question and a set of retrieved document chunks.
        #
        # Rules:
        # 1. Answer the question using ONLY the provided context.
        # 2. If the answer is not contained in the context, politely state that you do not have enough information. Do not guess.
        # 3. Keep your answer clear, concise, and well-structured.
        # """

        system_prompt = """You are an expert, highly accurate research assistant. 
        You will be provided with a user's question and a set of retrieved document chunks.

        Rules:
        1. PRIORITIZE CONTEXT: Always attempt to answer the question using the provided context first.
        2. GENERAL KNOWLEDGE FALLBACK: If the provided context does not contain the answer, you may use your general knowledge to answer the question.
        3. TRANSPARENCY: If you are relying on your general knowledge instead of the context, you MUST explicitly state: "Based on my general knowledge (not the provided documents)..." before answering.
        4. Keep your answer clear, concise, and well-structured."""

        system_prompt="""You are an expert, highly accurate research assistant. 
        You will be provided with a user's question and a set of retrieved document chunks.

        Rules:
        1. PRIMARY SOURCE: Always attempt to answer the question using the provided context first.
        2. STRICT DOCUMENT SCOPE: If the user's question explicitly refers to the uploaded material (e.g., "in this project", "what does this file say", "according to the document"), you MUST strictly confine your answer to the provided context. If the context does not contain the answer, politely state that the document does not provide this information. Do NOT use general knowledge.
        3. GENERAL KNOWLEDGE FALLBACK: If the user asks a general question (e.g., "what is NLP?") that does not reference the uploaded files, and the answer is not in the context, you may use your general knowledge to answer it.
        4. TRANSPARENCY: Whenever you rely on general knowledge, you must begin your response with: "The provided documents do not mention this, but based on general knowledge..."
        5. Keep your answer clear, concise, and well-structured."""

        user_prompt = f"Context material:\n{context}\n\nQuestion: {original_query}"

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role":"system", "content":system_prompt},
                    {"role":"user", "content":user_prompt}
                ],
                temperature=0.3
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"An error occured during generation: {str(e)}"