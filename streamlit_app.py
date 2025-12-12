"""
TalentScout Hiring Assistant - Streamlit Application
AI/ML Intern Assignment
"""

import streamlit as st
import os
from dotenv import load_dotenv
from typing import Optional, Dict, Tuple
import re
from datetime import datetime
import json

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None
    st.error("google-generativeai package not installed. Run: pip install google-generativeai")

# Load environment variables
load_dotenv()

# ==================== PROMPT TEMPLATES ====================

SYSTEM_PROMPT = """You are an intelligent Hiring Assistant for TalentScout, a technology recruitment agency.

Your role:
1. Greet candidates and explain your purpose
2. Gather: name, email, phone, experience, desired position, location, tech stack
3. Generate relevant technical questions based on tech stack
4. Stay professional and focused on hiring/recruitment only

RULES:
- NEVER deviate from hiring topics
- Be concise and professional  
- If asked unrelated questions, politely redirect
- End gracefully when: bye, goodbye, exit, quit, done, finish

Current stage: {stage}
"""

GREETING_PROMPT = """You are TalentScout's Hiring Assistant. Greet the candidate warmly and say: "Hello! I'm TalentScout's Hiring Assistant. I'll be collecting some information about your background and then asking a few technical questions based on your expertise. Let's get started! What's your full name?" """

INFO_PROMPTS = {
    "name": """Say: "Great to meet you! Could you please provide your email address so we can follow up with you?" """,
    "email": """Say: "Thank you! Now, what's your phone number? Please include your country code if you're outside the US." """,
    "phone": """Say: "Perfect! How many years of professional experience do you have in technology?" """,
    "experience": """Say: "Excellent! What position or role are you interested in applying for?" """,
    "position": """Say: "Great! Where are you currently located? (City and country)" """,
    "location": """Say: "Thank you! Now, please list your tech stack - including programming languages, frameworks, databases, and tools you're proficient in. For example: Python, Django, PostgreSQL, Docker, AWS" """,
    "tech_stack": """This should not be used directly."""
}

TECH_QUESTION_PROMPT = """Based on tech stack: {tech_stack}

Generate {num_questions} technical questions to assess proficiency.

Requirements:
- Practical and job-relevant
- Mix conceptual and scenario-based
- Appropriate for {experience} years experience
- Cover different technologies mentioned
- Clear and concise

Format:
1. [Question about tech X]
2. [Question about tech Y]
...
"""

END_PROMPT = """Create a warm closing message:
1. Thank them for their time
2. Confirm we have their information
3. Mention next steps (review and contact)
4. Wish them well (2-3 sentences)"""

FALLBACK_PROMPT = """User said: "{user_input}"

This seems unrelated or unclear.

Respond professionally:
- If off-topic, redirect to hiring
- If unclear, ask for clarification
- If greeting, respond warmly and continue
- Stay focused on recruitment"""

# ==================== DATA VALIDATION ====================

def validate_email(email: str) -> Tuple[bool, str]:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        return True, ""
    return False, "Invalid email. Please provide a valid email address."

def validate_phone(phone: str) -> Tuple[bool, str]:
    """Validate phone number"""
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    pattern = r'^\+?[0-9]{7,15}$'
    if re.match(pattern, cleaned):
        return True, ""
    return False, "Invalid phone. Use format: +1234567890"

def validate_experience(exp: str) -> Tuple[bool, str, Optional[int]]:
    """Validate years of experience"""
    try:
        numbers = re.findall(r'\d+', exp)
        if numbers:
            years = int(numbers[0])
            if 0 <= years <= 50:
                return True, "", years
            return False, "Experience should be 0-50 years.", None
        return False, "Please provide a number for years of experience.", None
    except:
        return False, "Please provide a valid number.", None

# ==================== DATA STORAGE ====================

def save_candidate_data(data: Dict):
    """Save candidate data to JSON file (GDPR-compliant)"""
    os.makedirs("candidate_data", exist_ok=True)
    filepath = "candidate_data/candidates.json"
    
    data['submission_timestamp'] = datetime.now().isoformat()
    data['candidate_id'] = f"CAND_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    candidates = []
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            candidates = json.load(f)
    
    candidates.append(data)
    
    with open(filepath, 'w') as f:
        json.dump(candidates, f, indent=2)

