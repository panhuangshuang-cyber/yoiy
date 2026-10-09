"use client";

// 文字实验室的"输入区"卡片。这一节给"开始分析"接上了后端：
// 点按钮就把输入的文字 POST 给 /api/analyze，拿到结果通过 onResult 交给父组件。
// 请求出问题时用 try/catch 接住，在按钮上方给一行提示，不让界面无声失效。
// 后端地址收在 .env.local 的 NEXT_PUBLIC_API_BASE_URL 里，改完要重启 next dev 才生效。
import { useState } from "react";
const API = process.env.NEXT_PUBLIC_API_BASE_URL;

// 和后端 backend/main.py 的 MAX_TEXT_LENGTH 保持一致：这里拦一道，
// 用户就不会先打完字再被后端退回来
const MAX_TEXT_LENGTH = 1000;

export default function InputCard({ onResult }) {
  const [text, setText] = useState(
    "今天的风很轻，适合把脑海里的想法慢慢写下来。",
  );
  const [error, setError] = useState("");

  async function handleAnalyze() {
    setError("");

    try {
      const res = await fetch(`${API}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ text }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        // 正常错误后端给的 detail 是字符串（如"文本不能为空"）；但如果撞上
        // FastAPI 的 422，detail 是数组，直接塞进 Error 会显示成 [object Object]
        const detail = Array.isArray(body.detail)
          ? body.detail.map((d) => d.msg).join("；")
          : body.detail;
        throw new Error(detail || `分析失败：${res.status}`);
      }

      onResult(await res.json());
    } catch (error) {
      setError(error.message);
    }
  }

  return (
    <article className="panel panel-half lab-panel card">
      <div className="panel-heading">
        <p className="section-kicker">输入区</p>
        <h3>贴一段中文</h3>
      </div>
      <form className="lab-form" onSubmit={(e) => e.preventDefault()}>
        <label htmlFor="text-input">文本内容</label>
        <textarea
          id="text-input"
          rows="8"
          maxLength={MAX_TEXT_LENGTH}
          placeholder="例如：生活没有标准答案，但每一天都值得认真感受。"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        {/* state 现身：text 一变，这行数字自动跟着变 */}
        <p className="lab-count">已输入 {text.length} 字</p>
        {error && <p className="lab-error">{error}</p>}
        <button
          className="primary-button"
          type="button"
          onClick={handleAnalyze}
        >
          开始分析
        </button>
      </form>
    </article>
  );
}
