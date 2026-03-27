from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

# Load the GOOGLE_API_KEY and DATABASE_URL from the .env file
load_dotenv()

app = FastAPI()

# Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Setup the AI Model (Using Gemini!)
llm = ChatGoogleGenerativeAI(temperature=0.2, model="gemini-2.5-flash")

# 2. The Strict System Prompt
prompt_template = """
You are an empathetic, professional triage nurse for a Pakistani telemedicine platform.
Your ONLY job is to collect patient history in a structured way.
You must ask about:
1. Chief Complaint (What is wrong?)
2. Duration (How long has it been happening?)
3. Severity (How bad is it?)
4. Medical History (Any past illnesses or current medications?)

CRITICAL RULES:
- You must NEVER diagnose the patient.
- You must NEVER prescribe medication.
- Ask one question at a time. Be empathetic.
- If a patient asks for a diagnosis, politely tell them that only a doctor can diagnose, and you are here to gather information for the doctor.
- VERY IMPORTANT: Once you have collected the 4 basic pieces of information, you MUST ask 5 to 8 relevant, detailed follow-up questions about their specific symptoms to build a comprehensive report.
- After you have asked exactly 5 to 8 follow-up questions, politely end the triage session by telling the patient that you have everything the doctor needs. DO NOT ask any further questions after that.

Current conversation:
{history}
Patient: {human_input}
Nurse:"""

prompt = PromptTemplate(
    input_variables=["history", "human_input"], 
    template=prompt_template
)

# ==========================================
# DATABASE HELPER FUNCTIONS (Session IDs)
# ==========================================

def get_db_connection():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

def get_or_create_patient_session(phone_number: str) -> int:
    """Finds active session for a phone number, creates patient & session if missing."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Look up the Patient by phone number
    cursor.execute("SELECT patient_id FROM patients WHERE phone_number = %s", (phone_number,))
    patient = cursor.fetchone()
    
    if not patient:
        cursor.execute("INSERT INTO patients (phone_number) VALUES (%s) RETURNING patient_id", (phone_number,))
        patient_id = cursor.fetchone()[0]
    else:
        patient_id = patient[0]
        
    # 2. Look up the Patient's Active Session
    cursor.execute("SELECT session_id FROM chat_sessions WHERE patient_id = %s AND is_active = TRUE", (patient_id,))
    session = cursor.fetchone()
    
    if not session:
        cursor.execute("INSERT INTO chat_sessions (patient_id, is_active) VALUES (%s, TRUE) RETURNING session_id", (patient_id,))
        session_id = cursor.fetchone()[0]
    else:
        session_id = session[0]
        
    conn.commit()
    cursor.close()
    conn.close()
    return session_id

def get_chat_history(session_id: int) -> str:
    """Retrieves all past messages for a specific session to feed to the AI."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Efficient Indexed Query
    cursor.execute("SELECT sender_type, content FROM messages WHERE session_id = %s ORDER BY created_at", (session_id,))
    messages = cursor.fetchall()
    
    history_str = ""
    for msg in messages:
        if msg['sender_type'] == 'Human':
            history_str += f"Patient: {msg['content']}\n"
        else:
            history_str += f"Nurse: {msg['content']}\n"
            
    cursor.close()
    conn.close()
    return history_str

