# 🌟 Career Stat Card

> ⚡ Generate FIFA-style career cards from your resume, powered by Google's Gemini AI.

**Career Stat Card** is an AI-powered application that parses your resume and a job title or description, then scores your abilities across six core career dimensions (e.g., Technical Proficiency, Adaptability). These scores are visualized as a card with hoverable explanations — much like a FIFA Ultimate Team card. This is just a fun little project that is a result of me wondering what my own card would look like in FIFA.

🧠 Built using Google Gemini + FastAPI + React.js.

---

## 🚀 Live Demo

Frontend: [Deployed on GitHub Pages](https://unnamed-catalyst.github.io/Career-Stat-Card/)  
Backend (FastAPI Swagger): [Deployed on Render](https://career-stat-cards.onrender.com/docs#)

> Note: The backend may take a few seconds to respond on the first call due to Render’s free tier limits on API use.

---

## 🧩 Features

- 📝 Upload your resume (PDF) + a job title or description
- ⚙️ Uses the Google Gemini AI API (gemini-2.5-flash-preview-05-20) to extract and rate your resume
- 🎮 Outputs a FIFA-style card with stats and career fit, scaling stats to fit experience in the field
- 🧾 Hover over stats to reveal explanations
- 📦 Containerized backend with Docker + deployed frontend via GitHub Pages

---

## 🧠 Stats Included


<div align="center">

| Attribute            | Description                                          |
|----------------------|------------------------------------------------------|
| Technical Proficiency | Tools, libraries, and engineering skillset          |
| Problem Solving       | Your ability to solve complex challenges            |
| Communication         | How clearly you convey technical work               |
| Domain Fit            | Alignment to the given job title or description     |
| Initiative & Impact   | Measurable contributions and leadership             |
| Adaptability          | How flexible and versatile your background is       |
| Overall Score         | Weighted average of the above                       |

</div>

---

## 🛠️ Tech Stack

<div align="center">

| Layer       | Tools                                                  |
|-------------|--------------------------------------------------------|
| **Backend** | Python ·FastAPI · Google Gemini API · PyMuPDF · Docker |
| **Frontend**| React.js · JavaScript · Vite · CSS                     |
| **Hosting** | Render.com · GitHub Pages                              |

</div>

---

## 💻 Running Locally

### 1. Clone this repo:
```bash
git clone https://github.com/unnamed-catalyst/Career-Stat-Card.git
cd Career-Stat-Card
```

### 2. Start the backend:

```bash
cd backend
docker build -t career-stat-api .
docker run -p 8000:8000 career-stat-api
```
The API will be available at http://localhost:8000.

### 3. Start the frontend:

```bash
cd frontend
npm install
npm run dev
```
The frontend should be available at http://localhost:5173.

