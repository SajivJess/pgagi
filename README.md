# TalentScout Hiring Assistant 💼

> AI-powered recruitment chatbot for initial candidate screening  
> **AI/ML Intern Assignment Submission**

---

## 📋 Overview

TalentScout Hiring Assistant is an intelligent chatbot that automates the initial screening phase of technology recruitment. Using advanced prompt engineering with Google Gemini LLM, it:

- Collects essential candidate information through natural conversation
- Gathers detailed tech stack declarations
- Generates personalized technical questions based on candidate's expertise
- Maintains professional context throughout the interaction
- Stores candidate data securely with GDPR compliance

---

## ✨ Features

### Core Functionality
- ✅ **Conversational UI**: Clean Streamlit interface for seamless interaction
- ✅ **Information Gathering**: Collects name, email, phone, experience, position, location, tech stack
- ✅ **Input Validation**: Real-time email/phone/experience format validation
- ✅ **Dynamic Question Generation**: Creates 3 relevant technical questions per tech stack
- ✅ **Context Management**: Maintains conversation flow and handles follow-ups
- ✅ **Scope Control**: Stays focused on hiring topics, redirects off-topic queries
- ✅ **Graceful Exit**: Handles conversation-ending keywords (bye, exit, quit, done)
- ✅ **Data Privacy**: GDPR-compliant JSON storage with timestamped IDs

### Technical Highlights
- **Prompt Engineering**: Crafted prompts for each conversation stage (greeting, info gathering, question generation, fallback, exit)
- **State Management**: Tracks conversation stages and candidate data across interactions
- **Validation Layer**: Regex patterns for email/phone, numeric validation for experience
- **Error Handling**: Graceful fallbacks for invalid inputs or API errors
- **Data Export**: Download candidate summaries as text files

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Frontend** | Streamlit |
| **LLM** | Google Gemini Pro |
| **API Integration** | `google-generativeai` SDK |
| **Language** | Python 3.8+ |
| **Data Storage** | JSON file-based (GDPR-compliant) |
| **Deployment** | Local (cloud-ready) |

