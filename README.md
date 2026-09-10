# SPARK-Student-Pathway-Academic-Readiness-Knowledge-Portal
SPARK – Student Pathway &amp; Academic Readiness Knowledge Portal is an AI-enabled student guidance platform that helps students plan academics, explore universities, track admission requirements, manage applications, monitor deadlines, and connect with counselors.
# SPARK – Student Pathway & Academic Readiness Knowledge Portal

**SPARK** is a comprehensive student guidance and academic planning platform designed to help students make informed decisions about their higher-education journey.

The platform brings academic information, university exploration, admission requirements, application tracking, deadlines, milestones, documents, essays, Letters of Recommendation (LORs), and counselor guidance into a single centralized portal.

## 🚀 Key Features

- 👨‍🎓 **Student Dashboard** – Centralized view of academic and application progress
- 📚 **Academic Tracking** – Manage academic performance, tests, and milestones
- 🎓 **University Exploration** – Explore and shortlist universities based on student goals
- 📋 **Prerequisites & Requirements** – Track admission requirements for universities and countries
- ⏰ **Deadline Management** – Monitor important application and admission deadlines
- 📄 **Document Management** – Upload and manage application-related documents
- ✍️ **Essay Management** – Create, manage, and track application essays
- 📝 **LOR Management** – Manage Letters of Recommendation
- 👩‍🏫 **Counselor Workspace** – Enables counselors to monitor and guide students
- 📊 **Readiness & Progress Tracking** – Helps students understand their application preparedness
- 🔔 **Alerts & Actions** – Highlights pending requirements and upcoming tasks
- 📑 **Interactive PDF Reports** – Generate structured student/application reports
- 🔐 **Role-Based Authentication** – Separate access for students and counselors

## 🛠️ Technology Stack

- **Backend:** Python, Flask
- **Database:** PostgreSQL
- **Frontend:** HTML, CSS, JavaScript, Jinja2
- **Data Processing:** Python
- **Authentication:** Flask-based role authentication
- **Reports:** Custom interactive PDF generation

## 🎯 Objective

SPARK aims to simplify the complex university application process by providing students and counselors with a structured platform for **academic planning, university selection, requirement tracking, application management, and progress monitoring**.

> **Plan smarter. Prepare better. Reach further.**

## 🔮 Future Scope

- AI-powered university recommendations
- Personalized admission-readiness scoring
- AI-assisted essay feedback
- Intelligent deadline reminders
- University requirement comparison
- Scholarship recommendation
- Multilingual student assistance
- Predictive admission analytics
- AI-powered counselor assistance

## 🚀 Deployment Guide

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/Sandhyakrishnamari/SPARK-3.git
cd SPARK-3
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create environment file:
```bash
cp .env.example .env
```

4. Run the application:
```bash
python app.py
```

### Vercel Deployment

#### Database Setup (Required for Production)

Since Vercel's serverless environment doesn't support persistent SQLite, you need to set up a PostgreSQL database:

**Option 1: Free PostgreSQL Services**

1. **ElephantSQL** (Free tier available)
   - Sign up at [elephantsql.com](https://www.elephantsql.com)
   - Create a new database
   - Copy the connection URL

2. **Supabase** (Free tier available)
   - Sign up at [supabase.com](https://supabase.com)
   - Create a new project
   - Go to Settings > Database
   - Copy the connection string

3. **Neon** (Free tier available)
   - Sign up at [neon.tech](https://neon.tech)
   - Create a new project
   - Copy the connection string

#### Deploy to Vercel

1. Push your code to GitHub

2. Go to [vercel.com](https://vercel.com) and import your repository

3. Add the following environment variables in Vercel project settings:
   - `DATABASE_URL`: Your PostgreSQL connection string
   - `SECRET_KEY`: A random secret key (generate one with: `python -c "import secrets; print(secrets.token_hex(32))"`)

4. Deploy!

The application will automatically:
- Detect PostgreSQL via `DATABASE_URL` environment variable
- Create all necessary tables on first run
- Handle both local SQLite and production PostgreSQL