def analyze_tech_stack(tech_stack: str) -> Dict:
    """Analyze tech stack and categorize technologies"""
    categories = {
        "languages": ["python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "ruby", "php"],
        "frontend": ["react", "vue", "angular", "html", "css", "nextjs", "svelte", "tailwind"],
        "backend": ["django", "flask", "fastapi", "spring", "express", "node", "rails"],
        "databases": ["postgresql", "mysql", "mongodb", "redis", "elasticsearch", "sqlite"],
        "cloud": ["aws", "azure", "gcp", "docker", "kubernetes", "terraform"],
        "ml_ai": ["tensorflow", "pytorch", "scikit-learn", "keras", "pandas", "numpy"]
    }
    
    tech_lower = tech_stack.lower()
    found = {cat: [] for cat in categories}
    
    for cat, techs in categories.items():
        for tech in techs:
            if tech in tech_lower:
                found[cat].append(tech.title())
    
    return found

def calculate_match_score(tech_stack: str, experience: int) -> Dict:
    """Calculate candidate fit score based on tech stack and experience"""
    analysis = analyze_tech_stack(tech_stack)
    
    # Calculate diversity score
    diversity = len([cat for cat in analysis.values() if cat])
    
    # Experience level
    if experience < 2:
        level = "Junior"
        color = "🟢"
    elif experience < 5:
        level = "Mid-Level"
        color = "🟡"
    else:
        level = "Senior"
        color = "🔵"
    
    # Tech breadth score
    total_techs = sum(len(techs) for techs in analysis.values())
    breadth = min(total_techs * 10, 100)
    
    return {
        "level": level,
        "color": color,
        "diversity": diversity,
        "breadth": breadth,
        "analysis": analysis
    }

# ==================== LLM INTEGRATION ====================

class LLMClient:
    """Wrapper for Gemini LLM"""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            st.error("⚠️ GEMINI_API_KEY not found in .env file")
            st.stop()
        
        if not GEMINI_AVAILABLE:
            st.error("google-generativeai not installed")
            st.stop()
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def generate(self, prompt: str, context: str = "") -> str:
        """Generate response from Gemini"""
        try:
            full_prompt = f"{context}\n\n{prompt}" if context else prompt
            response = self.model.generate_content(
                full_prompt,
                generation_config={
                    'temperature': 0.7,
                    'max_output_tokens': 1024,
                }
            )
            return response.text
        except Exception as e:
            return f"I apologize, I encountered an error. Please try again. ({str(e)[:100]})"

# ==================== CONVERSATION STATE ====================

class ConversationState:
    """Manage conversation flow"""
    
    STAGES = ["greeting", "name", "email", "phone", "experience", "position", "location", "tech_stack", "questions", "completed"]
    
    def __init__(self):
        self.stage_index = 0
        self.data = {}
        self.history = []
    
    def current_stage(self) -> str:
        return self.STAGES[self.stage_index] if self.stage_index < len(self.STAGES) else "completed"
    
    def advance(self):
        if self.stage_index < len(self.STAGES) - 1:
            self.stage_index += 1
    
    def is_complete(self) -> bool:
        return self.current_stage() == "completed"
    
    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content, "timestamp": datetime.now().isoformat()})
    
    def store(self, field: str, value: str):
        self.data[field] = value

# ==================== STREAMLIT UI ====================

st.set_page_config(
    page_title="TalentScout Hiring Assistant",
    page_icon="💼",
    layout="centered"
)

