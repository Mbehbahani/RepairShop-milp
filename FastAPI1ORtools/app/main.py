# app/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from app.optimiser import run_job
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="Optimiser API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ "https://oploy.netlify.app",
                    "http://oploy.netlify.app",
                    "https://opt.oploy.eu",
                    "http://opt.oploy.eu",
                    "http://localhost:3000",
                    "http://milp.netlify.app",
                    "https://milp.netlify.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class SchedulePayload(BaseModel):
    T:  dict[int, float]
    I:  dict[int, float]
    ST: dict[int, int]
    OV_limit: dict[str, int] | None = None
    d:  dict[str, dict[str, int]]
    e:  dict[str, dict[str, int]]

@app.post("/solve")
async def solve(payload: SchedulePayload):
    """
    POST the JSON; get back figure + stats synchronously
    (good enough for local testing; switch to BackgroundTasks/Celery later).
    """
    result = run_job(payload.model_dump())
    return result

@app.get("/")
def root():
    return {"msg": "Up & running 🎉  – hit /docs for Swagger UI"}
