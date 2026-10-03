from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

profile = {
    "heroTitle": "shuai",
    "heroSubtitle": "项目，创意，灵感，心得，我的作品",
}


class AnalyzeRequest(BaseModel):
    text: str


@app.post("/api/analyze")
@app.post("/api/")
def analyze(req: AnalyzeRequest):
    return {
        "text": req.text,
        "score": 0.5,
        "label": "偏平静",
        "pinyin": "（模块 6 再说）",
    }


@app.get("/api/profile")
def get_profile():
    return profile
