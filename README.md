# AI辩论器

一个小玩具项目：正方与反方各用独立大模型进行 4 轮激辩，最后由裁判模型输出《思辨终审报告》。克隆下来就能玩，**无需自行配置 API Key**（已内置，仅供好友试用）。

> API Key 会在一段时间后作废，届时项目将无法继续调用模型。

## 功能

- 正反方、裁判三端独立模型配置
- SSE 流式输出，打字机效果实时展示
- 每轮发言携带完整辩论上下文，确保真正交锋
- 裁决报告分章节卡片展示

## 项目结构

```
Debeater/
├── debate_core.py      # 辩论核心逻辑与 Prompt
├── server.py           # FastAPI 后端
├── frontend/           # 前端页面
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   └── assets/         # 背景图等资源
└── requirements.txt
```

## 快速开始

### 1. 安装依赖

```powershell
cd Debeater
python -m pip install -r requirements.txt
```

> Windows 若提示找不到 `pip`，请用 `python -m pip` 代替 `pip`。

### 2. 启动服务

```powershell
python -m uvicorn server:app --reload --port 8000
```

浏览器访问：**http://localhost:8000**

若 8000 端口被占用，可换端口：

```powershell
python -m uvicorn server:app --reload --port 8080
```

## API 接口

| 接口 | 说明 |
|------|------|
| `GET /api/models` | 获取可选模型列表 |
| `GET /api/debate/stream?topic=...&pro_model=...&con_model=...` | SSE 流式辩论 |

## 常见问题

**端口报错 `WinError 10013`**：端口已被占用，换一个端口或结束占用进程：

```powershell
netstat -ano | findstr ":8000"
taskkill /PID <进程号> /F
```

**模型列表**：在 `debate_core.py` 的 `MODEL_OPTIONS` 中增删。
