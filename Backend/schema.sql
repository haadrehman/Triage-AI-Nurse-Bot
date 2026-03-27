-- Drop tables if they already exist (for clean runs)
DROP TABLE IF EXISTS triage_summaries CASCADE;
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS chat_sessions CASCADE;
DROP TABLE IF EXISTS patients CASCADE;

-- 1. Patients Table
CREATE TABLE patients (
    patient_id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Chat Sessions Table
CREATE TABLE chat_sessions (
    session_id SERIAL PRIMARY KEY,
    patient_id INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_patient FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
);

-- 3. Messages Table
CREATE TABLE messages (
    message_id SERIAL PRIMARY KEY,
    session_id INT NOT NULL,
    sender_type VARCHAR(10) CHECK (sender_type IN ('Human', 'AI')),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_session FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
);

-- 4. Triage Summaries Table
CREATE TABLE triage_summaries (
    summary_id SERIAL PRIMARY KEY,
    session_id INT UNIQUE NOT NULL,
    chief_complaint TEXT,
    duration TEXT,
    severity TEXT,
    medical_history TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_session_summary FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
);

-- ==========================================
-- PERFORMANCE OPTIMIZATION (INDEXING)
-- ==========================================
-- Index for extremely fast message retrieval for active chat sessions
CREATE INDEX idx_messages_session_id ON messages(session_id);

-- Index to quickly find all sessions belonging to a specific patient
CREATE INDEX idx_sessions_patient_id ON chat_sessions(patient_id);

-- ==========================================
-- DATA PROCESSING (STORED PROCEDURES & TRIGGERS)
-- ==========================================
-- Stored Procedure: Automatically close a chat session when a summary is generated
CREATE OR REPLACE FUNCTION finalize_triage_session()
RETURNS TRIGGER AS $$
BEGIN
    -- Update the chat_session to inactive so no further messages go to it
    UPDATE chat_sessions
    SET is_active = FALSE
    WHERE session_id = NEW.session_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to execute the stored procedure AFTER an INSERT into triage_summaries
CREATE TRIGGER trigger_finalize_session
AFTER INSERT ON triage_summaries
FOR EACH ROW
EXECUTE FUNCTION finalize_triage_session();
