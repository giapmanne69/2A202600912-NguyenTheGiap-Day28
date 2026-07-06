# api-gateway/main.py
from fastapi import FastAPI, Request
from prometheus_fastapi_instrumentator import Instrumentator
import httpx, os, time

app = FastAPI(title="AI Platform API Gateway")
Instrumentator().instrument(app).expose(app)  # Integration 9: Prometheus

VLLM_URL = os.environ["VLLM_URL"]
QDRANT_URL = os.environ.get("QDRANT_URL", "http://qdrant:6333")

@app.post("/api/v1/chat")
async def chat(request: Request):
    from fastapi import HTTPException
    body = await request.json()
    if "query" not in body or not body["query"]:
        raise HTTPException(status_code=422, detail="Missing required field 'query'")
        
    query = body["query"]
    start = time.time()

    # 1. Vector search
    async with httpx.AsyncClient() as client:
        search_resp = await client.post(f"{QDRANT_URL}/collections/documents/points/search", json={
            "vector": body.get("embedding", [0.0] * 384),
            "limit": 3
        })
        context = search_resp.json().get("result", [])

    # 2. LLM inference
    prompt = f"Context: {context}\n\nQuery: {query}"
    headers = {
        "ngrok-skip-browser-warning": "true"
    }
    async with httpx.AsyncClient(timeout=30) as client:
        llm_resp = await client.post(
            f"{VLLM_URL}/v1/chat/completions",
            headers=headers,
            json={
                "model": "Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4",
                "messages": [{"role": "user", "content": prompt}]
            }
        )

    latency = (time.time() - start) * 1000
    try:
        result = llm_resp.json()
        answer = result["choices"][0]["message"]["content"]
        model_name = result["model"]
    except Exception as e:
        print(f"ERROR parsing LLM response. HTTP Status: {llm_resp.status_code}, Response Body: {llm_resp.text}")
        raise e

    return {
        "answer": answer,
        "latency_ms": round(latency, 2),
        "model": model_name
    }

@app.get("/health")
def health():
    return {"status": "ok"}