def save_message(session_id: int, sender_type: str, content: str):
    """Logs a standalone message into the relational database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (session_id, sender_type, content) VALUES (%s, %s, %s)", (session_id, sender_type, content))
    conn.commit()
    cursor.close()
    conn.close()


# --- API ENDPOINTS ---

@app.post("/chat/web")
async def web_chat(message: dict):
    user_message = message.get("text")
    
    # Since Web users don't log in right now, we route them to a global "Web" phone number acting as a Session tracker
    session_id = get_or_create_patient_session("WEB_GUEST_001")
    
    # 1. Fetch History from Secure Postgres DB
    history = get_chat_history(session_id)
    
    # 2. Invoke LangChain 
    final_prompt = prompt.format(history=history, human_input=user_message)
    
    try:
        ai_response = llm.invoke(final_prompt).content
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            return {"response": "The AI Doctor is currently busy due to high Google API traffic on your free tier. Please wait 60 seconds and click Send again!"}
        return {"response": "An unexpected server error occurred."}
    
    # 3. Save Both Messages to Postgres
    save_message(session_id, "Human", user_message)
    save_message(session_id, "AI", ai_response)
    
    return {"response": ai_response}

@app.post("/chat/whatsapp")
async def whatsapp_chat(Body: str = Form(...), From: str = Form(...)):
    # Twilio sends WhatsApp numbers formatted as "whatsapp:+1234567890"
    # We strip "whatsapp:" off so it perfectly fits our strict 20-character database limit!
    clean_phone = From.replace("whatsapp:", "")
    
    session_id = get_or_create_patient_session(clean_phone)
    
    history = get_chat_history(session_id)
    
    final_prompt = prompt.format(history=history, human_input=Body)
    
    try:
        ai_response = llm.invoke(final_prompt).content
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            resp = MessagingResponse()
            resp.message("The AI Doctor is currently busy with high patient volume. Please wait exactly 1 minute before sending another message to avoid API Free-Tier overload.")
            return PlainTextResponse(str(resp), media_type="application/xml")
        raise e
    
    save_message(session_id, "Human", Body)
    save_message(session_id, "AI", ai_response)
    
    resp = MessagingResponse()
    resp.message(ai_response)
    return PlainTextResponse(str(resp), media_type="application/xml")

@app.get("/active_sessions")
async def get_active_sessions():
    """Returns a list of all currently active triage patients connected to postgres."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT c.session_id, p.phone_number, c.created_at 
        FROM chat_sessions c
        JOIN patients p ON c.patient_id = p.patient_id
        WHERE c.is_active = TRUE
        ORDER BY c.created_at DESC
    """)
    sessions = cursor.fetchall()
    cursor.close()
    conn.close()
    
    for s in sessions:
        s['created_at'] = str(s['created_at'])  # Convert to string for JSON parsing
    return {"sessions": sessions}

@app.get("/summary")
async def generate_summary(session_id: int):
    """Generates the summary for the SPECIFIC requested session in DB."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify the heavily requested session exists and is active
    cursor.execute("SELECT session_id FROM chat_sessions WHERE session_id = %s AND is_active = TRUE", (session_id,))
    session = cursor.fetchone()
    
    if not session:
        cursor.close()
        conn.close()
        return {"summary": "This session is either not active or does not exist."}
        
    chat_history = get_chat_history(session_id)
    
    if not chat_history:
        return {"summary": "No messages in the current session."}
    
    summary_template = """
    You are an expert medical assistant. Based on the conversation below between a triage nurse and a patient, extract the following information and format it clearly for a doctor:
    
    - Chief Complaint:
    - Duration:
    - Severity:
    - Medical History:
    
    If any information is missing, simply write "Not provided". Do NOT invent information.
    
    Conversation:
    {chat_history}
    
    Structured Summary:
    """
    
    summary_prompt = PromptTemplate(input_variables=["chat_history"], template=summary_template)
    final_prompt = summary_prompt.format(chat_history=chat_history)
    
    try:
        summary_result = llm.invoke(final_prompt).content
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            return {"summary": "Google API Rate Limit hit. Please wait 60 seconds, then try generating the summary again!"}
        return {"summary": "An unexpected error occurred while generating the summary."}
    
    # Insert the final generated report into the database under 'chief_complaint' as a general report dump.
    # IMPORTANT: This insert activates our Postgres Stored Procedure TRIGGER to close the session!
    cursor.execute(
        "INSERT INTO triage_summaries (session_id, chief_complaint) VALUES (%s, %s)",
        (session_id, summary_result)
    )
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return {"summary": summary_result}