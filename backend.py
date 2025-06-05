# backend.py
import os
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import numpy as np
import faiss
from dotenv import load_dotenv
from openai import OpenAI
from threading import Lock

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY not set")

client = OpenAI(api_key=openai_api_key)
app = FastAPI()

dimension = 1536
index = faiss.IndexFlatL2(dimension)
embedding_store = []
incidents = []
solutions = []
fix_status = []

faiss_lock = Lock()

class Incident(BaseModel):
    description: str

def get_embedding_sync(text: str) -> list:
    try:
        response = client.embeddings.create(
            input=text,
            model="text-embedding-ada-002"
        )
        return response.data[0].embedding
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding error: {e}")

def query_similar(embedding: list, top_k=3) -> list:
    if len(embedding_store) == 0:
        return []
    with faiss_lock:
        D, I = index.search(np.array([embedding]).astype('float32'), top_k)
    results = []
    for i in I[0]:
        if i < len(embedding_store):
            results.append(embedding_store[i])
    return results

def generate_suggestion_sync(incident_text: str, similar_texts: list) -> str:
    prompt = f"Incident: {incident_text}\n"
    if similar_texts:
        prompt += "Similar past incidents:\n"
        for sim in similar_texts:
            prompt += f"- {sim}\n"
    prompt += "\nSuggest troubleshooting and remediation steps."

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Suggestion error: {e}")

def execute_fix_sync(index_param: int):
    if index_param < 0 or index_param >= len(solutions):
        raise HTTPException(status_code=400, detail="Invalid index")
    print(f"Executing fix for incident {index_param}: {solutions[index_param]}")
    import time
    time.sleep(2)  # Simulate delay
    fix_status[index_param] = "executed"
    print(f"Fix executed for incident {index_param}")

def agentic_workflow(description: str, idx: int):
    emb = get_embedding_sync(description)
    with faiss_lock:
        index.add(np.array([emb]).astype('float32'))
        embedding_store.append(description)

    similar = query_similar(emb)
    suggestion = generate_suggestion_sync(description, similar)

    incidents.append(description)
    solutions.append(suggestion)
    fix_status.append("pending")

    # Simulate agent executing fix in background
    execute_fix_sync(idx)

@app.post("/incident/")
async def receive_incident(incident: Incident, background_tasks: BackgroundTasks):
    idx = len(incidents)
    background_tasks.add_task(agentic_workflow, incident.description, idx)
    return {
        "incident": incident.description,
        "message": "Agent started processing the incident.",
        "status": "processing"
    }

@app.post("/execute_fix/")
async def execute_fix_endpoint(index_param: int):
    await asyncio.to_thread(execute_fix_sync, index_param)
    return {"status": "success", "message": f"Fix executed for incident {index_param}"}

@app.get("/history/")
async def history():
    return {
        "incidents": incidents,
        "solutions": solutions,
        "fix_status": fix_status
    }