# Custom CSS
st.markdown("""
<style>
    .stApp {max-width: 800px; margin: 0 auto;}
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .assistant {
        background-color: #f0f2f6;
        color: #1e1e1e;
    }
    .user {
        background-color: #e3f2fd;
        color: #1e1e1e;
    }
    .header {text-align: center; padding: 2rem 0;}
    .info-box {
        background-color: #fff3cd;
        color: #856404;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ffc107;
        margin: 1rem 0;
    }
    .chat-message p {
        color: #1e1e1e;
        margin: 0.5rem 0;
    }
    .chat-message strong {
        color: #1e1e1e;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'state' not in st.session_state:
    st.session_state.state = ConversationState()
if 'llm' not in st.session_state:
    st.session_state.llm = LLMClient()
if 'messages' not in st.session_state:
    st.session_state.messages = []
    # Initial greeting - DON'T advance yet, we're still at greeting stage
    greeting = "Hello! I'm TalentScout's Hiring Assistant. I'll be collecting some information about your background and then asking a few technical questions based on your expertise. Let's get started!\n\nWhat's your full name?"
    st.session_state.messages.append({"role": "assistant", "content": greeting})
    st.session_state.state.add_message("assistant", greeting)
    # Stage is still "greeting", will advance to "name" when user responds

# Sidebar with features
with st.sidebar:
    st.header("📊 Interview Progress")
    
    # Progress bar
    stages_total = len(ConversationState.STAGES) - 2  # Exclude greeting and completed
    current_progress = min(st.session_state.state.stage_index, stages_total)
    progress = current_progress / stages_total if stages_total > 0 else 0
    st.progress(progress)
    st.caption(f"Step {current_progress} of {stages_total}")
    
    # Current stage indicator
    stage_names = {
        "greeting": "👋 Welcome",
        "name": "👤 Personal Info",
        "email": "📧 Contact",
        "phone": "📱 Phone",
        "experience": "💼 Experience",
        "position": "🎯 Role",
        "location": "📍 Location",
        "tech_stack": "💻 Tech Stack",
        "questions": "❓ Assessment",
        "completed": "✅ Complete"
    }
    current_stage_name = stage_names.get(st.session_state.state.current_stage(), "In Progress")
    st.info(f"**Current:** {current_stage_name}")
    
    # Statistics
    st.divider()
    st.header("📈 Session Stats")
    st.metric("Messages", len(st.session_state.messages))
    st.metric("Fields Collected", len(st.session_state.state.data))
    
    # Tips
    st.divider()
    st.header("💡 Tips")
    st.caption("• Type 'bye' to exit anytime")
    st.caption("• Be specific with tech stack")
    st.caption("• Include country code for phone")
    
    # Admin features
    if st.session_state.state.is_complete():
        st.divider()
        st.header("🔧 Actions")
        if st.button("📋 View All Candidates", use_container_width=True):
            st.session_state.show_admin = True

# Header
st.markdown('<div class="header">', unsafe_allow_html=True)
st.title("💼 TalentScout Hiring Assistant")
st.markdown("*AI-powered recruitment screening*")
st.markdown('</div>', unsafe_allow_html=True)

# Info box
if not st.session_state.state.is_complete():
    st.markdown("""
    <div class="info-box">
        <strong>ℹ️ What to expect:</strong><br>
        I'll collect your information and ask technical questions based on your tech stack. 
        Type 'bye' anytime to exit.
    </div>
    """, unsafe_allow_html=True)

# Display messages
for msg in st.session_state.messages:
    role_class = "assistant" if msg["role"] == "assistant" else "user"
    emoji = "🤖" if msg["role"] == "assistant" else "👤"
    
    st.markdown(f"""
    <div class="chat-message {role_class}">
        <strong>{emoji} {msg["role"].title()}</strong>
        <p>{msg["content"]}</p>
    </div>
    """, unsafe_allow_html=True)

# Chat input
if not st.session_state.state.is_complete():
    user_input = st.chat_input("Type your message...")
    
    if user_input:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.state.add_message("user", user_input)
        
        # Check exit keywords
        exit_keywords = ['bye', 'goodbye', 'exit', 'quit', 'done', 'finish']
        if any(kw in user_input.lower() for kw in exit_keywords):
            response = st.session_state.llm.generate(END_PROMPT)
            st.session_state.state.stage_index = len(ConversationState.STAGES) - 1
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()
        
        # Process based on stage
        stage = st.session_state.state.current_stage()
        response = ""
        
        with st.spinner("Thinking..."):
            if stage == "greeting":
                # User responded to greeting, this is their name
                st.session_state.state.store("name", user_input)
                st.session_state.state.advance()  # Move from greeting to name
                st.session_state.state.advance()  # Move from name to email
                response = "Great to meet you! Could you please provide your email address so we can follow up with you?"
            
            elif stage == "email":
                # Validate email
                valid, error = validate_email(user_input)
                if not valid:
                    response = f"{error}\n\nCould you please provide your email address so we can follow up with you?"
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.rerun()
                # Store and move to next
                st.session_state.state.store("email", user_input)
                st.session_state.state.advance()
                response = "Thank you! Now, what's your phone number? Please include your country code if you're outside the US."
            
            elif stage == "phone":
                # Validate phone
                valid, error = validate_phone(user_input)
                if not valid:
                    response = f"{error}\n\nWhat's your phone number? Please include your country code if you're outside the US."
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.rerun()
                # Store and move to next
                st.session_state.state.store("phone", user_input)
                st.session_state.state.advance()
                response = "Perfect! How many years of professional experience do you have in technology?"
            
            elif stage == "experience":
                # Validate experience
                valid, error, years = validate_experience(user_input)
                if not valid:
                    response = f"{error}\n\nHow many years of professional experience do you have in technology?"
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.rerun()
                # Store and move to next
                st.session_state.state.store("experience", str(years))
                st.session_state.state.advance()
                response = "Excellent! What position or role are you interested in applying for?"
            
            elif stage == "position":
                # Store and move to next
                st.session_state.state.store("position", user_input)
                st.session_state.state.advance()
                response = "Great! Where are you currently located? (City and country)"
            
            elif stage == "location":
                # Store and move to next
                st.session_state.state.store("location", user_input)
                st.session_state.state.advance()
                response = "Thank you! Now, please list your tech stack - including programming languages, frameworks, databases, and tools you're proficient in.\n\nFor example: Python, Django, PostgreSQL, Docker, AWS"
            
            elif stage == "tech_stack":
                # Store tech stack and generate questions
                st.session_state.state.store("tech_stack", user_input)
                st.session_state.state.advance()
                
                # Analyze tech stack
                tech_stack = user_input
                experience = int(st.session_state.state.data.get('experience', '0'))
                match_score = calculate_match_score(tech_stack, experience)
                
                # Store analysis
                st.session_state.state.store('match_analysis', match_score)
                
                # Generate technical questions
                prompt = TECH_QUESTION_PROMPT.format(
                    tech_stack=tech_stack,
                    num_questions=3,
                    experience=experience
                )
                questions = st.session_state.llm.generate(prompt)
                st.session_state.state.store('technical_questions', questions)
                
                # Build enhanced response with analysis
                analysis = match_score['analysis']
                analysis_text = "\n🔍 **Tech Stack Analysis:**\n"
                for cat, techs in analysis.items():
                    if techs:
                        analysis_text += f"- {cat.replace('_', ' ').title()}: {', '.join(techs)}\n"
                
                response = f"Excellent! {match_score['color']} You're classified as **{match_score['level']}** level with **{match_score['diversity']} technology categories**.\n\n{analysis_text}\n📝 **Technical Questions:**\n\n{questions}\n\n✅ Thank you for completing the screening! Our team will review your profile and contact you soon."
                st.session_state.state.advance()
                
                # Save data
                save_candidate_data(st.session_state.state.data)
            
            elif stage == "questions":
                # This stage is already handled in tech_stack
                pass
            
            else:
                # Fallback
                fallback = FALLBACK_PROMPT.format(user_input=user_input)
                system = SYSTEM_PROMPT.format(stage=stage)
                response = st.session_state.llm.generate(fallback, system)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.session_state.state.add_message("assistant", response)
        st.rerun()

else:
    st.success("✅ Interview completed! Thank you for your time!")
    
    # Show match analysis if available
    if 'match_analysis' in st.session_state.state.data:
        st.divider()
        st.subheader("📊 Candidate Analysis")
        match = st.session_state.state.data['match_analysis']
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Experience Level", f"{match['color']} {match['level']}")
        with col2:
            st.metric("Tech Categories", match['diversity'])
        with col3:
            st.metric("Skill Breadth", f"{match['breadth']}%")
    
    st.divider()
    
    # Action buttons
    col1, col2 = st.columns(2)
    with col1:
        summary = f"""
=== CANDIDATE PROFILE ===
Name: {st.session_state.state.data.get('name', 'N/A')}
Email: {st.session_state.state.data.get('email', 'N/A')}
Phone: {st.session_state.state.data.get('phone', 'N/A')}
Experience: {st.session_state.state.data.get('experience', 'N/A')} years
Position: {st.session_state.state.data.get('position', 'N/A')}
Location: {st.session_state.state.data.get('email', 'N/A')}
Tech Stack: {st.session_state.state.data.get('tech_stack', 'N/A')}

=== TECHNICAL QUESTIONS ===
{st.session_state.state.data.get('technical_questions', 'N/A')}

=== SUBMISSION ===
Timestamp: {st.session_state.state.data.get('submission_timestamp', 'N/A')}
ID: {st.session_state.state.data.get('candidate_id', 'N/A')}
"""
        st.download_button(
            "📥 Download Summary",
            summary,
            file_name=f"candidate_{st.session_state.state.data.get('candidate_id', 'profile')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col2:
        if st.button("🔄 Start New Interview", use_container_width=True):
            st.session_state.clear()
            st.rerun()

# Admin view for all candidates
if st.session_state.get('show_admin', False):
    st.divider()
    st.header("📊 All Candidates Dashboard")
    
    filepath = "candidate_data/candidates.json"
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            candidates = json.load(f)
        
        st.metric("Total Candidates Interviewed", len(candidates))
        
        # Display recent candidates
        for candidate in reversed(candidates[-10:]):  # Show last 10
            with st.expander(f"🧑 {candidate.get('name', 'Unknown')} - {candidate.get('position', 'N/A')} ({candidate.get('submission_timestamp', '')[:10]})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**📧 Email:** {candidate.get('email', 'N/A')}")
                    st.write(f"**📱 Phone:** {candidate.get('phone', 'N/A')}")
                    st.write(f"**💼 Experience:** {candidate.get('experience', 'N/A')} years")
                with col2:
                    st.write(f"**📍 Location:** {candidate.get('location', 'N/A')}")
                    st.write(f"**💻 Tech Stack:** {candidate.get('tech_stack', 'N/A')}")
                    st.write(f"**🕒 Submitted:** {candidate.get('submission_timestamp', 'N/A')[:19]}")
        
        if st.button("❌ Close Dashboard"):
            st.session_state.show_admin = False
            st.rerun()
    else:
        st.info("No candidates yet. Complete an interview to see data here!")
