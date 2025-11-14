# Backend API - ?꾩쟾 ?먮룞??

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Claude](https://img.shields.io/badge/Claude-3.5%20Sonnet-orange.svg)](https://www.anthropic.com/)

?꾨줎?몄뿏???먯뿰???낅젰??Claude API濡??먮룞 蹂?섑븯??MCP Core???꾨떖?섎뒗 ?꾩쟾 ?먮룞??Backend API

## ?뱥 紐⑹감

- [媛쒖슂](#媛쒖슂)
- [?꾪궎?띿쿂](#?꾪궎?띿쿂)
- [?ㅼ튂](#?ㅼ튂)
- [?ъ슜踰?(#?ъ슜踰?
- [API 臾몄꽌](#api-臾몄꽌)
- [?덉젣](#?덉젣)
- [?몃윭釉붿뒋??(#?몃윭釉붿뒋??

## 媛쒖슂

### 二쇱슂 湲곕뒫

- ?쨼 **Claude AI ?듯빀**: ?먯뿰?대? CPU/Memory/Users濡??먮룞 蹂??
- ?봽 **?꾩쟾 ?먮룞??*: GitHub URL + ?먯뿰???낅젰留뚯쑝濡??덉륫 ?섑뻾
- ?뱤 **LSTM ?덉륫**: MCP Core? ?곕룞?섏뿬 由ъ냼???덉륫
- ?슚 **?댁긽 ?먯?**: ?먮룞 ?댁긽 ?먯? 諛?Discord ?뚮┝
- ?뙋 **CORS 吏??*: 紐⑤뱺 ?ㅻ━吏꾩뿉???묎렐 媛??

### 泥섎━ ?먮쫫

```
?꾨줎?몄뿏??
  ??
  ?쒋? GitHub URL: https://github.com/owner/repo
  ?붴? ?먯뿰?? "?쇳겕??꾩뿉 1000紐??뺣룄 ?ъ슜??寃?媛숈븘??
  ??
Backend API (???쒕쾭)
  ??
  ?쒋? 1. GitHub API ????μ냼 硫뷀??곗씠???섏쭛
  ?쒋? 2. Claude API ??CPU/Memory/Users 異붿텧
  ?쒋? 3. MCPContext ?앹꽦
  ?붴? 4. MCP Core /plans ?몄텧
  ??
MCP Core
  ??
  ?쒋? LSTM/Baseline ?덉륫
  ?쒋? Flavor 沅뚯옣
  ?쒋? ?댁긽 ?먯?
  ?붴? Discord ?뚮┝ (?댁긽 諛쒓껄 ??
  ??
Backend API ???꾨줎?몄뿏?쒕줈 寃곌낵 諛섑솚
```

## ?꾪궎?띿쿂

```
?뚢???????????????????
??  Frontend      ??
?? (React/Vue)    ??
?붴?????????р??????????
         ??POST /api/predict
         ??{github_url, user_input}
         ??
?뚢???????????????????
?? Backend API    ?? ?????쒕쾭
??  (FastAPI)     ??
?쒋???????????????????
??- GitHub API    ?? ??μ냼 ?뺣낫 ?섏쭛
??- Claude API    ?? ?먯뿰????JSON
??- MCP Core API  ?? ?덉륫 ?붿껌
?붴?????????р??????????
         ??POST /plans
         ??{context, metric_name}
         ??
?뚢???????????????????
??  MCP Core      ??
?? (LSTM Model)   ??
?쒋???????????????????
??- LSTM ?덉륫     ??
??- ?댁긽 ?먯?     ??
??- Discord ?뚮┝  ??
### ?쒕굹由ъ삤 2: 媛쒕컻 ?섍꼍 ?뚭퇋紐?

**?낅젰:**
```json
{
  "github_url": "https://github.com/nodejs/node",
  "user_input": "媛쒕컻 ?섍꼍?먯꽌 ?뚯뒪?? 50紐??뺣룄硫???寃?媛숈븘??
}
```

**Claude媛 ?먮룞 異붿텧:**
```json
{
  "service_type": "web",
  "expected_users": 50,
  "time_slot": "normal",
  "runtime_env": "dev",
  "curr_cpu": 1.0,
  "curr_mem": 2048.0,
  "reasoning": "媛쒕컻?섍꼍 50紐???1 CPU, 2GB 異⑸텇"
}
```

### ?쒕굹由ъ삤 3: 二쇰쭚 ?몃옒??

**?낅젰:**
```json
{
  "github_url": "https://github.com/django/django",
  "user_input": "二쇰쭚?먮뒗 1000紐??뺣룄 ?덉긽?⑸땲??
}
```

**Claude媛 ?먮룞 異붿텧:**
```json
{
  "service_type": "web",
  "expected_users": 1000,
  "time_slot": "weekend",
  "runtime_env": "prod",
  "curr_cpu": 2.0,
  "curr_mem": 4096.0,
  "reasoning": "二쇰쭚 1000紐???2 CPU, 4GB"
}
```

## ?몃윭釉붿뒋??

### Claude API ?ㅺ? ?놁쓣 ??

**利앹긽:**
```json
{
  "extracted_context": {
    "reasoning": "Claude API key not set"
  }
}
```

**?닿껐:**
1. `.env` ?뚯씪??`ANTHROPIC_API_KEY` ?ㅼ젙
2. [Anthropic Console](https://console.anthropic.com/)?먯꽌 ??諛쒓툒
3. ?쒕쾭 ?ъ떆??

### MCP Core ?곌껐 ?ㅽ뙣

**利앹긽:**
```json
{
  "detail": "MCP Core error: 500"
}
```

**?닿껐:**
1. MCP Core ?쒕쾭 ?ㅽ뻾 ?뺤씤:
   ```bash
   curl http://localhost:8000/health
   ```
2. `.env`?먯꽌 `MCP_CORE_URL` ?뺤씤
3. MCP Core 濡쒓렇 ?뺤씤

### GitHub API Rate Limit

**利앹긽:**
```json
{
  "detail": "GitHub API error: 403"
}
```

**?닿껐:**
1. `.env`??`GITHUB_TOKEN` ?ㅼ젙
2. [GitHub Settings ??Developer settings ??Personal access tokens](https://github.com/settings/tokens)?먯꽌 ?좏겙 ?앹꽦
3. 沅뚰븳: `public_repo` (怨듦컻 ??μ냼留??묎렐 ??

### CORS ?먮윭

**利앹긽 (釉뚮씪?곗? 肄섏넄):**
```
Access to fetch at 'http://localhost:8001/api/predict' from origin 'http://localhost:3000' 
has been blocked by CORS policy
```

**?닿껐:**
- ???쒕쾭???대? 紐⑤뱺 ?ㅻ━吏??덉슜 (`allow_origins=["*"]`)
- 釉뚮씪?곗? 罹먯떆 ??젣 ???ъ떆??

### Python ?⑦궎吏 ?놁쓬

**利앹긽:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**?닿껐:**
```bash
pip install -r requirements.txt
```

## ?섍꼍蹂???곸꽭

| 蹂??| ?꾩닔 | 湲곕낯媛?| ?ㅻ챸 |
|------|------|--------|------|
| `ANTHROPIC_API_KEY` | ??| - | Claude API ??|
| `MCP_CORE_URL` | ??| `http://localhost:8000` | MCP Core ?쒕쾭 二쇱냼 |
| `GITHUB_TOKEN` | ??| - | GitHub API ?좏겙 (Rate Limit ?꾪솕) |
| `BACKEND_PORT` | ??| `8001` | Backend API ?ы듃 |

## ?깅뒫 理쒖쟻??

### Rate Limiting

GitHub API Rate Limit:
- **?몄쬆 ?놁쓬**: 60???쒓컙
- **?몄쬆 ?덉쓬**: 5000???쒓컙

??`GITHUB_TOKEN` ?ㅼ젙 沅뚯옣

### Timeout ?ㅼ젙

```python
# GitHub API: 10珥?
# Claude API: 30珥?
# MCP Core: 30珥?
```

### 罹먯떛

?꾩옱 罹먯떛 誘멸뎄?? 異뷀썑 Redis 異붽? ?덉젙.

## ?쇱씠?쇱뒪

MIT License

## 湲곗뿬

Pull Request ?섏쁺?⑸땲??

## 臾몄쓽

?댁뒋: [GitHub Issues](https://github.com/your-repo/issues)

---

**Made with ?ㅿ툘 by MCP Team**

## ?ㅼ튂

## ?ㅼ튂

### 1. ?섍꼍蹂???ㅼ젙

`.env` ?뚯씪 ?앹꽦:

```bash
# ?꾩닔: Claude API ??
ANTHROPIC_API_KEY=sk-ant-api03-...

# ?좏깮: MCP Core ?쒕쾭 二쇱냼 (湲곕낯: http://localhost:8000)
MCP_CORE_URL=http://localhost:8000

# ?좏깮: GitHub API ?좏겙 (Rate Limit ?꾪솕??
GITHUB_TOKEN=ghp_...

# ?좏깮: Backend API ?ы듃 (湲곕낯: 8001)
BACKEND_PORT=8001
```

**Claude API ??諛쒓툒:**
1. [Anthropic Console](https://console.anthropic.com/) ?묒냽
2. API Keys ??Create Key
3. `.env` ?뚯씪??`ANTHROPIC_API_KEY` ?ㅼ젙

### 2. ?⑦궎吏 ?ㅼ튂

```bash
cd backend_api
pip install -r requirements.txt
```

**?꾩슂???⑦궎吏:**
- `fastapi`: Web ?꾨젅?꾩썙??
- `uvicorn`: ASGI ?쒕쾭
- `httpx`: 鍮꾨룞湲?HTTP ?대씪?댁뼵??
- `anthropic`: Claude API ?대씪?댁뼵??
- `pydantic`: ?곗씠??寃利?
- `python-dotenv`: ?섍꼍蹂??濡쒕뱶

### 3. ?쒕쾭 ?쒖옉

**諛⑸쾿 1: 吏곸젒 ?ㅽ뻾**
```bash
python main.py
```

**諛⑸쾿 2: uvicorn ?ъ슜**
```bash
uvicorn main:app --reload --port 8001
```

**?깃났 ??異쒕젰:**
```
?? Backend API: http://localhost:8001
?쨼 Claude: enabled
?뱻 MCP Core: http://localhost:8000
?뵎 GitHub Token: configured

?뮕 Tip: Set ANTHROPIC_API_KEY in .env file
INFO:     Uvicorn running on http://0.0.0.0:8001
```

## ?ъ슜踰?

### ?꾨줎?몄뿏?쒖뿉???몄텧

#### JavaScript (Fetch API)

```javascript
async function predictResources() {
  const response = await fetch('http://localhost:8001/api/predict', {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      github_url: 'https://github.com/fastapi/fastapi',
      user_input: '?쇳겕??꾩뿉 5000紐??덉긽?⑸땲?? CPU??留롮씠 ?꾩슂??寃?媛숈븘??'
    })
  });
  
  const result = await response.json();
  console.log(result);
}
```

#### React Example

```jsx
import { useState } from 'react';

function PredictForm() {
  const [githubUrl, setGithubUrl] = useState('');
  const [userInput, setUserInput] = useState('');
  const [result, setResult] = useState(null);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const response = await fetch('http://localhost:8001/api/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        github_url: githubUrl,
        user_input: userInput
      })
    });
    
    const data = await response.json();
    setResult(data);
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <input 
        value={githubUrl}
        onChange={(e) => setGithubUrl(e.target.value)}
        placeholder="GitHub URL"
      />
      <textarea
        value={userInput}
        onChange={(e) => setUserInput(e.target.value)}
        placeholder="?먯뿰???낅젰 (?? ?쇳겕??꾩뿉 1000紐??ъ슜)"
      />
      <button type="submit">?덉륫</button>
      
      {result && <pre>{JSON.stringify(result, null, 2)}</pre>}
    </form>
  );
}
```

#### Python Example

```python
import requests

response = requests.post('http://localhost:8001/api/predict', json={
    'github_url': 'https://github.com/fastapi/fastapi',
    'user_input': '?쇳겕??꾩뿉 5000紐??뺣룄 ?ъ슜??寃?媛숈뒿?덈떎.'
})

print(response.json())
```

### cURL Example

```bash
curl -X POST http://localhost:8001/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "github_url": "https://github.com/fastapi/fastapi",
    "user_input": "?쇳겕??꾩뿉 5000紐??덉긽?⑸땲??"
  }'
```

## API 臾몄꽌

### POST /api/predict

?꾩쟾 ?먮룞???덉륫 ?붾뱶?ъ씤??

#### Request Body

```json
{
  "github_url": "string",    // GitHub ??μ냼 URL (?꾩닔)
  "user_input": "string"     // ?먯뿰???붿껌?ы빆 (?꾩닔)
}
```

**?먯뿰???낅젰 ?덉떆:**
- "?쇳겕??꾩뿉 1000紐??뺣룄 ?ъ슜??寃?媛숈븘??
- "二쇰쭚??100紐? CPU 2媛쒕㈃ ??寃?媛숈뒿?덈떎"
- "媛쒕컻 ?섍꼍?먯꽌 ?뚯뒪?? 50紐??뺣룄"
- "?꾨줈?뺤뀡, 5000紐??댁긽 ?덉긽"

#### Response

```json
{
  "success": true,
  "github_info": {
    "full_name": "owner/repo",
    "description": "??μ냼 ?ㅻ챸",
    "language": "Python",
    "stars": 1234,
    "forks": 567
  },
  "extracted_context": {
    "service_type": "web",
    "expected_users": 5000,
    "time_slot": "peak",
    "curr_cpu": 4.0,
    "curr_mem": 8192.0,
    "reasoning": "5000紐??ъ슜????4 CPU, 8192 MB 沅뚯옣"
  },
  "predictions": {
    "lstm": {
      "cpu": 4.2,
      "memory": 8500.0
    },
    "baseline": {
      "cpu": 4.0,
      "memory": 8192.0
    }
  },
  "recommendations": {
    "flavor": "m5.xlarge",
    "cost_per_day": 4.32,
    "notes": "LSTM 紐⑤뜽 湲곕컲 沅뚯옣"
  }
}
```

#### Error Response

```json
{
  "detail": "GitHub API error: 404"
}
```

### GET /health

?쒕쾭 ?ъ뒪 泥댄겕

#### Response

```json
{
  "status": "healthy",
  "claude_api": "enabled"
}
```

## ?덉젣

### ?쒕굹由ъ삤 1: ?쇳겕???????ъ슜??

**?낅젰:**
```json
{
  "github_url": "https://github.com/facebook/react",
  "user_input": "?쇳겕??꾩뿉 10000紐??댁긽 ?덉긽?⑸땲?? ?몃옒?쎌씠 留롮쓣 寃?媛숈븘??"
}
```

**Claude媛 ?먮룞 異붿텧:**
```json
{
  "service_type": "web",
  "expected_users": 10000,
  "time_slot": "peak",
  "runtime_env": "prod",
  "curr_cpu": 8.0,
  "curr_mem": 16384.0,
  "reasoning": "10000紐? ??8 CPU, 16GB 沅뚯옣"
}
```

### ?쒕굹由ъ삤 2: 媛쒕컻 ?섍꼍 ?뚭퇋紐?

**?낅젰:**

```json
{
  "success": true,
  "github_info": {
    "full_name": "fastapi/fastapi",
    "language": "Python",
    "stars": 78000
  },
  "extracted_context": {
    "service_type": "api",
    "expected_users": 5000,
    "time_slot": "peak",
    "curr_cpu": 4.0,
    "curr_mem": 8192.0,
    "reasoning": "紐낆떆???ъ슜???섏? ?쇳겕???吏??
  },
  "predictions": {
    "predictions": [...]
  },
  "recommendations": {
    "flavor": "medium",
    "cost_per_day": 2.8
  }
}
```

## ?숈옉 ?먮━

1. **GitHub 遺꾩꽍**: GitHub API濡???μ냼 硫뷀??곗씠??
2. **Claude ?뚯떛**: ?먯뿰????CPU/Memory/Users ?먮룞 異붿텧
3. **MCPContext ?앹꽦**: /plans ?뺤떇?쇰줈 蹂??
4. **MCP Core ?몄텧**: LSTM ?덉륫, Flavor 異붿쿇, ?댁긽 ?먯?
5. **寃곌낵 諛섑솚**: ?꾨줎?몄뿏?쒖뿉 JSON ?묐떟

---

**?ы듃**: 8001  
**臾몄꽌**: http://localhost:8001/docs