---

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- Gemini API key ([get one here](https://aistudio.google.com/apikey))

### Setup Steps

1. **Clone the repository**
```bash
git clone https://github.com/SajivJess/Constructure-AI---Project-Brain.git
cd "Constructure-AI---Project-Brain"
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

Required packages:
- `streamlit>=1.28.0`
- `google-generativeai>=0.3.0`
- `python-dotenv>=1.0.0`

3. **Configure API Key**

Create a `.env` file in the project root:
```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

4. **Run the application**
```bash
streamlit run streamlit_app.py
```

The app will open at `http://localhost:8501`

---

## 🎯 Usage Guide

### Starting an Interview

1. Launch the app - you'll see an automated greeting
2. Follow the conversational prompts to provide:
   - Full Name
   - Email Address (validated)
   - Phone Number (validated)
   - Years of Experience (0-50)
   - Desired Position(s)
   - Current Location
   - Tech Stack (e.g., "Python, Django, PostgreSQL, Docker, AWS")

### Technical Questions

After declaring your tech stack, the assistant will:
- Analyze your technologies
- Generate 3 relevant technical questions
- Tailor difficulty to your experience level

### Ending the Conversation

Type any of these keywords to exit:
- `bye`
- `goodbye`
- `exit`
- `quit`
- `done`
- `finish`

### Downloading Results

After completion:
1. Click "📥 Download Summary"
2. Get a formatted text file with your profile and questions
3. Click "🔄 Start New Interview" to reset

---

## 🧠 Prompt Engineering Design

### System Architecture

The chatbot uses a **stage-based conversation flow** with specialized prompts:

#### 1. **Greeting Stage**
```
Purpose: Welcome candidate and set expectations
Approach: Warm introduction, brief overview of process
Output: 2-3 sentence greeting
```

#### 2. **Information Gathering**
```
Purpose: Collect 7 essential fields sequentially
Approach: Friendly questions with validation feedback
Fields: name → email → phone → experience → position → location → tech_stack
```

#### 3. **Technical Question Generation**
```
Input: Tech stack + years of experience
Prompt Template: "Generate {N} questions for {technologies} at {X} years level"
Output: Numbered list of practical, job-relevant questions
```

#### 4. **Context Maintenance**
```
Purpose: Handle follow-ups and clarifications
Approach: Inject conversation history into prompts
Mechanism: Last 5 messages passed as context
```

#### 5. **Fallback Handling**
```
Triggers: Off-topic queries, unclear inputs, greetings
Response: Polite redirection to hiring matters
Example: "I focus on recruitment. Let's continue with..."
```

#### 6. **Exit Flow**
```
Keywords: bye, goodbye, exit, quit, done, finish
Response: Thank candidate, confirm data, mention next steps
```

### Prompt Optimization Techniques

1. **Role Definition**: Clear identity as "TalentScout Hiring Assistant"
2. **Constraint Setting**: Explicit rules to prevent scope deviation
3. **Output Formatting**: Structured templates for consistent responses
4. **Context Injection**: Dynamic insertion of candidate data and stage info
5. **Temperature Control**: 0.7 for balanced creativity and consistency
6. **Token Limits**: Max 500 tokens per response for conciseness

---

## 📁 Project Structure

```
.
├── streamlit_app.py          # Main Streamlit application (all-in-one)
├── requirements.txt           # Python dependencies
├── .env                       # API keys (gitignored)
├── .env.example              # Template for environment variables
├── candidate_data/            # Stored candidate JSONs (gitignored)
│   └── candidates.json       # Candidate submissions
├── README.md                 # This file
└── .gitignore                # Excludes sensitive data
```

---

## 🔒 Data Privacy & Security

### GDPR Compliance

- **Consent**: Candidates informed of data collection purpose
- **Minimization**: Only essential recruitment data collected
- **Storage**: Local JSON files with encrypted options
- **Access Control**: File-based permissions (extendable to auth)
- **Retention**: Manual purging via file deletion
- **Right to be Forgotten**: Delete JSON entry on request

### Security Measures

1. ✅ API keys stored in `.env` (never committed)
2. ✅ Email/phone validation prevents injection attacks
3. ✅ Candidate data directory excluded from version control
4. ✅ No sensitive data logged or displayed in UI
5. ✅ Timestamps and unique IDs for audit trails

---

## 🧪 Testing

### Manual Test Scenarios

1. **Happy Path**
   - Provide all valid inputs
   - Verify technical questions generated
   - Check candidate_data/candidates.json created

2. **Validation Tests**
   - Invalid email: `testuser@` → should reject
   - Invalid phone: `abc123` → should reject
   - Invalid experience: `100 years` → should reject

3. **Edge Cases**
   - Exit mid-conversation: type `bye` at any stage
   - Off-topic query: ask about weather → redirects
   - Empty tech stack: triggers clarification prompt

4. **Context Tests**
   - Ask follow-up: "what about Python specifically?"
   - Verify previous answers maintained

### Automated Testing (Future)
```python
# Example test structure
def test_email_validation():
    assert validate_email("test@example.com")[0] == True
    assert validate_email("invalid-email")[0] == False

def test_conversation_flow():
    state = ConversationState()
    assert state.current_stage() == "greeting"
    state.advance()
    assert state.current_stage() == "name"
```

---

## 🚀 Deployment Options

### Local Deployment ✅
```bash
streamlit run streamlit_app.py
```

### Cloud Deployment (Bonus)

#### Option 1: Streamlit Cloud (Recommended)
1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io/)
3. Connect repository
4. Add `GEMINI_API_KEY` to Secrets
5. Deploy automatically

#### Option 2: AWS EC2
```bash
# Install dependencies
sudo apt update
sudo apt install python3-pip
pip3 install -r requirements.txt

# Run with nohup
nohup streamlit run streamlit_app.py --server.port 8501 &
```

#### Option 3: Google Cloud Run
```dockerfile
# Dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501"]
```

---

## 🎓 Challenges & Solutions

### Challenge 1: Maintaining Conversation Context
**Problem**: LLM has no memory between requests  
**Solution**: Inject last 5 messages as context in each prompt  
**Code**: `context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history[-5:]])`

### Challenge 2: Preventing Scope Deviation
**Problem**: Users ask off-topic questions  
**Solution**: System prompt with explicit rules + fallback prompt detecting deviation  
**Implementation**: Check for hiring-related keywords, redirect if absent

### Challenge 3: Dynamic Question Generation
**Problem**: Questions must match diverse tech stacks  
**Solution**: Parameterized prompt with tech stack and experience level  
**Template**: `"Generate {N} questions for {stack} at {years} years level"`

### Challenge 4: Data Validation Without Breaking Flow
**Problem**: Invalid inputs disrupt conversation  
**Solution**: Inline validation with friendly error messages, re-prompt same question  
**Example**: "Invalid email. Please provide a valid email address." + original question

### Challenge 5: Secure API Key Management
**Problem**: API keys in code = security risk  
**Solution**: Environment variables with `.env` file + `.gitignore`  
**Best Practice**: Streamlit Secrets for cloud deployment

---

## 📊 Evaluation Criteria Mapping

| Criterion | Implementation | Evidence |
|-----------|----------------|----------|
| **Technical Proficiency (40%)** | ✅ Gemini integration, prompt engineering, validation logic | `streamlit_app.py` lines 150-280 |
| **Problem-Solving (30%)** | ✅ Stage-based state machine, context injection, fallback handling | ConversationState class + prompts |
| **UI/UX (15%)** | ✅ Clean Streamlit interface, custom CSS, info box, chat bubbles | Lines 240-260 (CSS) |
| **Documentation (10%)** | ✅ Comprehensive README with setup, usage, prompt design | This file |
| **Bonus (5%)** | ✅ Deployment guide, GDPR compliance, downloadable summaries | Sections above |

---

## 📝 Future Enhancements

- [ ] **Multilingual Support**: Detect language and respond accordingly
- [ ] **Sentiment Analysis**: Gauge candidate enthusiasm via text analysis
- [ ] **Video Recording**: Optional video responses for questions
- [ ] **ATS Integration**: Export to Applicant Tracking Systems (Greenhouse, Lever)
- [ ] **Analytics Dashboard**: Visualize candidate stats, popular tech stacks
- [ ] **Auto-Scheduling**: Integrate with Calendly for interview booking
- [ ] **Email Notifications**: Auto-send summaries to recruiters

---

## 👤 Author

**Sajiv Jess**  
AI/ML Intern Candidate

- GitHub: [@SajivJess](https://github.com/SajivJess)
- Project: [Constructure-AI---Project-Brain](https://github.com/SajivJess/Constructure-AI---Project-Brain)

---

## 📄 License

This project is submitted as part of an AI/ML internship assignment.  
All rights reserved © 2025

---

## 🙏 Acknowledgments

- **Google Gemini**: LLM powering the conversational AI
- **Streamlit**: Rapid prototyping framework
- **TalentScout**: Fictional recruitment agency scenario
- **Assignment Provider**: For the challenging and educational task

---

## 📞 Support

For questions or issues:
1. Check the [Installation](#-installation) section
2. Verify your `.env` file has valid `GEMINI_API_KEY`
3. Ensure Python 3.8+ is installed
4. Check `candidate_data/` folder permissions

**Common Issues**:
- "GEMINI_API_KEY not found" → Create `.env` file with key
- "google-generativeai not installed" → Run `pip install google-generativeai`
- "Permission denied" → Run `chmod 755 streamlit_app.py`

---

**Live Demo Video**: [Coming Soon - LOOM recording]

**Submission Date**: December 12, 2025  
**Assignment Deadline**: 48 hours from receipt
