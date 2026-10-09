import os
import uuid
from datetime import datetime

from dotenv import load_dotenv
from fastapi import Cookie, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypinyin import Style, lazy_pinyin
from snownlp import SnowNLP

load_dotenv()
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS").split(",")



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
    # 跨域来源从环境变量 ALLOWED_ORIGINS 读取
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    allow_credentials=True,
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


SESSION_COOKIE_NAME = "session_id"
SESSION_COOKIE_MAX_AGE = 30 * 86400  # 30 天持久化


def get_or_create_session_id(response: Response, session_id: str | None = None) -> str:
    if not session_id:
        session_id = uuid.uuid4().hex
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            max_age=SESSION_COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
        )
    return session_id


@app.post("/api/analyze")
def analyze(
    req: AnalyzeRequest,
    response: Response,
    session_id: str | None = Cookie(default=None),
):
    # 校验放在这里、用 HTTPException 抛，而不是用 Field(min_length=...)：前端的
    # InputCard 读的是 body.detail，pydantic 的 422 会把 detail 给成数组，界面就成 [object Object] 了
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="文本不能为空")
    if len(text) > MAX_TEXT_LENGTH:
        raise HTTPException(status_code=400, detail=f"文本最多 {MAX_TEXT_LENGTH} 字")

    sid = get_or_create_session_id(response, session_id)

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
    save_record(result, session_id=sid)
    return result


@app.get("/api/history")
def history(
    response: Response,
    session_id: str | None = Cookie(default=None),
):
    # 路由函数和 storage 里的 history() 同名，所以导入时起个别名，各管各的
    if not session_id:
        sid = get_or_create_session_id(response, session_id)
        return recent_history(10, session_id=sid)
    return recent_history(10, session_id=session_id)
