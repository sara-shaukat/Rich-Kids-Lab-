## ⚠️ Running AI Features Locally

This project uses the **Groq API** to power the AI Mentor, AI Micro Business suggestion and AI-generated Report Card commentary. 
These features require your own Groq API key to work when running locally.

**To enable AI features:**
1. Get a free API key from [console.groq.com](https://console.groq.com)
2. Create a `.env` file inside the `backend/` folder (use `backend/.env.example` as a template)
3. Add your key:
4. Restart the backend server
   
**Without a key set**, the app still runs fully-the AI Mentor, Micro Business Suggestion and Report Card 
will fall back to pre-written template responses instead of live AI-generated ones, 
so all core features (Save, Spend, Grow, Give, badges, dashboard) remain fully functional.

📹 **See the demo video for the AI Mentor and AI Report Card in action.**
These were tested and working with a live Groq API key during development.
