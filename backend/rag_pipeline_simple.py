import os
import logging
from typing import List, Dict, Any, Optional
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class RAGPipeline:
    """Simplified RAG pipeline using OpenAI"""
    
    def __init__(self, doc_processor=None):
        # Try Gemini first, fall back to OpenAI
        gemini_key = os.getenv("GEMINI_API_KEY")
        
        # Filter out placeholder values
        if gemini_key and "YOUR_" not in gemini_key and gemini_key.startswith("AIza"):
            if GEMINI_AVAILABLE:
                try:
                    genai.configure(api_key=gemini_key)
                    self.client = genai.GenerativeModel('gemini-2.5-flash')
                    self.use_gemini = True
                    self.api_key_valid = True
                    logger.info("✅ Gemini API configured successfully with gemini-2.5-flash model")
                except Exception as e:
                    logger.error(f"❌ Failed to configure Gemini: {e}")
                    self.client = None
                    self.use_gemini = False
                    self.api_key_valid = False
            else:
                logger.error("❌ google-generativeai package not available")
                self.client = None
                self.use_gemini = False
                self.api_key_valid = False
        else:
            logger.error(f"❌ Gemini API key not valid or not set (key preview: {gemini_key[:20] if gemini_key else 'empty'}...)")
            self.client = None
            self.use_gemini = False
            self.api_key_valid = False
        
        self.doc_processor = doc_processor
        self.conversation_history = {}  # Store conversation history by ID
    
    async def generate_answer(self, query: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate an answer using retrieved context"""
        
        if not context_chunks:
            return {
                "answer": "I couldn't find any relevant information in the documents to answer your question.",
                "sources": [],
                "confidence": "low"
            }
        
        # Prepare context
        context = "\n\n".join([
            f"[From {chunk['filename']}, Page {chunk['page_number']}]:\n{chunk['content']}"
            for chunk in context_chunks[:3]  # Use top 3 chunks
        ])
        
        # Create prompt
        prompt = f"""You are an expert construction project document analyzer. Analyze the provided context and answer the question with precision.

Context from documents:
{context}

Question: {query}

Instructions:
1. Provide a clear, direct answer to the question
2. Use bullet points for multiple items or specifications
3. Include relevant technical details (measurements, ratings, materials, etc.)
4. Reference the specific document and page where information was found
5. If information is incomplete, clearly state what's missing
6. Use professional construction terminology

Answer:"""
        
        try:
            # Check if Gemini is configured
            if not self.client or not self.api_key_valid:
                raise Exception("Gemini API key not configured. Please add GEMINI_API_KEY to .env file.")
            
            # Call Gemini
            if self.use_gemini:
                logger.info(f"Sending query to Gemini: {query[:50]}...")
                full_prompt = f"You are a helpful construction project assistant.\n\n{prompt}"
                try:
                    response = self.client.generate_content(
                        full_prompt,
                        generation_config={
                            'temperature': 0.3,
                            'max_output_tokens': 1024,
                        }
                    )
                    
                    # Check if response has valid content
                    if hasattr(response, 'text') and response.text:
                        answer = response.text
                        logger.info(f"Gemini response received: {len(answer)} chars")
                    elif hasattr(response, 'candidates') and response.candidates:
                        # Try to extract from candidates if text accessor fails
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'content') and candidate.content.parts:
                            answer = candidate.content.parts[0].text
                            logger.info(f"Gemini response extracted from candidate: {len(answer)} chars")
                        else:
                            # Safety filter or other blocking
                            logger.warning(f"Gemini blocked response. Finish reason: {candidate.finish_reason}")
                            answer = f"Based on the retrieved documents:\n\n{context[:800]}\n\n*Note: The AI response was blocked by content filters. The information above is directly from your documents.*"
                    else:
                        logger.warning("Gemini returned empty response")
                        answer = f"Based on the retrieved documents:\n\n{context[:800]}\n\n*Note: AI response generation returned empty. The information above is directly from your documents.*"
                        
                except Exception as gemini_error:
                    logger.error(f"Gemini API error: {str(gemini_error)}")
                    # Return formatted context as fallback
                    answer = f"Based on the retrieved documents:\n\n{context[:800]}\n\n*Note: AI response generation is temporarily unavailable. The information above is directly from your documents.*"
            else:
                answer = f"Based on the retrieved documents:\n\n{context[:800]}\n\n*Note: AI response generation is not configured. The information above is directly from your documents.*"
            
            # Format sources with enhanced information
            sources = [
                {
                    "filename": chunk["filename"],
                    "page_number": chunk["page_number"],
                    "relevance_score": round(chunk.get("relevance_score", 0), 3),
                    "preview": chunk["content"][:150] + "..." if len(chunk["content"]) > 150 else chunk["content"]
                }
                for chunk in context_chunks[:3]
            ]
            
            # Calculate confidence based on relevance scores
            avg_score = sum(s["relevance_score"] for s in sources) / len(sources) if sources else 0
            if avg_score > 0.7:
                confidence = "high"
            elif avg_score > 0.5:
                confidence = "medium"
            else:
                confidence = "low"
            
            return {
                "answer": answer,
                "sources": sources,
                "confidence": confidence,
                "chunks_found": len(context_chunks)
            }
        except Exception as e:
            # Format sources even on error
            sources = [
                {
                    "filename": chunk["filename"],
                    "page_number": chunk["page_number"],
                    "relevance_score": chunk.get("relevance_score", 0)
                }
                for chunk in context_chunks[:3]
            ]
            
            # Check if it's a Gemini API key error
            error_msg = str(e)
            if "api key" in error_msg.lower() or "401" in error_msg:
                answer = f"I found relevant information in your documents, but the Gemini API key needs to be configured to generate an answer. Here's what I found:\n\n"
                for i, chunk in enumerate(context_chunks[:3], 1):
                    answer += f"\n{i}. From {chunk['filename']} (Page {chunk['page_number']}):\n{chunk['content'][:200]}...\n"
            else:
                answer = f"Sorry, I encountered an error: {error_msg}"
            
            return {
                "answer": answer,
                "sources": sources,
                "confidence": "error"
            }
    
    async def process_query(self, query: str, conversation_id: Optional[str] = None, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a query through the RAG pipeline"""
        
        if not self.doc_processor:
            return {
                "answer": "Document processor not initialized.",
                "sources": [],
                "confidence": "error",
                "conversation_id": conversation_id
            }
        
        # Search for relevant chunks with optional filters
        context_chunks = self.doc_processor.search_documents(query, top_k=5, filters=filters)
        
        # Generate answer using retrieved context
        result = await self.generate_answer(query, context_chunks)
        
        # Add conversation ID to result
        result["conversation_id"] = conversation_id
        
        # Store in conversation history if ID provided
        if conversation_id:
            if conversation_id not in self.conversation_history:
                self.conversation_history[conversation_id] = []
            self.conversation_history[conversation_id].append({
                "query": query,
                "answer": result["answer"],
                "sources": result["sources"]
            })
        
        return result
