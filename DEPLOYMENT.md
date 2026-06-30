# Deployment Guide for CineQuery AI (सिనిma AI)

This guide walks you through deploying the **Vite React Frontend** and the **FastAPI Python Backend** (including the local PyTorch SentenceTransformer model and persistent ChromaDB database) so that anyone can access the app online.

---

## 1. Production Architecture Overview

- **Frontend**: Hosted on **Vercel** or **Netlify** (Free static hosting).
- **Backend**: Hosted on **Render**, **Railway**, or a **VPS** (e.g. AWS EC2, DigitalOcean) with a **Persistent Disk Volume** mounted at the Chroma database folder.
- **Database**: Local SQLite/Chroma instance, stored on the persistent disk.

---

## 2. Deploying the Backend (FastAPI)

Your backend has two special needs:
1. **RAM**: Needs at least **1.5 GB of RAM** to load the embedding and re-ranking models into memory.
2. **Persistence**: Needs a persistent disk directory to prevent losing the 40,869 movie plots when the container restarts.

### Option A: Railway.app (Easiest)
1. Sign up on [Railway.app](https://railway.app/).
2. Click **New Project** -> **Deploy from GitHub repo**.
3. Select your repository.
4. Go to **Settings** -> **Volumes** -> Click **Add Volume** (Create a 5GB volume and mount it at `/data`).
5. Go to **Variables** and add:
   - `LLM_PROVIDER = groq`
   - `GROQ_API_KEY = <your-api-key>`
   - `CHROMA_STORE_DIR = /data/chroma_store` (Points to your persistent volume directory)
6. Railway will automatically detect the Python files and start the server using your `requirements.txt`.

### Option B: Render.com
1. Sign up on [Render.com](https://render.com/).
2. Create a new **Web Service** and connect your GitHub repository.
3. Configure the build:
   - **Runtime**: `Python`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. In **Advanced settings**:
   - Add a **Disk** (Mount Path: `/data`, Size: 5 GB).
   - Set the env variable: `CHROMA_STORE_DIR = /data/chroma_store`.
   - Add your `GROQ_API_KEY` and `LLM_PROVIDER`.

---

## 3. Deploying the Frontend (React / Vite)

Before deploying the frontend, update it to point to your new live backend URL:

1. Open `frontend/src/App.jsx`
2. Update the API base URL in the `useStream` hook instantiation:
   ```javascript
   // Replace localhost with your live backend domain
   const { streamMessage, loading } = useStream("https://your-backend-name.up.railway.app");
   ```

### Deploying on Vercel:
1. Log in to [Vercel](https://vercel.com/).
2. Click **Add New** -> **Project**.
3. Select your repository.
4. In the settings, configure the following:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. Click **Deploy**. Vercel will build the frontend assets and host them on a fast, free CDN subdomain.

---

## 4. Initial Ingestion in Production

Once the backend is live, you need to populate the database with the movie records:
1. Access the terminal shell of your service (available in Render/Railway dashboard console).
2. Run the ingestion command manually:
   ```bash
   python -m backend.ingestion.loader
   ```
   This will download the embedding model, scan the datasets folder, deduplicate the records, and index all 40,869 chunks directly onto your mounted persistent volume!
