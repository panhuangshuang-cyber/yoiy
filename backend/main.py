from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypinyin import Style, lazy_pinyin
from snownlp import SnowNLP

# storage 里的路径锚定在 backend/ 自身（见 storage.HISTORY_DB），所以不管从仓库根
# 还是从 backend/ 启动 uvicorn，读写的都是同一个 history.sqlite3。
#
# 但导入路径得跟着启动方式变：从仓库根跑 `uvicorn backend.main:app` 时本级是个包，
# 要用相对导入；在 backend/ 里跑 `uvicorn main:app` 时 main 是顶层模块，没有包可
# 相对，只能直接 import storage。两种都留着，谁在跑谁生效。
try:
    from .storage import MAX_TEXT_LENGTH, init_db, save_record
    from .storage import history as recent_history
except ImportError:
    from storage import MAX_TEXT_LENGTH, init_db, save_record
    from storage import history as recent_history

# 建表（必要时从旧的 history.json 迁一次数据）。模块导入时跑一次，保证第一个请求
# 进来前库已经就绪
init_db()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    # next dev 平时在 3000，端口被占时会自动退到 3001；localhost 和 127.0.0.1
    # 在浏览器眼里是两个不同的源，都得放行，否则 fetch 直接被跨源拦掉
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

profile = {
    "heroTitle": "关于我",
    "heroSubtitle": "项目，创意，灵感，心得，我的作品",
    "featuredWork": {
        "kicker": "作品",
        "title": "文字实验室",
        "copy": "拼音和情绪，挖掘中文里的细节",
        "linkLabel": "打开作品",
    },
    "identity": {
        "motto": "已识乾坤大，尤怜草木青",
        "learning": "零到全栈",
    },
}


class AnalyzeRequest(BaseModel):
    text: str


@app.get("/api/profile")
def get_profile():
    return profile


def score_label(score):
    if score >= 0.6:
        return "偏积极"
    elif score <= 0.4:
        return "偏消极"
    else:
        return "中性"


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    # 校验放在这里、用 HTTPException 抛，而不是用 Field(min_length=...)：前端的
    # InputCard 读的是 body.detail，pydantic 的 422 会把 detail 给成数组，界面就成 [object Object] 了
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="文本不能为空")
    if len(text) > MAX_TEXT_LENGTH:
        raise HTTPException(status_code=400, detail=f"文本最多 {MAX_TEXT_LENGTH} 字")

    # 空字符串会让 SnowNLP 除零崩溃，所以上面必须先拦住
    score = SnowNLP(text).sentiments
    result = {
        "text": text,
        "score": round(score, 2),
        # 用没舍入的原始分判档，否则 0.595 会被 round 成 0.6 而判成"偏积极"
        "label": score_label(score),
        "pinyin": " ".join(lazy_pinyin(text, style=Style.TONE)),
        # 存本地时间、不带时区尾巴（不写 +00:00）；local time 对看日志/记录更方便
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    save_record(result)
    return result


@app.get("/api/history")
def history():
    # 路由函数和 storage 里的 history() 同名，所以导入时起个别名，各管各的
    return recent_history(10)
