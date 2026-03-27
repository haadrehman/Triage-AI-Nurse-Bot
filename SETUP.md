# Complete Setup Guide
How to safely install and run the AI Triage Nurse locally from scratch.

## 1. Prerequisites
- **Node.js**: (Required to start the React Frontend)
- **Python**: (v3.12 or newer. `uv` or `pip` virtual environments highly recommended)
- **Postgres.app**: (Provides the local SQL Database strictly running on `localhost:5432`)
- **ngrok**: (Required to securely tunnel your local Python server to the internet for Twilio)
- **API Keys**: You will need free trial accounts for Google AI Studio and Twilio!

## 2. PostgreSQL Database Setup
1. Open Postgres.app and launch the terminal by double-clicking your database icon.
2. If it does not exist, manually create your exact project database:
   `CREATE DATABASE triage_nurse_ai_bot;`
3. Connect to that specific database:
   `\c triage_nurse_ai_bot`
4. Copy the entire contents of the `/Backend/schema.sql` file and paste it into the terminal to officially create all your Relational Tables, Indexes, and your PL/pgSQL Trigger!

## 3. Backend Setup (FastAPI & AI Engine)
1. Open a terminal and strictly navigate into the backend folder: `cd Backend`
2. Open or create the `.env` configuration file containing exactly:
```env
GEMINI_API_KEY="your-google-ai-key-here"
TWILIO_ACCOUNT_SID="your-twilio-sid-here"
TWILIO_AUTH_TOKEN="your-twilio-token-here"
DATABASE_URL="postgresql://m.haadrehman@localhost:5432/triage_nurse_ai_bot"
```
3. Initialize and activate your Python virtual environment (e.g. `uv venv`).
4. Install exactly what your application requires:
   `pip install fastapi uvicorn psycopg2-binary langchain langchain-google-genai twilio python-dotenv`
5. Run the live development server:
   `uvicorn main:app --reload`

## 4. Frontend Setup (React Dashboard)
1. Open a *new* terminal tab and navigate into the exact client directory: `cd client`
2. Install Javascript Node modules (First time only):
   `npm install`
3. Start the Live Doctor Dashboard Web App:
   `npm start`

## 5. WhatsApp Integration (Twilio Live Sandbox)
1. Open a *new* terminal tab and start an ngrok tunnel directly pointing to your FastAPI `8000` port:
   `ngrok http 127.0.0.1:8000`
2. Copy the secure Forwarding URL it outputs (Looks similar to `https://1234abcd.ngrok-free.app`).
3. Log in to the **Twilio Console** -> **Messaging** -> **Try it Out** -> **Send a WhatsApp Message**.
4. Inside your Sandbox Settings, locate the "When a message comes in" URL field. Paste your secure ngrok URL and ensure you add the exact Python route `/chat/whatsapp` to the very end!
5. Save your Sandbox settings! You can now freely text the Twilio provided number securely from your own WhatsApp.
