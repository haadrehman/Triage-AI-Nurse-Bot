# AI Triage Nurse & Live Doctor Dashboard
A full-stack, AI-powered telemedicine pre-consultation platform built for Advanced DBMS.

## Motivation & Problem Statement
Doctors spend critical time gathering routine history. Telemedicine platforms often lack intelligent pre-screening. This system addresses this by introducing an empathetic AI Virtual Triage Nurse that safely gathers patient history across multiple channels without ever diagnosing or prescribing medicine.

## System Architecture
- **Web App (React.js)**: Features a dual-interface. The left side is a patient chat interface simulating an Oladoc-style clinic, and the right side is a **Live Doctor Dashboard** pulling active waiting patients securely from the database.
- **WhatsApp Integration (Twilio Sandbox)**: Accessible triage for patients securely tied to their personal phone number.
- **AI Engine (Google Gemini 2.5 Flash)**: Strongly governed by strict prompt engineering instructing it to strictly gather: *Chief Complaint, Duration, Severity, and Medical History*.
- **Backend (FastAPI)**: Modern Python web server handling Web REST endpoints (`/chat/web`), Doctor Summaries (`/summary`), and asynchronous Twilio Webhooks (`/chat/whatsapp`).
- **Relational Database (PostgreSQL)**: Fully normalized architecture design (`patients`, `chat_sessions`, `messages`, `triage_summaries`) fulfilling the Advanced Database requirements, implementing query Indexes, Primary/Foreign Keys, and automated PL/pgSQL Triggers to manage chat session lifetimes.

## Project Structure
* `/Backend/` - Python FastAPI server `main.py`, Environment Variables `.env`, and core Database creation script `schema.sql`.
* `/client/` - React frontend UI (`App.js`), components, and styles.
* `README.md` - Core project architecture (this file).
* `SETUP.md` - Step-by-step local execution and environment setup instructions.
