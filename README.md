# Agent Team (Doomsage Crew)

Tere PC pe chalne wala chhota multi-agent system. 4 agents ek shared folder ke through aapas me baat karte hain aur website ya browser-game banate hain:

| Agent | Kya karta hai | Kahan chalta hai |
|---|---|---|
| PLANNER | Goal ko plan + tasks me todta hai (`plan.md`, `tasks.md`) | Groq (cloud, free) |
| CODER | Poora code likhta hai (`workspace/project/`) | Groq (cloud, free) |
| TESTER | Asli checks: files hain? HTML sahi? Server pe khulti hai? | Tere PC pe (no AI) |
| MEMORY | Har run ke baad `notes.md` khud update karta hai | Ollama (tere PC, free) |

Agents ki baat-cheet `workspace/messages.md` me dikhti hai. Agar tester FAIL kare, coder khud fix karta hai (2 round tak). Baad me REVIEWER agent bhi on kar sakta hai (`config.json` me `agents_enabled` me `"reviewer"` add kar).

---

## Setup (sirf ek baar, 10-15 min)

### 1. Python check karo
PowerShell kholo (Start me type: `powershell`) aur likho:
```
python --version
```
- Kuch `Python 3.11` jaisa aaya to theek hai.
- Error aaya to python.org se install karo. **Install karte time "Add Python to PATH" wala box TICK karna** (ye sabse important hai).

### 2. Ollama install karo (local AI ke liye)
1. https://ollama.com/download/windows se installer download karke chalao.
2. Install hone ke baad PowerShell me:
```
ollama pull qwen2.5:3b
```
(2 GB download, ek baar lagega. Ye chhota model teri RTX 3050 pe aaram se chalega.)
3. Optional, powerful local coding model (4.7 GB):
```
ollama pull qwen2.5-coder:7b
```

### 3. Groq ki free API key banao
1. https://console.groq.com kholo aur **GitHub se sign up** karo (free, card nahi maangta).
2. https://console.groq.com/keys pe jao → **Create API Key** → copy kar lo (sirf ek baar dikhti hai).

### 4. Kit set karo
PowerShell me (Downloads me zip kholi hai to):
```
cd C:\Users\kunal\Downloads\agent-team
pip install -r requirements.txt
copy .env.example .env
notepad .env
```
Notepad me `gsk_yaha_apni_key_paste_karo` ki jagah apni Groq key paste karo, save karke band kar do. **Ye key sirf tere PC pe rehti hai, kisi ko mat bhejna.**

### 5. Check karo sab sahi hai
```
python run.py --check
```
Sab OK aaya to done. Jo missing bole, wahi step dobara karo.

---

## Chalana

```
python run.py "ek gym ke liye premium dark website banao"
python run.py "snake game banao jo phone touch se chale"
python run.py "dental clinic ki landing page, appointment section ke saath"
```

Output `workspace\project\` me milta hai. Browser me dekhne ke liye:
```
cd workspace\project
python -m http.server 8000
```
Fir browser me kholo: http://localhost:8000

- `workspace\plan.md` - planner ka plan
- `workspace\tasks.md` - task list + tester ki failures
- `workspace\messages.md` - agents ki aapas ki baat-cheet
- `workspace\notes.md` - memory agent ke notes (kabhi delete mat karna)

## Settings (`config.json`)

- `agents_enabled` me `"reviewer"` add karo to 5th agent (local) code review karega.
- `"coder"` ka model `"ollama"` + `"qwen2.5-coder:7b"` kar doge to coder bhi fully local/offline chalega (slow par free, unlimited).
- Groq free limit: har model ~30 requests/min, 1000 requests/din. Limit lage to kit khud ruk ke retry karti hai.

## Important

- Kit sirf apne `workspace\` folder ke andar likhti hai. Teri koi aur file touch nahi hoti.
- Agar error aaye to poora error copy karke Instinct ko bhej dena, samjha dega.

## Sources (version cheezon ke liye)

- Groq models + free limits: https://console.groq.com/docs/models aur https://console.groq.com/docs/rate-limits
- Ollama models: https://ollama.com/library/qwen2.5-coder aur https://ollama.com/library/qwen2.5
- Ye kit model IDs `openai/gpt-oss-120b` (Groq) aur `qwen2.5:3b` (Ollama) pe test hui hai (Oct 2026). Model kabhi deprecate ho to `python run.py --check` bata dega.
