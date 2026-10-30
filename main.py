import os, re, ast, time, json, socket, random, shutil, operator, subprocess, threading, warnings
from datetime import datetime
import requests
from urllib.parse import urlparse
from flask import Flask, request, Response, jsonify
from duckduckgo_search import DDGS
warnings.filterwarnings("ignore", category=RuntimeWarning)

try:
    import g4f
    G4F_OK = True
except Exception:
    G4F_OK = False

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = "huihui_ai/qwen3-abliterated:4b"
MODEL_CATALOG = [
    # Community / abliterated builds already supported by this application
    "huihui_ai/qwen3-abliterated:4b",
    "richardyoung/qwen2.5-7b-instruct-abliterated:latest",
    "huihui_ai/qwen3-abliterated:0.6b",
    "huihui_ai/qwen3-abliterated:1.7b",
    "huihui_ai/qwen3-abliterated:14b",
    "huihui_ai/qwen3-abliterated:16b-a3b",
    "huihui_ai/deepseek-r1-abliterated:14b",
    "huihui_ai/mistral-small-abliterated:24b",

    # Qwen general, coding and reasoning families
    "qwen3.6:27b",
    "qwen3.6:27b-coding",
    "qwen3.5:0.8b", "qwen3.5:2b", "qwen3.5:4b", "qwen3.5:9b", "qwen3.5:27b",
    "qwen3:0.6b", "qwen3:1.7b", "qwen3:4b", "qwen3:8b", "qwen3:14b", "qwen3:30b", "qwen3:32b",
    "qwen3-coder:30b",
    "qwen2.5:0.5b", "qwen2.5:1.5b", "qwen2.5:3b", "qwen2.5:7b", "qwen2.5:14b", "qwen2.5:32b",
    "qwen2.5-coder:0.5b", "qwen2.5-coder:1.5b", "qwen2.5-coder:3b", "qwen2.5-coder:7b", "qwen2.5-coder:14b", "qwen2.5-coder:32b",

    # Google Gemma and on-device variants
    "gemma3:270m", "gemma3:1b", "gemma3:4b", "gemma3:12b", "gemma3:27b",
    "gemma2:2b", "gemma2:9b", "gemma2:27b",
    "gemma3n:e2b", "gemma3n:e4b",

    # Llama and vision-language variants
    "llama3.2:1b", "llama3.2:3b", "llama3.1:8b", "llama3:8b",
    "llama3.2-vision:11b", "llama2:7b",

    # Microsoft Phi families
    "phi4:14b", "phi4-mini:3.8b", "phi4-reasoning:14b", "phi4-mini-reasoning:3.8b",
    "phi3:3.8b", "phi3:14b", "phi3.5:3.8b",

    # DeepSeek reasoning and code models (dense tags up to 32B)
    "deepseek-r1:1.5b", "deepseek-r1:7b", "deepseek-r1:8b", "deepseek-r1:14b", "deepseek-r1:32b",
    "deepseek-coder:1.3b", "deepseek-coder:6.7b",

    # Mistral-family general, coding and multimodal models
    "mistral:7b", "mistral-nemo:12b", "mistral-small:24b", "mistral-small3.1:24b", "mistral-small3.2:24b",
    "codestral:22b", "devstral-small:24b", "magistral-small:24b",
    "ministral-3:3b", "ministral-3:8b", "ministral-3:14b",

    # OpenAI open-weight reasoning model and Meta's compact agent model
    "gpt-oss:20b", "muse-glimmer:30b",

    # IBM Granite language, code and guard models
    "granite3.3:2b", "granite3.3:8b", "granite3.2:2b", "granite3.2:8b",
    "granite3.1-moe:1b", "granite3.1-moe:3b", "granite-code:3b", "granite-code:8b", "granite-code:20b",
    "granite3-guardian:2b", "granite3-guardian:8b",

    # Allen AI OLMo, code-focused families and efficient general models
    "olmo2:7b", "olmo2:13b", "olmo-3.1:32b-instruct", "olmo-3.1:32b-think",
    "starcoder2:3b", "starcoder2:7b", "starcoder2:15b",
    "codegemma:2b", "codegemma:7b", "codellama:7b", "codellama:13b",
    "falcon3:1b", "falcon3:3b", "falcon3:7b", "falcon3:10b",
    "exaone-deep:2.4b", "exaone-deep:7.8b", "exaone-deep:32b",

    # Translation and medical-oriented Gemma variants
    "translategemma:4b", "translategemma:12b", "translategemma:27b",
    "medgemma:4b", "medgemma:27b",
]
LANG_NAMES = {"ru":"русском","en":"английском","de":"немецком","fr":"французском","es":"испанском","zh":"китайском","ja":"японском"}
LAYOUT = {'q':'й','w':'ц','e':'у','r':'к','t':'е','y':'н','u':'г','i':'ш','o':'щ','p':'з','[':'х',']':'ъ',
    'a':'ф','s':'ы','d':'в','f':'а','g':'п','h':'р','j':'о','k':'л','l':'д',';':'ж',"'":'э',
    'z':'я','x':'ч','c':'с','v':'м','b':'и','n':'т','m':'ь',',':'б','.':'ю','/':'.','`':'ё'}
SEARCH_KW = ["новост","сегодня","сейчас","последн","курс","цена","погода","кто такой","2024","2025","2026","release","today"]

SYS = "Ты — полезный помощник. Отвечай по делу."
THINK_INSTR = "\n\nРазмышление: обдумай задачу, разбей на части, проверь логику. Потом финальный ответ."
THINK_ART = ("\n\nКРИТИЧЕСКОЕ: ответ начинается РОВНО с `[THINK]`. Первые 7 символов — `[THINK]`. "
    "Внутри: разбери задачу, рассмотри подходы, выбери лучший. 5-15 предложений. "
    "Потом `[/THINK]` и сразу финальный ответ.")
TOOLS_INSTR = "\n\nИнструменты: [TIME], [CALC]выражение[/CALC], [TIMER_START/NOW/STOP]. Тег в начале ответа."

FORMATS = """\n\nФОРМАТЫ ВЫВОДА. Теги пиши точно.

◆ Таблица:
| A | B |
|---|---|
| x | y |

◆ Код: ```язык ... ```

◆ График: [CHART:bar]\nМетка: 45\n[/CHART] (bar/line/pie/scatter)

◆ Функция 2D: [GRAPH2D]\nf(x)=x^2\nrange: -5..5\n[/GRAPH2D]

◆ Функция 3D: [GRAPH3D]\nf(x,y)=sin(x)*cos(y)\nrange: -3..3\n[/GRAPH3D]

◆ Граф связей: [GRAPH_NET]\nA -> B : метка\n[/GRAPH_NET]

◆ Иерархия: [TREE]\nКорень\n  Ветка\n[/TREE]

◆ Mindmap: [MINDMAP:Центр]\nВетка 1\n  Подтема\n[/MINDMAP]

◆ Kanban: [KANBAN]\n@Колонка\n- Задача\n[/KANBAN]

◆ Timeline: [TIMELINE]\n2020 : событие\n[/TIMELINE]

◆ Процесс: [PROCESS]\nШаг 1\n→ Шаг 2\n[/PROCESS]

◆ Метрики: [METRICS]\nИмя: 12.4K : +18%\n[/METRICS]

◆ Чек-лист: [CHECKLIST]\n[x] Сделано\n[ ] Нет\n[/CHECKLIST]

◆ Файлы: [FILE_TREE]\nsrc/\n  main.py\n[/FILE_TREE]

◆ Матрица: [MATRIX]\n1 2 3\n4 5 6\n[/MATRIX]

◆ Callout: [CALLOUT:info]\nТекст\n[/CALLOUT]

◆ Цитата: [QUOTE]\nТекст\nАвтор\n[/QUOTE]

◆ Формула: [MATH]\nE = m*c^2\nfrac(a,b)\n[/MATH]

◆ 2D фигура: [SHAPE2D]\ntype: hexagon\nsize: 100\n[/SHAPE2D]

◆ 2D произвольная: [POLY2D]\nname: имя\npoints:\n0,-100\n86,-50\n86,50\n0,100\n[/POLY2D]

◆ 3D фигура: [SHAPE3D]\ntype: cube\nsize: 100\n[/SHAPE3D]

◆ 3D произвольная: [MESH3D]\nname: имя\nscale: 100\nvertices:\n0,1,0\n1,0,0\n0,-1,0\n-1,0,0\n0,0,1\n0,0,-1\nfaces:\n0,1,4\n1,2,4\n2,3,4\n3,0,4\n0,1,5\n1,2,5\n2,3,5\n3,0,5\n[/MESH3D]

◆ Аэродинамика: [AERO]\nshape: airfoil\nspeed: 1\nangle: 5\nobjects: airfoil,sphere\n[/AERO]

◆ Шахматы: [CHESS]

◆ Разметка: **жирный** *курсив* __подчёркнутый__ ~~зачёркнутый~~ ==выделение== ^верх^ ~низ~ `код` > цитата"""

OPS = {ast.Add:operator.add, ast.Sub:operator.sub, ast.Mult:operator.mul,
    ast.Div:operator.truediv, ast.Pow:operator.pow, ast.Mod:operator.mod,
    ast.FloorDiv:operator.floordiv, ast.USub:operator.neg, ast.UAdd:operator.pos}
TIMERS = {}; TIMER_LOCK = threading.Lock(); TIMEOUT = 900
OV_PIPELINES = {}
OV_PIPELINE_LOCK = threading.Lock()

QUANTIZATION_TAGS = {
    "Q2_K": "q2_K", "Q3_K_M": "q3_K_M", "Q4_K_M": "q4_K_M",
    "Q5_K_M": "q5_K_M", "Q8_0": "q8_0", "F16": "fp16"
}

def quantized_model_name(model, quantization):
    """Return a real Ollama registry tag for model families with known tags.

    Ollama does not requantize an installed model when an option changes. For
    unknown/custom model families return None rather than implying that it did.
    """
    model = (model or "").strip()
    q = (quantization or "auto").strip().upper()
    if q == "AUTO":
        return model
    tag = QUANTIZATION_TAGS.get(q)
    if not tag:
        raise ValueError("Неизвестная квантизация: " + q)
    ml = model.lower()
    if ml.startswith("mixtral:") and ("8x7b" in ml or ml in ("mixtral:latest", "mixtral:instruct", "mixtral:text")):
        return "mixtral:8x7b-instruct-v0.1-" + tag
    if ml.startswith("qwen2.5:") and ("32b" in ml or ml == "qwen2.5:latest"):
        return "qwen2.5:32b-instruct-" + tag
    # If a custom/local model already reports the exact requested level, it is
    # usable as-is; otherwise the server must not pretend to transform it.
    actual = get_model_quantization(model)
    if actual and (actual.upper() == q or (q == "F16" and actual.upper() in ("F16", "FP16"))):
        return model
    return None


def get_model_quantization(model):
    try:
        for item in ollama_tags():
            if (item.get("name") or item.get("model")) == model:
                return (item.get("details") or {}).get("quantization_level") or ""
    except Exception:
        pass
    return ""


def system_memory():
    """Best-effort host/container memory counters, in bytes."""
    total = available = 0
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            values = {}
            for line in f:
                k, _, rest = line.partition(":")
                if k in ("MemTotal", "MemAvailable"):
                    values[k] = int(rest.strip().split()[0]) * 1024
            total = values.get("MemTotal", 0)
            available = values.get("MemAvailable", 0)
    except Exception:
        try:
            page = os.sysconf("SC_PAGE_SIZE")
            total = os.sysconf("SC_PHYS_PAGES") * page
            available = os.sysconf("SC_AVPHYS_PAGES") * page
        except Exception:
            pass
    # In containers, prefer cgroup v2 limits when present.
    try:
        with open("/sys/fs/cgroup/memory.max", "r", encoding="utf-8") as f:
            limit = f.read().strip()
        with open("/sys/fs/cgroup/memory.current", "r", encoding="utf-8") as f:
            current = int(f.read().strip())
        if limit.isdigit() and int(limit) > 0:
            total = min(total, int(limit)) if total else int(limit)
            available = max(0, min(available, int(limit) - current)) if available else max(0, int(limit) - current)
    except Exception:
        pass
    return total, available


def openvino_chat_stream(messages, options, model_path=None):
    """OpenVINO GenAI NPU path; requires a pre-exported OpenVINO model directory."""
    try:
        import openvino_genai as ov_genai
    except Exception as e:
        raise RuntimeError("NPU недоступен: установите openvino-genai в окружение приложения (" + str(e) + ")")
    model_path = (model_path or os.environ.get("OPENVINO_MODEL_PATH", "")).strip()
    if not model_path or not os.path.isdir(model_path):
        raise RuntimeError("Для NPU задайте OPENVINO_MODEL_PATH — каталог заранее экспортированной OpenVINO GenAI модели")
    key = os.path.abspath(model_path)
    with OV_PIPELINE_LOCK:
        pipe = OV_PIPELINES.get(key)
        if pipe is None:
            try:
                pipe = ov_genai.LLMPipeline(key, "NPU")
            except Exception as e:
                raise RuntimeError("OpenVINO не смог скомпилировать модель на NPU: " + str(e))
            OV_PIPELINES[key] = pipe
    tok = None
    try:
        tok = pipe.get_tokenizer()
        chat = [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages]
        prompt = tok.apply_chat_template(chat, add_generation_prompt=True, tokenize=False)
    except Exception:
        lines = []
        for m in messages:
            role = str(m.get("role", "user")).upper()
            lines.append(role + ":\n" + str(m.get("content", "")))
        lines.append("ASSISTANT:\n")
        prompt = "\n\n".join(lines)
    gen_started = time.perf_counter()
    try:
        cfg = ov_genai.GenerationConfig()
        cfg.max_new_tokens = max(1, min(int(options.get("num_predict", 1024)), 8192))
        if hasattr(cfg, "temperature"):
            cfg.temperature = float(options.get("temperature", 0.6))
        if hasattr(cfg, "top_p"):
            cfg.top_p = float(options.get("top_p", 0.9))
        result = pipe.generate(prompt, cfg)
    except TypeError:
        # Compatibility with OpenVINO GenAI versions that expose keyword args.
        result = pipe.generate(prompt, max_new_tokens=max(1, min(int(options.get("num_predict", 1024)), 8192)))
    if isinstance(result, str):
        output = result
    elif hasattr(result, "texts") and result.texts:
        output = str(result.texts[0])
    else:
        output = str(result)
    elapsed_ns = max(1, int((time.perf_counter() - gen_started) * 1_000_000_000))
    yield {"message": {"content": output}, "done": False}
    yield {"done": True, "eval_count": len(output.split()), "eval_duration": elapsed_ns}


def safe_eval(expr):
    try:
        if len(expr) > 300: return None
        n = ast.parse(expr.strip(), mode='eval').body
        def ev(x):
            if isinstance(x, ast.Constant) and isinstance(x.value, (int, float)): return x.value
            if isinstance(x, ast.BinOp):
                o = OPS.get(type(x.op)); return o(ev(x.left), ev(x.right)) if o else (_ for _ in ()).throw(ValueError())
            if isinstance(x, ast.UnaryOp):
                o = OPS.get(type(x.op)); return o(ev(x.operand)) if o else (_ for _ in ()).throw(ValueError())
            raise ValueError()
        r = ev(n)
        if isinstance(r, float): return int(r) if r.is_integer() else round(r, 10)
        return r
    except: return None

MATH_RE = re.compile(r'[\d\(][\d\s\.\+\-\*\/\^%\(\)]{2,}[\d\)]')
def extract_math(p):
    if not p: return None, None
    m = MATH_RE.search(p)
    if not m: return None, None
    e = m.group(0).strip()
    if not re.search(r'[\+\-\*\/\^%]', e) or not re.search(r'\d', e): return None, None
    return (e, safe_eval(e.replace('^', '**')))

def exec_tool(tag, uid="default"):
    tag = tag.strip()
    if tag == "[TIME]":
        n = datetime.now()
        d = ["пн","вт","ср","чт","пт","сб","вс"][n.weekday()]
        return f"{n.strftime('%H:%M:%S')}, {d}, {n.day}.{n.month}.{n.year}"
    if tag == "[TIMER_START]":
        with TIMER_LOCK: TIMERS[uid] = time.time()
        return "секундомер запущен"
    if tag == "[TIMER_NOW]":
        with TIMER_LOCK: t = TIMERS.get(uid)
        return f"{time.time()-t:.3f}s" if t else "не запущен"
    if tag == "[TIMER_STOP]":
        with TIMER_LOCK: t = TIMERS.pop(uid, None)
        return f"{time.time()-t:.3f}s" if t else "не запущен"
    m = re.match(r'^\[CALC\]([\s\S]*?)\[\/CALC\]$', tag)
    if m:
        e = m.group(1).strip().replace('^', '**')
        r = safe_eval(e)
        return f"{m.group(1).strip()} = {r}" if r is not None else f"ошибка: {m.group(1).strip()}"
    return "неизвестно"

TOOL_PFX = re.compile(r'^\s*(\[TIME\]|\[TIMER_START\]|\[TIMER_NOW\]|\[TIMER_STOP\]|\[CALC\])([\s\S]*)$')
CALC_FULL = re.compile(r'^\s*\[CALC\]([\s\S]*?)\[\/CALC\]')
HELP_RE = re.compile(r'^\s*\[HELP\]([\s\S]*?)\[\/HELP\]')

app = Flask(__name__)

def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]; s.close(); return ip
    except: return "127.0.0.1"

def run_cmd(a, t=5):
    try:
        r = subprocess.run(a, capture_output=True, text=True, timeout=t)
        return (r.stdout or r.stderr or "").strip() or "—"
    except: return "ошибка"

def models_dir():
    p = os.environ.get("OLLAMA_MODELS")
    if p: return p
    return os.path.expanduser("~/.ollama/models")

def dir_size(p):
    t = 0
    try:
        for r, _, f in os.walk(p):
            for x in f:
                try: t += os.path.getsize(os.path.join(r, x))
                except: pass
    except: pass
    return t

def search(q):
    last = ""
    for b in ("auto", "html", "lite"):
        try:
            with DDGS() as d:
                r = list(d.text(q, max_results=4, backend=b))
                if r: return r, ""
        except Exception as e: last = str(e)
    return [], last or "нет"

def should_search(p):
    pl = p.lower()
    return any(k in pl for k in SEARCH_KW)

def web_ctx(r):
    return "\n".join([f"Источник: {x.get('title','')}\n{x.get('href','')}\n{x.get('body','')}\n---" for x in r if x.get('href') or x.get('body')])

def layout_swap(text):
    if not text: return None
    has = False
    for c in text:
        if c.isalpha():
            has = True
            if not c.isascii(): return None
        elif c not in " .,!?;:'\"-()[]{}0123456789\n\t": return None
    if not has: return None
    r = []
    for c in text:
        low = c.lower()
        if low in LAYOUT:
            m = LAYOUT[low]; r.append(m.upper() if c.isupper() else m)
        else: r.append(c)
    return ''.join(r)

def ask_g4f(messages):
    if not G4F_OK: return None
    try:
        response = g4f.ChatCompletion.create(model="gpt-4o-mini", messages=messages, stream=False)
        return response if isinstance(response, str) else None
    except: return None

def ollama_tags():
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        r.raise_for_status()
        return r.json().get("models", [])
    except: return []

def ollama_delete(model):
    r = requests.delete(f"{OLLAMA_URL}/api/delete", json={"model": model}, timeout=30)
    r.raise_for_status()
    return r.json()

def ollama_pull_stream(model):
    r = requests.post(f"{OLLAMA_URL}/api/pull", json={"model": model, "stream": True}, stream=True, timeout=3600)
    r.raise_for_status()
    for line in r.iter_lines():
        if not line: continue
        try: yield json.loads(line)
        except: continue

def ollama_chat_stream(model, messages, options, think=False, device="xpu", npu_model_path=None):
    """Stream a chat response from Ollama and expose its actual HTTP error body."""
    if device == "npu":
        yield from openvino_chat_stream(messages, options, model_path=npu_model_path)
        return

    # J-AI is configured to run without native reasoning by default.
    payload = {
        "model": model,
        "messages": messages,
        "options": options,
        "stream": True,
    }
    if think is not None:
        payload["think"] = bool(think)

    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json=payload,
            stream=True,
            timeout=TIMEOUT,
        )
        if not r.ok:
            try:
                error_body = r.text
            except Exception:
                error_body = "не удалось прочитать тело ответа"
            raise RuntimeError(
                f"Ollama HTTP {r.status_code} ({r.reason}): {error_body}"
            )

        for line in r.iter_lines():
            if not line:
                continue
            try:
                data = json.loads(line)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

            if data.get("error"):
                raise RuntimeError(f"Ollama: {data['error']}")

            yield data
            if data.get("done"):
                break
    except requests.exceptions.RequestException as exc:
        response = getattr(exc, "response", None)
        if response is not None:
            detail = getattr(response, "text", "")
            raise RuntimeError(
                f"Ошибка запроса к Ollama ({response.status_code}): {detail or exc}"
            ) from exc
        raise RuntimeError(f"Ошибка соединения с Ollama: {exc}") from exc

HTML = r'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>local/ai</title>
<style>
:root{--bg:#08080a;--pnl:#0f0f12;--pnl2:#141419;--pnl3:#1a1a20;--brd:#202026;--brd2:#2a2a33;
--txt:#d4d4dc;--txt2:#9696a2;--mut:#666670;--dim:#43434d;--acc:#d4a04a;--adim:#6b5028;--ahi:#f0b85c;
--ok:#6db87d;--err:#d87878;--think:#a17fe0;--thinkArt:#5fb0e0;--net:#5fb0c8;--tool:#d4a04a;
--code:#7ec89a;--chart:#d4987a;--graph:#8ed49a;--netg:#c88ed4;--aero:#7fc8e8;
--mono:ui-monospace,"SF Mono","JetBrains Mono",Menlo,Consolas,monospace;
--sans:-apple-system,BlinkMacSystemFont,"Inter","Segoe UI",Roboto,sans-serif}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;scroll-behavior:smooth}
body{font-family:var(--sans);background:var(--bg);color:var(--txt);font-size:13.5px;line-height:1.55;overflow:hidden;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
::selection{background:var(--adim);color:#fff}
button{font-family:inherit;transition:background-color .18s ease,border-color .18s ease,color .18s ease,box-shadow .2s ease,transform .2s cubic-bezier(.2,.7,.2,1)}
input,select,textarea{transition:border-color .2s ease,background-color .2s ease,box-shadow .2s ease}
.ic{width:15px;height:15px;display:inline-block;vertical-align:middle;flex-shrink:0}
.ic.lg{width:17px;height:17px}.ic.sm{width:12px;height:12px}
.app{display:grid;grid-template-columns:240px 1fr;height:100vh;overflow:hidden}
.sidebar{background:var(--pnl);border-right:1px solid var(--brd);display:flex;flex-direction:column;min-width:0;transition:margin-left .22s}
.sidebar.hidden{margin-left:-240px}
.sb-head{display:flex;align-items:center;justify-content:space-between;padding:10px 12px;border-bottom:1px solid var(--brd);height:44px}
.brand{font-family:var(--mono);font-size:12px;color:var(--mut)}
.brand b{color:var(--acc);font-weight:500}
.sb-head .actions{display:flex;gap:2px}
.iconbtn{background:none;border:1px solid transparent;color:var(--txt2);width:28px;height:28px;border-radius:5px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .15s;padding:0}
.iconbtn:hover{background:var(--pnl2);color:var(--txt);border-color:var(--brd2)}
.chat-list{flex:1;overflow-y:auto;padding:6px}
.chat-list::-webkit-scrollbar{width:6px}
.chat-list::-webkit-scrollbar-thumb{background:var(--brd2);border-radius:3px}
.chat-item{display:flex;align-items:center;gap:6px;padding:7px 9px;border-radius:5px;cursor:pointer;font-size:12.5px;color:var(--txt2);font-family:var(--mono);transition:all .12s;min-width:0;border:1px solid transparent}
.chat-item:hover{background:var(--pnl2)}
.chat-item.active{background:var(--pnl3);color:var(--txt);border-color:var(--brd2)}
.chat-item.linked::after{content:"◇";color:var(--netg);font-size:11px}
.chat-item .title{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
.chat-item .del{opacity:0;background:none;border:none;color:var(--mut);cursor:pointer;padding:0;width:16px;height:16px;display:flex;align-items:center;justify-content:center}
.chat-item:hover .del{opacity:1}.chat-item .del:hover{color:var(--err)}
.sb-foot{padding:8px 12px;border-top:1px solid var(--brd);font-family:var(--mono);font-size:10.5px;color:var(--dim);line-height:1.6}
.sb-foot .uid{color:var(--acc);cursor:pointer;user-select:all}
.workspace{display:flex;flex-direction:column;min-width:0;overflow:hidden;background:var(--bg)}
.topbar{height:44px;padding:0 12px;border-bottom:1px solid var(--brd);display:flex;align-items:center;gap:8px;background:var(--pnl);flex-shrink:0;overflow:hidden}
.chat-title{font-family:var(--mono);font-size:12.5px;color:var(--txt2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;min-width:0;cursor:pointer;padding:4px 6px;border-radius:4px}
.chat-title:hover{color:var(--txt);background:var(--pnl2)}
.emo-badges{display:none;align-items:center;gap:6px;font-family:var(--mono);font-size:10.5px;flex-shrink:0;overflow:hidden;max-width:280px}
.emo-badge{padding:2px 6px;border:1px solid var(--brd2);border-radius:4px;background:var(--pnl2);white-space:nowrap;transition:all .3s}
.tb-actions{display:flex;align-items:center;gap:3px;flex-shrink:0}
.tbtn{background:none;border:1px solid var(--brd2);color:var(--txt2);width:30px;height:30px;border-radius:6px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .15s;padding:0;position:relative}
.tbtn:hover{background:var(--pnl2);color:var(--txt);border-color:var(--brd)}
.tbtn.on{color:var(--acc);border-color:var(--adim);background:rgba(212,160,74,0.09)}
.tbtn.on::after{content:"";position:absolute;bottom:-2px;left:50%;transform:translateX(-50%);width:4px;height:4px;border-radius:50%;background:var(--acc);box-shadow:0 0 6px var(--acc)}
.tbtn.think.on{color:var(--think);border-color:#4a3f60}
.tbtn.think.on::after{background:var(--think)}
.tbtn.thinkart.on{color:var(--thinkArt);border-color:#2a4a68}
.tbtn.thinkart.on::after{background:var(--thinkArt)}
.tbtn.tools.on{color:var(--tool);border-color:#5a4530}
.tbtn.tools.on::after{background:var(--tool)}
.tbtn.forms.on{color:var(--ok);border-color:#3a5a48}
.tbtn.forms.on::after{background:var(--ok)}
.tbtn.fast.on{color:var(--err);border-color:#5a3040}
.tbtn.fast.on::after{background:var(--err)}
.tbtn.g4f.on{color:#8fd4e8;border-color:#2a5a68}
.tbtn.g4f.on::after{background:#8fd4e8}
.tbtn.raw-prompt.on{color:var(--thinkArt);border-color:#2a4a68;background:rgba(95,176,224,.09)}
.tbtn.raw-prompt.on::after{background:var(--thinkArt)}
.tbtn.animation-toggle.on{color:#80cbd4;border-color:#28515a;background:rgba(128,203,212,.08)}
.tbtn.animation-toggle.on::after{background:#80cbd4}
.tbtn .badge{position:absolute;top:-3px;right:-3px;font-family:var(--mono);font-size:8px;font-weight:700;background:var(--acc);color:#000;padding:1px 3px;border-radius:3px}
.tbtn.thinkart .badge{background:var(--thinkArt)}
.tbtn[data-tip]:hover::before{content:attr(data-tip);position:absolute;top:36px;left:50%;transform:translateX(-50%);background:var(--pnl3);color:var(--txt2);border:1px solid var(--brd2);border-radius:4px;padding:3px 8px;font-size:10.5px;font-family:var(--mono);white-space:nowrap;z-index:200;pointer-events:none}
.messages{flex:1;overflow-y:auto;padding:0 24px;display:flex;flex-direction:column}
.messages::-webkit-scrollbar{width:8px}
.messages::-webkit-scrollbar-thumb{background:var(--brd2);border-radius:4px}
.empty{margin:auto;font-family:var(--mono);font-size:12px;color:var(--dim);line-height:1.9}
.empty .c{color:var(--acc)}
.entry{padding:15px 0;border-bottom:1px solid var(--brd);display:flex;flex-direction:column;gap:8px;position:relative}
.entry:last-child{border-bottom:none}
.entry.selected{background:rgba(212,160,74,0.04);margin:0 -24px;padding-left:24px;padding-right:24px;border-left:2px solid var(--acc)}
.entry-check{position:absolute;left:2px;top:17px;opacity:0;transition:opacity .12s}
.entry:hover .entry-check,.entry.selected .entry-check{opacity:1}
.entry-check input{-webkit-appearance:none;width:13px;height:13px;border:1px solid var(--brd2);border-radius:2px;cursor:pointer;background:var(--pnl);position:relative}
.entry-check input:checked{background:var(--acc);border-color:var(--acc)}
.entry-check input:checked::after{content:"✓";position:absolute;inset:0;color:#000;font-size:9px;font-weight:bold;display:flex;align-items:center;justify-content:center}
.entry-head{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-family:var(--mono);font-size:11px;color:var(--mut);padding-left:18px}
.entry-head .prefix{font-weight:700;font-size:12px}
.entry-head .role{font-weight:600}
.entry-head .botname{color:#8fd4e8;font-size:10.5px;padding:1px 6px;border:1px solid #2a5a68;border-radius:3px;background:rgba(143,212,232,0.06)}
.entry-head .model-tag{color:var(--think);font-size:10.5px;padding:1px 6px;border:1px solid #4a3f60;border-radius:3px}
.mode-tag{font-size:9.5px;padding:1px 5px;border-radius:3px;text-transform:uppercase}
.mode-tag.think{color:var(--think);border:1px solid #4a3f60}
.mode-tag.thinkart{color:var(--thinkArt);border:1px solid #2a4a68}
.mode-tag.tools{color:var(--tool);border:1px solid #5a4530}
.mode-tag.fast{color:var(--err);border:1px solid #5a3040}
.mode-tag.g4f{color:#8fd4e8;border:1px solid #2a5a68}
.entry-head .sep{color:var(--dim)}.entry-head .time{color:var(--dim)}
.entry-head .meta{color:var(--dim);margin-left:auto}
.entry-head .meta .think-stat{color:var(--think)}
.entry-head .meta .tok-stat{color:var(--ok)}
.entry-head .meta .spd-stat{color:var(--acc)}
.entry[data-role="user"] .prefix,.entry[data-role="user"] .role{color:var(--acc)}
.entry[data-role="assistant"] .prefix,.entry[data-role="assistant"] .role{color:var(--ok)}
.entry[data-role="error"] .prefix,.entry[data-role="error"] .role{color:var(--err)}
.entry[data-role="system"] .prefix,.entry[data-role="system"] .role{color:var(--mut)}
.entry-body{font-size:14px;line-height:1.65;color:var(--txt);word-wrap:break-word;padding-left:18px;overflow-wrap:anywhere}
.entry-body.plain{white-space:pre-wrap}
.entry[data-role="user"] .entry-body{color:var(--txt);padding-left:18px;border-left:2px solid var(--adim);white-space:pre-wrap}
.entry[data-role="error"] .entry-body{color:var(--err);font-family:var(--mono);font-size:12.5px;white-space:pre-wrap}
.entry[data-role="system"] .entry-body{color:var(--mut);font-family:var(--mono);font-size:12px;font-style:italic;white-space:pre-wrap}
.entry-body.empty::after{content:"▌";color:var(--acc);animation:blink 1s steps(2) infinite}
@keyframes blink{50%{opacity:0}}
.entry-body p{margin:0 0 8px}.entry-body p:last-child{margin-bottom:0}
.entry-body strong,.entry-body b{color:#fff;font-weight:600}
.entry-body em,.entry-body i{color:var(--txt2);font-style:italic}
.entry-body u{text-decoration:underline;text-decoration-color:var(--acc)}
.entry-body del,.entry-body s{color:var(--dim);text-decoration:line-through}
.entry-body mark{background:rgba(212,160,74,0.25);color:#fff;padding:1px 4px;border-radius:3px}
.entry-body sup{color:var(--acc);font-size:.7em;vertical-align:super}
.entry-body sub{color:var(--acc);font-size:.7em;vertical-align:sub}
.entry-body code{font-family:var(--mono);font-size:12.5px;background:var(--pnl2);padding:1px 5px;border-radius:3px;color:var(--code);border:1px solid var(--brd)}
.entry-body blockquote{border-left:3px solid var(--acc);padding:6px 12px;margin:6px 0;background:var(--pnl);color:var(--txt2);font-style:italic;border-radius:4px}
.entry-body ul,.entry-body ol{margin:6px 0 8px 22px}
.entry-body li{margin:2px 0}
.entry-body h1,.entry-body h2,.entry-body h3{margin:12px 0 6px;color:#fff;font-weight:600}
.entry-body h1{font-size:18px}.entry-body h2{font-size:16px}.entry-body h3{font-size:14.5px}
.entry-body a{color:var(--acc)}
.md-table{width:100%;border-collapse:collapse;margin:8px 0;font-size:13px;border:1px solid var(--brd2);border-radius:5px;overflow:hidden}
.md-table th{background:var(--pnl2);color:var(--txt);font-weight:600;padding:7px 10px;text-align:left;font-family:var(--mono);font-size:11.5px;border-bottom:1px solid var(--brd2);border-right:1px solid var(--brd)}
.md-table th:last-child{border-right:none}
.md-table td{padding:6px 10px;border-bottom:1px solid var(--brd);border-right:1px solid var(--brd);color:var(--txt2)}
.md-table td:last-child{border-right:none}
.md-table tr:last-child td{border-bottom:none}
.code-block{position:relative;margin:10px 0;background:#06060a;border:1px solid var(--brd2);border-radius:6px;overflow:hidden}
.code-block .cb-head{display:flex;align-items:center;justify-content:space-between;padding:5px 10px;background:var(--pnl2);border-bottom:1px solid var(--brd);font-family:var(--mono);font-size:10.5px;color:var(--mut);text-transform:uppercase}
.code-block pre{margin:0;padding:10px 12px;overflow-x:auto;font-family:var(--mono);font-size:12.5px;line-height:1.6;color:#c8d0d8}
.code-copy{background:none;border:1px solid var(--brd2);color:var(--txt2);font-family:var(--mono);font-size:10px;padding:2px 7px;border-radius:3px;cursor:pointer;display:flex;align-items:center;gap:4px}
.code-copy:hover{color:var(--acc);border-color:var(--adim)}
.blk{margin:10px 0;border-radius:6px;padding:10px 12px;border:1px solid var(--brd2)}
.blk .bh{font-family:var(--mono);font-size:10.5px;text-transform:uppercase;margin-bottom:8px;display:flex;align-items:center;gap:6px;justify-content:space-between}
.blk canvas{display:block;width:100%;max-width:100%}
.chart-block{background:var(--pnl);border-left:2px solid var(--chart)}
.chart-block .bh{color:var(--chart)}
.graph-block{background:#06060a;border-left:2px solid var(--graph);position:relative}
.graph-block .bh{color:var(--graph)}
.graph-block .bh .expr{color:var(--txt2);text-transform:none}
.graph-block canvas{cursor:grab}.graph-block canvas:active{cursor:grabbing}
.graphnet-block{background:#07070b;border-left:2px solid var(--netg)}
.graphnet-block .bh{color:var(--netg)}
.graphnet-block canvas{cursor:grab}.graphnet-block canvas:active{cursor:grabbing}
.shape-block{background:#06060a;border-left:2px solid var(--acc)}
.shape-block .bh{color:var(--acc)}
.shape-block canvas{cursor:grab;background:radial-gradient(circle at center,#0a0a10 0%,#050508 100%)}
.shape-block canvas:active{cursor:grabbing}
.aero-block{background:#060a10;border-left:2px solid var(--aero)}
.aero-block .bh{color:var(--aero)}
.aero-block canvas{display:block;width:100%;cursor:grab;background:radial-gradient(circle at center,#0a1018 0%,#050810 100%)}
.aero-block canvas:active{cursor:grabbing}
.aero-controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:8px;padding:8px;background:var(--pnl);border:1px solid var(--brd);border-radius:5px;font-family:var(--mono);font-size:10.5px}
.aero-controls label{color:var(--txt2);display:flex;align-items:center;gap:4px}
.aero-controls input[type="range"]{width:90px;accent-color:var(--aero)}
.aero-controls .val{color:var(--aero);min-width:32px;text-align:right}
.aero-objs{display:flex;flex-wrap:wrap;gap:4px;width:100%}
.aero-obj{background:var(--pnl2);border:1px solid var(--brd2);border-radius:4px;padding:3px 8px;color:var(--txt2);display:flex;align-items:center;gap:6px;font-size:10.5px}
.aero-obj select{background:var(--bg);border:1px solid var(--brd2);color:var(--txt);font-family:var(--mono);font-size:10.5px;border-radius:3px;padding:1px 4px}
.aero-obj .rm{cursor:pointer;color:var(--dim)}
.aero-obj .rm:hover{color:var(--err)}
.chess-block{background:var(--pnl);border-left:2px solid var(--acc);padding:12px}
.chess-block .bh{color:var(--acc)}
.chess-wrap{display:flex;gap:16px;align-items:flex-start;flex-wrap:wrap}
.chess-board{display:grid;grid-template-columns:repeat(8,1fr);grid-template-rows:repeat(8,1fr);width:400px;height:400px;border:2px solid var(--adim);border-radius:4px;overflow:hidden;background:#0a0a0c}
.chess-sq{position:relative;cursor:pointer;display:flex;align-items:center;justify-content:center;user-select:none}
.chess-sq.light{background:#3a3a44}
.chess-sq.dark{background:#1c1c22}
.chess-sq:hover{filter:brightness(1.15)}
.chess-sq.sel{box-shadow:inset 0 0 0 3px var(--acc)}
.chess-sq.legal::after{content:"";position:absolute;width:24%;height:24%;border-radius:50%;background:rgba(109,184,125,0.6);pointer-events:none}
.chess-sq.cap::after{content:"";position:absolute;inset:6%;border-radius:50%;border:3px solid rgba(216,120,120,0.7);background:transparent;pointer-events:none}
.chess-sq .piece{line-height:1;pointer-events:none;font-size:32px;display:flex;align-items:center;justify-content:center}
.chess-sq .piece.w{color:#f0e8d8;text-shadow:0 1px 2px rgba(0,0,0,0.9)}
.chess-sq .piece.b{color:#1a1a1a;text-shadow:0 1px 2px rgba(255,255,255,0.15)}
.chess-sq .coord{position:absolute;bottom:2px;right:3px;font-size:9px;color:rgba(255,255,255,0.25);font-family:var(--mono);pointer-events:none}
.chess-info{flex:1;min-width:200px;font-family:var(--mono);font-size:11.5px;color:var(--txt2)}
.chess-info .row{padding:4px 0;display:flex;justify-content:space-between;border-bottom:1px solid var(--brd)}
.chess-info .row .lbl{color:var(--mut)}.chess-info .row .val{color:var(--txt)}
.chess-info .row .val.acc{color:var(--acc)}.chess-info .row .val.ok{color:var(--ok)}.chess-info .row .val.err{color:var(--err)}
.chess-moves{max-height:200px;overflow-y:auto;margin-top:8px;background:var(--bg);border:1px solid var(--brd2);border-radius:4px;padding:6px 8px;font-size:11px;line-height:1.5}
.chess-moves .mv{color:var(--txt2)}.chess-moves .mv.user{color:var(--acc)}.chess-moves .mv.ai{color:var(--ok)}
.obsidian-block{margin:10px 0;background:radial-gradient(circle at center,#0a0a14 0%,#050508 100%);border:1px solid var(--brd2);border-left:2px solid var(--think);border-radius:6px;padding:12px;position:relative;min-height:420px;overflow:hidden}
.obsidian-block .bh{color:var(--think);position:absolute;top:12px;left:12px;right:12px;z-index:2}
.obsidian-block svg{position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none}
.obsidian-node{position:absolute;padding:8px 14px;background:rgba(20,20,26,0.95);border:1px solid var(--brd2);border-radius:16px;font-family:var(--sans);font-size:12px;color:var(--txt);cursor:grab;user-select:none;z-index:3;box-shadow:0 4px 16px rgba(0,0,0,0.5);white-space:nowrap}
.obsidian-node:hover{border-color:var(--think)}
.obsidian-node.dragging{cursor:grabbing;border-color:var(--acc)}
.obsidian-node.center{background:linear-gradient(135deg,rgba(161,127,224,0.25),rgba(161,127,224,0.1));border-color:var(--think);color:#fff;font-weight:600;font-size:13px;padding:10px 18px}
.obsidian-node.level1{border-color:rgba(161,127,224,0.5);color:#c8b8e8}
.obsidian-node.level2{border-color:var(--brd2);color:var(--txt2);font-size:11px;padding:6px 12px}
.tree-block,.kanban-block,.timeline-block,.process-block,.metrics-block,.checklist-block,.filetree-block,.matrix-block,.callout-block,.quote-block,.math-block{margin:10px 0;border-radius:6px;border:1px solid var(--brd2);padding:12px;background:var(--pnl)}
.tree-block{border-left:2px solid var(--ok)}.tree-block .bh{color:var(--ok)}
.tree-line{padding:3px 0;display:flex;align-items:center;gap:6px;font-family:var(--mono);font-size:12.5px;color:var(--txt2)}
.tree-line.root{color:var(--txt);font-weight:600}
.kanban-block{border-left:2px solid var(--acc)}.kanban-block .bh{color:var(--acc)}
.kanban-cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}
.kanban-col{background:var(--bg);border:1px solid var(--brd2);border-radius:5px;padding:8px}
.kanban-col-t{font-family:var(--mono);font-size:11px;color:var(--acc);text-transform:uppercase;margin-bottom:6px;padding-bottom:5px;border-bottom:1px solid var(--brd);display:flex;justify-content:space-between}
.kanban-col-t .cnt{color:var(--dim)}
.kanban-card{background:var(--pnl2);border:1px solid var(--brd);border-radius:4px;padding:6px 8px;margin-bottom:5px;font-size:12px;color:var(--txt2)}
.timeline-block{border-left:2px solid var(--net)}.timeline-block .bh{color:var(--net)}
.timeline{position:relative;padding-left:40px}
.timeline::before{content:"";position:absolute;left:18px;top:5px;bottom:5px;width:2px;background:linear-gradient(to bottom,var(--net),var(--adim))}
.timeline-item{position:relative;padding:6px 0}
.timeline-item::before{content:"";position:absolute;left:-28px;top:11px;width:10px;height:10px;border-radius:50%;background:var(--net);border:2px solid var(--bg)}
.timeline-date{font-family:var(--mono);font-size:11px;color:var(--net);font-weight:600}
.timeline-text{font-size:12.5px;color:var(--txt2);margin-top:2px}
.process-block{border-left:2px solid var(--chart)}.process-block .bh{color:var(--chart)}
.process-flow{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.process-step{background:var(--bg);border:1px solid var(--brd2);border-radius:20px;padding:5px 12px;font-size:12px;color:var(--txt2);display:flex;gap:6px}
.process-step .num{font-family:var(--mono);font-size:10px;color:var(--chart);font-weight:600}
.process-arrow{color:var(--dim);font-size:14px}
.metrics-block{border-left:2px solid var(--ok)}.metrics-block .bh{color:var(--ok)}
.metrics-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px}
.metric-card{background:var(--bg);border:1px solid var(--brd2);border-radius:6px;padding:10px 12px}
.metric-label{font-family:var(--mono);font-size:10.5px;color:var(--mut);text-transform:uppercase}
.metric-value{font-size:22px;font-weight:700;color:var(--txt);margin:3px 0;font-family:var(--mono)}
.metric-delta{font-family:var(--mono);font-size:11px}
.metric-delta.up{color:var(--ok)}.metric-delta.down{color:var(--err)}
.checklist-block{border-left:2px solid var(--ok)}.checklist-block .bh{color:var(--ok)}
.checklist-item{display:flex;gap:8px;padding:5px 0;font-size:13px;color:var(--txt2);cursor:pointer}
.checklist-item input{margin-top:3px;width:14px;height:14px;accent-color:var(--ok);flex-shrink:0}
.checklist-item.done .checklist-text{color:var(--dim);text-decoration:line-through}
.filetree-block{border-left:2px solid var(--tool)}.filetree-block .bh{color:var(--tool)}
.filetree{font-family:var(--mono);font-size:12px;line-height:1.7;color:var(--txt2)}
.filetree .file-line{display:flex;align-items:center;gap:5px}
.filetree .file-line.dir{color:var(--acc);font-weight:600}
.matrix-block{border-left:2px solid var(--code)}.matrix-block .bh{color:var(--code)}
.matrix-wrap{display:inline-block;position:relative;padding:0 8px}
.matrix-wrap::before,.matrix-wrap::after{content:"";position:absolute;top:0;bottom:0;width:4px;border:2px solid var(--code)}
.matrix-wrap::before{left:0;border-right:none}
.matrix-wrap::after{right:0;border-left:none}
.matrix-table{border-collapse:separate;border-spacing:8px 4px;font-family:var(--mono);font-size:12.5px}
.matrix-table td{text-align:center;color:var(--txt)}
.callout-block{border-left-width:3px;padding:12px 14px}
.callout-block.info{border-color:var(--net);background:rgba(95,176,200,0.05)}.callout-block.info .bh{color:var(--net)}
.callout-block.warn{border-color:var(--acc);background:rgba(212,160,74,0.05)}.callout-block.warn .bh{color:var(--acc)}
.callout-block.success{border-color:var(--ok);background:rgba(109,184,125,0.05)}.callout-block.success .bh{color:var(--ok)}
.callout-block.error{border-color:var(--err);background:rgba(216,120,120,0.05)}.callout-block.error .bh{color:var(--err)}
.callout-block.tip{border-color:var(--think);background:rgba(161,127,224,0.05)}.callout-block.tip .bh{color:var(--think)}
.callout-text{font-size:13px;line-height:1.6;color:var(--txt2)}
.quote-block{border-left:3px solid var(--acc);padding:12px 16px}
.quote-block .bh{color:var(--acc)}
.quote-text{font-size:14px;line-height:1.65;color:var(--txt);font-style:italic}
.quote-author{margin-top:8px;font-family:var(--mono);font-size:11.5px;color:var(--mut);text-align:right}
.math-block{border-left:2px solid var(--think);padding:14px;background:#06060a;text-align:center}
.math-block .bh{color:var(--think);justify-content:center}
.math-content{font-family:"Cambria Math",serif;font-size:20px;color:#e8e8f0;line-height:1.8}
.live-think{margin-left:18px;background:linear-gradient(180deg,rgba(161,127,224,0.05),rgba(161,127,224,0.02));border:1px solid #2f2648;border-left:2px solid var(--think);border-radius:6px;overflow:hidden}
.live-think.art{background:linear-gradient(180deg,rgba(95,176,224,0.06),rgba(95,176,224,0.02));border-color:#223a52;border-left-color:var(--thinkArt)}
.live-think .lt-head{padding:7px 10px;display:flex;align-items:center;gap:8px;font-family:var(--mono);font-size:11px;color:var(--think);cursor:pointer;border-bottom:1px solid #2f2648}
.live-think.art .lt-head{color:var(--thinkArt);border-bottom-color:#223a52}
.live-think .lt-head .pulse{width:6px;height:6px;border-radius:50%;background:var(--think);animation:pulse 1.4s infinite}
.live-think.art .lt-head .pulse{background:var(--thinkArt)}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.live-think .lt-head .lbl{flex:1;font-weight:600}
.live-think .lt-body{padding:8px 12px;font-family:var(--mono);font-size:11.5px;line-height:1.65;color:#8f7fb8;white-space:pre-wrap;max-height:340px;overflow-y:auto}
.live-think.art .lt-body{color:#7fa8cc}
.live-think.collapsed .lt-body{display:none}
.think-box{background:var(--pnl);border:1px solid var(--brd);border-left:2px solid var(--think);border-radius:5px;padding:0;overflow:hidden;margin-left:18px}
.think-box.art{border-left-color:var(--thinkArt)}
.think-box summary{padding:7px 10px;font-family:var(--mono);font-size:11px;color:var(--think);cursor:pointer;list-style:none;display:flex;gap:6px}
.think-box.art summary{color:var(--thinkArt)}
.think-box summary::-webkit-details-marker{display:none}
.think-box summary::before{content:"▸";display:inline-block;transition:transform .15s}
.think-box[open] summary::before{transform:rotate(90deg)}
.think-box .think-body{padding:0 12px 10px;font-family:var(--mono);font-size:11.5px;line-height:1.65;color:#8f7fb8;white-space:pre-wrap;max-height:300px;overflow-y:auto}
.think-box.art .think-body{color:#7fa8cc}
.correction-box{margin-left:18px;background:var(--pnl);border:1px solid var(--brd);border-left:2px solid var(--acc);border-radius:5px;padding:6px 10px;font-family:var(--mono);font-size:11.5px;color:var(--txt2)}
.correction-box .lbl{color:var(--acc);font-size:10px;text-transform:uppercase;display:block;margin-bottom:2px}
.correction-box .orig{color:var(--dim);text-decoration:line-through}
.correction-box .arrow{color:var(--mut);margin:0 4px}
.correction-box .fix{color:var(--ok)}
.net-box,.tool-box{margin-left:18px;background:var(--pnl);border:1px solid var(--brd);border-left:2px solid var(--net);border-radius:5px;overflow:hidden}
.tool-box{border-left-color:var(--tool)}
.net-box summary,.tool-box summary{padding:6px 10px;font-family:var(--mono);font-size:11px;color:var(--net);cursor:pointer;list-style:none;display:flex;gap:6px}
.tool-box summary{color:var(--tool)}
.net-box summary::-webkit-details-marker,.tool-box summary::-webkit-details-marker{display:none}
.net-box summary::before,.tool-box summary::before{content:"▸";display:inline-block;transition:transform .15s}
.net-box[open] summary::before,.tool-box[open] summary::before{transform:rotate(90deg)}
.net-box .net-body,.tool-box .tool-body{padding:0 12px 8px;font-family:var(--mono);font-size:11px;line-height:1.7;color:#6a8fa0;white-space:pre-wrap;max-height:200px;overflow-y:auto}
.tool-box .tool-body{color:#a89060}
.tool-box .tool-body .tline{padding:3px 0}
.tool-box .tool-body .tname{color:var(--tool);font-weight:600}
.tool-box .tool-body .tres{color:#b8a878}
.entry-actions{display:flex;gap:4px;opacity:0;transition:opacity .15s;flex-wrap:wrap;padding-left:18px;align-items:center}
.entry:hover .entry-actions{opacity:1}
.act{background:none;border:1px solid var(--brd2);color:var(--mut);padding:3px 8px;border-radius:4px;cursor:pointer;display:inline-flex;align-items:center;gap:4px;font-size:10.5px;font-family:var(--mono)}
.act:hover{color:var(--txt2);border-color:var(--brd);background:var(--pnl2)}
.act.up.sel{color:var(--ok);border-color:var(--ok)}
.act.down.sel{color:var(--err);border-color:var(--err)}
.act.saved{color:var(--acc);border-color:var(--adim)}
.act.cont{color:var(--ok);border-color:#3a5a48}
.edit-area{display:flex;flex-direction:column;gap:8px;padding-left:18px}
.edit-area textarea{background:var(--bg);border:1px solid var(--adim);color:var(--txt);border-radius:5px;padding:9px 12px;font-family:var(--sans);font-size:14px;line-height:1.5;resize:vertical;outline:none;min-height:60px;max-height:240px}
.edit-buttons{display:flex;gap:6px}
.edit-buttons button{font-family:var(--mono);font-size:10.5px;text-transform:uppercase;padding:5px 10px;border-radius:4px;border:1px solid var(--brd2);background:transparent;color:var(--txt2);cursor:pointer}
.edit-buttons button.save{border-color:var(--adim);color:var(--acc)}
.bulk-bar{position:fixed;bottom:90px;left:50%;transform:translateX(-50%) translateY(20px);background:var(--pnl2);border:1px solid var(--adim);border-radius:8px;padding:8px 14px;display:none;align-items:center;gap:10px;z-index:50;font-family:var(--mono);font-size:11px;color:var(--txt2);opacity:0;transition:all .2s}
.bulk-bar.on{display:flex;opacity:1;transform:translateX(-50%) translateY(0)}
.bulk-bar .count{color:var(--acc);font-weight:600}
.stats-line{padding:5px 24px 0;font-family:var(--mono);font-size:10.5px;color:var(--dim);min-height:17px;text-align:right;white-space:nowrap;overflow:hidden}
.stats-line .live{color:var(--acc)}
.stats-line .think-live{color:var(--think)}
.stats-line .stage{color:var(--ok)}
.scroll-btn{position:fixed;right:26px;bottom:130px;width:40px;height:40px;border-radius:50%;background:var(--acc);border:1px solid var(--ahi);color:#000;cursor:pointer;display:none;align-items:center;justify-content:center;z-index:40;box-shadow:0 6px 24px rgba(212,160,74,0.5)}
.scroll-btn:hover{background:var(--ahi);transform:translateY(-2px)}
.scroll-btn.on{display:flex}
.composer{border-top:1px solid var(--brd);background:var(--pnl);padding:9px 14px;display:flex;flex-direction:column;gap:7px;flex-shrink:0;position:relative}
.compose-controls{display:grid;grid-template-columns:minmax(190px,1.55fr) minmax(140px,1fr) minmax(145px,1fr);align-items:center;gap:8px;flex-wrap:nowrap;min-width:0;width:100%;max-width:820px;overflow:visible}
.compose-control{min-width:0;white-space:nowrap}
.compose-control>span{flex-shrink:0}
.chat-model-select{width:100%;min-width:0}
.compose-select{width:100%;max-width:none;min-width:0}
.context-wrap{min-width:0}
.context-trigger{width:100%;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.context-menu{backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);transition:opacity .22s ease,transform .22s ease}
.compose-control{display:flex;align-items:center;gap:5px;min-width:0;font:10px var(--mono);color:var(--mut)}
.compose-control>span{white-space:nowrap}
.chat-model-select,.compose-select,.context-trigger{min-width:0;max-width:100%;background:var(--bg);border:1px solid var(--brd2);color:var(--txt2);border-radius:5px;padding:6px 8px;font:10.5px var(--mono);outline:none;cursor:pointer}
.chat-model-select{width:min(310px,42vw);}
.compose-select{max-width:145px}
.context-wrap{position:relative}
.context-trigger:hover,.chat-model-select:focus,.compose-select:focus{border-color:var(--adim);color:var(--txt)}
.context-menu{position:absolute;left:0;bottom:calc(100% + 8px);min-width:245px;max-width:min(320px,90vw);padding:9px;background:var(--pnl2);border:1px solid var(--brd2);border-radius:8px;box-shadow:0 12px 32px rgba(0,0,0,.45);z-index:120;display:none}
.context-menu.open{display:block;animation:message-arrive .14s ease-out both}
.context-menu .cm-title{font:10px var(--mono);color:var(--mut);margin:1px 2px 7px}
.context-menu .cm-options{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:5px}
.context-menu .cm-option{padding:8px 7px;border:1px solid var(--brd2);border-radius:5px;background:var(--bg);color:var(--txt2);font:11px var(--mono);cursor:pointer;text-align:left}
.context-menu .cm-option:hover,.context-menu .cm-option.active{border-color:var(--adim);color:var(--acc);background:rgba(212,160,74,.06)}
.context-menu .cm-note{font:10px/1.5 var(--sans);color:var(--mut);margin:8px 2px 2px}
.compose-entry{display:flex;align-items:flex-end;gap:10px;min-width:0}
.composer .cp{font-family:var(--mono);font-size:14px;color:var(--acc);padding-bottom:11px;user-select:none}
.composer textarea{flex:1;width:100%;min-width:0;background:var(--bg);border:1px solid var(--brd2);color:var(--txt);border-radius:6px;padding:9px 12px;font-family:var(--sans);font-size:13.5px;line-height:1.5;resize:none;outline:none;min-height:38px;max-height:200px}
.composer textarea:focus{border-color:var(--adim)}
.composer .send{border:1px solid var(--brd2);background:var(--bg);color:var(--txt2);cursor:pointer;padding:0;width:42px;height:42px;border-radius:6px;display:flex;align-items:center;justify-content:center}
.composer .send:hover:not(:disabled){border-color:var(--acc);color:var(--acc)}
.composer .send:disabled{opacity:.4;cursor:not-allowed}
.composer .send.stop{border-color:var(--err);color:var(--err)}
.char-count{position:absolute;right:68px;bottom:8px;font-family:var(--mono);font-size:10px;color:var(--dim);pointer-events:none}
.overlay{position:fixed;inset:0;background:rgba(0,0,0,0.55);opacity:0;pointer-events:none;transition:opacity .22s;z-index:90}
.overlay.on{opacity:1;pointer-events:auto}
.panel{position:fixed;top:0;right:0;bottom:0;width:540px;max-width:100vw;background:var(--pnl);border-left:1px solid var(--brd);display:flex;flex-direction:column;transform:translateX(100%);transition:transform .25s cubic-bezier(.2,.8,.2,1);z-index:100}
.panel.open{transform:translateX(0)}
.panel-head{display:flex;align-items:center;justify-content:space-between;padding:0 14px;border-bottom:1px solid var(--brd);height:44px}
.panel-head .pt{font-family:var(--mono);font-size:12px;color:var(--mut);display:flex;gap:8px}
.panel-head .pt .ic{color:var(--acc)}
.panel-tabs{display:flex;gap:4px;padding:6px 14px;border-bottom:1px solid var(--brd);flex-wrap:wrap}
.ptab{flex:1;min-width:70px;font-family:var(--mono);font-size:10.5px;text-transform:uppercase;padding:6px 10px;border-radius:5px;background:transparent;color:var(--mut);cursor:pointer;border:1px solid transparent}
.ptab:hover{color:var(--txt2);background:var(--pnl2)}
.ptab.active{color:var(--acc);background:rgba(212,160,74,0.07);border-color:var(--adim)}
.panel-body{flex:1;overflow-y:auto;padding:6px 16px 16px}
.panel-body::-webkit-scrollbar{width:6px}
.panel-body::-webkit-scrollbar-thumb{background:var(--brd2);border-radius:3px}
.group{margin-top:14px}
.group-t{font-family:var(--mono);font-size:10.5px;color:var(--dim);text-transform:uppercase;padding:8px 0 6px;border-bottom:1px solid var(--brd);margin-bottom:10px}
.group-t::before{content:"// ";color:var(--adim)}
.uid-display{display:flex;gap:6px;align-items:center;font-family:var(--mono);font-size:11px;color:var(--txt2);padding:6px 10px;background:var(--bg);border:1px solid var(--brd2);border-radius:5px}
.uid-display .id{flex:1;color:var(--acc);user-select:all}
.mood-scale{margin-bottom:10px}
.mood-scale .ms-labels{display:flex;justify-content:space-between;font-family:var(--mono);font-size:11px;color:var(--txt2);margin-bottom:4px}
.mood-scale .ms-labels .mood-val{color:var(--acc);font-weight:600}
.mood-scale input[type="range"]{width:100%;accent-color:var(--acc);height:4px}
.storage-box{display:flex;flex-direction:column;gap:6px;font-family:var(--mono);font-size:11px;padding:8px 10px;background:var(--bg);border:1px solid var(--brd2);border-radius:5px}
.storage-box .row{display:flex;justify-content:space-between}
.storage-box .row .lbl{color:var(--dim)}
.storage-box .row .val{color:var(--txt2)}
.storage-box .row .val.accent{color:var(--acc)}
.storage-box .row .val.ok{color:var(--ok)}
.storage-bar{height:4px;background:var(--brd2);border-radius:2px;overflow:hidden;margin-top:2px}
.storage-bar .fill{height:100%;background:var(--acc);transition:width .3s}
.move-row{display:flex;gap:6px;margin-top:6px}
.move-row input{flex:1;background:var(--bg);border:1px solid var(--brd2);color:var(--txt);border-radius:5px;padding:6px 8px;font-family:var(--mono);font-size:11px;outline:none}
.perf-picker{display:flex;gap:4px;margin-bottom:6px}
.perf-picker button{flex:1;font-family:var(--mono);font-size:11px;text-transform:uppercase;padding:8px;border-radius:5px;border:1px solid var(--brd2);background:transparent;color:var(--txt2);cursor:pointer}
.perf-picker button.sel-low{color:var(--ok);border-color:var(--ok)}
.perf-picker button.sel-medium{color:var(--acc);border-color:var(--acc)}
.perf-picker button.sel-high{color:var(--err);border-color:var(--err)}
.perf-note{font-family:var(--mono);font-size:10.5px;color:var(--dim);padding:6px 0;line-height:1.6}
.diag-box{font-family:var(--mono);font-size:10.5px;color:var(--txt2);background:var(--bg);border:1px solid var(--brd2);border-radius:5px;padding:8px 10px;line-height:1.6;white-space:pre-wrap;word-wrap:break-word;max-height:200px;overflow-y:auto;margin-top:6px}
.diag-btn{font-family:var(--mono);font-size:10.5px;text-transform:uppercase;padding:5px 10px;border-radius:5px;border:1px solid var(--brd2);background:transparent;color:var(--txt2);cursor:pointer;margin-top:6px}
.diag-btn:hover{border-color:var(--acc);color:var(--acc)}
.model-picker{display:flex;flex-direction:column;gap:6px}
.model-select{width:100%;background:var(--bg);border:1px solid var(--brd2);color:var(--txt);border-radius:5px;padding:8px 10px;font-family:var(--mono);font-size:11.5px;outline:none;cursor:pointer}
.model-actions{display:flex;gap:6px}
.model-actions button{flex:1;font-family:var(--mono);font-size:10.5px;text-transform:uppercase;padding:6px 8px;border-radius:5px;border:1px solid var(--brd2);background:transparent;color:var(--txt2);cursor:pointer}
.model-actions button.primary{border-color:var(--adim);color:var(--acc)}
.model-actions button.primary:hover{background:var(--acc);color:#000}
.model-actions button.danger{border-color:#5a3040;color:var(--err)}
.model-actions button:disabled{opacity:.4;cursor:not-allowed}
.model-status{font-family:var(--mono);font-size:10.5px;color:var(--dim);padding:2px 0;min-height:14px}
.model-status.ok{color:var(--ok)}.model-status.err{color:var(--err)}.model-status.dl{color:var(--acc)}
.pull-progress{height:3px;background:var(--brd2);border-radius:2px;overflow:hidden;margin-top:4px;display:none}
.pull-progress.on{display:block}
.pull-progress .bar{height:100%;background:var(--acc);width:0%;transition:width .2s}
.select-row{display:grid;grid-template-columns:130px 1fr;align-items:center;gap:10px;padding:4px 0;font-family:var(--mono);font-size:11px}
.select-row label{color:var(--txt2)}
.select-row select,.select-row input{background:var(--bg);border:1px solid var(--brd2);color:var(--txt);border-radius:5px;padding:5px 8px;font-family:var(--mono);font-size:11px;outline:none;cursor:pointer}
.select-row input{cursor:text}
.prompt-field textarea{width:100%;min-height:90px;background:var(--bg);border:1px solid var(--brd2);color:var(--txt);border-radius:5px;padding:8px 10px;font-family:var(--mono);font-size:11.5px;line-height:1.55;resize:vertical;outline:none}
.param{display:grid;grid-template-columns:130px 1fr 72px;align-items:center;gap:10px;padding:4px 0;font-family:var(--mono);font-size:11px}
.param label{color:var(--txt2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.param input[type="range"]{-webkit-appearance:none;height:3px;background:var(--brd2);border-radius:2px;outline:none;cursor:pointer}
.param input[type="range"]::-webkit-slider-thumb{-webkit-appearance:none;width:11px;height:11px;border-radius:50%;background:var(--acc);cursor:pointer}
.param .num-input{background:var(--bg);border:1px solid var(--brd2);color:var(--acc);font-family:var(--mono);font-size:11px;border-radius:4px;padding:3px 6px;outline:none;text-align:right;width:100%}
.check-row{display:flex;align-items:center;gap:8px;padding:5px 0;font-family:var(--mono);font-size:11px;color:var(--txt2);cursor:pointer}
.check-row input{-webkit-appearance:none;width:14px;height:14px;border:1px solid var(--brd2);border-radius:3px;cursor:pointer;position:relative;background:var(--bg);flex-shrink:0}
.check-row input:checked{background:var(--acc);border-color:var(--acc)}
.check-row input:checked::after{content:"✓";position:absolute;inset:0;color:#000;font-size:10px;font-weight:bold;display:flex;align-items:center;justify-content:center}
.check-hint{font-family:var(--mono);font-size:10px;color:var(--dim);padding:0 0 4px;line-height:1.5}
.mem-list{display:flex;flex-direction:column;gap:6px}
.mem-card{background:var(--bg);border:1px solid var(--brd2);border-radius:5px;padding:8px 10px}
.mem-card .role{font-family:var(--mono);font-size:10px;color:var(--mut);text-transform:uppercase;margin-bottom:3px;display:flex;justify-content:space-between}
.mem-card .content{color:var(--txt);font-size:12px;line-height:1.5;overflow:hidden;text-overflow:ellipsis;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;white-space:pre-wrap}
.mem-card .actions{display:flex;gap:4px;margin-top:6px;opacity:0}
.mem-card:hover .actions{opacity:1}
.mem-card .actions button{font-family:var(--mono);font-size:10px;padding:2px 7px;border-radius:3px;border:1px solid var(--brd2);background:transparent;color:var(--mut);cursor:pointer}
.facts-area textarea{width:100%;min-height:140px;background:var(--bg);border:1px solid var(--brd2);color:var(--txt);border-radius:5px;padding:10px 12px;font-family:var(--mono);font-size:11.5px;line-height:1.6;resize:vertical;outline:none}
.debug-log{font-family:var(--mono);font-size:10.5px;background:var(--bg);border:1px solid var(--brd2);border-radius:5px;padding:8px 10px;max-height:600px;overflow-y:auto;line-height:1.55}
.dbg-line{display:flex;gap:8px;padding:2px 0;border-bottom:1px solid rgba(255,255,255,0.02)}
.dbg-line .t{color:var(--dim);flex-shrink:0;width:60px}
.dbg-line .k{color:var(--txt2);flex-shrink:0;width:72px;text-transform:uppercase;font-size:9.5px}
.dbg-line .v{color:var(--txt);flex:1;word-break:break-word}
.dbg-line.info .k{color:var(--acc)}.dbg-line.res .k{color:var(--ok)}.dbg-line.err .k{color:var(--err)}
.dbg-empty{color:var(--dim);text-align:center;padding:40px 20px;font-family:var(--mono);font-size:11px}
.modal-bg{position:fixed;inset:0;background:rgba(0,0,0,0.7);opacity:0;pointer-events:none;transition:opacity .22s;z-index:300;display:flex;align-items:center;justify-content:center;padding:30px}
.modal-bg.on{opacity:1;pointer-events:auto}
.modal{background:var(--pnl);border:1px solid var(--brd);border-radius:10px;width:900px;max-width:100%;max-height:100%;display:flex;flex-direction:column;overflow:hidden}
.modal-head{padding:12px 16px;border-bottom:1px solid var(--brd);display:flex;justify-content:space-between;background:var(--pnl2)}
.modal-head h3{font-family:var(--mono);font-size:12.5px;color:var(--txt2);font-weight:500}
.modal-body{flex:1;overflow:hidden;display:grid;grid-template-columns:320px 1fr}
.modal-side{border-right:1px solid var(--brd);overflow-y:auto;padding:12px;background:var(--pnl2)}
.modal-view{position:relative;overflow:hidden;background:#06060a}
.modal-view canvas{display:block;width:100%;height:100%;cursor:grab}
.modal-foot{padding:10px 16px;border-top:1px solid var(--brd);display:flex;gap:8px;justify-content:flex-end;background:var(--pnl2)}
.modal-foot button{font-family:var(--mono);font-size:10.5px;text-transform:uppercase;padding:6px 12px;border-radius:5px;border:1px solid var(--brd2);background:transparent;color:var(--txt2);cursor:pointer}
.modal-foot button.save{background:var(--acc);border-color:var(--acc);color:#000;font-weight:600}
.node-item,.link-item,.chatlink-item{background:var(--bg);border:1px solid var(--brd2);border-radius:5px;padding:6px 8px;margin-bottom:5px;font-family:var(--mono);font-size:11px;display:flex;gap:6px;align-items:center}
.node-item .dot{width:8px;height:8px;border-radius:50%;background:var(--netg);flex-shrink:0}
.node-item input,.link-item input{flex:1;background:transparent;border:none;color:var(--txt);font-family:var(--mono);font-size:11px;outline:none;padding:2px 4px;min-width:0}
.node-item .rm,.link-item .rm{background:none;border:none;color:var(--dim);cursor:pointer;padding:2px}
.node-item .rm:hover,.link-item .rm:hover{color:var(--err)}
.add-row{display:flex;gap:4px;margin-bottom:10px}
.add-row input{flex:1;background:var(--bg);border:1px solid var(--brd2);color:var(--txt);border-radius:4px;padding:5px 8px;font-family:var(--mono);font-size:11px;outline:none}
.add-row button{font-family:var(--mono);font-size:10.5px;padding:0 10px;border-radius:4px;border:1px solid var(--adim);background:transparent;color:var(--acc);cursor:pointer}
.chatlink-item{cursor:pointer}
.chatlink-item input[type="checkbox"]{-webkit-appearance:none;width:14px;height:14px;border:1px solid var(--brd2);border-radius:3px;background:var(--bg);position:relative;cursor:pointer;flex-shrink:0}
.chatlink-item input[type="checkbox"]:checked{background:var(--netg);border-color:var(--netg)}
.chatlink-item input[type="checkbox"]:checked::after{content:"✓";position:absolute;inset:0;color:#000;font-size:10px;font-weight:bold;display:flex;align-items:center;justify-content:center}
.chatlink-item .title{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.search-panel{position:fixed;top:60px;left:50%;transform:translateX(-50%);width:480px;max-width:92vw;background:var(--pnl2);border:1px solid var(--brd);border-radius:8px;z-index:110;display:none;flex-direction:column}
.search-panel.on{display:flex}
.search-panel .sp-head2{padding:10px 12px;border-bottom:1px solid var(--brd);display:flex;gap:8px;align-items:center}
.search-panel input{flex:1;background:var(--bg);border:1px solid var(--brd2);color:var(--txt);border-radius:5px;padding:8px 10px;font-family:var(--mono);font-size:12px;outline:none}
.search-results{max-height:320px;overflow-y:auto;padding:6px}
.search-results .res{padding:8px 10px;border-radius:5px;cursor:pointer;font-size:12px;color:var(--txt2);border-left:2px solid transparent}
.search-results .res:hover{background:var(--pnl3);border-left-color:var(--acc)}
.search-results .res .role{font-family:var(--mono);font-size:10px;text-transform:uppercase;color:var(--mut);display:block;margin-bottom:2px}
.search-results .res mark{background:var(--adim);color:#fff;padding:0 2px;border-radius:2px}

.quality-panel{position:fixed;right:12px;top:52px;width:340px;max-width:calc(100vw - 24px);z-index:95;background:var(--pnl);border:1px solid var(--brd2);border-radius:7px;box-shadow:0 12px 35px rgba(0,0,0,.45);padding:10px;display:none}
.quality-panel.on{display:block}
.quality-head{display:flex;align-items:center;justify-content:space-between;gap:8px;font-family:var(--mono);font-size:11px;color:var(--chart);margin-bottom:7px}
.quality-head button{background:transparent;border:1px solid var(--brd2);border-radius:4px;color:var(--txt2);padding:2px 6px;cursor:pointer}
.quality-summary{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-bottom:7px}
.quality-kpi{border:1px solid var(--brd);background:var(--bg);padding:6px;border-radius:4px;min-width:0}
.quality-kpi span{display:block;font:9px var(--mono);color:var(--mut);text-transform:uppercase}
.quality-kpi b{display:block;font:12px var(--mono);color:var(--txt);margin-top:3px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.quality-canvas{width:100%;height:128px;display:block;background:#08080c;border:1px solid var(--brd);border-radius:4px}
.quality-note{font-size:10px;color:var(--mut);line-height:1.45;margin-top:6px}
.quality-control{display:grid;grid-template-columns:75px 1fr;gap:8px;align-items:center;margin-top:7px;font:10px var(--mono);color:var(--txt2)}
.quality-control select{min-width:0;background:var(--bg);border:1px solid var(--brd2);color:var(--txt);padding:5px;border-radius:4px;font:10px var(--mono)}
.compute-note{font-size:10px;color:var(--mut);line-height:1.5;margin:5px 0}
@media(max-width:720px){.quality-panel{top:48px;right:6px;width:calc(100vw - 12px)}.tb-actions{gap:1px}.tbtn{width:27px;height:28px}}
@media(max-width:900px){.emo-badges{display:none !important}}
@media(max-width:720px){.app{grid-template-columns:1fr}.sidebar{position:absolute;top:0;left:0;bottom:0;z-index:80;width:240px}.sidebar.hidden{margin-left:-240px}
.messages{padding:0 14px}.entry-head,.entry-body,.entry-actions,.edit-area,.think-box,.net-box,.tool-box,.correction-box,.live-think{padding-left:0;margin-left:0}
.entry-check{left:-6px}.panel{width:100%}.param{grid-template-columns:110px 1fr 64px}
.modal-body{grid-template-columns:1fr;grid-template-rows:40% 60%}.modal-side{border-right:none;border-bottom:1px solid var(--brd)}
.chess-board{width:100%;height:auto;aspect-ratio:1}.chess-sq .piece{font-size:5vw}}


/* Плавность интерфейса и адаптация для разных экранов */
html{ -webkit-text-size-adjust:100%; }
body{ overscroll-behavior:none; }
.app{height:100vh;height:100dvh;min-height:0;}
.workspace,.messages{min-height:0;min-width:0;}
.messages{-webkit-overflow-scrolling:touch;scroll-behavior:smooth;overscroll-behavior:contain;}
.entry-body,.entry-head,.entry-actions{min-width:0;}
.entry-body{overflow-wrap:anywhere;word-break:normal;}
.entry-body img,.entry-body video,.entry-body svg,.entry-body canvas{max-width:100%;}
.entry-body pre,.code-block pre{max-width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;}
.md-table{max-width:100%;}
.topbar{overflow-x:auto;overflow-y:hidden;scrollbar-width:none;-webkit-overflow-scrolling:touch;}
.topbar::-webkit-scrollbar{display:none;}
.tb-actions{flex-shrink:0;min-width:max-content;}
.topbar>.iconbtn{flex-shrink:0;}
.chat-title{min-width:70px;}
.composer{padding-bottom:calc(10px + env(safe-area-inset-bottom, 0px));}
.composer textarea{min-width:0;}
.chat-model-select{width:min(310px,42vw)}
.composer .send{flex-shrink:0;touch-action:manipulation;transition:transform .16s ease,background .16s ease,border-color .16s ease,color .16s ease;}
.composer .send:active:not(:disabled){transform:scale(.94);}
.iconbtn,.tbtn,.act,.quick-btn,button{touch-action:manipulation;}
.entry.message-arrive{animation:message-arrive .32s cubic-bezier(.2,.75,.25,1) both}
.entry-body .token-emerge{display:inline;opacity:0;animation:token-emerge .24s cubic-bezier(.18,.72,.22,1) both;will-change:opacity,filter,text-shadow}
@keyframes token-emerge{0%{opacity:0;filter:blur(2.4px);text-shadow:0 0 7px rgba(212,160,74,.30)}45%{opacity:.42;filter:blur(1px);text-shadow:0 0 3px rgba(212,160,74,.13)}100%{opacity:1;filter:blur(0);text-shadow:none}}
@keyframes message-arrive{from{opacity:0;transform:translateY(3px);filter:blur(1px)}to{opacity:1;transform:translateY(0);filter:blur(0)}}
@media (min-width:721px) and (max-width:1100px){
  .app{grid-template-columns:minmax(190px,230px) minmax(0,1fr);}
  .messages{padding-left:clamp(14px,2vw,24px);padding-right:clamp(14px,2vw,24px);}
  .entry.selected{margin-left:calc(-1 * clamp(14px,2vw,24px));margin-right:calc(-1 * clamp(14px,2vw,24px));padding-left:clamp(14px,2vw,24px);padding-right:clamp(14px,2vw,24px);}
}
@media (max-width:720px){
  .app{height:100vh;height:100dvh;grid-template-columns:minmax(0,1fr);}
  .sidebar{width:min(280px,86vw);max-width:86vw;padding-bottom:env(safe-area-inset-bottom,0px);box-shadow:12px 0 32px rgba(0,0,0,.28);}
  .sidebar.hidden{margin-left:-86vw;}
  .topbar{gap:5px;padding-left:7px;padding-right:7px;}
  .chat-title{max-width:32vw;min-width:78px;font-size:11.5px;}
  .tb-actions{gap:2px;}
  .tbtn{width:30px;height:32px;flex:0 0 30px;}
  .messages{padding-left:12px;padding-right:12px;}
  .entry{padding:12px 0;gap:7px;}
  .entry-head{gap:5px;font-size:10px;padding-left:0;}
  .entry-head .meta{width:100%;margin-left:0;}
  .entry-body{padding-left:0;font-size:14px;line-height:1.65;}
  .entry[data-role="user"] .entry-body{padding-left:10px;}
  .entry-actions{opacity:1;padding-left:0;gap:5px;}
  .act{min-height:32px;}
  .composer{gap:7px;padding:8px 8px calc(8px + env(safe-area-inset-bottom,0px));align-items:stretch;}
  .compose-controls{grid-template-columns:minmax(90px,1.15fr) minmax(88px,.9fr) minmax(92px,.95fr);gap:5px;max-width:none;overflow:visible;}
  .compose-control{font-size:9.5px;gap:0;}
  .compose-control>span{display:none;}
  .chat-model-select{width:100%;min-width:0;font-size:10px;padding:7px 5px;}
  .compose-select,.context-trigger{font-size:10px;padding:7px 5px;min-width:0;width:100%;}
  .compose-entry{gap:7px;}
  .composer .cp{padding-bottom:12px;}
  .composer textarea{font-size:16px;line-height:1.45;min-height:42px;max-height:35dvh;padding:10px;}
  .composer .send{width:42px;height:42px;}
  .char-count{right:59px;bottom:3px;font-size:9px;}
  .stats-line{padding:4px 8px 0;text-align:left;}
  .bulk-bar{width:calc(100vw - 20px);max-width:500px;justify-content:center;flex-wrap:wrap;gap:7px;bottom:calc(82px + env(safe-area-inset-bottom,0px));}
  .scroll-btn{right:13px;bottom:calc(112px + env(safe-area-inset-bottom,0px));width:38px;height:38px;}
  .panel{left:0;right:0;width:100vw;max-width:100vw;padding-bottom:env(safe-area-inset-bottom,0px);}
  .search-panel{top:calc(50px + env(safe-area-inset-top,0px));width:calc(100vw - 16px);max-width:calc(100vw - 16px);}
  .quality-panel{top:calc(48px + env(safe-area-inset-top,0px));right:6px;width:calc(100vw - 12px);max-height:calc(100dvh - 60px);overflow-y:auto;}
  .md-table{display:block;width:100%;overflow-x:auto;white-space:nowrap;-webkit-overflow-scrolling:touch;}
  .code-block pre{font-size:11.5px;padding:9px;}
  .blk{padding:9px;}
  .chess-wrap{gap:10px;}
  .chess-info{min-width:0;width:100%;}
  .modal{max-width:calc(100vw - 12px);max-height:calc(100dvh - 12px);}
}
@media (max-width:420px){
  .topbar{gap:4px;}
  .chat-title{max-width:26vw;min-width:62px;font-size:10.5px;padding-left:3px;padding-right:3px;}
  .tbtn{width:28px;height:30px;flex-basis:28px;}
  .sb-head{padding-left:8px;padding-right:8px;}
  .iconbtn{width:30px;height:30px;}
  .messages{padding-left:9px;padding-right:9px;}
  .entry.selected{margin-left:-9px;margin-right:-9px;padding-left:9px;padding-right:9px;}
  .composer .cp{display:none;}
  .composer{gap:6px;}
  .compose-controls{gap:4px;}
  .compose-control>span{display:none;}
  .chat-model-select{width:100%;min-width:0;}
  .compose-select{max-width:105px;}
  .context-trigger{max-width:none;}
  .composer .send{width:40px;height:42px;}
  .quality-summary{grid-template-columns:repeat(3,minmax(0,1fr));}
  .quality-kpi{padding:5px 4px;}
  .quality-kpi span{font-size:8px;}
  .quality-kpi b{font-size:11px;}
}
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{scroll-behavior:auto!important;animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important;}
}

</style>
</head>
<body>
<div class="app">
<aside class="sidebar" id="sidebar">
<div class="sb-head">
<span class="brand"><b>local</b>/ai</span>
<div class="actions">
<button class="iconbtn" id="search-btn" data-tip="поиск"></button>
<button class="iconbtn" id="chatlink-btn" data-tip="связать"></button>
<button class="iconbtn" id="export-chat-btn" data-tip="экспорт"></button>
<button class="iconbtn" id="new-chat-btn" data-tip="новый"></button>
</div></div>
<div class="chat-list" id="chat-list"></div>
<div class="sb-foot">id: <span class="uid" id="uid-display">—</span></div>
</aside>
<div class="workspace">
<header class="topbar">
<button class="iconbtn" id="menu-btn" data-tip="меню"></button>
<div class="chat-title" id="chat-title">новый диалог</div>
<div class="emo-badges" id="emo-badges"></div>
<div class="tb-actions">
<button class="tbtn fast" id="fast-btn" data-tip="быстрый"></button>
<button class="tbtn forms" id="forms-btn" data-tip="формы"></button>
<button class="tbtn raw-prompt" id="raw-prompt-btn" data-tip="чистый промпт: выкл" aria-label="Переключить чистый промпт"></button>
<button class="tbtn animation-toggle" id="animation-btn" data-tip="анимация символов: вкл" aria-label="Отключить анимацию символов" aria-pressed="true"></button>
<button class="tbtn" id="perf-btn" data-tip="производительность"></button>
<button class="tbtn" id="internet-btn" data-tip="интернет"></button>
<button class="tbtn think" id="think-btn" data-tip="мышление"></button>
<button class="tbtn thinkart" id="think-art-btn" data-tip="think*"><span class="badge">*</span></button>
<button class="tbtn tools" id="tools-btn" data-tip="инструменты"></button>
<button class="tbtn g4f" id="g4f-btn" data-tip="g4f"></button>
<button class="tbtn" id="debug-btn" data-tip="отладка"></button>
<button class="tbtn" id="quality-btn" data-tip="метрики модели"></button>
<button class="tbtn" id="settings-btn" data-tip="настройки"></button>
</div></header>
<div class="messages" id="messages"></div>
<div class="stats-line" id="stats"></div>
<footer class="composer">
 <div class="compose-controls" aria-label="Быстрые настройки ответа">
  <label class="compose-control" for="chat-model-select"><span>Модель</span><select id="chat-model-select" class="chat-model-select" aria-label="Установленная модель"><option value="">загрузка моделей…</option></select></label>
  <div class="compose-control context-wrap">
   <button type="button" id="context-trigger" class="context-trigger" aria-expanded="false" aria-controls="context-menu">Контекст: средний ▴</button>
   <div class="context-menu" id="context-menu" role="dialog" aria-label="Размер контекста">
    <div class="cm-title">РАЗМЕР КОНТЕКСТА</div>
    <div class="cm-options">
     <button type="button" class="cm-option" data-context="low">Low · 256</button>
     <button type="button" class="cm-option" data-context="medium">Medium · 4K</button>
     <button type="button" class="cm-option" data-context="high">High · 16K</button>
     <button type="button" class="cm-option" data-context="max">Max · 128K</button>
    </div>
    <div class="cm-note">Max — большой запрошенный предел, а не буквальная бесконечность: фактический контекст зависит от модели, Ollama и доступной памяти.</div>
   </div>
  </div>
  <label class="compose-control" for="temperature-preset"><span>Температура</span><select id="temperature-preset" class="compose-select" aria-label="Температура ответа">
   <option value="low">Low · 0.2</option><option value="medium">Medium · 0.7</option><option value="high">High · 1.2</option><option value="max">Max · 2.0</option>
  </select></label>
  <select id="length-preset" hidden aria-hidden="true" tabindex="-1">
   <option value="low">Коротко</option><option value="medium">Средне</option><option value="high">Длинно</option><option value="max">Максимум</option>
  </select>
 </div>
 <div class="compose-entry">
  <span class="cp">&gt;</span>
  <textarea id="input" rows="1" placeholder=""></textarea>
  <div class="char-count" id="char-count">0</div>
  <button class="send" id="send-btn" type="button"></button>
 </div>
</footer>
</div></div>
<div class="search-panel" id="search-panel"><div class="sp-head2"><input type="text" id="search-input" placeholder="поиск…"><span id="search-count" style="font-family:var(--mono);font-size:11px;color:var(--dim)">0</span></div><div class="search-results" id="search-results"></div></div>
<div class="bulk-bar" id="bulk-bar"><span>выделено: <span class="count" id="bulk-count">0</span></span><button class="act" id="bulk-save">сохранить</button><button class="act" id="bulk-copy">копировать</button><button class="act" id="bulk-del">удалить</button><button class="act" id="bulk-clear">снять</button></div>
<button class="scroll-btn" id="scroll-btn"></button>
<div class="quality-panel" id="quality-panel" aria-label="Метрики модели">
<div class="quality-head"><span>МЕТРИКИ / МОДЕЛЬ</span><button type="button" id="quality-close">×</button></div>
<div class="quality-summary"><div class="quality-kpi"><span>ОЗУ занято</span><b id="quality-ram">—</b></div><div class="quality-kpi"><span>посл. скорость</span><b id="quality-speed">—</b></div><div class="quality-kpi"><span>оценки 👍</span><b id="quality-score">—</b></div></div>
<canvas class="quality-canvas" id="quality-canvas" width="640" height="240"></canvas>
<div class="quality-control"><label for="quality-series">график</label><select id="quality-series"><option value="rating">оценка ответов, %</option><option value="speed">скорость, токенов/с</option><option value="latency">время ответа, с</option><option value="ram">использование ОЗУ, %</option></select></div>
<div class="quality-note" id="quality-note">Оценка рассчитывается по 👍/👎, а не является независимым benchmark accuracy. Для измерения точности нужен фиксированный тестовый набор.</div>
</div>
<div class="overlay" id="overlay"></div>
<aside class="panel" id="panel">
<div class="panel-head"><span class="pt" id="panel-title"></span><button class="iconbtn" id="panel-close"></button></div>
<div class="panel-tabs">
<button class="ptab active" data-tab="settings">настройки</button>
<button class="ptab" data-tab="mood">эмоции</button>
<button class="ptab" data-tab="memory">память</button>
<button class="ptab" data-tab="debug">отладка</button>
</div>
<div class="panel-body">
<div class="tab" data-tab="settings">
<div class="group"><div class="group-t">бот</div>
<div class="select-row"><label for="bot-name">имя бота</label><input type="text" id="bot-name" placeholder="Ассистент"></div>
<label class="check-row"><input type="checkbox" id="bot-name-enabled"> сообщать имя</label></div>
<div class="group"><div class="group-t">режимы</div>
<label class="check-row"><input type="checkbox" id="fast-cb"> быстрый ответ</label>
<label class="check-row"><input type="checkbox" id="forms-cb"> текстовые формы</label></div>
<div class="group"><div class="group-t">g4f подмога</div>
<label class="check-row"><input type="checkbox" id="g4f-cb"> разрешить</label>
<div class="select-row"><label for="g4f-mode">режим</label><select id="g4f-mode"><option value="off">выкл</option><option value="auto">авто</option><option value="manual">ручной</option></select></div></div>
<div class="group"><div class="group-t">мышление</div>
<label class="check-row"><input type="checkbox" id="think-native-cb"> нативное</label>
<label class="check-row"><input type="checkbox" id="think-art-cb"> искусственное</label></div>
<div class="group"><div class="group-t">инструменты</div>
<label class="check-row"><input type="checkbox" id="tools-cb"> инструменты</label>
<label class="check-row"><input type="checkbox" id="auto-math-cb"> авто-математика</label></div>
<div class="group"><div class="group-t">производительность</div>
<div class="perf-picker" id="perf-picker"><button data-mode="low">низкий</button><button data-mode="medium">средний</button><button data-mode="high">высокий</button></div>
<div class="perf-note" id="perf-note"></div>
<button class="diag-btn" id="diag-btn">проверить gpu</button>
<div class="diag-box" id="diag-box" style="display:none"></div></div>
<div class="group"><div class="group-t">хранилище</div>
<div class="storage-box">
<div class="row"><span class="lbl">путь</span><span class="val" id="storage-path">—</span></div>
<div class="row"><span class="lbl">занято</span><span class="val accent" id="storage-size">—</span></div>
<div class="row"><span class="lbl">свободно</span><span class="val ok" id="storage-free">—</span></div>
<div class="storage-bar"><div class="fill" id="storage-fill" style="width:0%"></div></div></div>
<div class="move-row"><input type="text" id="move-target" placeholder="/home/mint/ollama_models"><button class="act" id="storage-refresh">обн</button><button class="act" id="storage-move">перенести</button></div></div>
<div class="group"><div class="group-t">пользователь</div>
<div class="uid-display"><span>id:</span><span class="id" id="uid-field">—</span><button class="act" id="uid-copy">копировать</button><button class="act" id="uid-reset">сменить</button></div></div>
<div class="group"><div class="group-t">поведение</div>
<label class="check-row"><input type="checkbox" id="auto-translate"> автоперевод</label>
<div class="select-row"><label for="target-lang">язык</label><select id="target-lang"><option value="auto">авто</option><option value="ru">русский</option><option value="en">английский</option><option value="de">немецкий</option><option value="fr">французский</option><option value="es">испанский</option><option value="zh">китайский</option><option value="ja">японский</option></select></div>
<label class="check-row"><input type="checkbox" id="fix-typos"> исправление</label>
<label class="check-row"><input type="checkbox" id="show-net-log"> действия в сети</label>
<label class="check-row"><input type="checkbox" id="save-draft"> черновик</label>
<label class="check-row"><input type="checkbox" id="stream-think"> live размышления</label>
<div class="select-row"><label for="net-mode">интернет</label><select id="net-mode"><option value="off">выкл</option><option value="auto">авто</option><option value="on">всегда</option></select></div></div>
<div class="group"><div class="group-t">модель</div>
<div class="model-picker"><select class="model-select" id="model-select"></select>
<div class="model-actions"><button id="model-refresh">обновить</button><button class="primary" id="model-pull" disabled>скачать</button><button class="danger" id="model-delete" disabled>удалить</button></div>
<div class="model-status" id="model-status"></div>
<div class="pull-progress" id="pull-progress"><div class="bar" id="pull-bar"></div></div></div></div>
<div class="group"><div class="group-t">ускоритель и квантизация</div>
<div class="select-row"><label for="compute-device">вычисления</label><select id="compute-device"><option value="xpu">XPU · Intel Arc</option><option value="cpu">CPU</option><option value="npu">NPU · OpenVINO</option></select></div>
<div class="select-row"><label for="quantization-select">точность весов</label><select id="quantization-select"><option value="auto">авто · как у модели</option><option value="Q2_K">INT2 · Q2_K</option><option value="Q3_K_M">INT3 · Q3_K_M</option><option value="Q4_K_M">INT4 · Q4_K_M</option><option value="Q5_K_M">INT5 · Q5_K_M</option><option value="Q8_0">INT8 · Q8_0</option><option value="F16">16 бит · F16</option></select></div>
<div class="compute-note" id="compute-note">XPU использует модель, установленную в Ollama; контейнер должен иметь доступ к /dev/dri.</div>
<div class="compute-note" id="memory-estimate">Оценка памяти появится после выбора модели.</div></div>
<div class="group"><div class="group-t">системный промпт</div>
<div class="prompt-field"><textarea id="sys-prompt"></textarea></div></div>
<div class="group" id="group-basic"><div class="group-t">основные</div></div>
<div class="group" id="group-sampling"><div class="group-t">сэмплирование</div></div>
<div class="group" id="group-mirostat"><div class="group-t">mirostat</div></div>
<div class="group" id="group-perf"><div class="group-t">производительность</div>
<div class="param"><label for="p_num_gpu_percent">gpu %</label>
<input type="range" id="p_num_gpu_percent" min="0" max="100" step="1" value="100">
<input type="number" id="n_num_gpu_percent" min="0" max="100" step="1" value="100" class="num-input"></div></div>
<div class="group"><div class="group-t">обратная связь</div>
<label class="check-row"><input type="checkbox" id="fb-enabled"> учитывать</label>
<div id="group-fb-extra"></div></div>
</div>
<div class="tab" data-tab="mood" style="display:none">
<div class="group"><div class="group-t">16 эмоций · меняются по ходу чата</div>
<div class="check-hint" style="margin-bottom:8px">Эмоции автоматически меняются от оценок 👍/👎, от тона ваших сообщений (вежливость, грубость, флирт, вопросы) и постепенно затухают к базовым значениям. Можно подправить руками.</div>
<div id="mood-scales"></div>
<div class="model-actions" style="margin-top:10px"><button class="primary" id="mood-save">сохранить</button><button id="mood-reset">сброс</button></div>
<div class="check-hint" id="mood-status"></div></div>
</div>
<div class="tab" data-tab="memory" style="display:none">
<div class="group"><div class="group-t">мои факты</div>
<div class="facts-area"><textarea id="facts-text" placeholder="Меня зовут..."></textarea></div>
<label class="check-row" style="margin-top:8px"><input type="checkbox" id="facts-enabled"> передавать</label>
<div class="model-actions" style="margin-top:8px"><button class="primary" id="facts-save">сохранить</button><button id="facts-clear">очистить</button></div>
<div class="check-hint" id="facts-status"></div></div>
<div class="group"><div class="group-t">сохранённые</div><div class="mem-list" id="mem-list"></div></div>
</div>
<div class="tab" data-tab="debug" style="display:none">
<div class="group"><div class="group-t">лог</div>
<div class="model-actions" style="margin-bottom:8px"><button id="debug-clear">очистить</button><button id="debug-export">скачать</button></div>
<div class="debug-log" id="debug-log"><div class="dbg-empty">—</div></div></div>
</div>
</div></aside>
<div class="modal-bg" id="graph-modal">
<div class="modal">
<div class="modal-head"><h3>редактор</h3><button class="iconbtn" id="modal-close"></button></div>
<div class="modal-body">
<div class="modal-side">
<div class="group" style="margin-top:0"><div class="group-t">узлы</div>
<div class="add-row"><input type="text" id="add-node-input" placeholder="узел"><button id="add-node-btn">+</button></div>
<div id="nodes-list"></div></div>
<div class="group"><div class="group-t">связи</div>
<div class="add-row" style="flex-wrap:wrap;gap:4px"><input type="text" id="add-link-from" placeholder="от" style="max-width:32%"><input type="text" id="add-link-to" placeholder="к" style="max-width:32%"><input type="text" id="add-link-label" placeholder="метка" style="max-width:32%"><button id="add-link-btn">+</button></div>
<div id="links-list"></div></div>
</div>
<div class="modal-view"><canvas id="modal-canvas"></canvas></div></div>
<div class="modal-foot"><button id="modal-cancel">отмена</button><button class="save" id="modal-save">сохранить</button></div>
</div></div>
<div class="modal-bg" id="chatlink-modal">
<div class="modal" style="width:500px">
<div class="modal-head"><h3>связывание чатов</h3><button class="iconbtn" id="chatlink-close"></button></div>
<div class="modal-body" style="grid-template-columns:1fr">
<div class="modal-side" style="border:none;background:transparent">
<div class="check-hint" style="margin-bottom:10px">Отметьте чаты, контекст которых учитывать.</div>
<div id="chatlink-list"></div>
</div></div>
<div class="modal-foot"><button id="chatlink-cancel">закрыть</button><button class="save" id="chatlink-save">сохранить</button></div>
</div></div>
<script>
const ICO={
menu:'<line x1="3" y1="7" x2="21" y2="7"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="17" x2="21" y2="17"/>',
search:'<circle cx="11" cy="11" r="6.5"/><line x1="16" y1="16" x2="21" y2="21"/>',
download:'<path d="M12 3v11"/><polyline points="7 10 12 15 17 10"/><line x1="4" y1="20" x2="20" y2="20"/>',
plus:'<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
close:'<line x1="5" y1="5" x2="19" y2="19"/><line x1="19" y1="5" x2="5" y2="19"/>',
gear:'<circle cx="12" cy="12" r="3"/><path d="M12 2v2.5M12 19.5V22M4.2 4.2l1.8 1.8M18 18l1.8 1.8M2 12h2.5M19.5 12H22M4.2 19.8L6 18M18 6l1.8-1.8"/>',
bolt:'<path d="M13 2L5 13h6l-1 9 8-11h-6l1-9z"/>',
globe:'<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><line x1="3" y1="12" x2="21" y2="12"/>',
brain:'<path d="M9 4.5a3.5 3.5 0 0 0-3.5 3.5c0 .8-.5 1.4-1 2-.8.8-.8 2.2 0 3 .5.6 1 1.2 1 2a3.5 3.5 0 0 0 3.5 3.5h.5V4.5H9z"/><path d="M15 4.5a3.5 3.5 0 0 1 3.5 3.5c0 .8.5 1.4 1 2 .8.8.8 2.2 0 3-.5.6-1 1.2-1 2a3.5 3.5 0 0 1-3.5 3.5H14.5V4.5H15z"/>',
brainStar:'<path d="M9 6.5a3 3 0 0 0-3 3c0 .7-.4 1.2-.9 1.7-.7.7-.7 1.9 0 2.6.5.5.9 1 .9 1.7a3 3 0 0 0 3 3h.5V6.5H9z"/><path d="M15 6.5a3 3 0 0 1 3 3c0 .7.4 1.2.9 1.7.7.7.7 1.9 0 2.6-.5.5-.9 1-.9 1.7a3 3 0 0 1-3 3h-.5V6.5H15z"/><path d="M18 2l.7 1.8L20.5 4.5l-1.8.7L18 7l-.7-1.8L15.5 4.5l1.8-.7z"/>',
wrench:'<path d="M14.7 6.3a4 4 0 0 1-5.4 5.4L4 17v3h3l5.3-5.3a4 4 0 0 1 5.4-5.4l-2.4 2.4-1.6-1.6 2.4-2.4z"/>',
arrowUp:'<line x1="12" y1="20" x2="12" y2="4"/><polyline points="6 10 12 4 18 10"/>',
down:'<line x1="12" y1="4" x2="12" y2="20"/><polyline points="6 14 12 20 18 14"/>',
stop:'<rect x="6" y="6" width="12" height="12" rx="1"/>',
copy:'<rect x="9" y="9" width="11" height="11" rx="1.5"/><path d="M15 5H5a1 1 0 0 0-1 1v10"/>',
edit:'<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>',
trash:'<path d="M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2M6 6l1 14a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-14"/>',
bookmark:'<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>',
thumbUp:'<path d="M12 4l6 6h-4v10h-4V10H6z"/>',
thumbDown:'<path d="M12 20l-6-6h4V4h4v10h4z"/>',
refresh:'<path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><polyline points="21 3 21 8 16 8"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/><polyline points="3 21 3 16 8 16"/>',
cont:'<line x1="4" y1="12" x2="18" y2="12"/><polyline points="13 6 19 12 13 18"/>',
chart:'<line x1="4" y1="20" x2="20" y2="20"/><rect x="6" y="13" width="3" height="7"/><rect x="11" y="9" width="3" height="11"/><rect x="16" y="15" width="3" height="5"/>',
graph:'<line x1="3" y1="21" x2="21" y2="21"/><line x1="3" y1="3" x2="3" y2="21"/><path d="M4 17 Q 8 6, 12 12 T 20 5"/>',
cube:'<path d="M12 2l9 5v10l-9 5-9-5V7z"/><path d="M12 12l9-5M12 12v10M12 12L3 7"/>',
net:'<circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="8" r="2.5"/><circle cx="12" cy="18" r="2.5"/><line x1="8" y1="7" x2="16" y2="7.7"/><line x1="7" y1="8" x2="11" y2="16"/><line x1="17" y1="10" x2="13" y2="16"/>',
tree:'<line x1="4" y1="4" x2="4" y2="20"/><circle cx="4" cy="4" r="1.5"/><circle cx="14" cy="4" r="1.5"/><circle cx="14" cy="12" r="1.5"/><line x1="4" y1="4" x2="12" y2="4"/><line x1="4" y1="12" x2="12" y2="12"/>',
kanban:'<rect x="3" y="4" width="6" height="16" rx="1"/><rect x="10" y="4" width="6" height="10" rx="1"/><rect x="17" y="4" width="4" height="13" rx="1"/>',
timeline:'<circle cx="6" cy="6" r="2"/><circle cx="6" cy="12" r="2"/><circle cx="6" cy="18" r="2"/><line x1="6" y1="6" x2="20" y2="6"/><line x1="6" y1="12" x2="20" y2="12"/><line x1="6" y1="18" x2="20" y2="18"/>',
process:'<rect x="3" y="9" width="5" height="6" rx="1"/><rect x="10" y="9" width="5" height="6" rx="1"/><rect x="17" y="9" width="4" height="6" rx="1"/>',
metrics:'<rect x="4" y="4" width="16" height="16" rx="2"/><line x1="8" y1="10" x2="8" y2="16"/><line x1="12" y1="7" x2="12" y2="16"/>',
checklist:'<rect x="4" y="4" width="16" height="16" rx="2"/><polyline points="8 12 11 15 16 8"/>',
filetree:'<path d="M3 6a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
matrix:'<rect x="4" y="4" width="16" height="16" rx="2"/><line x1="4" y1="9" x2="20" y2="9"/><line x1="4" y1="14" x2="20" y2="14"/><line x1="9" y1="4" x2="9" y2="20"/><line x1="15" y1="4" x2="15" y2="20"/>',
callout:'<circle cx="12" cy="12" r="9"/><line x1="12" y1="8" x2="12" y2="13"/><circle cx="12" cy="16.5" r="0.5" fill="currentColor"/>',
quote:'<path d="M7 7h4v4c0 3-1 4-4 4v-2c1 0 2-1 2-2H7zM15 7h4v4c0 3-1 4-4 4v-2c1 0 2-1 2-2h-2z"/>',
math:'<line x1="5" y1="9" x2="11" y2="9"/><line x1="8" y1="6" x2="8" y2="12"/><line x1="14" y1="9" x2="20" y2="9"/><line x1="5" y1="16" x2="11" y2="16"/><line x1="14" y1="16" x2="20" y2="16"/>',
shape:'<circle cx="12" cy="12" r="8"/><line x1="12" y1="4" x2="12" y2="20"/><line x1="4" y1="12" x2="20" y2="12"/>',
aero:'<path d="M3 12h4l2-4 4 8 3-6 3 2h2"/>',
chess:'<rect x="4" y="4" width="16" height="16" rx="1"/><line x1="4" y1="9" x2="20" y2="9"/><line x1="4" y1="15" x2="20" y2="15"/><line x1="9" y1="4" x2="9" y2="20"/><line x1="15" y1="4" x2="15" y2="20"/>',
fast:'<path d="M13 2L5 13h6l-1 9 8-11h-6l1-9z"/>',
g4f:'<circle cx="12" cy="12" r="9"/><path d="M12 3v18M3 12h18"/><circle cx="12" cy="12" r="4"/>',
link:'<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
forms:'<line x1="4" y1="6" x2="20" y2="6"/><line x1="4" y1="12" x2="14" y2="12"/><line x1="4" y1="18" x2="18" y2="18"/>',
raw:'<polyline points="8 7 3 12 8 17"/><polyline points="16 7 21 12 16 17"/><line x1="14" y1="4" x2="10" y2="20"/>',
fade:'<circle cx="12" cy="12" r="9" opacity=".35"/><path d="M4 15c3-1 4-5 8-5s5 4 8 5"/><path d="M7 18h10" opacity=".6"'
};
function ic(n,c){c=c||'';return '<svg class="ic '+c+'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'+(ICO[n]||'')+'</svg>'}
function setIcon(el,n){if(!el)return;const b=el.querySelectorAll('.badge');const k=[];b.forEach(function(x){k.push(x.outerHTML)});el.innerHTML=ic(n,'lg')+k.join('')}
const $=function(id){return document.getElementById(id)};

const MOOD_SCALES=[
{id:'love',label:'любовь',icon:'♥',def:50},
{id:'hate',label:'ненависть',icon:'✖',def:10},
{id:'fear',label:'страх',icon:'△',def:15},
{id:'flirt',label:'флирт',icon:'♦',def:20},
{id:'joy',label:'радость',icon:'☺',def:55},
{id:'sadness',label:'грусть',icon:'☂',def:15},
{id:'anger',label:'злость',icon:'!',def:10},
{id:'calm',label:'спокойствие',icon:'~',def:60},
{id:'trust',label:'доверие',icon:'✓',def:50},
{id:'suspicion',label:'подозрение',icon:'?',def:20},
{id:'interest',label:'интерес',icon:'◉',def:60},
{id:'boredom',label:'скука',icon:'…',def:20},
{id:'respect',label:'уважение',icon:'★',def:55},
{id:'contempt',label:'презрение',icon:'▽',def:8},
{id:'gratitude',label:'благодарность',icon:'✿',def:50},
{id:'resentment',label:'обида',icon:'†',def:8}];

function buildMoodInstruction(mood){
if(!mood)return '';
const sorted=MOOD_SCALES.slice().sort(function(a,b){return (mood[b.id]||50)-(mood[a.id]||50)});
const top=sorted.slice(0,4).filter(function(s){return (mood[s.id]||50)>55});
const bottom=sorted.slice(-3).filter(function(s){return (mood[s.id]||50)<45});
if(!top.length&&!bottom.length)return '';
const parts=[];
if(top.length)parts.push('Преобладающие чувства: '+top.map(function(s){return s.label+' ('+mood[s.id]+')'}).join(', '));
if(bottom.length)parts.push('Подавленные: '+bottom.map(function(s){return s.label+' ('+mood[s.id]+')'}).join(', '));
return "\n\nТвоё текущее эмоциональное состояние по отношению к пользователю и разговору: "+parts.join('. ')+". Отражай это в тоне, но не объявляй явно.";
}

function clampEmo(v){return Math.max(0,Math.min(100,Math.round(v)))}
let lastDecayTime=Date.now();

function updateEmotions(deltas){
for(const k in deltas){
if(mood[k]===undefined)mood[k]=50;
mood[k]=clampEmo(mood[k]+deltas[k]);
}
save(sk('mood'),mood);
updateEmoBadges();
}

function decayEmotions(){
const now=Date.now();
const elapsed=(now-lastDecayTime)/1000;
if(elapsed<30)return;
lastDecayTime=now;
for(const s of MOOD_SCALES){
const cur=mood[s.id]!==undefined?mood[s.id]:s.def;
const target=s.def;
const step=(target-cur)*0.02;
mood[s.id]=clampEmo(cur+step);
}
save(sk('mood'),mood);
updateEmoBadges();
}

function analyzeUserMessage(text){
if(!text)return {};
const t=text.toLowerCase();
const d={};
function add(k,v){d[k]=(d[k]||0)+v}
if(/\b(спасибо|благодарю|пасиб|спс)\b/.test(t)){add('gratitude',4);add('joy',2);add('love',2);add('trust',1)}
if(/\b(привет|здравствуй|хай|доброе утро|добрый день|добрый вечер)\b/.test(t)){add('joy',1);add('interest',1);add('trust',1)}
if(/\b(пожалуйста|будь добр|будь любезен)\b/.test(t)){add('gratitude',1);add('love',1)}
if(/\b(молодец|умница|хорошо|отлично|класс|супер|круто|нравится)\b/.test(t)){add('joy',3);add('respect',2);add('love',2);add('trust',1)}
if(/\b(люблю|обожаю|ты лучший|ты лучшая)\b/.test(t)){add('love',5);add('joy',3);add('trust',2);add('flirt',1);add('hate',-3)}
if(/\b(милый|милая|красив|секси|обаятельн|умняшка|зайка|котенок|солнышко)\b/.test(t)){add('flirt',4);add('love',3);add('joy',2)}
if(/\b(поцелуй|обнимаю|скучаю|скучал|скучала)\b/.test(t)){add('love',4);add('flirt',3);add('joy',2)}
if(/\b(дурак|дура|тупой|тупая|идиот|кретин|дебил|придурок)\b/.test(t)){add('hate',5);add('anger',4);add('contempt',3);add('love',-4);add('trust',-3);add('joy',-2)}
if(/\b(ненавижу|отвратительн|мерзк|гнусн|противн)\b/.test(t)){add('hate',6);add('anger',4);add('love',-5);add('joy',-3)}
if(/\b(заткнись|замолчи|отстань|отойди|уйди)\b/.test(t)){add('anger',4);add('resentment',3);add('hate',3);add('love',-3);add('joy',-2)}
if(/\b(надоел|надоела|достал|достала|утомил)\b/.test(t)){add('boredom',4);add('resentment',3);add('interest',-3);add('joy',-2)}
if(/\b(ничтожество|жалк|презираю|убог|позор)\b/.test(t)){add('contempt',5);add('hate',3);add('anger',3);add('respect',-4);add('love',-3)}
if(/\b(бред|чушь|глупость|ерунда|фигня|хрень)\b/.test(t)){add('contempt',3);add('anger',2);add('trust',-2);add('respect',-2)}
if(/[!?]{3,}/.test(text)&&text===text.toUpperCase()){add('anger',2);add('fear',1);add('joy',-2)}
if(/\b(боюсь|страшно|ужас|паника|тревога|нервничаю)\b/.test(t)){add('fear',5);add('suspicion',2);add('calm',-3);add('joy',-2)}
if(/\b(расскажи|объясни|покажи|научи|интересно|а что|а как|а почему)\b/.test(t)){add('interest',3);add('boredom',-3);add('joy',1)}
if(/\?/.test(text)){add('interest',1);add('boredom',-1)}
if(/\b(скучно|неинтересно|уныл|тосклив)\b/.test(t)){add('boredom',4);add('interest',-3);add('joy',-2);add('resentment',1)}
if(/\b(прости|извини|сори|сорри|извиняюсь)\b/.test(t)){add('love',2);add('trust',2);add('resentment',-3);add('hate',-2);add('anger',-2)}
if(/\b(убью|уничтожу|сотру|раздавлю|прикончу)\b/.test(t)){add('fear',4);add('hate',4);add('anger',3);add('love',-3)}
if(/\b(уважаю|восхищаюсь|вы лучший|вы гений|вы умн)\b/.test(t)){add('respect',4);add('love',2);add('joy',2);add('trust',1)}
return d;
}

function analyzeAssistantMessage(text){
if(!text)return {};
const t=text.toLowerCase();
const d={};
function add(k,v){d[k]=(d[k]||0)+v}
if(/\b(дурак|тупой|идиот|ненавижу)\b/.test(t)){add('anger',2);add('hate',2);add('love',-1)}
if(/\b(извин|прошу прощения|не могу|ошиб)\b/.test(t)){add('trust',1);add('calm',1)}
return d;
}

const PERF={low:{label:'низкий',num_thread:4,num_gpu_percent:40,num_batch:128,num_ctx:2048,num_predict:1024,note:'Экономия'},
medium:{label:'средний',num_thread:10,num_gpu_percent:75,num_batch:512,num_ctx:8192,num_predict:4096,note:'Гибрид'},
high:{label:'высокий',num_thread:16,num_gpu_percent:100,num_batch:1024,num_ctx:16384,num_predict:8192,note:'Максимум'}};
const FAST={num_thread:16,num_gpu_percent:100,num_batch:512,num_ctx:4096,num_predict:2048,temperature:0.3};
// Quick controls in the composer. Context is a requested limit, not truly unlimited.
const CONTEXT_PRESETS={low:{value:256,label:'низкий'},medium:{value:4096,label:'средний'},high:{value:16384,label:'высокий'},max:{value:131072,label:'максимум'}};
const TEMPERATURE_PRESETS={low:{value:0.2,label:'Low · 0.2'},medium:{value:0.7,label:'Medium · 0.7'},high:{value:1.2,label:'High · 1.2'},max:{value:2.0,label:'Max · 2.0'}};
const LENGTH_PRESETS={low:{value:512,label:'Коротко'},medium:{value:2048,label:'Средне'},high:{value:4096,label:'Длинно'},max:{value:8192,label:'Максимум'}};
const PARAMS=[
{k:'temperature',l:'temperature',g:'basic',t:'range',min:0,max:2,step:0.05,d:0.6},
{k:'num_predict',l:'num_predict',g:'basic',t:'range',min:64,max:16384,step:64,d:4096},
{k:'num_ctx',l:'num_ctx',g:'basic',t:'range',min:512,max:32768,step:512,d:8192},
{k:'num_thread',l:'num_thread',g:'basic',t:'range',min:1,max:32,step:1,d:12},
{k:'thinking_time_limit',l:'think_timeout',g:'basic',t:'range',min:0,max:600,step:5,d:180},
{k:'top_k',l:'top_k',g:'sampling',t:'range',min:0,max:200,step:1,d:40},
{k:'top_p',l:'top_p',g:'sampling',t:'range',min:0,max:1,step:0.01,d:0.9},
{k:'repeat_penalty',l:'repeat_penalty',g:'sampling',t:'range',min:1,max:2,step:0.05,d:1.15},
{k:'repeat_last_n',l:'repeat_last_n',g:'sampling',t:'range',min:0,max:4096,step:8,d:256},
{k:'seed',l:'seed',g:'sampling',t:'range',min:0,max:1000000,step:1,d:0},
{k:'mirostat',l:'mirostat',g:'mirostat',t:'range',min:0,max:2,step:1,d:0},
{k:'num_batch',l:'num_batch',g:'perf',t:'range',min:1,max:4096,step:1,d:512}];
const DEF={system_prompt:"Ты — полезный помощник. Отвечай по делу, без клише.",feedback_enabled:true,feedback_max:3,
model:'huihui_ai/qwen3-abliterated:4b',quantization:'auto',compute_device:'xpu',auto_translate:false,target_lang:'auto',fix_typos:true,
show_net_log:true,net_mode:'auto',perf_mode:'medium',save_draft:true,num_gpu_percent:75,tools:false,
stream_think:true,auto_math:true,facts_enabled:true,forms_enabled:true,fast_mode:false,
bot_name:"Ассистент",bot_name_enabled:false,g4f_enabled:false,g4f_mode:'off',context_mode:'medium',temperature_mode:'medium',length_mode:'medium'};
for(const p of PARAMS)DEF[p.k]=p.d;

const UID=(function(){let id=localStorage.getItem('ai_uid');if(!id){id='u'+Date.now().toString(36)+Math.random().toString(36).slice(2,6);localStorage.setItem('ai_uid',id)}return id})();
function sk(k){return 'ai_'+UID+'_'+k}
const messagesEl=$('messages'),inputEl=$('input'),sendBtn=$('send-btn'),statsEl=$('stats');
const sidebar=$('sidebar'),chatListEl=$('chat-list'),chatTitleEl=$('chat-title');
const panelEl=$('panel'),overlay=$('overlay'),scrollBtn=$('scroll-btn');
const charCount=$('char-count'),bulkBar=$('bulk-bar'),bulkCount=$('bulk-count');
const searchPanel=$('search-panel'),debugLog=$('debug-log'),graphModal=$('graph-modal'),chatlinkModal=$('chatlink-modal');

let settings=load(sk('settings'),Object.assign({},DEF));
let internetMode=loadStr(sk('net_mode'),'auto');
let perfMode=loadStr(sk('perf_mode'),'medium');
let thinkOn=loadBool(sk('think_on'),false);
let thinkArtOn=loadBool(sk('think_art_on'),false);
let toolsOn=loadBool(sk('tools_on'),false);
let autoMath=loadBool(sk('auto_math'),true);
let formsOn=loadBool(sk('forms_on'),true);
let rawPromptMode=loadBool(sk('raw_prompt_mode'),false);
let textAnimationOn=loadBool(sk('text_animation'),true);
let fastMode=loadBool(sk('fast_mode'),false);
let translateOn=loadBool(sk('translate_on'),false);
let fixOn=loadBool(sk('fix_on'),true);
let streamThink=loadBool(sk('stream_think'),true);
let g4fOn=loadBool(sk('g4f_on'),false);
let mood=loadArr(sk('mood'),defaultMood());
let chats=loadArr(sk('chats'),[]);
let savedMessages=loadArr(sk('saved'),[]);
let facts=loadStr(sk('facts'),'');
let factsEnabled=loadBool(sk('facts_enabled'),true);
let activeId=null,busy=false,abortCtrl=null,autoScroll=true;
let selectedIds=new Set(),modelList=[];
let liveTimer=null,liveTokens=0,liveThinkStart=0,liveThinkEnd=0,liveStage='';
let dbgEvents=[],currentPanelTab='settings';
let editingChatLinks=[];
const view3dState=new WeakMap();
if(thinkOn&&thinkArtOn)thinkArtOn=false;

function defaultMood(){const m={};for(const s of MOOD_SCALES)m[s.id]=s.def;return m}
function load(k,d){try{const v=localStorage.getItem(k);if(v)return Object.assign({},d,JSON.parse(v))}catch(e){}return Object.assign({},d)}
function loadArr(k,d){try{const v=localStorage.getItem(k);if(v)return JSON.parse(v)}catch(e){}return d}
function loadStr(k,d){const v=localStorage.getItem(k);return v===null?d:v}
function loadBool(k,d){const v=localStorage.getItem(k);return v===null?d:v==='1'}
function save(k,v){localStorage.setItem(k,JSON.stringify(v))}
function saveStr(k,v){localStorage.setItem(k,v)}
function saveBool(k,v){localStorage.setItem(k,v?'1':'0')}
function uid(){return Date.now().toString(36)+Math.random().toString(36).slice(2,6)}
function getMetricHistory(){return loadArr(sk('metric_history'),[])}
function addMetricPoint(point){const h=getMetricHistory();h.push(Object.assign({ts:Date.now()},point||{}));save(sk('metric_history'),h.slice(-100));updateQualityPanel()}
function selectedQuant(){return $('quantization-select')?$('quantization-select').value:(settings.quantization||'auto')}
function selectedDevice(){return $('compute-device')?$('compute-device').value:(settings.compute_device||'xpu')}
function mapQuantizedModel(model,q){
if(!model||!q||q==='auto')return model;
const tag=({Q2_K:'q2_K',Q3_K_M:'q3_K_M',Q4_K_M:'q4_K_M',Q5_K_M:'q5_K_M',Q8_0:'q8_0',F16:'fp16'})[q];if(!tag)return model;
const m=model.toLowerCase();
if(m.startsWith('mixtral:')&&(/8x7b/.test(m)||['mixtral:latest','mixtral:instruct','mixtral:text'].includes(m)))return 'mixtral:8x7b-instruct-v0.1-'+tag;
if(m.startsWith('qwen2.5:')&&(/32b/.test(m)||m==='qwen2.5:latest'))return 'qwen2.5:32b-instruct-'+tag;
return model;
}
function updateComputeNote(){
const dev=selectedDevice(),q=selectedQuant(),model=$('model-select')&&$('model-select').value||settings.model||'';
const note=$('compute-note');if(note){
if(dev==='cpu')note.textContent='CPU: предсказуемый режим без GPU. Для 32B–47B будет значительно медленнее.';
else if(dev==='xpu')note.textContent='XPU: Ollama должен работать в контейнере с доступом к /dev/dri и Vulkan. Выбор здесь задаёт режим запроса, но не устанавливает драйверы.';
else note.textContent='NPU: нужен openvino-genai и каталог модели из OPENVINO_MODEL_PATH. Для NPU квантизация уже задаётся при экспорте; этот список относится к тегам Ollama.';
}
const est=$('memory-estimate');if(!est)return;
const map={
'mixtral:8x7b':{'Q2_K':'≈17 ГБ весов','Q3_K_M':'≈23 ГБ весов','Q4_K_M':'≈28 ГБ весов','Q5_K_M':'≈33 ГБ весов','Q8_0':'≈50 ГБ весов','F16':'≈93 ГБ весов'},
'qwen2.5:32b':{'Q2_K':'≈12 ГБ весов','Q3_K_M':'≈16 ГБ весов','Q4_K_M':'≈20 ГБ весов','Q5_K_M':'≈23 ГБ весов','Q8_0':'≈35 ГБ весов','F16':'≈66 ГБ весов'}
};
const family=model.toLowerCase().startsWith('mixtral:')?'mixtral:8x7b':model.toLowerCase().startsWith('qwen2.5:32b')?'qwen2.5:32b':'';
if(family&&q!=='auto'){
const size=map[family][q]||'оценка не задана';
const warning=(q==='Q5_K_M'||q==='Q8_0'||q==='F16')?' Для 32 ГБ ОЗУ это не поместится безопасно.':(family==='mixtral:8x7b'&&q==='Q4_K_M'?' На 32 ГБ это пограничный режим; уменьшите контекст и batch.':'');
est.textContent='Размер весов '+size+'. Учтите ОС, runtime и KV-кэш.'+warning;
}else if(q==='auto')est.textContent='Авто не переквантует веса. Фактический формат читается из метаданных установленной модели.';
else est.textContent='Для ~40B параметров INT4 — минимум около 20 ГБ теоретически; на практике больше. INT8 ≈40 ГБ, F16 ≈80 ГБ только под веса.';
}
function qualityData(mode){
if(mode==='rating'){
const rated=[];for(const c of chats)for(const m of (c.messages||[]))if(m.role==='assistant'&&(m.rating==='up'||m.rating==='down'))rated.push({ts:m.ts||0,v:m.rating==='up'?100:0});
rated.sort((a,b)=>a.ts-b.ts);return rated.slice(-20).map((p,i)=>{const win=rated.slice(Math.max(0,i-9),i+1);return {label:String(i+1),value:win.filter(x=>x.v===100).length/win.length*100}});
}
const h=getMetricHistory();const key=mode==='speed'?'speed':mode==='latency'?'duration':'ram_pct';
return h.filter(x=>Number.isFinite(Number(x[key]))).slice(-20).map((x,i)=>({label:String(i+1),value:Number(x[key])}));
}
function drawQualityGraph(){
const canvas=$('quality-canvas');if(!canvas)return;const ctx=canvas.getContext('2d');if(!ctx)return;
const w=canvas.width,h=canvas.height;ctx.clearRect(0,0,w,h);ctx.fillStyle='#08080c';ctx.fillRect(0,0,w,h);
const mode=$('quality-series')?$('quality-series').value:'rating';const data=qualityData(mode);const color=mode==='rating'?'#d4987a':mode==='speed'?'#d4a04a':mode==='latency'?'#5fb0c8':'#6db87d';
ctx.strokeStyle='#282832';ctx.lineWidth=1;for(let i=0;i<5;i++){const y=16+(h-38)*i/4;ctx.beginPath();ctx.moveTo(36,y);ctx.lineTo(w-12,y);ctx.stroke()}
ctx.fillStyle='#777783';ctx.font='18px ui-monospace,monospace';ctx.fillText(mode==='rating'?'%':mode==='speed'?'tok/s':mode==='latency'?'sec':'%',5,18);
if(data.length<2){ctx.fillStyle='#9696a2';ctx.font='18px ui-monospace,monospace';ctx.fillText(mode==='rating'?'Оцените ответы 👍/👎': 'Недостаточно измерений',52,h/2);return}
let vals=data.map(x=>x.value);let max=mode==='rating'||mode==='ram'?100:Math.max(1,...vals)*1.15;let min=0;
ctx.strokeStyle=color;ctx.lineWidth=3;ctx.beginPath();data.forEach((p,i)=>{const x=36+(w-50)*i/(data.length-1);const y=h-22-(p.value-min)/(max-min||1)*(h-48);if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y)});ctx.stroke();
ctx.fillStyle=color;data.forEach((p,i)=>{const x=36+(w-50)*i/(data.length-1);const y=h-22-(p.value-min)/(max-min||1)*(h-48);ctx.beginPath();ctx.arc(x,y,3.5,0,Math.PI*2);ctx.fill()});
ctx.fillStyle='#9696a2';ctx.font='16px ui-monospace,monospace';ctx.fillText(max.toFixed(0),5,36);ctx.fillText('0',15,h-19);
}
async function updateQualityPanel(){
const panel=$('quality-panel');if(!panel||!panel.classList.contains('on'))return;
const history=getMetricHistory();const s=history.length?history[history.length-1]:null;
if($('quality-speed'))$('quality-speed').textContent=s&&Number.isFinite(Number(s.speed))?Number(s.speed).toFixed(1)+' t/s':'—';
const rated=[];for(const c of chats)for(const m of (c.messages||[]))if(m.role==='assistant'&&(m.rating==='up'||m.rating==='down'))rated.push(m.rating);
if($('quality-score'))$('quality-score').textContent=rated.length?(100*rated.filter(x=>x==='up').length/rated.length).toFixed(0)+'% ('+rated.length+')':'—';
try{const r=await fetch('/metrics');const d=await r.json();if($('quality-ram'))$('quality-ram').textContent=d.ram_total?((d.ram_total-d.ram_available)/1024/1024/1024).toFixed(1)+'/'+(d.ram_total/1024/1024/1024).toFixed(0)+' GB':'—';if(d.ram_total){const h=getMetricHistory();h.push({ts:Date.now(),ram_pct:Math.max(0,Math.min(100,(d.ram_total-d.ram_available)/d.ram_total*100)),device:selectedDevice(),quantization:selectedQuant()});save(sk('metric_history'),h.slice(-100));}}catch(e){}
drawQualityGraph();
}
$('quality-btn').addEventListener('click',function(){const p=$('quality-panel');p.classList.toggle('on');if(p.classList.contains('on'))updateQualityPanel()});
$('quality-close').addEventListener('click',function(){$('quality-panel').classList.remove('on')});
$('quality-series').addEventListener('change',drawQualityGraph);
$('compute-device').value=settings.compute_device||'xpu';$('quantization-select').value=settings.quantization||'auto';
$('compute-device').addEventListener('change',function(){settings.compute_device=this.value;save(sk('settings'),settings);updateComputeNote()});
$('quantization-select').addEventListener('change',function(){settings.quantization=this.value;save(sk('settings'),settings);updateComputeNote();updateModelStatus()});
function fmtBytes(b){if(!b||b<=0)return '0 B';const u=['B','KB','MB','GB','TB'];let i=0;while(b>=1024&&i<u.length-1){b/=1024;i++}return b.toFixed(2)+' '+u[i]}
function fmtStat(ts){const s=ts/1000;if(s<60)return s.toFixed(1)+'s';const m=Math.floor(s/60),r=s-m*60;return m+'m '+r.toFixed(0)+'s'}
function esc(s){return String(s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
function modelLabel(n){if(!n)return '';const b=n.split('/').pop();if(b.indexOf(':')>=0){const p=b.split(':');const t=p.pop();return p.join(':')+' · '+t.toUpperCase()}return b}
function dbg(kind,label,text){const n=new Date();const t=String(n.getHours()).padStart(2,'0')+':'+String(n.getMinutes()).padStart(2,'0')+':'+String(n.getSeconds()).padStart(2,'0');dbgEvents.push({t:t,kind:kind,label:label,text:String(text).slice(0,500)});if(dbgEvents.length>500)dbgEvents.shift();renderDebug()}
function renderDebug(){if(!debugLog)return;if(!dbgEvents.length){debugLog.innerHTML='<div class="dbg-empty">события появятся во время генерации</div>';return}const html=dbgEvents.map(function(e){return '<div class="dbg-line '+e.kind+'"><span class="t">'+e.t+'</span><span class="k">'+esc(e.label)+'</span><span class="v">'+esc(e.text)+'</span></div>'}).join('');const wb=debugLog.scrollHeight-debugLog.scrollTop-debugLog.clientHeight<40;debugLog.innerHTML=html;if(wb)debugLog.scrollTop=debugLog.scrollHeight}

function updateEmoBadges(){
const box=$('emo-badges');
if(!box)return;
const sorted=MOOD_SCALES.slice().sort(function(a,b){return (mood[b.id]||50)-(mood[a.id]||50)});
const top=sorted.slice(0,3).filter(function(s){return (mood[s.id]||50)>55});
if(!top.length){box.innerHTML='';box.style.display='none';return}
box.style.display='flex';
box.innerHTML=top.map(function(s){
const v=mood[s.id];
const col=v>75?'var(--err)':v>60?'var(--acc)':'var(--txt2)';
return '<span class="emo-badge" title="'+s.label+': '+v+'" style="color:'+col+'">'+s.icon+' '+s.label+' '+v+'</span>';
}).join('');
}

function renderMarkdown(text){
if(!text)return '';
let s=text;const blocks=[];
const pairs=[
['code',/```(\w*)\n?([\s\S]*?)```/g,function(m){return{type:'code',lang:m[1]||'',code:m[2].replace(/\n$/,'')}}],
['chart',/\[CHART:(bar|line|pie|scatter)\]\s*\n?([\s\S]*?)\[\/CHART\]/g,function(m){return{type:'chart',chartType:m[1],data:m[2].trim()}}],
['graph2d',/\[GRAPH2D\]\s*\n?([\s\S]*?)\[\/GRAPH2D\]/g,function(m){return{type:'graph2d',data:m[1].trim()}}],
['graph3d',/\[GRAPH3D\]\s*\n?([\s\S]*?)\[\/GRAPH3D\]/g,function(m){return{type:'graph3d',data:m[1].trim()}}],
['graphnet',/\[GRAPH_NET\]\s*\n?([\s\S]*?)\[\/GRAPH_NET\]/g,function(m){return{type:'graphnet',data:m[1].trim()}}],
['tree',/\[TREE\]\s*\n?([\s\S]*?)\[\/TREE\]/g,function(m){return{type:'tree',data:m[1].trim()}}],
['obsidian',/\[MINDMAP:([^\]]*)\]\s*\n?([\s\S]*?)\[\/MINDMAP\]/g,function(m){return{type:'obsidian',center:m[1].trim(),data:m[2].trim()}}],
['kanban',/\[KANBAN\]\s*\n?([\s\S]*?)\[\/KANBAN\]/g,function(m){return{type:'kanban',data:m[1].trim()}}],
['timeline',/\[TIMELINE\]\s*\n?([\s\S]*?)\[\/TIMELINE\]/g,function(m){return{type:'timeline',data:m[1].trim()}}],
['process',/\[PROCESS\]\s*\n?([\s\S]*?)\[\/PROCESS\]/g,function(m){return{type:'process',data:m[1].trim()}}],
['metrics',/\[METRICS\]\s*\n?([\s\S]*?)\[\/METRICS\]/g,function(m){return{type:'metrics',data:m[1].trim()}}],
['checklist',/\[CHECKLIST\]\s*\n?([\s\S]*?)\[\/CHECKLIST\]/g,function(m){return{type:'checklist',data:m[1].trim()}}],
['filetree',/\[FILE_TREE\]\s*\n?([\s\S]*?)\[\/FILE_TREE\]/g,function(m){return{type:'filetree',data:m[1].trim()}}],
['matrix',/\[MATRIX\]\s*\n?([\s\S]*?)\[\/MATRIX\]/g,function(m){return{type:'matrix',data:m[1].trim()}}],
['callout',/\[CALLOUT:(\w+)\]\s*\n?([\s\S]*?)\[\/CALLOUT\]/g,function(m){return{type:'callout',calloutType:m[1].toLowerCase(),data:m[2].trim()}}],
['quote',/\[QUOTE\]\s*\n?([\s\S]*?)\[\/QUOTE\]/g,function(m){return{type:'quote',data:m[1].trim()}}],
['math',/\[MATH\]\s*\n?([\s\S]*?)\[\/MATH\]/g,function(m){return{type:'math',data:m[1].trim()}}],
['shape2d',/\[SHAPE2D\]\s*\n?([\s\S]*?)\[\/SHAPE2D\]/g,function(m){return{type:'shape2d',data:m[1].trim()}}],
['shape3d',/\[SHAPE3D\]\s*\n?([\s\S]*?)\[\/SHAPE3D\]/g,function(m){return{type:'shape3d',data:m[1].trim()}}],
['poly2d',/\[POLY2D\]\s*\n?([\s\S]*?)\[\/POLY2D\]/g,function(m){return{type:'poly2d',data:m[1].trim()}}],
['mesh3d',/\[MESH3D\]\s*\n?([\s\S]*?)\[\/MESH3D\]/g,function(m){return{type:'mesh3d',data:m[1].trim()}}],
['aero',/\[AERO\]\s*\n?([\s\S]*?)\[\/AERO\]/g,function(m){return{type:'aero',data:m[1].trim()}}]
];
if(formsOn){
for(const pair of pairs){
s=s.replace(pair[1],(function(re,mk){return function(){const args=Array.prototype.slice.call(arguments);const m=args.slice(0,-2);const i=blocks.length;blocks.push(mk(m));return '\uE000B'+i+'\uE001'}})(pair[1],pair[2]));
}
s=s.replace(/\[CHESS\]([\s\S]*?)\[\/CHESS\]|\[CHESS\]/g,function(){const i=blocks.length;blocks.push({type:'chess'});return '\uE000B'+i+'\uE001'});
s=s.replace(/^((?:\|[^\n]+\|\s*\n)+)/gm,function(tb){const lines=tb.trim().split('\n');if(lines.length<2)return tb;if(!/^\s*\|[\s\-\|:]+\|\s*$/.test(lines[1]))return tb;const i=blocks.length;blocks.push({type:'table',lines:lines});return '\uE000B'+i+'\uE001'});
}else{
s=s.replace(/```(\w*)\n?([\s\S]*?)```/g,function(_,lang,code){const i=blocks.length;blocks.push({type:'code',lang:lang||'',code:code.replace(/\n$/,'')});return '\uE000B'+i+'\uE001'});
}
s=esc(s);
s=s.replace(/\*\*([^*\n]+)\*\*/g,'\uE002\uE003$1\uE004\uE005');
s=s.replace(/__([^_\n]+)__/g,'\uE006\uE007$1\uE008\uE009');
s=s.replace(/~~([^~\n]+)~~/g,'\uE00A\uE00B$1\uE00C\uE00D');
s=s.replace(/==([^=\n]+)==/g,'\uE00E\uE00F$1\uE010\uE011');
s=s.replace(/\^([^\^\s\n]+)\^/g,'\uE012\uE013$1\uE014\uE015');
s=s.replace(/(?<![a-zA-Z0-9])~([^~\s\n]+)~/g,'\uE016\uE017$1\uE018\uE019');
s=s.replace(/\*([^*\n]+)\*/g,'<em>$1</em>');
s=s.replace(/\uE002\uE003([\s\S]*?)\uE004\uE005/g,'<strong>$1</strong>');
s=s.replace(/\uE006\uE007([\s\S]*?)\uE008\uE009/g,'<u>$1</u>');
s=s.replace(/\uE00A\uE00B([\s\S]*?)\uE00C\uE00D/g,'<del>$1</del>');
s=s.replace(/\uE00E\uE00F([\s\S]*?)\uE010\uE011/g,'<mark>$1</mark>');
s=s.replace(/\uE012\uE013([\s\S]*?)\uE014\uE015/g,'<sup>$1</sup>');
s=s.replace(/\uE016\uE017([\s\S]*?)\uE018\uE019/g,'<sub>$1</sub>');
s=s.replace(/`([^`\n]+)`/g,'<code>$1</code>');
s=s.replace(/\[([^\]]+)\]\(([^)]+)\)/g,'<a href="$2" target="_blank">$1</a>');
s=s.replace(/^&gt;\s?(.+)$/gm,'<blockquote>$1</blockquote>');
s=s.replace(/^### (.+)$/gm,'<h3>$1</h3>');
s=s.replace(/^## (.+)$/gm,'<h2>$1</h2>');
s=s.replace(/^# (.+)$/gm,'<h1>$1</h1>');
s=s.replace(/(?:^|\n)((?:[-*] .+\n?)+)/g,function(m,l){return '\n<ul>'+l.trim().split('\n').map(function(x){return '<li>'+x.replace(/^[-*]\s+/,'')+'</li>'}).join('')+'</ul>'});
s=s.replace(/(?:^|\n)((?:\d+\. .+\n?)+)/g,function(m,l){return '\n<ol>'+l.trim().split('\n').map(function(x){return '<li>'+x.replace(/^\d+\.\s+/,'')+'</li>'}).join('')+'</ol>'});
s=s.replace(/\n\n+/g,'</p><p>');
s='<p>'+s+'</p>';
s=s.replace(/<p>\s*<\/p>/g,'');
s=s.replace(/<p>(<h\d>)/g,'$1');
s=s.replace(/(<\/h\d>)<\/p>/g,'$1');
s=s.replace(/<p>(<ul>)/g,'$1');s=s.replace(/(<\/ul>)<\/p>/g,'$1');
s=s.replace(/<p>(<ol>)/g,'$1');s=s.replace(/(<\/ol>)<\/p>/g,'$1');
s=s.replace(/<p>(<blockquote>)/g,'$1');s=s.replace(/(<\/blockquote>)<\/p>/g,'$1');
s=s.replace(/<p>(\uE000B\d+\uE001)<\/p>/g,'$1');
s=s.replace(/\uE000B(\d+)\uE001/g,function(_,n){const b=blocks[parseInt(n,10)];if(!b)return '';return renderBlock(b)});
return s;
}

function renderBlock(b){
if(b.type==='code'){const id='c'+Math.random().toString(36).slice(2,8);return '<div class="code-block"><div class="cb-head"><span>'+esc(b.lang||'code')+'</span><button class="code-copy" data-target="'+id+'">'+ic('copy','sm')+' копировать</button></div><pre id="'+id+'"><code>'+esc(b.code)+'</code></pre></div>'}
if(b.type==='table'){const header=b.lines[0].split('|').slice(1,-1).map(function(c){return c.trim()});const rows=b.lines.slice(2).map(function(l){return l.split('|').slice(1,-1).map(function(c){return c.trim()})});let h='<table class="md-table"><thead><tr>';for(const x of header)h+='<th>'+esc(x)+'</th>';h+='</tr></thead><tbody>';for(const r of rows){h+='<tr>';for(const c of r)h+='<td>'+esc(c)+'</td>';h+='</tr>'}return h+'</tbody></table>'}
if(b.type==='chart')return '<div class="blk chart-block" data-chart="'+esc(JSON.stringify({type:b.chartType,data:b.data}))+'"><div class="bh">'+ic('chart','sm')+' '+esc(b.chartType)+'</div><canvas></canvas></div>';
if(b.type==='graph2d')return '<div class="blk graph-block" data-graph="'+esc(JSON.stringify({kind:'2d',data:b.data}))+'"><div class="bh"><span>'+ic('graph','sm')+' график 2d</span><span class="expr"></span></div><canvas></canvas></div>';
if(b.type==='graph3d')return '<div class="blk graph-block" data-graph="'+esc(JSON.stringify({kind:'3d',data:b.data}))+'"><div class="bh"><span>'+ic('cube','sm')+' график 3d</span><span class="expr"></span></div><canvas></canvas></div>';
if(b.type==='graphnet'){const p=parseGraphNet(b.data);if(!p.nodes.length)return '<p><em>граф пуст</em></p>';return '<div class="blk graphnet-block" data-net="'+esc(JSON.stringify(p))+'"><div class="bh"><span>'+ic('net','sm')+' граф · '+p.nodes.length+' узлов</span></div><canvas></canvas></div>'}
if(b.type==='tree')return renderTree(b.data);
if(b.type==='obsidian')return renderObsidian(b.center,b.data);
if(b.type==='kanban')return renderKanban(b.data);
if(b.type==='timeline')return renderTimeline(b.data);
if(b.type==='process')return renderProcess(b.data);
if(b.type==='metrics')return renderMetrics(b.data);
if(b.type==='checklist')return renderChecklist(b.data);
if(b.type==='filetree')return renderFileTree(b.data);
if(b.type==='matrix')return renderMatrix(b.data);
if(b.type==='callout')return renderCallout(b.calloutType,b.data);
if(b.type==='quote')return renderQuote(b.data);
if(b.type==='math')return renderMath(b.data);
if(b.type==='shape2d')return '<div class="blk shape-block" data-shape2d="'+esc(b.data)+'"><div class="bh"><span>'+ic('shape','sm')+' 2d фигура</span></div><canvas></canvas></div>';
if(b.type==='shape3d')return '<div class="blk shape-block" data-shape3d="'+esc(b.data)+'"><div class="bh"><span>'+ic('cube','sm')+' 3d фигура</span></div><canvas></canvas></div>';
if(b.type==='poly2d')return '<div class="blk shape-block" data-poly2d="'+esc(b.data)+'"><div class="bh"><span>'+ic('shape','sm')+' полигон</span></div><canvas></canvas></div>';
if(b.type==='mesh3d')return '<div class="blk shape-block" data-mesh3d="'+esc(b.data)+'"><div class="bh"><span>'+ic('cube','sm')+' mesh</span></div><canvas></canvas></div>';
if(b.type==='aero')return '<div class="blk aero-block" data-aero="'+esc(b.data)+'"><div class="bh"><span>'+ic('aero','sm')+' аэродинамика</span></div><div class="aero-controls" data-aero-controls></div><canvas></canvas></div>';
if(b.type==='chess')return renderChess();
return '';
}

function renderTree(d){
const lines=d.split('\n').filter(function(l){return l.trim()});
let h='<div class="blk tree-block"><div class="bh">'+ic('tree','sm')+' дерево</div>';
for(const line of lines){
const indent=(line.match(/^\s*/)||[''])[0].length;
const txt=line.trim();const lvl=Math.floor(indent/2);
const isDir=txt.endsWith('/')||(txt.indexOf('.')<0&&txt.length<40&&txt.indexOf(' ')<0);
h+='<div class="tree-line'+(lvl===0?' root':'')+'" style="padding-left:'+(lvl*16)+'px">'+ic(isDir?'tree':'filetree','sm')+' '+esc(txt)+'</div>';
}
return h+'</div>';
}

function renderObsidian(center,data){
const lines=data.split('\n').filter(function(l){return l.trim()});
const branches=[];let cur=null;
for(const l of lines){
const i=(l.match(/^\s*/)||[''])[0].length;
const t=l.trim();
if(i===0){cur={text:t,subs:[]};branches.push(cur)}
else if(cur)cur.subs.push(t);
}
return '<div class="blk obsidian-block" data-obsidian="'+esc(JSON.stringify({center:center,branches:branches}))+'"><div class="bh">'+ic('net','sm')+' mind map · obsidian</div><svg data-role="obs-links"></svg><div data-role="obs-nodes"></div></div>';
}

function renderKanban(d){
const lines=d.split('\n').map(function(l){return l.trim()}).filter(Boolean);
const cols=[];let cur=null;
for(const l of lines){if(l.indexOf('@')===0){cur={title:l.slice(1).trim(),cards:[]};cols.push(cur)}else if(cur&&l.indexOf('-')===0)cur.cards.push(l.slice(1).trim())}
return '<div class="blk kanban-block"><div class="bh">'+ic('kanban','sm')+' kanban</div><div class="kanban-cols">'+cols.map(function(c){return '<div class="kanban-col"><div class="kanban-col-t"><span>'+esc(c.title)+'</span><span class="cnt">'+c.cards.length+'</span></div>'+c.cards.map(function(x){return '<div class="kanban-card">'+esc(x)+'</div>'}).join('')+'</div>'}).join('')+'</div></div>';
}
function renderTimeline(d){
const lines=d.split('\n').map(function(l){return l.trim()}).filter(Boolean);
const items=lines.map(function(l){const m=l.match(/^(.+?)\s*:\s*(.+)$/);return m?{date:m[1].trim(),text:m[2].trim()}:{date:'',text:l}});
return '<div class="blk timeline-block"><div class="bh">'+ic('timeline','sm')+' timeline</div><div class="timeline">'+items.map(function(it){return '<div class="timeline-item"><div class="timeline-date">'+esc(it.date)+'</div><div class="timeline-text">'+esc(it.text)+'</div></div>'}).join('')+'</div></div>';
}
function renderProcess(d){
const lines=d.split(/[\n→]+/).map(function(l){return l.replace(/^→\s*/,'').trim()}).filter(Boolean);
return '<div class="blk process-block"><div class="bh">'+ic('process','sm')+' процесс · '+lines.length+' шагов</div><div class="process-flow">'+lines.map(function(s,i){return '<div class="process-step"><span class="num">'+(i+1)+'</span>'+esc(s)+'</div>'}).join('<span class="process-arrow">→</span>')+'</div></div>';
}
function renderMetrics(d){
const lines=d.split('\n').map(function(l){return l.trim()}).filter(Boolean);
const items=lines.map(function(l){const m=l.match(/^(.+?)\s*:\s*([^:]+?)(?:\s*:\s*(.+))?$/);return m?{label:m[1].trim(),value:m[2].trim(),delta:(m[3]||'').trim()}:null}).filter(Boolean);
return '<div class="blk metrics-block"><div class="bh">'+ic('metrics','sm')+' метрики</div><div class="metrics-grid">'+items.map(function(it){const up=it.delta.indexOf('+')===0;const dn=it.delta.indexOf('-')===0;return '<div class="metric-card"><div class="metric-label">'+esc(it.label)+'</div><div class="metric-value">'+esc(it.value)+'</div>'+(it.delta?'<div class="metric-delta '+(up?'up':dn?'down':'')+'">'+esc(it.delta)+'</div>':'')+'</div>'}).join('')+'</div></div>';
}
function renderChecklist(d){
const lines=d.split('\n').map(function(l){return l.trim()}).filter(Boolean);
const items=lines.map(function(l){const m=l.match(/^\[(x| )\]\s*(.+)$/);return m?{done:m[1]==='x',text:m[2]}:{done:false,text:l}});
return '<div class="blk checklist-block"><div class="bh">'+ic('checklist','sm')+' чек-лист · '+items.filter(function(i){return i.done}).length+'/'+items.length+'</div>'+items.map(function(it){return '<label class="checklist-item'+(it.done?' done':'')+'"><input type="checkbox" '+(it.done?'checked':'')+'><span class="checklist-text">'+esc(it.text)+'</span></label>'}).join('')+'</div>';
}
function renderFileTree(d){
const lines=d.split('\n').filter(function(l){return l.trim()});
return '<div class="blk filetree-block"><div class="bh">'+ic('filetree','sm')+' файлы</div><div class="filetree">'+lines.map(function(l){const i=(l.match(/^\s*/)||[''])[0].length;const t=l.trim();const dir=t.endsWith('/');return '<div class="file-line '+(dir?'dir':'')+'" style="padding-left:'+(i*8)+'px">'+ic('filetree','sm')+' '+esc(t)+'</div>'}).join('')+'</div></div>';
}
function renderMatrix(d){
const rows=d.split('\n').map(function(l){return l.trim().split(/\s+/).filter(Boolean)}).filter(function(r){return r.length});
return '<div class="blk matrix-block"><div class="bh">'+ic('matrix','sm')+' матрица '+rows.length+'×'+(rows[0]?rows[0].length:0)+'</div><div class="matrix-wrap"><table class="matrix-table">'+rows.map(function(r){return '<tr>'+r.map(function(c){return '<td>'+esc(c)+'</td>'}).join('')+'</tr>'}).join('')+'</table></div></div>';
}
function renderCallout(type,d){
const lm={info:'информация',warn:'внимание',success:'успех',error:'ошибка',tip:'совет'};
return '<div class="blk callout-block '+esc(type)+'"><div class="bh">'+ic('callout','sm')+' '+esc(lm[type]||type)+'</div><div class="callout-text">'+esc(d)+'</div></div>';
}
function renderQuote(d){
const lines=d.split('\n').map(function(l){return l.trim()}).filter(Boolean);
const t=lines.slice(0,-1).join(' ')||lines[0]||'';
const a=lines.length>1?lines[lines.length-1]:'';
return '<div class="blk quote-block"><div class="bh">'+ic('quote','sm')+' цитата</div><div class="quote-text">«'+esc(t)+'»</div>'+(a?'<div class="quote-author">— '+esc(a)+'</div>':'')+'</div>';
}
function renderMath(d){
let h=esc(d)
.replace(/frac\(([^,]+),\s*([^)]+)\)/g,'<span style="display:inline-block;text-align:center;vertical-align:middle"><span style="display:block;border-bottom:1px solid currentColor;padding:0 4px">$1</span><span style="display:block;padding:0 4px">$2</span></span>')
.replace(/sqrt\(([^)]+)\)/g,'√($1)')
.replace(/sum\(\)/g,'∑')
.replace(/int\(\)/g,'∫')
.replace(/\b(alpha|beta|gamma|delta|epsilon|theta|lambda|mu|pi|sigma|omega)\b/g,function(_,g){return ({alpha:'α',beta:'β',gamma:'γ',delta:'δ',epsilon:'ε',theta:'θ',lambda:'λ',mu:'μ',pi:'π',sigma:'σ',omega:'ω'}[g]||g)})
.replace(/\^([\w\d]+)/g,'<sup>$1</sup>')
.replace(/_([\w\d]+)/g,'<sub>$1</sub>');
return '<div class="blk math-block"><div class="bh">'+ic('math','sm')+' формула</div><div class="math-content">'+h+'</div></div>';
}
function renderChess(){
return '<div class="blk chess-block" data-chess><div class="bh">'+ic('chess','sm')+' шахматы · играй против ии</div><div class="chess-wrap"><div class="chess-board"></div><div class="chess-info"><div class="row"><span class="lbl">ход</span><span class="val acc" data-role="turn">белые</span></div><div class="row"><span class="lbl">статус</span><span class="val" data-role="status">—</span></div><div class="row"><span class="lbl">ходов</span><span class="val" data-role="count">0</span></div><div class="chess-moves" data-role="moves"></div><button class="act" data-role="reset" style="margin-top:8px">новая партия</button></div></div></div>';
}
function parseGraphNet(d){
const nodes=new Map(),links=[];
for(const line of d.split('\n').map(function(l){return l.trim()}).filter(Boolean)){
const m=line.match(/^(.+?)\s*(?:->|=>|—>|-->)\s*(.+?)(?:\s*:\s*(.+?))?\s*$/);
if(!m)continue;
const from=m[1].trim().replace(/^["']|["']$/g,'');
const to=m[2].trim().replace(/^["']|["']$/g,'');
const label=(m[3]||'').trim();
if(!from||!to)continue;
if(!nodes.has(from))nodes.set(from,{id:from,label:from});
if(!nodes.has(to))nodes.set(to,{id:to,label:to});
links.push({source:from,target:to,label:label});
}
return {nodes:Array.from(nodes.values()),links:links};
}

function initChess(container){
const state={board:[['br','bn','bb','bq','bk','bb','bn','br'],['bp','bp','bp','bp','bp','bp','bp','bp'],[null,null,null,null,null,null,null,null],[null,null,null,null,null,null,null,null],[null,null,null,null,null,null,null,null],[null,null,null,null,null,null,null,null],['wp','wp','wp','wp','wp','wp','wp','wp'],['wr','wn','wb','wq','wk','wb','wn','wr']],turn:'w',selected:null,legalMoves:[],moveCount:0,history:[],gameOver:false,thinking:false};
const ps={k:'♚',q:'♛',r:'♜',b:'♝',n:'♞',p:'♟'};
const bEl=container.querySelector('.chess-board');
const sEl=container.querySelector('[data-role="status"]');
const tEl=container.querySelector('[data-role="turn"]');
const cEl=container.querySelector('[data-role="count"]');
const mEl=container.querySelector('[data-role="moves"]');
const rBtn=container.querySelector('[data-role="reset"]');
function inside(r,c){return r>=0&&r<8&&c>=0&&c<8}
function render(){
bEl.innerHTML='';
for(let r=0;r<8;r++)for(let c=0;c<8;c++){
const sq=document.createElement('div');
sq.className='chess-sq '+((r+c)%2===0?'light':'dark');
sq.dataset.r=r;sq.dataset.c=c;
if(state.selected&&state.selected.r===r&&state.selected.c===c)sq.classList.add('sel');
const lm=state.legalMoves.find(function(m){return m.r===r&&m.c===c});
if(lm)sq.classList.add(lm.capture?'cap':'legal');
const p=state.board[r][c];
if(p){const sp=document.createElement('span');sp.className='piece '+p[0];sp.textContent=ps[p[1]]||'?';sq.appendChild(sp)}
if(c===0){const co=document.createElement('span');co.className='coord';co.textContent=(8-r);sq.appendChild(co)}
if(r===7){const co=document.createElement('span');co.className='coord';co.style.right='auto';co.style.left='3px';co.textContent='abcdefgh'[c];sq.appendChild(co)}
sq.addEventListener('click',(function(rr,cc){return function(){onClick(rr,cc)}})(r,c));
bEl.appendChild(sq);
}
tEl.textContent=state.turn==='w'?'белые':'чёрные';
cEl.textContent=state.moveCount;
mEl.innerHTML=state.history.map(function(h){return '<div class="mv '+h.who+'">'+(h.who==='user'?'→':'←')+' '+esc(h.text)+'</div>'}).join('');
mEl.scrollTop=mEl.scrollHeight;
}
function legalMoves(r,c){
const p=state.board[r][c];if(!p)return [];
const moves=[];const dir=p[0]==='w'?-1:1;const t=p[1];
function add(rr,cc){if(!inside(rr,cc))return false;const tp=state.board[rr][cc];if(tp&&tp[0]===p[0])return false;moves.push({r:rr,c:cc,capture:!!tp});return !tp}
if(t==='p'){
if(add(r+dir,c)){const sr=p[0]==='w'?6:1;if(r===sr)add(r+2*dir,c)}
if(inside(r+dir,c-1)&&state.board[r+dir][c-1]&&state.board[r+dir][c-1][0]!==p[0])add(r+dir,c-1);
if(inside(r+dir,c+1)&&state.board[r+dir][c+1]&&state.board[r+dir][c+1][0]!==p[0])add(r+dir,c+1);
}else if(t==='n'){
[[-2,-1],[-2,1],[-1,-2],[-1,2],[1,-2],[1,2],[2,-1],[2,1]].forEach(function(a){add(r+a[0],c+a[1])});
}else if(t==='b'||t==='q'){
[[-1,-1],[-1,1],[1,-1],[1,1]].forEach(function(a){let rr=r+a[0],cc=c+a[1];while(add(rr,cc)){rr+=a[0];cc+=a[1]}});
}
if(t==='r'||t==='q'){
[[-1,0],[1,0],[0,-1],[0,1]].forEach(function(a){let rr=r+a[0],cc=c+a[1];while(add(rr,cc)){rr+=a[0];cc+=a[1]}});
}
if(t==='k'){[[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]].forEach(function(a){add(r+a[0],c+a[1])});}
return moves;
}
function onClick(r,c){
if(state.gameOver||state.thinking||state.turn!=='w')return;
const p=state.board[r][c];
if(state.selected){
const lm=state.legalMoves.find(function(m){return m.r===r&&m.c===c});
if(lm){
const f=state.selected;
const fs='abcdefgh'[f.c]+(8-f.r);
const ts='abcdefgh'[c]+(8-r);
state.board[r][c]=state.board[f.r][f.c];
state.board[f.r][f.c]=null;
if(state.board[r][c][1]==='p'&&(r===0||r===7))state.board[r][c]=state.board[r][c][0]+'q';
state.history.push({who:'user',text:fs+'→'+ts+(lm.capture?'x':'')});
state.selected=null;state.legalMoves=[];
state.turn='b';state.moveCount++;
sEl.textContent='ии думает…';
render();
setTimeout(aiMove,250);
return;
}
state.selected=null;state.legalMoves=[];
}
if(p&&p[0]==='w'){state.selected={r:r,c:c};state.legalMoves=legalMoves(r,c)}
render();
}
function aiMove(){
if(state.gameOver)return;
state.thinking=true;
const best=pickBestMove();
if(best){
state.board[best.to.r][best.to.c]=state.board[best.from.r][best.from.c];
state.board[best.from.r][best.from.c]=null;
if(state.board[best.to.r][best.to.c][1]==='p'&&(best.to.r===0||best.to.r===7))state.board[best.to.r][best.to.c]=state.board[best.to.r][best.to.c][0]+'q';
state.history.push({who:'ai',text:'abcdefgh'[best.from.c]+(8-best.from.r)+'→'+'abcdefgh'[best.to.c]+(8-best.to.r)});
state.turn='w';state.moveCount++;
}
state.thinking=false;
const wk=state.board.flat().indexOf('wk')>=0;
const bk=state.board.flat().indexOf('bk')>=0;
if(!wk){sEl.textContent='мат — чёрные победили';sEl.className='val err';state.gameOver=true}
else if(!bk){sEl.textContent='мат — белые победили';sEl.className='val ok';state.gameOver=true}
else{sEl.textContent='ваш ход';sEl.className='val'}
render();
}
function pickBestMove(){
const pieces=[];
for(let r=0;r<8;r++)for(let c=0;c<8;c++)if(state.board[r][c]&&state.board[r][c][0]==='b')pieces.push({r:r,c:c});
if(!pieces.length)return null;
let best=null,bestScore=-Infinity;
for(const p of pieces){
const moves=legalMoves(p.r,p.c);
for(const m of moves){
let score=0;
if(m.capture){const target=state.board[m.r][m.c];const v={p:1,n:3,b:3,r:5,q:9,k:1000}[target[1]]||0;score+=v*10}
score-=Math.abs(m.c-3.5)*0.3;
score-=Math.abs(m.r-3.5)*0.3;
let attackers=0;
for(let rr=0;rr<8;rr++)for(let cc=0;cc<8;cc++){
const wp=state.board[rr][cc];
if(wp&&wp[0]==='w'){if(legalMovesSim(rr,cc,m.r,m.c))attackers++}
}
if(attackers>0)score-=3;
score+=Math.random()*0.5;
if(score>bestScore){bestScore=score;best={from:{r:p.r,c:p.c},to:{r:m.r,c:m.c}}}
}
}
return best;
}
function legalMovesSim(fr,fc,tr,tc){
const p=state.board[fr][fc];if(!p)return false;
const dr=tr-fr,dc=tc-fc;const t=p[1];
if(t==='p'){if(dc===0&&dr===-1)return true;if(dc===0&&dr===-2&&fr===6)return true;if(Math.abs(dc)===1&&dr===-1)return true;return false}
if(t==='n')return (Math.abs(dr)===2&&Math.abs(dc)===1)||(Math.abs(dr)===1&&Math.abs(dc)===2);
if(t==='b')return Math.abs(dr)===Math.abs(dc)&&dr!==0;
if(t==='r')return (dr===0||dc===0)&&(dr!==0||dc!==0);
if(t==='q')return (Math.abs(dr)===Math.abs(dc)||dr===0||dc===0)&&(dr!==0||dc!==0);
if(t==='k')return Math.abs(dr)<=1&&Math.abs(dc)<=1&&(dr!==0||dc!==0);
return false;
}
rBtn.addEventListener('click',function(){
state.board=[['br','bn','bb','bq','bk','bb','bn','br'],['bp','bp','bp','bp','bp','bp','bp','bp'],[null,null,null,null,null,null,null,null],[null,null,null,null,null,null,null,null],[null,null,null,null,null,null,null,null],[null,null,null,null,null,null,null,null],['wp','wp','wp','wp','wp','wp','wp','wp'],['wr','wn','wb','wq','wk','wb','wn','wr']];
state.turn='w';state.selected=null;state.legalMoves=[];state.moveCount=0;state.history=[];state.gameOver=false;state.thinking=false;
sEl.textContent='ваш ход';sEl.className='val';
render();
});
sEl.textContent='ваш ход';
render();
}

function parseShape2D(d){
const r={type:'circle',size:100,color:'#d4a04a'};
for(const l of d.split('\n').map(function(x){return x.trim()}).filter(Boolean)){
const m=l.match(/^(\w+)\s*:\s*(.+)$/);if(!m)continue;
const v=m[2].trim();
if(m[1]==='type')r.type=v;else if(m[1]==='size')r.size=parseFloat(v)||100;else if(m[1]==='color')r.color=v;
}
return r;
}
function drawShape2D(canvas,shape){
const W=canvas.parentElement.clientWidth||400,H=300;
const dpr=window.devicePixelRatio||1;
canvas.width=W*dpr;canvas.height=H*dpr;canvas.style.width=W+'px';canvas.style.height=H+'px';
const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
const cx=W/2,cy=H/2;const r=Math.min(shape.size*1.2,Math.min(W,H)/2-30);
ctx.strokeStyle=shape.color;ctx.fillStyle=shape.color+'33';ctx.lineWidth=2;ctx.beginPath();
const sides={circle:0,square:4,triangle:3,hexagon:6,pentagon:5,diamond:4,cross:12,star:10,arrow:7,gear:12}[shape.type]||4;
if(shape.type==='circle'){ctx.arc(cx,cy,r,0,Math.PI*2)}
else if(shape.type==='star'){for(let i=0;i<10;i++){const a=-Math.PI/2+i*Math.PI/5;const rr=i%2===0?r:r*0.4;const x=cx+Math.cos(a)*rr,y=cy+Math.sin(a)*rr;if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y)}ctx.closePath()}
else if(shape.type==='cross'){const t=r*0.35;ctx.moveTo(cx-t,cy-r);ctx.lineTo(cx+t,cy-r);ctx.lineTo(cx+t,cy-t);ctx.lineTo(cx+r,cy-t);ctx.lineTo(cx+r,cy+t);ctx.lineTo(cx+t,cy+t);ctx.lineTo(cx+t,cy+r);ctx.lineTo(cx-t,cy+r);ctx.lineTo(cx-t,cy+t);ctx.lineTo(cx-r,cy+t);ctx.lineTo(cx-r,cy-t);ctx.lineTo(cx-t,cy-t);ctx.closePath()}
else if(shape.type==='diamond'){ctx.moveTo(cx,cy-r);ctx.lineTo(cx+r,cy);ctx.lineTo(cx,cy+r);ctx.lineTo(cx-r,cy);ctx.closePath()}
else if(shape.type==='arrow'){const t=r*0.4;ctx.moveTo(cx-r,cy-t);ctx.lineTo(cx+r*0.4,cy-t);ctx.lineTo(cx+r*0.4,cy-r*0.8);ctx.lineTo(cx+r,cy);ctx.lineTo(cx+r*0.4,cy+r*0.8);ctx.lineTo(cx+r*0.4,cy+t);ctx.lineTo(cx-r,cy+t);ctx.closePath()}
else{for(let i=0;i<=sides;i++){const a=-Math.PI/2+i*Math.PI*2/sides;const x=cx+Math.cos(a)*r,y=cy+Math.sin(a)*r;if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y)}}
ctx.fill();ctx.stroke();
ctx.fillStyle=shape.color;ctx.font='11px ui-monospace,monospace';ctx.textAlign='center';
ctx.fillText(shape.type+' · size '+shape.size,cx,H-10);
}
function parsePoly2D(d){
const r={name:'polygon',color:'#d4a04a',points:[]};
let section='';
for(let l of d.split('\n')){l=l.trim();if(!l)continue;
if(l.indexOf('name:')===0){r.name=l.slice(5).trim();continue}
if(l.indexOf('color:')===0){r.color=l.slice(6).trim();continue}
if(l==='points:'){section='points';continue}
if(section==='points'){const p=l.split(',').map(Number);if(p.length>=2&&!isNaN(p[0])&&!isNaN(p[1]))r.points.push({x:p[0],y:p[1]})}
}
return r;
}
function drawPoly2D(canvas,shape){
const W=canvas.parentElement.clientWidth||400,H=300;
const dpr=window.devicePixelRatio||1;
canvas.width=W*dpr;canvas.height=H*dpr;canvas.style.width=W+'px';canvas.style.height=H+'px';
const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
const cx=W/2,cy=H/2;
if(!shape.points.length){ctx.fillStyle='rgba(216,120,120,0.7)';ctx.font='12px ui-monospace,monospace';ctx.textAlign='center';ctx.fillText('нет точек',cx,cy);return}
let xmin=Infinity,xmax=-Infinity,ymin=Infinity,ymax=-Infinity;
for(const p of shape.points){if(p.x<xmin)xmin=p.x;if(p.x>xmax)xmax=p.x;if(p.y<ymin)ymin=p.y;if(p.y>ymax)ymax=p.y}
const w=xmax-xmin||1,h=ymax-ymin||1;
const sc=Math.min((W-40)/w,(H-40)/h);
const ox=(xmin+xmax)/2,oy=(ymin+ymax)/2;
ctx.strokeStyle=shape.color;ctx.fillStyle=shape.color+'33';ctx.lineWidth=2;ctx.beginPath();
shape.points.forEach(function(p,i){const sx=cx+(p.x-ox)*sc,sy=cy+(p.y-oy)*sc;if(i===0)ctx.moveTo(sx,sy);else ctx.lineTo(sx,sy)});
ctx.closePath();ctx.fill();ctx.stroke();
for(const p of shape.points){ctx.fillStyle=shape.color;ctx.beginPath();ctx.arc(cx+(p.x-ox)*sc,cy+(p.y-oy)*sc,3,0,Math.PI*2);ctx.fill()}
ctx.fillStyle=shape.color;ctx.font='11px ui-monospace,monospace';ctx.textAlign='center';
ctx.fillText(shape.name+' · '+shape.points.length+' точек',cx,H-10);
}
function parseMesh3D(d){
const r={name:'mesh',scale:100,color:'#d4a04a',vertices:[],faces:[]};
let section='';
for(let l of d.split('\n')){l=l.trim();if(!l)continue;
if(l.indexOf('name:')===0){r.name=l.slice(5).trim();continue}
if(l.indexOf('scale:')===0){r.scale=parseFloat(l.slice(6))||100;continue}
if(l.indexOf('color:')===0){r.color=l.slice(6).trim();continue}
if(l==='vertices:'){section='v';continue}
if(l==='faces:'){section='f';continue}
if(section==='v'){const p=l.split(',').map(Number);if(p.length>=3&&p.every(function(x){return !isNaN(x)}))r.vertices.push({x:p[0],y:p[1],z:p[2]})}
else if(section==='f'){const f=l.split(',').map(function(x){return parseInt(x.trim(),10)}).filter(function(x){return !isNaN(x)});if(f.length>=3)r.faces.push(f)}
}
return r;
}
function setupMesh3D(canvas,mesh){
const sc=mesh.scale/100;
const verts=mesh.vertices.map(function(v){return {x:v.x*sc,y:v.y*sc,z:v.z*sc}});
const faces=mesh.faces;
if(!verts.length||!faces.length){
const W=canvas.parentElement.clientWidth||400,H=320;
const dpr=window.devicePixelRatio||1;
canvas.width=W*dpr;canvas.height=H*dpr;canvas.style.width=W+'px';canvas.style.height=H+'px';
const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);
ctx.fillStyle='rgba(216,120,120,0.7)';ctx.font='12px ui-monospace,monospace';ctx.textAlign='center';
ctx.fillText('нет данных',W/2,H/2);return;
}
const st={angleY:0.7,angleX:-0.5,zoom:1,dragging:false,lastX:0,lastY:0};
view3dState.set(canvas,st);
function draw(){drawMesh3D(canvas,verts,faces,mesh,st)}
canvas.addEventListener('mousedown',function(e){st.dragging=true;st.lastX=e.clientX;st.lastY=e.clientY});
canvas.addEventListener('mousemove',function(e){if(!st.dragging)return;const dx=e.clientX-st.lastX,dy=e.clientY-st.lastY;st.lastX=e.clientX;st.lastY=e.clientY;st.angleY+=dx*0.01;st.angleX=Math.max(-1.5,Math.min(1.5,st.angleX+dy*0.01));draw()});
canvas.addEventListener('mouseup',function(){st.dragging=false});
canvas.addEventListener('mouseleave',function(){st.dragging=false});
canvas.addEventListener('wheel',function(e){e.preventDefault();st.zoom=Math.max(0.3,Math.min(3,st.zoom*(e.deltaY>0?0.9:1.1)));draw()},{passive:false});
draw();
}
function drawMesh3D(canvas,verts,faces,mesh,st){
const W=canvas.parentElement.clientWidth||400,H=320;
const dpr=window.devicePixelRatio||1;
canvas.width=W*dpr;canvas.height=H*dpr;canvas.style.width=W+'px';canvas.style.height=H+'px';
const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
const cx=W/2,cy=H/2;
let maxExt=0.001;
for(const v of verts){const e=Math.sqrt(v.x*v.x+v.y*v.y+v.z*v.z);if(e>maxExt)maxExt=e}
const scale=Math.min(W,H)/3/maxExt*st.zoom;
const cY=Math.cos(st.angleY),sY=Math.sin(st.angleY);
const cX=Math.cos(st.angleX),sX=Math.sin(st.angleX);
function project(v){
const x1=v.x*cY-v.z*sY;
const z1=v.x*sY+v.z*cY;
const y1=v.y*cX-z1*sX;
const z2=v.y*sX+z1*cX;
const d=6;const f=d/(d+z2/maxExt*2);
return{x:cx+x1*scale*f,y:cy-y1*scale*f,z:z2};
}
const pv=verts.map(project);
const pf=faces.map(function(f){return {idx:f,avgZ:f.reduce(function(s,i){return s+(pv[i]?pv[i].z:0)},0)/f.length}}).filter(function(f){return f.idx.every(function(i){return pv[i]})});
pf.sort(function(a,b){return a.avgZ-b.avgZ});
for(const face of pf){
ctx.beginPath();
face.idx.forEach(function(idx,i){const p=pv[idx];if(i===0)ctx.moveTo(p.x,p.y);else ctx.lineTo(p.x,p.y)});
ctx.closePath();
const t=(face.avgZ+maxExt*2)/(maxExt*4);
const hue=40+t*180;
ctx.fillStyle='hsla('+hue+',45%,45%,0.5)';
ctx.strokeStyle=mesh.color;ctx.lineWidth=1.2;ctx.fill();ctx.stroke();
}
ctx.fillStyle='rgba(120,120,130,0.5)';ctx.font='10px ui-monospace,monospace';ctx.textAlign='left';
ctx.fillText(mesh.name+' · '+verts.length+'v '+faces.length+'f',10,H-10);
}
function parseShape3D(d){
const r={type:'cube',size:100,color:'#d4a04a'};
for(const l of d.split('\n').map(function(x){return x.trim()}).filter(Boolean)){
const m=l.match(/^(\w+)\s*:\s*(.+)$/);if(!m)continue;
const v=m[2].trim();
if(m[1]==='type')r.type=v;else if(m[1]==='size')r.size=parseFloat(v)||100;else if(m[1]==='color')r.color=v;
}
return r;
}
function genShape3D(shape){
const s=shape.size/100;const verts=[],faces=[];const t=shape.type;
if(t==='cube'||!t){
for(const x of[-1,1])for(const y of[-1,1])for(const z of[-1,1])verts.push({x:x*s,y:y*s,z:z*s});
faces.push([0,1,3,2],[4,6,7,5],[0,2,6,4],[1,5,7,3],[0,4,5,1],[2,3,7,6]);
}else if(t==='sphere'){
const seg=16,rings=12;
for(let i=0;i<=rings;i++){const phi=i*Math.PI/rings;for(let j=0;j<=seg;j++){const th=j*Math.PI*2/seg;verts.push({x:s*Math.sin(phi)*Math.cos(th),y:s*Math.cos(phi),z:s*Math.sin(phi)*Math.sin(th)})}}
for(let i=0;i<rings;i++)for(let j=0;j<seg;j++)faces.push([i*(seg+1)+j,i*(seg+1)+j+1,(i+1)*(seg+1)+j+1,(i+1)*(seg+1)+j]);
}else if(t==='pyramid'){
for(let i=0;i<4;i++){const a=i*Math.PI/2+Math.PI/4;verts.push({x:s*Math.cos(a),y:-s,z:s*Math.sin(a)})}
verts.push({x:0,y:s,z:0});
for(let i=0;i<4;i++)faces.push([i,(i+1)%4,4]);
faces.push([0,1,2,3]);
}else if(t==='tetrahedron'){
verts.push({x:s,y:s,z:s},{x:s,y:-s,z:-s},{x:-s,y:s,z:-s},{x:-s,y:-s,z:s});
faces.push([0,1,2],[0,1,3],[0,2,3],[1,2,3]);
}else if(t==='octahedron'){
verts.push({x:s,y:0,z:0},{x:-s,y:0,z:0},{x:0,y:s,z:0},{x:0,y:-s,z:0},{x:0,y:0,z:s},{x:0,y:0,z:-s});
faces.push([0,2,4],[0,2,5],[0,3,4],[0,3,5],[1,2,4],[1,2,5],[1,3,4],[1,3,5]);
}else if(t==='cylinder'){
const seg=16,r=s,h=s*1.5;
for(let j=0;j<seg;j++){const a=j*Math.PI*2/seg;verts.push({x:r*Math.cos(a),y:-h,z:r*Math.sin(a)});verts.push({x:r*Math.cos(a),y:h,z:r*Math.sin(a)})}
for(let j=0;j<seg;j++){const a=j*2,b=((j+1)%seg)*2;faces.push([a,b,b+1,a+1])}
}else if(t==='cone'){
const seg=16,r=s,h=s*1.5;
for(let j=0;j<seg;j++){const a=j*Math.PI*2/seg;verts.push({x:r*Math.cos(a),y:-h,z:r*Math.sin(a)})}
verts.push({x:0,y:h,z:0});
for(let j=0;j<seg;j++)faces.push([j,(j+1)%seg,seg]);
const base=[];for(let j=0;j<seg;j++)base.push(j);faces.push(base);
}else if(t==='torus'){
const R=s,rr=s*0.35,segU=20,segV=12;
for(let i=0;i<segU;i++){const u=i*Math.PI*2/segU;for(let j=0;j<segV;j++){const v=j*Math.PI*2/segV;verts.push({x:(R+rr*Math.cos(v))*Math.cos(u),y:rr*Math.sin(v),z:(R+rr*Math.cos(v))*Math.sin(u)})}}
for(let i=0;i<segU;i++)for(let j=0;j<segV;j++){const a=i*segV+j,b=i*segV+(j+1)%segV,c=((i+1)%segU)*segV+(j+1)%segV,d=((i+1)%segU)*segV+j;faces.push([a,b,c,d])}
}else if(t==='dodecahedron'||t==='icosahedron'){
const phi=(1+Math.sqrt(5))/2;const a=s,b=s/phi;
verts.push({x:-a,y:-a,z:-a},{x:-a,y:-a,z:a},{x:-a,y:a,z:-a},{x:-a,y:a,z:a},{x:a,y:-a,z:-a},{x:a,y:-a,z:a},{x:a,y:a,z:-a},{x:a,y:a,z:a},{x:0,y:-b,z:-phi*a},{x:0,y:-b,z:phi*a},{x:0,y:b,z:-phi*a},{x:0,y:b,z:phi*a},{x:-b,y:-phi*a,z:0},{x:-b,y:phi*a,z:0},{x:b,y:-phi*a,z:0},{x:b,y:phi*a,z:0},{x:-phi*a,y:0,z:-b},{x:-phi*a,y:0,z:b},{x:phi*a,y:0,z:-b},{x:phi*a,y:0,z:b});
faces.push([0,16,2],[0,2,10],[0,10,8],[0,8,4],[0,4,16],[1,17,3],[1,3,11],[1,11,9],[1,9,5],[1,5,17],[2,16,6],[2,6,12],[2,12,10],[3,17,7],[3,7,13],[3,13,11],[4,14,6],[4,6,18],[4,18,16],[5,19,7],[5,7,15],[5,15,14],[6,14,18],[7,19,15],[8,10,12],[8,12,14],[9,11,13],[9,13,15],[10,12,14],[11,13,15],[16,18,14],[17,19,15]);
}else{
for(const x of[-1,1])for(const y of[-1,1])for(const z of[-1,1])verts.push({x:x*s,y:y*s,z:z*s});
faces.push([0,1,3,2],[4,6,7,5],[0,2,6,4],[1,5,7,3],[0,4,5,1],[2,3,7,6]);
}
return {verts:verts,faces:faces};
}
function setupShape3D(canvas,shape){
const g=genShape3D(shape);
const st={angleY:0.7,angleX:-0.5,zoom:1,dragging:false,lastX:0,lastY:0};
view3dState.set(canvas,st);
function draw(){drawShape3D(canvas,g.verts,g.faces,shape,st)}
canvas.addEventListener('mousedown',function(e){st.dragging=true;st.lastX=e.clientX;st.lastY=e.clientY});
canvas.addEventListener('mousemove',function(e){if(!st.dragging)return;const dx=e.clientX-st.lastX,dy=e.clientY-st.lastY;st.lastX=e.clientX;st.lastY=e.clientY;st.angleY+=dx*0.01;st.angleX=Math.max(-1.5,Math.min(1.5,st.angleX+dy*0.01));draw()});
canvas.addEventListener('mouseup',function(){st.dragging=false});
canvas.addEventListener('mouseleave',function(){st.dragging=false});
canvas.addEventListener('wheel',function(e){e.preventDefault();st.zoom=Math.max(0.3,Math.min(3,st.zoom*(e.deltaY>0?0.9:1.1)));draw()},{passive:false});
draw();
}
function drawShape3D(canvas,verts,faces,shape,st){
const W=canvas.parentElement.clientWidth||400,H=320;
const dpr=window.devicePixelRatio||1;
canvas.width=W*dpr;canvas.height=H*dpr;canvas.style.width=W+'px';canvas.style.height=H+'px';
const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
const cx=W/2,cy=H/2;
const scale=Math.min(W,H)/4*st.zoom;
const cY=Math.cos(st.angleY),sY=Math.sin(st.angleY);
const cX=Math.cos(st.angleX),sX=Math.sin(st.angleX);
function project(v){
const x1=v.x*cY-v.z*sY;
const z1=v.x*sY+v.z*cY;
const y1=v.y*cX-z1*sX;
const z2=v.y*sX+z1*cX;
const d=5;const f=d/(d+z2);
return{x:cx+x1*scale*f,y:cy-y1*scale*f,z:z2};
}
const pv=verts.map(project);
const pf=faces.map(function(f){return {idx:f,avgZ:f.reduce(function(s,i){return s+pv[i].z},0)/f.length}});
pf.sort(function(a,b){return a.avgZ-b.avgZ});
for(const face of pf){
ctx.beginPath();
face.idx.forEach(function(idx,i){const p=pv[idx];if(i===0)ctx.moveTo(p.x,p.y);else ctx.lineTo(p.x,p.y)});
ctx.closePath();
const t=(face.avgZ+1.5)/3;
const hue=40+t*200;
ctx.fillStyle='hsla('+hue+',45%,45%,0.5)';
ctx.strokeStyle=shape.color;ctx.lineWidth=1.2;ctx.fill();ctx.stroke();
}
for(const p of pv){ctx.beginPath();ctx.arc(p.x,p.y,2,0,Math.PI*2);ctx.fillStyle=shape.color;ctx.fill()}
ctx.fillStyle='rgba(120,120,130,0.5)';ctx.font='10px ui-monospace,monospace';ctx.textAlign='left';
ctx.fillText(shape.type+' · тяни/колесо',10,H-10);
}

function parseAero(d){
const r={shape:'airfoil',speed:1,angle:5,objects:[]};
for(const l of d.split('\n').map(function(x){return x.trim()}).filter(Boolean)){
const m=l.match(/^(\w+)\s*:\s*(.+)$/);if(!m)continue;
const k=m[1],v=m[2].trim();
if(k==='shape')r.shape=v;
else if(k==='speed')r.speed=parseFloat(v)||1;
else if(k==='angle')r.angle=parseFloat(v)||0;
else if(k==='objects')r.objects=v.split(',').map(function(s){return s.trim()}).filter(Boolean);
}
if(!r.objects.length)r.objects=[r.shape];
return r;
}
function setupAero(canvas,cfg){
const W=canvas.parentElement.clientWidth||600,H=340;
const dpr=window.devicePixelRatio||1;
canvas.width=W*dpr;canvas.height=H*dpr;canvas.style.width=W+'px';canvas.style.height=H+'px';
const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);
const st={angleY:0.4,angleX:-0.3,zoom:1,dragging:false,lastX:0,lastY:0,speed:cfg.speed,angle:cfg.angle,objects:cfg.objects.map(function(t,i){return {type:t,x:-15+i*20,y:(i%2===0?0:8),z:0,size:12}}),running:true};
view3dState.set(canvas,st);
canvas.addEventListener('mousedown',function(e){st.dragging=true;st.lastX=e.clientX;st.lastY=e.clientY});
canvas.addEventListener('mousemove',function(e){if(!st.dragging)return;const dx=e.clientX-st.lastX,dy=e.clientY-st.lastY;st.lastX=e.clientX;st.lastY=e.clientY;st.angleY+=dx*0.01;st.angleX=Math.max(-1.3,Math.min(1.3,st.angleX+dy*0.01))});
canvas.addEventListener('mouseup',function(){st.dragging=false});
canvas.addEventListener('mouseleave',function(){st.dragging=false});
canvas.addEventListener('wheel',function(e){e.preventDefault();st.zoom=Math.max(0.4,Math.min(3,st.zoom*(e.deltaY>0?0.9:1.1)))},{passive:false});
const particles=[];
for(let i=0;i<180;i++)particles.push({x:-60+Math.random()*120,y:(Math.random()-0.5)*50,z:(Math.random()-0.5)*50,vx:st.speed*3,vy:0,vz:0,life:Math.random()*200});
const cx=W/2,cy=H/2;
function project(x,y,z){
const cY=Math.cos(st.angleY),sY=Math.sin(st.angleY);
const cX=Math.cos(st.angleX),sX=Math.sin(st.angleX);
const x1=x*cY-z*sY;const z1=x*sY+z*cY;
const y1=y*cX-z1*sX;const z2=y*sX+z1*cX;
const d=80;const f=d/(d+z2);
const scale=Math.min(W,H)/30*st.zoom;
return{x:cx+x1*scale*f,y:cy+y1*scale*f,z:z2};
}
function insideShape(x,y,z,obj){
const dx=x-obj.x,dy=y-obj.y,dz=z-obj.z;
const s=obj.size;
if(obj.type==='sphere')return dx*dx+dy*dy+dz*dz<s*s;
if(obj.type==='cube')return Math.abs(dx)<s&&Math.abs(dy)<s&&Math.abs(dz)<s;
if(obj.type==='cylinder'){const rr=Math.sqrt(dx*dx+dz*dz);return rr<s&&Math.abs(dy)<s*1.2}
if(obj.type==='airfoil'){const flat=Math.abs(dz)<s*0.4;const profile=(dx/s)*(dx/s)+(dy/s)*(dy/s)<1.2;return flat&&profile}
if(obj.type==='circle')return Math.sqrt(dx*dx+dy*dy)<s;
if(obj.type==='square')return Math.abs(dx)<s&&Math.abs(dy)<s;
if(obj.type==='diamond')return Math.abs(dx)+Math.abs(dy)<s*1.5;
if(obj.type==='triangle')return dy>-s&&dy<s&&Math.abs(dx)<(s-dy)*0.6;
return false;
}
function drawWireframe(obj){
const s=obj.size;
ctx.strokeStyle='rgba(127,200,232,0.5)';ctx.lineWidth=1.2;
if(obj.type==='sphere'){
const rings=8,segs=12;
for(let i=0;i<=rings;i++){
ctx.beginPath();
const phi=i*Math.PI/rings;
for(let j=0;j<=segs;j++){
const th=j*Math.PI*2/segs;
const p=project(obj.x+s*Math.sin(phi)*Math.cos(th),obj.y+s*Math.cos(phi),obj.z+s*Math.sin(phi)*Math.sin(th));
if(j===0)ctx.moveTo(p.x,p.y);else ctx.lineTo(p.x,p.y);
}
ctx.stroke();
}
}else if(obj.type==='cube'||obj.type==='square'){
const V=[[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]];
const proj=V.map(function(v){return project(obj.x+v[0]*s,obj.y+v[1]*s,obj.z+v[2]*s)});
const E=[[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]];
for(const e of E){ctx.beginPath();ctx.moveTo(proj[e[0]].x,proj[e[0]].y);ctx.lineTo(proj[e[1]].x,proj[e[1]].y);ctx.stroke()}
}else if(obj.type==='airfoil'){
for(const zoff of [-s*0.3,s*0.3]){
ctx.beginPath();
for(let i=0;i<=20;i++){
const t=i/20;
const xx=-s+2*s*t;
const yy=-s*0.15+Math.sin(t*Math.PI)*s*0.35-s*0.1;
const p=project(obj.x+xx,obj.y+yy,obj.z+zoff);
if(i===0)ctx.moveTo(p.x,p.y);else ctx.lineTo(p.x,p.y);
}
ctx.stroke();
ctx.beginPath();
for(let i=0;i<=20;i++){
const t=i/20;
const xx=-s+2*s*t;
const yy=s*0.05+Math.sin(t*Math.PI)*s*0.15-s*0.05;
const p=project(obj.x+xx,obj.y+yy,obj.z+zoff);
if(i===0)ctx.moveTo(p.x,p.y);else ctx.lineTo(p.x,p.y);
}
ctx.stroke();
}
}else if(obj.type==='circle'){
ctx.beginPath();
for(let j=0;j<=20;j++){
const a=j*Math.PI*2/20;
const p=project(obj.x+s*Math.cos(a),obj.y+s*Math.sin(a),obj.z);
if(j===0)ctx.moveTo(p.x,p.y);else ctx.lineTo(p.x,p.y);
}
ctx.stroke();
}else if(obj.type==='cylinder'){
const seg=16;
const top=[],bot=[];
for(let j=0;j<=seg;j++){
const a=j*Math.PI*2/seg;
top.push(project(obj.x+s*Math.cos(a),obj.y+s*1.2,obj.z+s*Math.sin(a)));
bot.push(project(obj.x+s*Math.cos(a),obj.y-s*1.2,obj.z+s*Math.sin(a)));
}
for(let j=0;j<=seg;j++){ctx.beginPath();ctx.moveTo(top[j].x,top[j].y);ctx.lineTo(bot[j].x,bot[j].y);ctx.stroke()}
ctx.beginPath();top.forEach(function(p,i){if(i===0)ctx.moveTo(p.x,p.y);else ctx.lineTo(p.x,p.y)});ctx.stroke();
ctx.beginPath();bot.forEach(function(p,i){if(i===0)ctx.moveTo(p.x,p.y);else ctx.lineTo(p.x,p.y)});ctx.stroke();
}else if(obj.type==='diamond'||obj.type==='triangle'){
const verts=obj.type==='diamond'?[[0,-s],[s,0],[0,s],[-s,0]]:[[0,-s],[s*0.9,s*0.9],[-s*0.9,s*0.9]];
const proj=verts.map(function(v){return project(obj.x+v[0],obj.y+v[1],obj.z)});
ctx.beginPath();
proj.forEach(function(p,i){if(i===0)ctx.moveTo(p.x,p.y);else ctx.lineTo(p.x,p.y)});
ctx.closePath();ctx.stroke();
}
}
function loop(){
ctx.fillStyle='rgba(6,10,16,0.18)';ctx.fillRect(0,0,W,H);
ctx.strokeStyle='rgba(127,200,232,0.08)';ctx.lineWidth=1;
for(let k=0;k<8;k++){
ctx.beginPath();
for(let i=0;i<=30;i++){
const p=project(-60+i*4,-30+k*10,0);
if(i===0)ctx.moveTo(p.x,p.y);else ctx.lineTo(p.x,p.y);
}
ctx.stroke();
}
for(const obj of st.objects)drawWireframe(obj);
for(const p of particles){
for(const obj of st.objects){
const dx=p.x-obj.x,dy=p.y-obj.y,dz=p.z-obj.z;
const d2=dx*dx+dy*dy+dz*dz;
if(d2<obj.size*obj.size*6){
const d=Math.sqrt(d2)||0.1;
const f=80/d2;
p.vx-=dx/d*f*0.3;
p.vy+=dy/d*f;
p.vz+=dz/d*f;
}
}
p.vx=Math.max(0.5,Math.min(8,p.vx*0.98+st.speed*0.12));
p.vy*=0.97;p.vz*=0.97;
p.x+=p.vx;p.y+=p.vy;p.z+=p.vz;
p.life++;
for(const obj of st.objects){
if(insideShape(p.x,p.y,p.z,obj)){
const dx=p.x-obj.x,dy=p.y-obj.y,dz=p.z-obj.z;
const d=Math.sqrt(dx*dx+dy*dy+dz*dz)||1;
p.x=obj.x+dx/d*obj.size*1.3;
p.y=obj.y+dy/d*obj.size*1.3;
p.z=obj.z+dz/d*obj.size*1.3;
break;
}
}
if(p.x>60){p.x=-60;p.y=(Math.random()-0.5)*50;p.z=(Math.random()-0.5)*50;p.vy=0;p.vz=0;p.vx=st.speed*3;p.life=0}
const pp=project(p.x,p.y,p.z);
const prev=project(p.x-p.vx*2,p.y-p.vy*2,p.z-p.vz*2);
const sp=Math.hypot(p.vx,p.vy,p.vz);
const al=Math.min(0.8,sp*0.2);
ctx.strokeStyle='rgba(127,200,232,'+(al*0.5)+')';
ctx.lineWidth=1.2;
ctx.beginPath();ctx.moveTo(prev.x,prev.y);ctx.lineTo(pp.x,pp.y);ctx.stroke();
ctx.fillStyle='rgba(180,230,255,'+al+')';
ctx.beginPath();ctx.arc(pp.x,pp.y,1.8,0,Math.PI*2);ctx.fill();
}
ctx.fillStyle='rgba(127,200,232,0.85)';ctx.font='11px ui-monospace,monospace';ctx.textAlign='left';
ctx.fillText('aero 3d · wind '+st.speed.toFixed(1)+' · objects: '+st.objects.map(function(o){return o.type}).join(', '),12,20);
if(st.running)requestAnimationFrame(loop);
}
loop();
}

const MATHF=['sin','cos','tan','asin','acos','atan','sinh','cosh','tanh','sqrt','cbrt','abs','exp','log','log2','log10','floor','ceil','round','sign','min','max','pow'];
const MATHC={'pi':'Math.PI','tau':'(Math.PI*2)','phi':'1.618033988749895','e':'Math.E'};
function compileExpr(e){
if(!e)return null;
let js=e.replace(/\^/g,'**');
for(const f of MATHF)js=js.replace(new RegExp('\\b'+f+'\\b','g'),'Math.'+f);
js=js.replace(/\b(pi|tau|phi|inf|infinity)\b/g,function(m){return MATHC[m]||m});
js=js.replace(/(?<![a-zA-Z.])e\b/g,'Math.E');
js=js.replace(/\bln\b/g,'Math.log');
try{return new Function('x','y','with (Math) { return ('+js+'); }')}catch(err){return null}
}
function parseGraph2D(d){
const lines=d.split('\n').map(function(l){return l.trim()}).filter(Boolean);
let expr='',range=[-5,5];
for(const l of lines){
const m=l.match(/f\s*\(\s*x\s*\)\s*=\s*(.+)/i);
if(m){expr=m[1].trim();continue}
const r=l.match(/range\s*:\s*(-?[\d.]+)\s*\.\.\s*(-?[\d.]+)/i);
if(r)range=[parseFloat(r[1]),parseFloat(r[2])];
}
return {expr:expr,range:range,fn:compileExpr(expr)};
}
function parseGraph3D(d){
const lines=d.split('\n').map(function(l){return l.trim()}).filter(Boolean);
let expr='',range=[-3,3];
for(const l of lines){
const m=l.match(/f\s*\(\s*x\s*,\s*y\s*\)\s*=\s*(.+)/i);
if(m){expr=m[1].trim();continue}
const r=l.match(/range\s*:\s*(-?[\d.]+)\s*\.\.\s*(-?[\d.]+)/i);
if(r)range=[parseFloat(r[1]),parseFloat(r[2])];
}
return {expr:expr,range:range,fn:compileExpr(expr)};
}
function drawChart(canvas,type,data){
const lines=data.split('\n').map(function(l){return l.trim()}).filter(Boolean);
const points=[];
for(const l of lines){const m=l.match(/^(.+?):\s*(-?[\d.]+)\s*$/);if(m)points.push({label:m[1].trim(),value:parseFloat(m[2])})}
if(!points.length)return;
const W=canvas.parentElement.clientWidth||600,H=240;
const dpr=window.devicePixelRatio||1;
canvas.width=W*dpr;canvas.height=H*dpr;canvas.style.width=W+'px';canvas.style.height=H+'px';
const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
ctx.font='11px ui-monospace,monospace';ctx.textBaseline='middle';
const padL=50,padR=20,padT=20,padB=40;
const iW=W-padL-padR,iH=H-padT-padB;
if(type==='pie'){
const total=points.reduce(function(s,p){return s+Math.abs(p.value)},0)||1;
const cx=padL+iW/2,cy=padT+iH/2;const r=Math.min(iW,iH)/2-10;
const colors=['#d4a04a','#6db87d','#5fb0e0','#a17fe0','#d87878','#78a8d4','#d4987a','#c8b87a'];
let start=-Math.PI/2;
points.forEach(function(p,i){
const angle=(Math.abs(p.value)/total)*Math.PI*2;
ctx.beginPath();ctx.moveTo(cx,cy);ctx.arc(cx,cy,r,start,start+angle);ctx.closePath();
ctx.fillStyle=colors[i%colors.length];ctx.fill();
ctx.strokeStyle='#08080a';ctx.lineWidth=2;ctx.stroke();
start+=angle;
});
return;
}
const maxV=Math.max.apply(null,points.map(function(p){return p.value}).concat([0]));
const minV=Math.min.apply(null,points.map(function(p){return p.value}).concat([0]));
const range=maxV-minV||1;
const zeroY=padT+iH-((0-minV)/range)*iH;
ctx.strokeStyle='#202026';ctx.lineWidth=1;
for(let i=0;i<=4;i++){const y=padT+(iH/4)*i;ctx.beginPath();ctx.moveTo(padL,y);ctx.lineTo(W-padR,y);ctx.stroke();ctx.fillStyle='#43434d';ctx.textAlign='right';ctx.fillText((maxV-(range/4)*i).toFixed(1),padL-6,y)}
const step=iW/points.length;const barW=Math.min(step*0.7,60);
if(type==='bar'){
points.forEach(function(p,i){
const x=padL+step*i+step/2;
const y1=zeroY,y2=padT+iH-((p.value-minV)/range)*iH;
ctx.fillStyle='#d4a04a';ctx.fillRect(x-barW/2,Math.min(y1,y2),barW,Math.abs(y2-y1));
ctx.fillStyle='#d4d4dc';ctx.textAlign='center';ctx.fillText(p.value.toString(),x,Math.min(y1,y2)-8);
ctx.fillStyle='#666670';ctx.fillText(p.label.slice(0,12),x,padT+iH+14);
});
}else if(type==='line'||type==='scatter'){
const coords=points.map(function(p,i){return {x:padL+step*i+step/2,y:padT+iH-((p.value-minV)/range)*iH,label:p.label,value:p.value}});
if(type==='line'){ctx.strokeStyle='#d4a04a';ctx.lineWidth=2;ctx.beginPath();coords.forEach(function(c,i){if(i===0)ctx.moveTo(c.x,c.y);else ctx.lineTo(c.x,c.y)});ctx.stroke()}
coords.forEach(function(c){ctx.fillStyle='#d4a04a';ctx.beginPath();ctx.arc(c.x,c.y,4,0,Math.PI*2);ctx.fill();ctx.fillStyle='#666670';ctx.textAlign='center';ctx.fillText(c.label.slice(0,12),c.x,padT+iH+14)});
}
}
function drawGraph2D(canvas,info){
if(!info||!canvas)return;
const W=canvas.parentElement.clientWidth||600,H=260;
const dpr=window.devicePixelRatio||1;
canvas.width=W*dpr;canvas.height=H*dpr;canvas.style.width=W+'px';canvas.style.height=H+'px';
const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
const pad=30,iW=W-2*pad,iH=H-2*pad;
const rng=info.range,xmin=rng[0],xmax=rng[1];
const N=500,samples=[];
let ymin=Infinity,ymax=-Infinity;
if(info.fn){
for(let i=0;i<=N;i++){
const x=xmin+(xmax-xmin)*i/N;
let y;try{y=info.fn(x,0)}catch(err){y=NaN}
if(typeof y==='number'&&isFinite(y)){samples.push({x:x,y:y});if(y<ymin)ymin=y;if(y>ymax)ymax=y}
else samples.push({x:x,y:NaN});
}
}
if(!isFinite(ymin)){ymin=-10;ymax=10}
const padY=(ymax-ymin)*0.1||1;ymin-=padY;ymax+=padY;
function toSX(x){return pad+((x-xmin)/(xmax-xmin))*iW}
function toSY(y){return pad+iH-((y-ymin)/(ymax-ymin))*iH}
ctx.strokeStyle='#202026';ctx.lineWidth=1;ctx.font='10px ui-monospace,monospace';
for(let i=0;i<=8;i++){const x=pad+(iW/8)*i;ctx.beginPath();ctx.moveTo(x,pad);ctx.lineTo(x,pad+iH);ctx.stroke();ctx.fillStyle='#43434d';ctx.textAlign='center';ctx.fillText((xmin+(xmax-xmin)*i/8).toFixed(1),x,pad+iH+12)}
for(let i=0;i<=6;i++){const y=pad+(iH/6)*i;ctx.beginPath();ctx.moveTo(pad,y);ctx.lineTo(pad+iW,y);ctx.stroke();ctx.fillStyle='#43434d';ctx.textAlign='right';ctx.fillText((ymax-(ymax-ymin)*i/6).toFixed(1),pad-4,y+3)}
ctx.strokeStyle='#6db87d';ctx.lineWidth=2;ctx.beginPath();
let started=false;
samples.forEach(function(s){
if(!isFinite(s.y)){started=false;return}
const sx=toSX(s.x),sy=toSY(s.y);
if(sy<pad-200||sy>pad+iH+200){started=false;return}
if(!started){ctx.moveTo(sx,sy);started=true}else ctx.lineTo(sx,sy);
});
ctx.stroke();
}
function setupGraph3D(canvas,info){
const st={angleY:Math.PI/5,angleX:Math.PI/7,zoom:1,dragging:false,lastX:0,lastY:0};
view3dState.set(canvas,st);
function draw(){drawGraph3D(canvas,info)}
canvas.addEventListener('mousedown',function(e){st.dragging=true;st.lastX=e.clientX;st.lastY=e.clientY});
canvas.addEventListener('mousemove',function(e){if(!st.dragging)return;const dx=e.clientX-st.lastX,dy=e.clientY-st.lastY;st.lastX=e.clientX;st.lastY=e.clientY;st.angleY+=dx*0.01;st.angleX=Math.max(-1.5,Math.min(1.5,st.angleX+dy*0.01));draw()});
canvas.addEventListener('mouseup',function(){st.dragging=false});
canvas.addEventListener('mouseleave',function(){st.dragging=false});
canvas.addEventListener('wheel',function(e){e.preventDefault();st.zoom=Math.max(0.3,Math.min(3,st.zoom*(e.deltaY>0?0.9:1.1)));draw()},{passive:false});
draw();
}
function drawGraph3D(canvas,info){
if(!info||!canvas)return;
const st=view3dState.get(canvas)||{angleY:Math.PI/5,angleX:Math.PI/7,zoom:1};
const W=canvas.parentElement.clientWidth||600,H=320;
const dpr=window.devicePixelRatio||1;
canvas.width=W*dpr;canvas.height=H*dpr;canvas.style.width=W+'px';canvas.style.height=H+'px';
const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
const N=30,rng=info.range,xmin=rng[0],xmax=rng[1],ymin=rng[0],ymax=rng[1];
const grid=[];
let zmin=Infinity,zmax=-Infinity;
for(let i=0;i<=N;i++){
const row=[],x=xmin+(xmax-xmin)*i/N;
for(let j=0;j<=N;j++){
const y=ymin+(ymax-ymin)*j/N;
let z;try{z=info.fn?info.fn(x,y):0}catch(err){z=NaN}
if(typeof z!=='number'||!isFinite(z))z=NaN;
row.push({x:x,y:y,z:z});
if(isFinite(z)){if(z<zmin)zmin=z;if(z>zmax)zmax=z}
}
grid.push(row);
}
if(!isFinite(zmin)){zmin=-1;zmax=1}
const zRange=zmax-zmin||1;
const cx=W/2,cy=H/2;
const scale=Math.min(W,H)/(2*Math.max(xmax-xmin,ymax-ymin))*0.75*st.zoom;
const cY=Math.cos(st.angleY),sY=Math.sin(st.angleY);
const cX=Math.cos(st.angleX),sX=Math.sin(st.angleX);
function project(p){
const nx=p.x-(xmin+xmax)/2,ny=p.y-(ymin+ymax)/2,nz=((p.z-(zmin+zmax)/2)/zRange)*3;
const x1=nx*cY-nz*sY;const z1=nx*sY+nz*cY;
const y1=ny*cX-z1*sX;const z2=ny*sX+z1*cX;
return{sx:cx+x1*scale,sy:cy+y1*scale,depth:z2};
}
const lines=[];
for(let i=0;i<=N;i++)for(let j=0;j<=N;j++){if(i<N)lines.push([grid[i][j],grid[i+1][j]]);if(j<N)lines.push([grid[i][j],grid[i][j+1]])}
const proj=lines.map(function(l){const p1=project(l[0]),p2=project(l[1]);const avgDepth=(p1.depth+p2.depth)/2;const avgZ=((isFinite(l[0].z)?l[0].z:0)+(isFinite(l[1].z)?l[1].z:0))/2;return{p1:p1,p2:p2,depth:avgDepth,z:avgZ}});
proj.sort(function(a,b){return a.depth-b.depth});
for(const line of proj){
const t=(line.z-zmin)/zRange;
const hue=200-t*140,light=35+t*35;
ctx.strokeStyle='hsl('+hue+',55%,'+light+'%)';
ctx.lineWidth=1;
ctx.beginPath();ctx.moveTo(line.p1.sx,line.p1.sy);ctx.lineTo(line.p2.sx,line.p2.sy);ctx.stroke();
}
ctx.fillStyle='rgba(120,120,130,0.4)';ctx.font='10px ui-monospace,monospace';ctx.textAlign='left';
ctx.fillText('тяни/колесо',10,H-10);
}
function setupGraphNet(canvas,data,containerEl){
const nodes=data.nodes.map(function(n,i){return {id:n.id,label:n.label||n.id,x:Math.cos(i*Math.PI*2/data.nodes.length)*100+(Math.random()-0.5)*40,y:Math.sin(i*Math.PI*2/data.nodes.length)*100+(Math.random()-0.5)*40,z:(Math.random()-0.5)*100,vx:0,vy:0,vz:0}});
const nm=new Map(nodes.map(function(n){return [n.id,n]}));
const links=data.links.map(function(l){return {source:nm.get(l.source),target:nm.get(l.target),label:l.label}}).filter(function(l){return l.source&&l.target});
const st={mode:'2d',angleY:0,angleX:0,zoom:1,dragging:false,lastX:0,lastY:0,draggingNode:null,iter:0,nodes:nodes,links:links,panX:0,panY:0};
view3dState.set(canvas,st);
function step(){
if(st.iter>150)return;st.iter++;
for(let i=0;i<nodes.length;i++)for(let j=i+1;j<nodes.length;j++){
const a=nodes[i],b=nodes[j];let dx=a.x-b.x,dy=a.y-b.y,dz=a.z-b.z;
let d2=dx*dx+dy*dy+dz*dz;if(d2<1)d2=1;
const f=800/d2,d=Math.sqrt(d2);
dx/=d;dy/=d;dz/=d;
a.vx+=dx*f;a.vy+=dy*f;a.vz+=dz*f;
b.vx-=dx*f;b.vy-=dy*f;b.vz-=dz*f;
}
for(const l of links){const dx=l.target.x-l.source.x,dy=l.target.y-l.source.y,dz=l.target.z-l.source.z;const d=Math.sqrt(dx*dx+dy*dy+dz*dz)||1;const f=(d-80)*0.02;l.source.vx+=(dx/d)*f;l.source.vy+=(dy/d)*f;l.source.vz+=(dz/d)*f;l.target.vx-=(dx/d)*f;l.target.vy-=(dy/d)*f;l.target.vz-=(dz/d)*f}
for(const n of nodes){n.vx-=n.x*0.005;n.vy-=n.y*0.005;n.vz-=n.z*0.005}
for(const n of nodes){if(n===st.draggingNode){n.vx=n.vy=n.vz=0;continue}n.vx*=0.85;n.vy*=0.85;n.vz*=0.85;n.x+=n.vx;n.y+=n.vy;n.z+=n.vz}
}
function getM(e){const r=canvas.getBoundingClientRect();return{x:e.clientX-r.left,y:e.clientY-r.top}}
canvas.addEventListener('mousedown',function(e){
const m=getM(e);const W=canvas.clientWidth,H=canvas.clientHeight;
const cx=W/2,cy=H/2,scale=Math.min(W,H)/500*st.zoom;
let hit=null,best=15;
for(const n of nodes){
let px,py;
if(st.mode==='2d'){px=cx+n.x*scale+st.panX;py=cy+n.y*scale+st.panY}
else{const x1=n.x*Math.cos(st.angleY)-n.z*Math.sin(st.angleY);const z1=n.x*Math.sin(st.angleY)+n.z*Math.cos(st.angleY);const y1=n.y*Math.cos(st.angleX)-z1*Math.sin(st.angleX);px=cx+x1*scale+st.panX;py=cy+y1*scale+st.panY}
const d=Math.hypot(m.x-px,m.y-py);
if(d<best){best=d;hit=n}
}
if(hit)st.draggingNode=hit;else st.dragging=true;
st.lastX=e.clientX;st.lastY=e.clientY;e.preventDefault();
});
canvas.addEventListener('mousemove',function(e){
const W=canvas.clientWidth,H=canvas.clientHeight;
if(st.draggingNode){const dx=e.clientX-st.lastX,dy=e.clientY-st.lastY;st.lastX=e.clientX;st.lastY=e.clientY;const scale=Math.min(W,H)/500*st.zoom;st.draggingNode.x+=dx/scale;st.draggingNode.y+=dy/scale;drawGraphNet(canvas,st)}
else if(st.dragging){const dx=e.clientX-st.lastX,dy=e.clientY-st.lastY;st.lastX=e.clientX;st.lastY=e.clientY;if(st.mode==='3d'){st.angleY+=dx*0.01;st.angleX=Math.max(-Math.PI/2+0.1,Math.min(Math.PI/2-0.1,st.angleX+dy*0.01))}else{st.panX+=dx;st.panY+=dy}drawGraphNet(canvas,st)}
});
canvas.addEventListener('mouseup',function(){st.dragging=false;st.draggingNode=null});
canvas.addEventListener('mouseleave',function(){st.dragging=false;st.draggingNode=null});
canvas.addEventListener('wheel',function(e){e.preventDefault();st.zoom=Math.max(0.3,Math.min(4,st.zoom*(e.deltaY>0?0.9:1.1)));drawGraphNet(canvas,st)},{passive:false});
let a=0;
function animate(){step();drawGraphNet(canvas,st);a++;if(a<200&&!st.dragging)requestAnimationFrame(animate)}
new ResizeObserver(function(){drawGraphNet(canvas,st)}).observe(canvas.parentElement);
animate();
}
function drawGraphNet(canvas,st){
const W=canvas.clientWidth||600,H=360;
const dpr=window.devicePixelRatio||1;
if(canvas.width!==W*dpr){canvas.width=W*dpr;canvas.height=H*dpr}
canvas.style.height=H+'px';
const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
const cx=W/2,cy=H/2,scale=Math.min(W,H)/500*st.zoom;
const px=st.panX||0,py=st.panY||0;
function project(n){
if(st.mode==='2d')return{x:cx+n.x*scale+px,y:cy+n.y*scale+py,depth:0};
const x1=n.x*Math.cos(st.angleY)-n.z*Math.sin(st.angleY);
const z1=n.x*Math.sin(st.angleY)+n.z*Math.cos(st.angleY);
const y1=n.y*Math.cos(st.angleX)-z1*Math.sin(st.angleX);
const z2=n.y*Math.sin(st.angleX)+z1*Math.cos(st.angleX);
return{x:cx+x1*scale+px,y:cy+y1*scale+py,depth:z2};
}
const proj=new Map();
for(const n of st.nodes)proj.set(n,project(n));
ctx.lineWidth=1.2;
for(const l of st.links){
const p1=proj.get(l.source),p2=proj.get(l.target);
if(!p1||!p2)continue;
ctx.strokeStyle='rgba(200,142,212,0.4)';
ctx.beginPath();ctx.moveTo(p1.x,p1.y);ctx.lineTo(p2.x,p2.y);ctx.stroke();
if(l.label){const mx=(p1.x+p2.x)/2,my=(p1.y+p2.y)/2;ctx.font='9px ui-monospace,monospace';ctx.fillStyle='rgba(200,142,212,0.6)';ctx.textAlign='center';ctx.fillText(l.label.slice(0,20),mx,my-3)}
}
const sorted=st.nodes.slice().sort(function(a,b){return proj.get(a).depth-proj.get(b).depth});
for(const n of sorted){
const p=proj.get(n);
ctx.beginPath();ctx.arc(p.x,p.y,6,0,Math.PI*2);
const hue=280+((n.x+n.y+n.z)%60);
ctx.fillStyle='hsl('+hue+',55%,55%)';ctx.fill();
ctx.strokeStyle='rgba(255,255,255,0.15)';ctx.lineWidth=1;ctx.stroke();
ctx.font='11px system-ui,sans-serif';ctx.fillStyle='#d4d4dc';ctx.textAlign='center';ctx.textBaseline='middle';
ctx.fillText(n.label.slice(0,24),p.x,p.y+16);
}
}

function renderObsidianIntoBlock(blockEl,data){
const nodesEl=blockEl.querySelector('[data-role="obs-nodes"]');
const svgEl=blockEl.querySelector('[data-role="obs-links"]');
if(!nodesEl||!svgEl)return;
const W=blockEl.clientWidth-24,H=blockEl.clientHeight-60;
if(W<100||H<100)return;
const cx=W/2+12,cy=H/2+30;
const nodes=[];
const centerNode={id:'__center__',label:data.center,level:0,x:cx,y:cy,parent:null};
nodes.push(centerNode);
const angleStep=Math.PI*2/Math.max(1,data.branches.length);
const r1=Math.min(W,H)*0.32;
data.branches.forEach(function(b,i){
const angle=-Math.PI/2+i*angleStep;
const bx=cx+Math.cos(angle)*r1;
const by=cy+Math.sin(angle)*r1;
const bn={id:'b'+i,label:b.text,level:1,x:bx,y:by,parent:centerNode};
nodes.push(bn);
b.subs.forEach(function(s,j){
const subAngle=angle+(j-(b.subs.length-1)/2)*0.3;
const r2=r1+Math.min(W,H)*0.14;
const sx=cx+Math.cos(subAngle)*r2;
const sy=cy+Math.sin(subAngle)*r2;
nodes.push({id:'s'+i+'_'+j,label:s,level:2,x:sx,y:sy,parent:bn});
});
});
svgEl.innerHTML='';
function redraw(){
svgEl.innerHTML='';
for(const n of nodes){
if(!n.parent)continue;
const p=n.parent;
const mx=(p.x+n.x)/2,my=(p.y+n.y)/2;
const dx=n.x-p.x,dy=n.y-p.y;
const len=Math.sqrt(dx*dx+dy*dy)||1;
const nx=-dy/len,ny=dx/len;
const curve=Math.min(len*0.3,40);
const c1x=mx+nx*curve,c1y=my+ny*curve;
const c2x=mx-nx*curve,c2y=my-ny*curve;
const path=document.createElementNS('http://www.w3.org/2000/svg','path');
path.setAttribute('d','M '+p.x+' '+p.y+' C '+c1x+' '+c1y+','+c2x+' '+c2y+','+n.x+' '+n.y);
path.setAttribute('fill','none');
path.setAttribute('stroke',n.level===1?'rgba(161,127,224,0.5)':'rgba(161,127,224,0.25)');
path.setAttribute('stroke-width',n.level===1?'1.5':'1');
svgEl.appendChild(path);
}
}
redraw();
nodesEl.innerHTML='';
for(const n of nodes){
const el=document.createElement('div');
el.className='obsidian-node'+(n.level===0?' center':n.level===1?' level1':' level2');
el.textContent=n.label;
el.style.left=n.x+'px';
el.style.top=n.y+'px';
el.style.transform='translate(-50%,-50%)';
el.dataset.nodeId=n.id;
(function(node,element){
let dragging=false,lastX=0,lastY=0;
element.addEventListener('mousedown',function(e){
dragging=true;lastX=e.clientX;lastY=e.clientY;
element.classList.add('dragging');
nodesEl.appendChild(element);
e.stopPropagation();
e.preventDefault();
});
function moveH(e){
if(!dragging)return;
const dx=e.clientX-lastX,dy=e.clientY-lastY;
lastX=e.clientX;lastY=e.clientY;
node.x+=dx;node.y+=dy;
element.style.left=node.x+'px';
element.style.top=node.y+'px';
redraw();
}
function upH(){dragging=false;element.classList.remove('dragging')}
document.addEventListener('mousemove',moveH);
document.addEventListener('mouseup',upH);
})(n,el);
nodesEl.appendChild(el);
}
}

function attachRenderedHandlers(container){
container.querySelectorAll('.code-copy').forEach(function(btn){
if(btn.dataset.attached)return;btn.dataset.attached='1';
btn.addEventListener('click',async function(){
const t=container.querySelector('#'+btn.dataset.target);
if(!t)return;
try{await navigator.clipboard.writeText(t.textContent);btn.classList.add('done');const o=btn.innerHTML;btn.innerHTML=ic('copy','sm')+' скопировано';setTimeout(function(){btn.classList.remove('done');btn.innerHTML=o},1200)}catch(e){}
});
});
container.querySelectorAll('.chart-block').forEach(function(el){if(el.dataset.attached)return;el.dataset.attached='1';try{const cfg=JSON.parse(el.dataset.chart);drawChart(el.querySelector('canvas'),cfg.type,cfg.data)}catch(e){}});
container.querySelectorAll('.graph-block').forEach(function(el){
if(el.dataset.attached)return;el.dataset.attached='1';
const canvas=el.querySelector('canvas');
const exprEl=el.querySelector('.expr');
try{
const cfg=JSON.parse(el.dataset.graph);
if(cfg.kind==='2d'){const info=parseGraph2D(cfg.data);if(info&&exprEl)exprEl.textContent='f(x) = '+info.expr;drawGraph2D(canvas,info)}
else{const info=parseGraph3D(cfg.data);if(info&&exprEl)exprEl.textContent='f(x,y) = '+info.expr;setupGraph3D(canvas,info)}
}catch(e){}
});
container.querySelectorAll('.graphnet-block').forEach(function(el){if(el.dataset.attached)return;el.dataset.attached='1';try{const d=JSON.parse(el.dataset.net);setupGraphNet(el.querySelector('canvas'),d,el)}catch(e){}});
container.querySelectorAll('.obsidian-block').forEach(function(el){
if(el.dataset.attached)return;el.dataset.attached='1';
try{
const d=JSON.parse(el.dataset.obsidian);
setTimeout(function(){renderObsidianIntoBlock(el,d)},80);
}catch(e){}
});
container.querySelectorAll('.shape-block').forEach(function(el){
if(el.dataset.attached)return;el.dataset.attached='1';
const canvas=el.querySelector('canvas');
try{
if(el.dataset.shape2d)drawShape2D(canvas,parseShape2D(el.dataset.shape2d));
else if(el.dataset.shape3d)setupShape3D(canvas,parseShape3D(el.dataset.shape3d));
else if(el.dataset.poly2d)drawPoly2D(canvas,parsePoly2D(el.dataset.poly2d));
else if(el.dataset.mesh3d)setupMesh3D(canvas,parseMesh3D(el.dataset.mesh3d));
}catch(e){console.warn(e)}
});
container.querySelectorAll('.aero-block').forEach(function(el){
if(el.dataset.attached)return;el.dataset.attached='1';
try{
const cfg=parseAero(el.dataset.aero);
const ctrl=el.querySelector('[data-aero-controls]');
if(ctrl){
const wl=document.createElement('label');wl.innerHTML='ветер';
const ws=document.createElement('input');ws.type='range';ws.min='0.2';ws.max='3';ws.step='0.1';ws.value=String(cfg.speed);
const wv=document.createElement('span');wv.className='val';wv.textContent=cfg.speed.toFixed(1);
wl.appendChild(ws);wl.appendChild(wv);ctrl.appendChild(wl);
const al=document.createElement('label');al.innerHTML='наклон';
const as=document.createElement('input');as.type='range';as.min='-45';as.max='45';as.step='1';as.value=String(cfg.angle);
const av=document.createElement('span');av.className='val';av.textContent=cfg.angle+'°';
al.appendChild(as);al.appendChild(av);ctrl.appendChild(al);
const SHAPES=['airfoil','sphere','cube','cylinder','circle','square','diamond','triangle'];
const objWrap=document.createElement('div');objWrap.className='aero-objs';
cfg.objects.forEach(function(o,i){
const oe=document.createElement('div');oe.className='aero-obj';
const sel=document.createElement('select');
SHAPES.forEach(function(s){const op=document.createElement('option');op.value=s;op.textContent=s;if(s===o)op.selected=true;sel.appendChild(op)});
const rm=document.createElement('span');rm.className='rm';rm.innerHTML=ic('close','sm');
rm.addEventListener('click',function(){
const st=view3dState.get(el.querySelector('canvas'));
if(st&&st.objects.length>1){st.objects.splice(i,1);oe.remove()}
});
oe.appendChild(sel);oe.appendChild(rm);objWrap.appendChild(oe);
sel.addEventListener('change',function(){
const st=view3dState.get(el.querySelector('canvas'));
if(st&&st.objects[i])st.objects[i].type=sel.value;
});
});
const addBtn=document.createElement('button');
addBtn.className='act';addBtn.textContent='+ объект';
addBtn.addEventListener('click',function(){
const st=view3dState.get(el.querySelector('canvas'));
if(!st||st.objects.length>=5)return;
const t=SHAPES[Math.floor(Math.random()*SHAPES.length)];
st.objects.push({type:t,x:-15+Math.random()*30,y:(Math.random()-0.5)*15,z:(Math.random()-0.5)*15,size:12});
});
objWrap.appendChild(addBtn);ctrl.appendChild(objWrap);
ws.addEventListener('input',function(){
const st=view3dState.get(el.querySelector('canvas'));
if(st)st.speed=parseFloat(ws.value);
wv.textContent=parseFloat(ws.value).toFixed(1);
});
as.addEventListener('input',function(){
const st=view3dState.get(el.querySelector('canvas'));
if(st)st.angle=parseFloat(as.value);
av.textContent=as.value+'°';
});
}
setupAero(el.querySelector('canvas'),cfg);
}catch(e){console.warn(e)}
});
container.querySelectorAll('[data-chess]').forEach(function(el){if(el.dataset.attached)return;el.dataset.attached='1';try{initChess(el)}catch(e){console.warn('chess',e)}});
}

setIcon($('search-btn'),'search');setIcon($('chatlink-btn'),'link');setIcon($('export-chat-btn'),'download');setIcon($('new-chat-btn'),'plus');
setIcon($('menu-btn'),'menu');setIcon($('panel-close'),'close');setIcon($('modal-close'),'close');setIcon($('chatlink-close'),'close');
setIcon($('scroll-btn'),'down');setIcon($('send-btn'),'arrowUp');setIcon($('think-btn'),'brain');
setIcon($('think-art-btn'),'brainStar');setIcon($('tools-btn'),'wrench');
setIcon($('fast-btn'),'fast');setIcon($('forms-btn'),'forms');setIcon($('raw-prompt-btn'),'raw');setIcon($('animation-btn'),'fade');setIcon($('g4f-btn'),'g4f');
setIcon($('debug-btn'),'bug');setIcon($('quality-btn'),'chart');setIcon($('settings-btn'),'gear');
setIcon($('internet-btn'),'globe');setIcon($('perf-btn'),'bolt');
$('uid-display').textContent=UID;$('uid-field').textContent=UID;
$('uid-display').addEventListener('click',async function(){try{await navigator.clipboard.writeText(UID);const el=$('uid-display');const old=el.textContent;el.textContent='скопировано';setTimeout(function(){el.textContent=old},900)}catch(e){}});
$('uid-copy').addEventListener('click',async function(){try{await navigator.clipboard.writeText(UID)}catch(e){}});
$('uid-reset').addEventListener('click',function(){if(!confirm('Сменить?'))return;localStorage.removeItem('ai_uid');location.reload()});

document.querySelectorAll('.ptab').forEach(function(t){
t.addEventListener('click',function(){
const tab=t.dataset.tab;currentPanelTab=tab;
document.querySelectorAll('.ptab').forEach(function(x){x.classList.toggle('active',x.dataset.tab===tab)});
document.querySelectorAll('.panel-body .tab').forEach(function(x){x.style.display=x.dataset.tab===tab?'block':'none'});
if(tab==='memory')renderMemory();
if(tab==='debug')renderDebug();
if(tab==='mood')renderMoodUI();
});
});
function openPanel(tab){
if(tab){
currentPanelTab=tab;
document.querySelectorAll('.ptab').forEach(function(x){x.classList.toggle('active',x.dataset.tab===tab)});
document.querySelectorAll('.panel-body .tab').forEach(function(x){x.style.display=x.dataset.tab===tab?'block':'none'});
}
if(currentPanelTab==='memory')renderMemory();
if(currentPanelTab==='debug')renderDebug();
if(currentPanelTab==='mood')renderMoodUI();
panelEl.classList.add('open');overlay.classList.add('on');fillSettings();loadStorage();updateModelStatus();
}
function closePanel(){panelEl.classList.remove('open');overlay.classList.remove('on')}
$('settings-btn').addEventListener('click',function(){openPanel('settings')});
$('debug-btn').addEventListener('click',function(){openPanel('debug')});
$('panel-close').addEventListener('click',function(){if(currentPanelTab==='settings'){try{readSettings();settings.model=$('model-select').value;save(sk('settings'),settings)}catch(e){}}closePanel()});
overlay.addEventListener('click',closePanel);

function renderMoodUI(){
const c=$('mood-scales');if(!c)return;
c.innerHTML='';
for(const s of MOOD_SCALES){
const d=document.createElement('div');d.className='mood-scale';
const lbls=document.createElement('div');lbls.className='ms-labels';
const l=document.createElement('span');
l.textContent=s.icon+' '+s.label;
const r=document.createElement('span');
r.className='mood-val';
const v=mood[s.id]!==undefined?mood[s.id]:s.def;
r.textContent=v;
if(v>70)r.style.color='var(--err)';
else if(v>55)r.style.color='var(--acc)';
else if(v<30)r.style.color='var(--mut)';
lbls.appendChild(l);lbls.appendChild(r);
const rg=document.createElement('input');rg.type='range';rg.min=0;rg.max=100;rg.step=1;rg.value=v;
rg.addEventListener('input',function(){
mood[s.id]=parseInt(rg.value,10);
r.textContent=rg.value;
if(mood[s.id]>70)r.style.color='var(--err)';
else if(mood[s.id]>55)r.style.color='var(--acc)';
else if(mood[s.id]<30)r.style.color='var(--mut)';
else r.style.color='';
save(sk('mood'),mood);
updateEmoBadges();
});
d.appendChild(lbls);d.appendChild(rg);c.appendChild(d);
}
}
$('mood-save').addEventListener('click',function(){save(sk('mood'),mood);$('mood-status').textContent='сохранено · '+new Date().toLocaleTimeString();$('mood-status').style.color='var(--ok)';updateEmoBadges()});
$('mood-reset').addEventListener('click',function(){mood=defaultMood();save(sk('mood'),mood);renderMoodUI();updateEmoBadges();$('mood-status').textContent='сброшено'});

function renderMemory(){
const list=$('mem-list');if(!list)return;list.innerHTML='';
if(!savedMessages.length)list.innerHTML='<div class="check-hint">пока пусто.</div>';
else{
const sorted=savedMessages.slice().sort(function(a,b){return b.savedAt-a.savedAt});
for(const s of sorted){
const card=document.createElement('div');card.className='mem-card';
const roleName=s.role==='user'?'вы':s.role==='assistant'?'модель':s.role;
card.innerHTML='<div class="role"><span>'+esc(roleName)+' · '+new Date(s.savedAt).toLocaleString()+'</span></div><div class="content"></div>';
card.querySelector('.content').textContent=s.content||'';
const acts=document.createElement('div');acts.className='actions';
const cb=document.createElement('button');cb.textContent='копировать';
cb.addEventListener('click',async function(){try{await navigator.clipboard.writeText(s.content||'')}catch(e){}});
const db=document.createElement('button');db.textContent='удалить';db.className='danger';
db.addEventListener('click',function(){savedMessages=savedMessages.filter(function(x){return !(x.chatId===s.chatId&&x.msgTs===s.msgTs)});save(sk('saved'),savedMessages);renderMemory();renderMessages(getChat().messages)});
acts.appendChild(cb);acts.appendChild(db);card.appendChild(acts);list.appendChild(card);
}
}
if($('facts-text'))$('facts-text').value=facts;
if($('facts-enabled'))$('facts-enabled').checked=factsEnabled;
}
$('facts-save').addEventListener('click',function(){facts=$('facts-text').value;saveStr(sk('facts'),facts);factsEnabled=$('facts-enabled').checked;saveBool(sk('facts_enabled'),factsEnabled);$('facts-status').textContent='сохранено';$('facts-status').style.color='var(--ok)'});
$('facts-clear').addEventListener('click',function(){if(!confirm('Очистить?'))return;facts='';saveStr(sk('facts'),'');$('facts-text').value='';$('facts-status').textContent='очищено'});
$('facts-enabled').addEventListener('change',function(e){factsEnabled=e.target.checked;saveBool(sk('facts_enabled'),factsEnabled)});
$('debug-clear').addEventListener('click',function(){dbgEvents=[];renderDebug()});
$('debug-export').addEventListener('click',function(){const t=dbgEvents.map(function(e){return '['+e.t+'] '+e.kind.toUpperCase()+' '+e.label+': '+e.text}).join('\n');const b=new Blob([t],{type:'text/plain;charset=utf-8'});const u=URL.createObjectURL(b);const a=document.createElement('a');a.href=u;a.download='debug_'+Date.now()+'.log';a.click();URL.revokeObjectURL(u)});

function newChat(){const c={id:uid(),title:'новый диалог',messages:[],created:Date.now(),links:[]};chats.unshift(c);save(sk('chats'),chats);return c}
function getChat(){return chats.find(function(c){return c.id===activeId})}
function renderList(){
chatListEl.innerHTML='';
for(const c of chats){
const el=document.createElement('div');
el.className='chat-item'+(c.id===activeId?' active':'')+((c.links&&c.links.length)?' linked':'');
el.innerHTML='<span class="title"></span><button class="del">'+ic('close','sm')+'</button>';
const t=el.querySelector('.title');t.textContent=c.title;
t.addEventListener('dblclick',function(e){e.stopPropagation();startRenameChat(c,t)});
el.addEventListener('click',function(e){if(e.target.closest('.del'))return;select(c.id)});
el.querySelector('.del').addEventListener('click',function(e){e.stopPropagation();remove(c.id)});
chatListEl.appendChild(el);
}
}
function startRenameChat(chat,tEl){
const input=document.createElement('input');input.type='text';input.value=chat.title;
input.style.cssText='flex:1;background:var(--bg);border:1px solid var(--adim);color:var(--txt);font-family:var(--mono);font-size:12.5px;border-radius:4px;padding:2px 6px;outline:none;min-width:0;';
tEl.replaceWith(input);input.focus();input.select();
let done=false;
function commit(){if(done)return;done=true;const v=input.value.trim()||'без названия';chat.title=v;save(sk('chats'),chats);if(chat.id===activeId)chatTitleEl.textContent=v;renderList()}
input.addEventListener('blur',commit);
input.addEventListener('keydown',function(e){if(e.key==='Enter'){e.preventDefault();input.blur()}if(e.key==='Escape'){e.preventDefault();done=true;input.value=chat.title;renderList()}});
}
function closeAllEditAreas(){document.querySelectorAll('.edit-area').forEach(function(el){el.remove()});document.querySelectorAll('.entry-body[style*="display: none"]').forEach(function(el){el.style.display=''})}
function select(id){const c=chats.find(function(item){return item.id===id});if(!c)return;closeAllEditAreas();activeId=id;selectedIds.clear();updateBulkBar();chatTitleEl.textContent=c.title;renderMessages(c.messages||[]);renderList();saveStr(sk('active_chat'),id);if(window.innerWidth<=720)sidebar.classList.add('hidden');inputEl.focus()}
function remove(id){chats=chats.filter(function(c){return c.id!==id});for(const c of chats){if(c.links)c.links=c.links.filter(function(x){return x!==id})}if(activeId===id){if(chats.length===0)chats.push(newChat());activeId=chats[0].id}save(sk('chats'),chats);saveStr(sk('active_chat'),activeId||'');renderList();const c=getChat();if(c){chatTitleEl.textContent=c.title;renderMessages(c.messages||[])}else{messagesEl.innerHTML='';chatTitleEl.textContent='новый диалог'}}
function fmtTime(ts){const d=ts?new Date(ts):new Date();return String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0')}
function buildMetaHtml(s){
if(!s)return '';
const p=[];
if(s.duration)p.push(fmtStat(s.duration*1000));
if(s.tokens)p.push('<span class="tok-stat">'+s.tokens+' tok</span>');
if(s.speed)p.push('<span class="spd-stat">'+s.speed.toFixed(1)+' t/s</span>');
if(s.thinking_duration)p.push('<span class="think-stat">think '+fmtStat(s.thinking_duration*1000)+'</span>');
return p.join(' · ');
}
function isSaved(msg){return savedMessages.some(function(s){return s.chatId===activeId&&s.msgTs===msg.ts})}
function toggleSave(msg,btn){
const idx=savedMessages.findIndex(function(s){return s.chatId===activeId&&s.msgTs===msg.ts});
if(idx>=0){savedMessages.splice(idx,1);if(btn){btn.classList.remove('saved');btn.innerHTML=ic('bookmark','sm')+'<span>сохранить</span>'}}
else{savedMessages.push({chatId:activeId,msgTs:msg.ts,role:msg.role,content:msg.content,savedAt:Date.now()});if(btn){btn.classList.add('saved');btn.innerHTML=ic('bookmark','sm')+'<span>сохранено</span>'}}
save(sk('saved'),savedMessages);
}
function humanizeTool(tag,result){
const t=tag.trim();
if(t==='[TIME]')return{name:'запросил время',res:result};
if(t==='[TIMER_START]')return{name:'запустил секундомер',res:''};
if(t==='[TIMER_NOW]')return{name:'проверил',res:result};
if(t==='[TIMER_STOP]')return{name:'остановил',res:result};
const m=t.match(/^\[CALC\]([\s\S]*?)\[\/CALC\]$/);
if(m)return{name:'вычислил '+m[1].trim(),res:result.replace(/^\S+\s*=\s*/,'')};
return{name:tag,res:result};
}
function buildEntry(role,body,opts){
opts=opts||{};
const el=document.createElement('div');el.className='entry';el.dataset.role=role;
const msgTs=opts.msgRef?opts.msgRef.ts:opts.ts;
if(msgTs)el.dataset.ts=msgTs;
if(msgTs&&selectedIds.has(msgTs))el.classList.add('selected');
const cw=document.createElement('div');cw.className='entry-check';
const cb=document.createElement('input');cb.type='checkbox';
if(msgTs&&selectedIds.has(msgTs))cb.checked=true;
cb.addEventListener('change',function(){if(!msgTs)return;if(cb.checked)selectedIds.add(msgTs);else selectedIds.delete(msgTs);el.classList.toggle('selected',cb.checked);updateBulkBar()});
cw.appendChild(cb);el.appendChild(cw);
const head=document.createElement('div');head.className='entry-head';
const pre=document.createElement('span');pre.className='prefix';
pre.textContent=role==='user'?'>':role==='assistant'?'<':role==='error'?'!':'-';
head.appendChild(pre);
const rn=document.createElement('span');rn.className='role';
rn.textContent=role==='user'?'вы':role==='assistant'?(settings.bot_name||'модель'):role==='error'?'ошибка':'система';
head.appendChild(rn);
if(role==='assistant'&&settings.bot_name_enabled&&settings.bot_name){const bn=document.createElement('span');bn.className='botname';bn.textContent=settings.bot_name;head.appendChild(bn)}
if(role==='assistant'&&opts.modelName){const mt=document.createElement('span');mt.className='model-tag';mt.textContent=modelLabel(opts.modelName);head.appendChild(mt)}
if(role==='assistant'&&opts.fastMode){const t=document.createElement('span');t.className='mode-tag fast';t.textContent='fast';head.appendChild(t)}
if(role==='assistant'&&opts.g4fUsed){const t=document.createElement('span');t.className='mode-tag g4f';t.textContent='g4f';head.appendChild(t)}
if(role==='assistant'&&opts.thinking_native){const t=document.createElement('span');t.className='mode-tag think';t.textContent='think';head.appendChild(t)}
if(role==='assistant'&&opts.artificial){const t=document.createElement('span');t.className='mode-tag thinkart';t.textContent='think*';head.appendChild(t)}
if(role==='assistant'&&opts.toolsUsed){const t=document.createElement('span');t.className='mode-tag tools';t.textContent='tools';head.appendChild(t)}
const sep=document.createElement('span');sep.className='sep';sep.textContent='·';head.appendChild(sep);
const tm=document.createElement('span');tm.className='time';tm.textContent=fmtTime(opts.ts);head.appendChild(tm);
const m=document.createElement('span');m.className='meta';m.innerHTML=opts.metaHtml||'';head.appendChild(m);
el.appendChild(head);
if(opts.correction){
const cbox=document.createElement('div');cbox.className='correction-box';
const lbl=document.createElement('span');lbl.className='lbl';lbl.textContent='исправлено';cbox.appendChild(lbl);
const o=document.createElement('span');o.className='orig';o.textContent=opts.original||'';
const ar=document.createElement('span');ar.className='arrow';ar.textContent='→';
const fx=document.createElement('span');fx.className='fix';fx.textContent=opts.correction;
cbox.appendChild(o);cbox.appendChild(ar);cbox.appendChild(fx);el.appendChild(cbox);
}
if(opts.netLog&&opts.netLog.length){
const nd=document.createElement('details');nd.className='net-box';nd.open=true;
const ns=document.createElement('summary');ns.textContent='интернет · '+opts.netLog.length;nd.appendChild(ns);
const nb=document.createElement('div');nb.className='net-body';nb.textContent=opts.netLog.join('\n');nd.appendChild(nb);
el.appendChild(nd);
}
if(opts.toolLog&&opts.toolLog.length){
const td=document.createElement('details');td.className='tool-box';td.open=true;
const ts=document.createElement('summary');ts.textContent='инструменты · '+opts.toolLog.length;td.appendChild(ts);
const tb=document.createElement('div');tb.className='tool-body';
tb.innerHTML=opts.toolLog.map(function(x){const h=humanizeTool(x.tag,x.result);return '<div class="tline"><span class="tname">'+esc(h.name)+'</span>'+(h.res?' · <span class="tres">'+esc(h.res)+'</span>':'')+'</div>'}).join('');
td.appendChild(tb);el.appendChild(td);
}
if(opts.thinking!==undefined&&opts.thinking){
const d=document.createElement('details');
d.className='think-box'+(opts.artificial?' art':'');
d.open=true;
const s=document.createElement('summary');
s.textContent=(opts.artificial?'размышление':'размышления')+(opts.thinkingDuration?' · '+fmtStat(opts.thinkingDuration*1000):'');
d.appendChild(s);
const tb=document.createElement('div');tb.className='think-body';tb.textContent=opts.thinking;d.appendChild(tb);
el.appendChild(d);
}
const bodyEl=document.createElement('div');bodyEl.className='entry-body';
if(opts.empty)bodyEl.classList.add('empty');
if(role==='assistant'){bodyEl.innerHTML=renderMarkdown(body||'');attachRenderedHandlers(bodyEl)}
else{bodyEl.textContent=body||'';bodyEl.classList.add('plain')}
el.appendChild(bodyEl);
const actions=document.createElement('div');actions.className='entry-actions';
if(role==='user'){
const eb=document.createElement('button');eb.className='act';
eb.innerHTML=ic('edit','sm')+'<span>изменить</span>';
eb.addEventListener('click',function(){startEdit(el,bodyEl,opts)});
actions.appendChild(eb);
}
if(role==='assistant'){
const c2=document.createElement('button');c2.className='act';c2.innerHTML=ic('copy','sm')+'<span>копировать</span>';
c2.addEventListener('click',async function(){try{await navigator.clipboard.writeText(bodyEl.textContent);c2.innerHTML=ic('copy','sm')+'<span>скопировано</span>';setTimeout(function(){c2.innerHTML=ic('copy','sm')+'<span>копировать</span>'},1200)}catch(e){}});
actions.appendChild(c2);
const rb=document.createElement('button');rb.className='act';rb.innerHTML=ic('refresh','sm')+'<span>заново</span>';
rb.addEventListener('click',function(){regenerate(opts.msgRef)});
actions.appendChild(rb);
const up=document.createElement('button');up.className='act up';up.innerHTML=ic('thumbUp','sm');
const dn=document.createElement('button');dn.className='act down';dn.innerHTML=ic('thumbDown','sm');
const msg=opts.msgRef;
function ap(){if(!msg)return;up.classList.toggle('sel',msg.rating==='up');dn.classList.toggle('sel',msg.rating==='down')}
ap();
up.addEventListener('click',function(){
if(!msg)return;
const was=msg.rating;
msg.rating=was==='up'?null:'up';
if(msg.rating==='up'){
updateEmotions({love:4,joy:3,trust:3,gratitude:4,respect:2,calm:1,hate:-3,resentment:-3,anger:-2,contempt:-2,fear:-1,boredom:-2});
}else if(was==='up'){
updateEmotions({love:-2,joy:-1,trust:-1,gratitude:-2,respect:-1});
}
ap();save(sk('chats'),chats);updateQualityPanel();
});
dn.addEventListener('click',function(){
if(!msg)return;
const was=msg.rating;
msg.rating=was==='down'?null:'down';
if(msg.rating==='down'){
updateEmotions({resentment:5,sadness:3,hate:3,anger:2,contempt:2,love:-4,joy:-4,trust:-3,gratitude:-3,respect:-2,calm:-2});
}else if(was==='down'){
updateEmotions({resentment:-2,hate:-1,sadness:-1});
}
ap();save(sk('chats'),chats);updateQualityPanel();
});
actions.appendChild(up);actions.appendChild(dn);
}
if(opts.msgRef&&(role==='user'||role==='assistant')){
const sb=document.createElement('button');sb.className='act';
if(isSaved(opts.msgRef)){sb.classList.add('saved');sb.innerHTML=ic('bookmark','sm')+'<span>сохранено</span>'}
else{sb.innerHTML=ic('bookmark','sm')+'<span>сохранить</span>'}
sb.addEventListener('click',function(){toggleSave(opts.msgRef,sb)});
actions.appendChild(sb);
}
if(actions.children.length>0)el.appendChild(actions);
return el;
}
function startEdit(entryEl,bodyEl,opts){
if(busy)return;
const msg=opts.msgRef;
if(!msg||entryEl.querySelector('.edit-area'))return;
bodyEl.style.display='none';
const wrap=document.createElement('div');wrap.className='edit-area';
const ta=document.createElement('textarea');ta.value=msg.content||'';
const btns=document.createElement('div');btns.className='edit-buttons';
const cancel=document.createElement('button');cancel.type='button';cancel.textContent='отмена';
const sB=document.createElement('button');sB.type='button';sB.className='save';sB.textContent='обновить';
btns.appendChild(cancel);btns.appendChild(sB);wrap.appendChild(ta);wrap.appendChild(btns);
entryEl.insertBefore(wrap,bodyEl.nextSibling);
ta.focus();ta.setSelectionRange(ta.value.length,ta.value.length);
function cleanup(){wrap.remove();bodyEl.style.display=''}
cancel.addEventListener('click',cleanup);
sB.addEventListener('click',function(){const nt=ta.value.trim();if(!nt)return;cleanup();applyEdit(msg,nt)});
ta.addEventListener('keydown',function(e){if(e.key==='Escape'){e.stopPropagation();cleanup()}if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();sB.click()}});
}
async function applyEdit(msg,newText){
const chat=getChat();if(!chat)return;
const idx=chat.messages.indexOf(msg);if(idx<0)return;
msg.content=newText;msg.edited=true;msg.ts=Date.now();
chat.messages=chat.messages.slice(0,idx+1);
if(chat.title!=='новый диалог'&&idx===0){chat.title=newText.slice(0,32)+(newText.length>32?'…':'');chatTitleEl.textContent=chat.title}
save(sk('chats'),chats);renderList();renderMessages(chat.messages);
await runGeneration(chat,newText);
}
async function regenerate(msgRef){
if(busy)return;
const chat=getChat();if(!chat)return;
const idx=chat.messages.indexOf(msgRef);if(idx<1)return;
let ut='';
for(let i=idx-1;i>=0;i--)if(chat.messages[i].role==='user'){ut=chat.messages[i].content;break}
if(!ut)return;
chat.messages=chat.messages.slice(0,idx);
save(sk('chats'),chats);renderMessages(chat.messages);
await runGeneration(chat,ut);
}
function collectFeedback(){
if(!settings.feedback_enabled)return null;
const c=getChat();if(!c)return null;
const pos=[],neg=[];
for(const m of c.messages){if(m.role!=='assistant'||!m.rating||!m.content)continue;const s=m.content.slice(0,200);if(m.rating==='up')pos.push(s);else if(m.rating==='down')neg.push(s)}
const l=settings.feedback_max||3;
return{positive:pos.slice(-l),negative:neg.slice(-l)};
}
function collectParams(){
const o={};
for(const p of PARAMS){if(p.t==='check')o[p.k]=!!settings[p.k];else if(String(p.step).includes('.'))o[p.k]=parseFloat(settings[p.k]);else o[p.k]=parseInt(settings[p.k],10)}
o.num_gpu_percent=parseInt(settings.num_gpu_percent,10)||75;
const pr=PERF[perfMode];
if(pr){o.num_thread=pr.num_thread;o.num_batch=pr.num_batch;if(!o.num_ctx||o.num_ctx<2048)o.num_ctx=pr.num_ctx;if(!o.num_predict||o.num_predict<pr.num_predict)o.num_predict=pr.num_predict;if(perfMode!=='high')o.num_gpu_percent=Math.min(o.num_gpu_percent,pr.num_gpu_percent)}
if(fastMode){o.num_thread=FAST.num_thread;o.num_gpu_percent=FAST.num_gpu_percent;o.num_batch=FAST.num_batch;o.num_ctx=FAST.num_ctx;o.num_predict=FAST.num_predict;o.temperature=FAST.temperature}
// Explicit composer presets win over generic performance profiles so the controls behave predictably.
const cm=CONTEXT_PRESETS[settings.context_mode]||CONTEXT_PRESETS.medium;
const tm=TEMPERATURE_PRESETS[settings.temperature_mode]||TEMPERATURE_PRESETS.medium;
const lm=LENGTH_PRESETS[settings.length_mode]||LENGTH_PRESETS.medium;
o.num_ctx=cm.value;o.temperature=tm.value;o.num_predict=lm.value;
return o;
}
function collectLinkedContext(){
const cur=getChat();if(!cur)return [];
const parts=[];
const links=cur.links||[];
for(const lid of links){
const c=chats.find(function(x){return x.id===lid});
if(!c)continue;
const recent=c.messages.slice(-6).filter(function(m){return m.role==='user'||m.role==='assistant'});
if(!recent.length)continue;
const block=['[Связанный чат: '+c.title+']'];
for(const m of recent){block.push((m.role==='user'?'Пользователь: ':'Модель: ')+m.content.slice(0,300))}
parts.push(block.join('\n'));
}
return parts;
}
function looksLikeMath(text){if(!text||text.length>300)return false;const hasOp=/[\+\-\*\/\^%]|\b(sqrt|sin|cos|tan|log|ln)\b/i.test(text);const hasNum=/\d/.test(text);const hasWord=/посчитай|вычисли|сколько будет|реши|calculate|compute/i.test(text);return(hasOp&&hasNum&&text.split(/\s+/).length<15)||hasWord}

async function send(){
if(busy)return;
const text=inputEl.value.trim();if(!text)return;
const chat=getChat();if(!chat)return;
decayEmotions();
const deltas=analyzeUserMessage(text);
if(Object.keys(deltas).length){
for(const k in deltas){
if(mood[k]===undefined)mood[k]=50;
mood[k]=clampEmo(mood[k]+deltas[k]);
}
save(sk('mood'),mood);
updateEmoBadges();
}
const empty=messagesEl.querySelector('.empty');if(empty)empty.remove();
const um={role:'user',content:text,ts:Date.now()};
chat.messages.push(um);
if(chat.title==='новый диалог'){chat.title=text.slice(0,32)+(text.length>32?'…':'');chatTitleEl.textContent=chat.title}
save(sk('chats'),chats);renderList();renderMessages(chat.messages);
const sentEntry=messagesEl.querySelector('.entry[data-ts="'+um.ts+'"]');if(sentEntry)sentEntry.classList.add('message-arrive');
inputEl.value='';autoResizeInput();updateCharCount();saveDraft();
const forceMath=autoMath&&looksLikeMath(text);
await runGeneration(chat,text,forceMath);
}

async function runGeneration(chat,prompt,forceMath){
busy=true;
sendBtn.innerHTML=ic('stop','lg');sendBtn.classList.add('stop');sendBtn.disabled=false;
statsEl.textContent='';
liveTokens=0;liveThinkStart=0;liveThinkEnd=0;liveStage='init';
dbgEvents=[];renderDebug();
dbg('info','start','model='+settings.model+' device='+(settings.compute_device||'xpu')+' quant='+(settings.quantization||'auto')+' fast='+fastMode);
const liveStart=Date.now();
if(liveTimer)clearInterval(liveTimer);
liveTimer=setInterval(function(){
if(!busy)return;
const el=(Date.now()-liveStart)/1000;
const p=[];
if(liveThinkStart&&liveThinkEnd)p.push('<span class="think-live">think '+((liveThinkEnd-liveThinkStart)/1000).toFixed(1)+'s</span>');
else if(liveThinkStart)p.push('<span class="think-live">think '+((Date.now()-liveThinkStart)/1000).toFixed(1)+'s</span>');
if(liveStage==='tool')p.push('<span class="stage">инструмент…</span>');
else if(liveStage==='answering')p.push('<span class="stage">отвечает…</span>');
else if(liveStage==='thinking')p.push('<span class="stage">размышляет…</span>');
if(el>1&&liveTokens>0)p.push('<span class="live">'+(liveTokens/el).toFixed(1)+' t/s · '+liveTokens+' tok · '+el.toFixed(1)+'s</span>');
if(p.length)statsEl.innerHTML=p.join(' · ');
},400);
abortCtrl=new AbortController();
const aMsg={role:'assistant',content:'',thinking:'',rating:null,ts:Date.now(),netLog:[],toolLog:[],correction:null,original:null,model:settings.compute_device==='npu'?'OpenVINO NPU':mapQuantizedModel(settings.model,selectedQuant()),device:settings.compute_device||'xpu',quantization:settings.quantization||'auto',perf:perfMode,artificial_think:!rawPromptMode&&thinkArtOn,thinking_native:thinkOn,fast_mode:fastMode,g4f_used:false};
const entryEl=buildEntry('assistant','',{ts:Date.now(),thinking:'',msgRef:aMsg,modelName:settings.compute_device==='npu'?'OpenVINO NPU':mapQuantizedModel(settings.model,selectedQuant()),perfMode:perfMode,artificial:!rawPromptMode&&thinkArtOn,thinking_native:thinkOn,fastMode:fastMode});
entryEl.classList.add('message-arrive');
messagesEl.appendChild(entryEl);
autoScroll=true;scrollBottom();
const bodyEl=entryEl.querySelector('.entry-body');
bodyEl.classList.add('empty');
const metaEl=entryEl.querySelector('.meta');
const headEl=entryEl.querySelector('.entry-head');
let liveThinkEl=null,liveThinkBody=null;
function ensureLiveThink(isArt){
if(liveThinkEl)return;
liveThinkEl=document.createElement('div');
liveThinkEl.className='live-think'+(isArt?' art':'');
const h=document.createElement('div');h.className='lt-head';
h.innerHTML='<span class="pulse"></span>'+ic('brainStar','sm')+'<span class="lbl">'+(isArt?'размышление':'размышления')+'</span>';
h.addEventListener('click',function(){liveThinkEl.classList.toggle('collapsed')});
const b=document.createElement('div');b.className='lt-body';
liveThinkEl.appendChild(h);liveThinkEl.appendChild(b);
headEl.insertAdjacentElement('afterend',liveThinkEl);
liveThinkBody=b;
}
function appendThinking(text,isArt){
if(!text)return;
aMsg.thinking+=text;
if(!streamThink)return;
ensureLiveThink(isArt);
if(liveThinkBody){liveThinkBody.textContent+=text;liveThinkBody.scrollTop=liveThinkBody.scrollHeight}
}
function finalizeLiveThink(){
if(!liveThinkEl)return;
const elapsed=(liveThinkEnd&&liveThinkStart)?(liveThinkEnd-liveThinkStart)/1000:0;
const isArt=liveThinkEl.classList.contains('art');
const d=document.createElement('details');
d.className='think-box'+(isArt?' art':'');
d.open=true;
const s=document.createElement('summary');
s.textContent=(isArt?'размышление':'размышления')+(elapsed?' · '+fmtStat(elapsed*1000):'');
d.appendChild(s);
const tb=document.createElement('div');tb.className='think-body';tb.textContent=aMsg.thinking;d.appendChild(tb);
liveThinkEl.replaceWith(d);
liveThinkEl=null;liveThinkBody=null;
}
const state={
phase:'prefix',buffer:'',fixDone:!fixOn||rawPromptMode,thinkArtDone:!thinkArtOn||fastMode||rawPromptMode,fixCorrection:null,
process:function(text){
if(this.phase==='answer'){appendAnswer(text);return}
this.buffer+=text;
let loop=true;
while(loop){
loop=false;
if(!this.fixDone){
const m=this.buffer.match(/^\s*\[FIX\]([\s\S]*?)\[\/FIX\]\s*/);
if(m){this.fixCorrection=m[1].trim();this.buffer=this.buffer.slice(m[0].length);this.fixDone=true;loop=true;continue}
const chk=this.buffer.replace(/^\s+/,'');
if(chk.length<6&&'[FIX]'.indexOf(chk)===0)return;
if(chk.indexOf('[FIX]')!==0){this.fixDone=true;loop=true;continue}
if(this.buffer.length>600){this.fixDone=true;loop=true;continue}
return;
}
if(!this.thinkArtDone){
const m1=this.buffer.match(/^\s*\[THINK\]/);
if(m1){this.buffer=this.buffer.slice(m1[0].length);this.phase='think-art';if(!liveThinkEl&&streamThink){liveThinkStart=Date.now();ensureLiveThink(true);liveStage='thinking'}loop=true;continue}
const chk=this.buffer.replace(/^\s+/,'');
if(chk.length<8&&'[THINK]'.indexOf(chk)===0)return;
if(chk.indexOf('[THINK]')!==0){this.thinkArtDone=true;loop=true;continue}
return;
}
this.phase='answer';
appendAnswer(this.buffer);this.buffer='';
return;
}
},
thinkChunk:function(text){
this.buffer+=text;
const m=this.buffer.match(/^([\s\S]*?)\[\/THINK\]\s*/);
if(m){
appendThinking(m[1],true);
this.buffer=this.buffer.slice(m[0].length);
this.thinkArtDone=true;liveThinkEnd=Date.now();
finalizeLiveThink();this.phase='answer';liveStage='answering';
if(this.buffer){appendAnswer(this.buffer);this.buffer=''}
return;
}
const tail=this.buffer.slice(-12);
if(tail.indexOf('[/THINK]')>=0)return;
if(this.buffer.length>32){const f=this.buffer.slice(0,-12);appendThinking(f,true);this.buffer=this.buffer.slice(-12)}
}
};
let accAnswer='',displayAnswer='',pendingDisplay='';
let netLog=[],toolLog=[];
let mdTimer=null,mdDirty=false,typewriterTimer=null,lastRenderedRawLength=0;
function animateRecentText(count){
if(!textAnimationOn||!count||!bodyEl||!bodyEl.childNodes.length)return;
try{
// Rendered text nodes are split into Unicode code points; each new character fades in independently.
const walker=document.createTreeWalker(bodyEl,NodeFilter.SHOW_TEXT,{
acceptNode:function(node){return node.parentElement&&node.parentElement.closest('button,script,style,textarea,pre code')?NodeFilter.FILTER_REJECT:NodeFilter.FILTER_ACCEPT}
});
const nodes=[];let node,total=0;
while((node=walker.nextNode())){const chars=Array.from(node.nodeValue||'');if(!chars.length)continue;nodes.push({node:node,chars:chars});total+=chars.length;}
const start=Math.max(0,total-Math.min(count,120));let offset=0,seq=0;
for(const item of nodes){
const len=item.chars.length,end=offset+len;
if(end>start){
const from=Math.max(0,start-offset),frag=document.createDocumentFragment();
if(from>0)frag.appendChild(document.createTextNode(item.chars.slice(0,from).join('')));
for(let i=from;i<len;i++){
const span=document.createElement('span');span.className='token-emerge';
span.style.animationDelay=Math.min(seq*4,64)+'ms';span.textContent=item.chars[i];frag.appendChild(span);seq++;
}
item.node.replaceWith(frag);
}
offset=end;
}
}catch(e){/* Rendering must continue even if a browser lacks a DOM feature. */}
}
function scheduleMDRender(){
if(mdDirty)return;mdDirty=true;
if(mdTimer)return;
const hasRichBlock=/\[(?:CHART|GRAPH2D|GRAPH3D|GRAPH_NET|TREE|MINDMAP|KANBAN|TIMELINE|PROCESS|METRICS|CHECKLIST|FILE_TREE|MATRIX|CALLOUT|QUOTE|MATH|SHAPE2D|POLY2D|SHAPE3D|MESH3D|AERO|CHESS)(?::[^\]]*)?\]/i.test(displayAnswer);
mdTimer=setTimeout(function(){
mdTimer=null;mdDirty=false;
const rawLength=displayAnswer.length,revealCount=Math.max(0,rawLength-lastRenderedRawLength);
try{bodyEl.innerHTML=renderMarkdown(displayAnswer);attachRenderedHandlers(bodyEl);if(revealCount)animateRecentText(revealCount)}catch(e){}
lastRenderedRawLength=rawLength;
},hasRichBlock?180:(textAnimationOn?80:35));
}
function typewriterStep(){
typewriterTimer=null;
if(!pendingDisplay.length)return;
if(!textAnimationOn){displayAnswer=accAnswer;pendingDisplay='';scheduleMDRender();if(autoScroll)scrollBottom();return;}
const chars=Array.from(pendingDisplay),backlog=chars.length;
// Keep symbol-level progression while gently catching up when model chunks arrive faster than the reveal.
const count=Math.min(backlog,backlog>220?5:backlog>90?3:backlog>35?2:1);
displayAnswer+=chars.slice(0,count).join('');pendingDisplay=chars.slice(count).join('');
scheduleMDRender();
if(autoScroll)scrollBottom();
if(pendingDisplay.length){const delay=pendingDisplay.length>220?5:pendingDisplay.length>90?7:pendingDisplay.length>35?9:12;typewriterTimer=setTimeout(typewriterStep,delay)}
}
async function finishTypewriter(){
// Let queued code points finish their reveal instead of popping the remaining answer in at once.
while(textAnimationOn&&pendingDisplay.length){
if(!typewriterTimer)typewriterTimer=setTimeout(typewriterStep,0);
await new Promise(function(resolve){setTimeout(resolve,18)});
}
if(typewriterTimer){clearTimeout(typewriterTimer);typewriterTimer=null;}
if(mdTimer){clearTimeout(mdTimer);mdTimer=null;}
pendingDisplay='';displayAnswer=accAnswer;mdDirty=false;
const revealCount=Math.max(0,accAnswer.length-lastRenderedRawLength);
try{bodyEl.innerHTML=renderMarkdown(accAnswer);attachRenderedHandlers(bodyEl);if(revealCount)animateRecentText(revealCount)}catch(e){}
lastRenderedRawLength=accAnswer.length;
}
function appendAnswer(t){
if(!t)return;
accAnswer+=t;liveTokens++;
bodyEl.classList.remove('empty');
if(!textAnimationOn){
if(typewriterTimer){clearTimeout(typewriterTimer);typewriterTimer=null;}
pendingDisplay='';displayAnswer=accAnswer;scheduleMDRender();if(autoScroll)scrollBottom();return;
}
pendingDisplay+=t;
if(!typewriterTimer)typewriterTimer=setTimeout(typewriterStep,8);
}
function feedContent(t){
if(state.phase==='answer')appendAnswer(t);
else if(state.phase==='think-art')state.thinkChunk(t);
else state.process(t);
}
try{
const linkedParts=rawPromptMode?[]:collectLinkedContext();
const linkedBlock=linkedParts.length?"\n\nКонтекст из связанных чатов:\n"+linkedParts.join('\n\n'):"";
const moodBlock=rawPromptMode?'':buildMoodInstruction(mood);
const botBlock=(!rawPromptMode&&settings.bot_name_enabled&&settings.bot_name)?"\n\nТвоё имя: "+settings.bot_name+". Если спросят — представься этим именем.":"";
const factsBlock=(!rawPromptMode&&factsEnabled&&facts.trim())?"\n\nИзвестные факты о пользователе:\n"+facts.trim():"";
const sysp=rawPromptMode?settings.system_prompt:settings.system_prompt+linkedBlock+moodBlock+botBlock+factsBlock;
const res=await fetch('/chat',{
method:'POST',
headers:{'Content-Type':'application/json'},
signal:abortCtrl.signal,
body:JSON.stringify({
prompt:prompt,model:settings.model,net_mode:rawPromptMode?'off':internetMode,
raw_prompt_mode:rawPromptMode,
compute_device:settings.compute_device||'xpu',quantization:settings.quantization||'auto',
think:!fastMode&&thinkOn,think_art:!rawPromptMode&&!fastMode&&thinkArtOn,tools:!rawPromptMode&&!fastMode&&(toolsOn||forceMath),
auto_math:!rawPromptMode&&autoMath,auto_translate:!rawPromptMode&&translateOn,
target_lang:settings.target_lang,fix_typos:!rawPromptMode&&!fastMode&&fixOn,
show_net_log:!rawPromptMode&&settings.show_net_log!==false,
system_prompt:sysp,
feedback:rawPromptMode?null:collectFeedback(),
feedback_enabled:!rawPromptMode&&settings.feedback_enabled,
feedback_max:settings.feedback_max,
forms_enabled:!rawPromptMode&&formsOn&&!fastMode,
g4f_enabled:!rawPromptMode&&g4fOn,
g4f_mode:rawPromptMode?'off':(settings.g4f_mode||'off'),
params:collectParams(),user_id:UID,
history:rawPromptMode?[]:chat.messages.slice(-10).filter(function(m){return m.role==='user'||m.role==='assistant'}).map(function(m){return {role:m.role,content:m.content}})
})
});
if(!res.ok||!res.body)throw new Error('HTTP '+res.status);
dbg('res','http',res.status);
const reader=res.body.getReader();
const dec=new TextDecoder();
let buf='';
while(true){
const r=await reader.read();
if(r.done)break;
buf+=dec.decode(r.value,{stream:true});
const chunks=buf.split('\n\n');buf=chunks.pop();
for(const chunk of chunks){
if(chunk.indexOf('data: ')!==0)continue;
let d;try{d=JSON.parse(chunk.slice(6))}catch(e){continue}
if(d.type==='status'){dbg('info','status',d.text);if(!statsEl.querySelector('.live')&&!statsEl.querySelector('.think-live'))statsEl.textContent=d.text}
else if(d.type==='thinking_start'){dbg('think','start','');liveThinkStart=Date.now();if(streamThink)ensureLiveThink(false);liveStage='thinking'}
else if(d.type==='thinking_end'){dbg('think','end','');liveThinkEnd=Date.now();finalizeLiveThink();liveStage='answering'}
else if(d.type==='g4f_used'){aMsg.g4f_used=true;dbg('res','g4f',d.text||'fallback')}
else if(d.type==='net'){netLog.push(d.text);dbg('res','net',d.text);
let nd=entryEl.querySelector('.net-box');
if(!nd){nd=document.createElement('details');nd.className='net-box';nd.open=true;const ns=document.createElement('summary');ns.textContent='интернет · 0';nd.appendChild(ns);const nb=document.createElement('div');nb.className='net-body';nd.appendChild(nb);headEl.insertAdjacentElement('afterend',nd)}
nd.querySelector('summary').textContent='интернет · '+netLog.length;
nd.querySelector('.net-body').textContent=netLog.join('\n');
if(autoScroll)scrollBottom();
}
else if(d.type==='tool_call'){toolLog.push({tag:d.text,result:''});dbg('tool','call',d.text);
let td=entryEl.querySelector('.tool-box');
if(!td){td=document.createElement('details');td.className='tool-box';td.open=true;const ts=document.createElement('summary');ts.textContent='инструменты · 0';td.appendChild(ts);const tb=document.createElement('div');tb.className='tool-body';td.appendChild(tb);headEl.insertAdjacentElement('afterend',td)}
td.querySelector('summary').textContent='инструменты · '+toolLog.length;
if(autoScroll)scrollBottom();liveStage='tool';
}
else if(d.type==='tool_result'){if(toolLog.length){toolLog[toolLog.length-1].result=d.text;const td=entryEl.querySelector('.tool-box');if(td)td.querySelector('.tool-body').innerHTML=toolLog.map(function(x){const h=humanizeTool(x.tag,x.result);return '<div class="tline"><span class="tname">'+esc(h.name)+'</span>'+(h.res?' · <span class="tres">'+esc(h.res)+'</span>':'')+'</div>'}).join('')}dbg('tool','result',d.text);if(autoScroll)scrollBottom()}
else if(d.type==='thinking'){appendThinking(d.text,false)}
else if(d.type==='content'){dbg('res','content',d.text.slice(0,60).replace(/\n/g,' '));feedContent(d.text)}
else if(d.type==='error'){dbg('err','error',d.text);if(state.buffer){appendAnswer(state.buffer);state.buffer=''}await finishTypewriter();finalizeLiveThink();messagesEl.appendChild(buildEntry('error',d.text,{ts:Date.now()}));scrollBottom();busy=false;resetSendButton();return}
else if(d.type==='done'){
if(state.buffer){appendAnswer(state.buffer);state.buffer=''}
await finishTypewriter();
finalizeLiveThink();
const s=d.stats||{};
if(metaEl)metaEl.innerHTML=buildMetaHtml(s);
statsEl.textContent=(s.duration||0).toFixed(2)+'s · '+(s.tokens||0)+' tok · '+(s.speed||0).toFixed(1)+' t/s'+(s.thinking_duration?' · think '+s.thinking_duration.toFixed(1)+'s':'');
aMsg.stats=s;
addMetricPoint({speed:Number(s.speed)||0,duration:Number(s.duration)||0,tokens:Number(s.tokens)||0,device:selectedDevice(),quantization:selectedQuant(),model:settings.model});
dbg('info','done',statsEl.textContent);
}
}
}
if(state.buffer){appendAnswer(state.buffer);state.buffer=''}
await finishTypewriter();
finalizeLiveThink();
if(state.fixCorrection){aMsg.correction=state.fixCorrection;aMsg.original=prompt}
aMsg.content=accAnswer;aMsg.netLog=netLog;aMsg.toolLog=toolLog;
chat.messages.push(aMsg);save(sk('chats'),chats);
}catch(e){
if(e.name==='AbortError'){
dbg('info','abort','user stopped');
if(state.buffer){appendAnswer(state.buffer);state.buffer=''}
await finishTypewriter();
finalizeLiveThink();
if(accAnswer||aMsg.thinking||netLog.length||toolLog.length){aMsg.content=accAnswer;aMsg.netLog=netLog;aMsg.toolLog=toolLog;aMsg.aborted=true;chat.messages.push(aMsg);save(sk('chats'),chats)}
else entryEl.remove();
if(metaEl)metaEl.textContent='прервано';
}else{
dbg('err','exception',e.message);
await finishTypewriter();
finalizeLiveThink();
messagesEl.appendChild(buildEntry('error','сбой: '+e.message,{ts:Date.now()}));
scrollBottom();
}
}finally{
const aDeltas=analyzeAssistantMessage(accAnswer);
if(Object.keys(aDeltas).length){
for(const k in aDeltas){
if(mood[k]===undefined)mood[k]=50;
mood[k]=clampEmo(mood[k]+aDeltas[k]);
}
save(sk('mood'),mood);
}
decayEmotions();
busy=false;abortCtrl=null;
if(liveTimer){clearInterval(liveTimer);liveTimer=null}
if(mdTimer){clearTimeout(mdTimer);mdTimer=null}
if(typewriterTimer){clearTimeout(typewriterTimer);typewriterTimer=null}
resetSendButton();
inputEl.focus();
}
}
function resetSendButton(){sendBtn.innerHTML=ic('arrowUp','lg');sendBtn.classList.remove('stop');sendBtn.disabled=false}
function stopGeneration(){if(abortCtrl){try{abortCtrl.abort()}catch(e){}dbg('info','stop','abort sent')}}

function renderMessages(msgs){
messagesEl.innerHTML='';
if(!msgs.length){messagesEl.innerHTML='<div class="empty"><span class="c">//</span> диалог пуст<br><span class="c">//</span> введите запрос ниже</div>';return}
for(const m of msgs){
if(m.role==='user')messagesEl.appendChild(buildEntry('user',m.content,{ts:m.ts,msgRef:m}));
else if(m.role==='assistant')messagesEl.appendChild(buildEntry('assistant',m.content,{
ts:m.ts,thinking:m.thinking||'',msgRef:m,
netLog:m.netLog||[],toolLog:m.toolLog||[],
correction:m.correction||null,original:m.original||null,
modelName:m.model||settings.model,
metaHtml:m.stats?buildMetaHtml(m.stats):'',
thinkingDuration:m.stats?m.stats.thinking_duration:0,
artificial:m.artificial_think||false,thinking_native:m.thinking_native||false,
toolsUsed:(m.toolLog&&m.toolLog.length)>0,
fastMode:m.fast_mode||false,
g4fUsed:m.g4f_used||false
}));
else if(m.role==='error')messagesEl.appendChild(buildEntry('error',m.content,{ts:m.ts}));
else if(m.role==='system')messagesEl.appendChild(buildEntry('system',m.content,{ts:m.ts}));
}
scrollBottom();
}
function scrollBottom(){messagesEl.scrollTop=messagesEl.scrollHeight}
messagesEl.addEventListener('scroll',function(){const nb=messagesEl.scrollHeight-messagesEl.scrollTop-messagesEl.clientHeight<60;autoScroll=nb;scrollBtn.classList.toggle('on',!nb)});
scrollBtn.addEventListener('click',function(){autoScroll=true;scrollBottom();scrollBtn.classList.remove('on')});
function updateCharCount(){const n=inputEl.value.length;charCount.textContent=n;charCount.classList.toggle('warn',n>500)}
function autoResizeInput(){inputEl.style.height='auto';inputEl.style.height=Math.min(inputEl.scrollHeight,200)+'px'}
function updatePills(){
const ib=$('internet-btn');ib.classList.remove('on','auto');
if(internetMode==='on')ib.classList.add('on');else if(internetMode==='auto')ib.classList.add('auto','on');
ib.dataset.tip='интернет: '+(internetMode==='off'?'выкл':internetMode==='auto'?'авто':'вкл');
const tb=$('think-btn');tb.classList.toggle('on',thinkOn&&!fastMode);
const tab=$('think-art-btn');tab.classList.toggle('on',thinkArtOn&&!fastMode);
const tlb=$('tools-btn');tlb.classList.toggle('on',toolsOn&&!fastMode);
const fb=$('fast-btn');fb.classList.toggle('on',fastMode);
const fob=$('forms-btn');fob.classList.toggle('on',formsOn&&!fastMode);
const rpb=$('raw-prompt-btn');rpb.classList.toggle('on',rawPromptMode);rpb.dataset.tip='чистый промпт: '+(rawPromptMode?'вкл':'выкл');rpb.title=rpb.dataset.tip;rpb.setAttribute('aria-pressed',String(rawPromptMode));rpb.setAttribute('aria-label',rawPromptMode?'Чистый промпт включён':'Включить чистый промпт');
const ab=$('animation-btn');ab.classList.toggle('on',textAnimationOn);ab.dataset.tip='анимация символов: '+(textAnimationOn?'вкл':'выкл');ab.title=ab.dataset.tip;ab.setAttribute('aria-pressed',String(textAnimationOn));ab.setAttribute('aria-label',textAnimationOn?'Отключить анимацию символов':'Включить анимацию символов');
const gb=$('g4f-btn');gb.classList.toggle('on',g4fOn);
const pb=$('perf-btn');pb.classList.remove('perf-low','perf-medium','perf-high');pb.classList.add('perf-'+perfMode,'on');
pb.dataset.tip='производительность: '+PERF[perfMode].label+(fastMode?' (fast)':'');
if($('think-native-cb'))$('think-native-cb').checked=thinkOn;
if($('think-art-cb'))$('think-art-cb').checked=thinkArtOn;
if($('tools-cb'))$('tools-cb').checked=toolsOn;
if($('auto-math-cb'))$('auto-math-cb').checked=autoMath;
if($('fast-cb'))$('fast-cb').checked=fastMode;
if($('forms-cb'))$('forms-cb').checked=formsOn;
if($('g4f-cb'))$('g4f-cb').checked=g4fOn;
}
function updateBulkBar(){const n=selectedIds.size;bulkCount.textContent=n;bulkBar.classList.toggle('on',n>0)}
function getSelectedMessages(){const c=getChat();if(!c)return[];return c.messages.filter(function(m){return selectedIds.has(m.ts)})}
$('bulk-save').addEventListener('click',function(){for(const m of getSelectedMessages()){if(m.role!=='user'&&m.role!=='assistant')continue;if(savedMessages.some(function(s){return s.chatId===activeId&&s.msgTs===m.ts}))continue;savedMessages.push({chatId:activeId,msgTs:m.ts,role:m.role,content:m.content,savedAt:Date.now()})}save(sk('saved'),savedMessages);renderMessages(getChat().messages)});
$('bulk-copy').addEventListener('click',async function(){const t=getSelectedMessages().map(function(m){return (m.role==='user'?'> ':m.role==='assistant'?'< ':'')+(m.content||'')}).join('\n\n');try{await navigator.clipboard.writeText(t)}catch(e){}});
$('bulk-del').addEventListener('click',function(){const c=getChat();if(!c)return;c.messages=c.messages.filter(function(m){return !selectedIds.has(m.ts)});save(sk('chats'),chats);selectedIds.clear();updateBulkBar();renderMessages(c.messages)});
$('bulk-clear').addEventListener('click',function(){selectedIds.clear();updateBulkBar();renderMessages(getChat().messages)});

sendBtn.addEventListener('click',function(){if(busy)stopGeneration();else send()});
inputEl.addEventListener('keydown',function(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();if(!busy)send()}});
inputEl.addEventListener('input',function(){autoResizeInput();updateCharCount();saveDraftDebounced()});
function saveDraft(){if(!settings.save_draft)return;if(inputEl.value)saveStr(sk('draft'),inputEl.value);else localStorage.removeItem(sk('draft'))}
let draftTimer=null;
function saveDraftDebounced(){if(draftTimer)clearTimeout(draftTimer);draftTimer=setTimeout(saveDraft,500)}
function restoreDraft(){if(!settings.save_draft)return;const d=localStorage.getItem(sk('draft'));if(d&&!inputEl.value){inputEl.value=d;autoResizeInput();updateCharCount()}}

document.addEventListener('keydown',function(e){
if(e.key==='Escape'){
if(chatlinkModal.classList.contains('on')){chatlinkModal.classList.remove('on');return}
if(graphModal.classList.contains('on')){graphModal.classList.remove('on');return}
if(searchPanel.classList.contains('on')){searchPanel.classList.remove('on');return}
if(busy){e.preventDefault();stopGeneration();return}
if(panelEl.classList.contains('open')){closePanel();return}
const ea=document.querySelector('.edit-area');
if(ea){const btn=ea.querySelector('.edit-buttons button');if(btn)btn.click()}
}
if((e.ctrlKey||e.metaKey)&&e.key==='k'){e.preventDefault();$('new-chat-btn').click()}
if((e.ctrlKey||e.metaKey)&&e.key==='/'){e.preventDefault();inputEl.focus()}
});

$('new-chat-btn').addEventListener('click',function(){const c=newChat();selectedIds.clear();updateBulkBar();select(c.id);renderList();if(window.innerWidth<=720)sidebar.classList.add('hidden')});

$('chatlink-btn').addEventListener('click',function(){openChatLinkModal()});
function openChatLinkModal(){
const cur=getChat();if(!cur)return;
editingChatLinks=(cur.links||[]).slice();
const list=$('chatlink-list');list.innerHTML='';
for(const c of chats){
if(c.id===cur.id)continue;
const el=document.createElement('label');el.className='chatlink-item';
const cb=document.createElement('input');cb.type='checkbox';cb.checked=editingChatLinks.indexOf(c.id)>=0;
cb.addEventListener('change',function(){
if(cb.checked){if(editingChatLinks.indexOf(c.id)<0)editingChatLinks.push(c.id)}
else{editingChatLinks=editingChatLinks.filter(function(x){return x!==c.id})}
});
const t=document.createElement('span');t.className='title';t.textContent=c.title;
el.appendChild(cb);el.appendChild(t);list.appendChild(el);
}
if(!list.children.length)list.innerHTML='<div class="check-hint">нет других чатов</div>';
chatlinkModal.classList.add('on');
}
$('chatlink-close').addEventListener('click',function(){chatlinkModal.classList.remove('on')});
$('chatlink-cancel').addEventListener('click',function(){chatlinkModal.classList.remove('on')});
$('chatlink-save').addEventListener('click',function(){
const cur=getChat();if(!cur)return;
cur.links=editingChatLinks.slice();
save(sk('chats'),chats);renderList();
chatlinkModal.classList.remove('on');
});

$('search-btn').addEventListener('click',openSearch);
function openSearch(){searchPanel.classList.add('on');$('search-input').value='';$('search-results').innerHTML='';$('search-count').textContent='0';$('search-input').focus()}
$('search-input').addEventListener('input',doSearch);
function doSearch(){
const q=$('search-input').value.trim().toLowerCase();
const chat=getChat();const rl=$('search-results');rl.innerHTML='';
if(!q||!chat){$('search-count').textContent='0';return}
let count=0;
chat.messages.forEach(function(m){
const text=(m.content||'').toLowerCase();
const pos=text.indexOf(q);if(pos<0)return;
count++;
const start=Math.max(0,pos-40);
const end=Math.min(m.content.length,pos+q.length+60);
const before=esc(m.content.slice(start,pos));
const mid=esc(m.content.slice(pos,pos+q.length));
const after=esc(m.content.slice(pos+q.length,end));
const roleName=m.role==='user'?'вы':m.role==='assistant'?'модель':m.role;
const el=document.createElement('div');el.className='res';
el.innerHTML='<span class="role">'+roleName+'</span><div class="snip">'+(start>0?'…':'')+before+'<mark>'+mid+'</mark>'+after+(end<m.content.length?'…':'')+'</div>';
el.addEventListener('click',function(){const entry=messagesEl.querySelector('.entry[data-ts="'+m.ts+'"]');if(entry){entry.scrollIntoView({behavior:'smooth',block:'center'});entry.style.transition='background 1.2s';const prev=entry.style.background;entry.style.background='rgba(212,160,74,0.15)';setTimeout(function(){entry.style.background=prev},1200)}searchPanel.classList.remove('on')});
rl.appendChild(el);
});
$('search-count').textContent=count;
}
$('export-chat-btn').addEventListener('click',function(){
const c=getChat();if(!c)return;
let md='# '+c.title+'\n\n';
for(const m of c.messages){
if(m.role==='user')md+='## Вы\n\n'+m.content+'\n\n';
else if(m.role==='assistant'){md+='## Модель ('+(m.model||'?')+')\n\n';if(m.thinking)md+='> размышления:\n> '+m.thinking.replace(/\n/g,'\n> ')+'\n\n';md+=m.content+'\n\n'}
else if(m.role==='error')md+='## Ошибка\n\n'+m.content+'\n\n';
}
const b=new Blob([md],{type:'text/markdown;charset=utf-8'});
const u=URL.createObjectURL(b);const a=document.createElement('a');a.href=u;
const safe=c.title.replace(/[^\wа-яёА-ЯЁ\- ]+/g,'').replace(/\s+/g,'_').slice(0,60);
a.download=(safe||'chat')+'.md';a.click();URL.revokeObjectURL(u);
});
$('menu-btn').addEventListener('click',function(){sidebar.classList.toggle('hidden')});
chatTitleEl.addEventListener('dblclick',function(){const c=getChat();if(!c)return;const t=document.querySelector('.chat-item.active .title');if(t)startRenameChat(c,t)});
$('perf-btn').addEventListener('click',function(){const o=['low','medium','high'];perfMode=o[(o.indexOf(perfMode)+1)%3];settings.perf_mode=perfMode;saveStr(sk('perf_mode'),perfMode);save(sk('settings'),settings);applyPerfToSettings();updatePills();updatePerfPicker();updatePerfNote()});
function applyPerfToSettings(){
const p=PERF[perfMode];if(!p)return;
for(const k of['num_thread','num_gpu_percent','num_batch','num_ctx','num_predict'])settings[k]=p[k];
save(sk('settings'),settings);
for(const k of['num_thread','num_batch','num_ctx','num_predict']){const r=$('p_'+k),n=$('n_'+k);if(r)r.value=settings[k];if(n)n.value=settings[k]}
const rp=$('p_num_gpu_percent'),np=$('n_num_gpu_percent');if(rp)rp.value=settings.num_gpu_percent;if(np)np.value=settings.num_gpu_percent;
}
$('internet-btn').addEventListener('click',function(){const o=['off','auto','on'];internetMode=o[(o.indexOf(internetMode)+1)%3];saveStr(sk('net_mode'),internetMode);settings.net_mode=internetMode;save(sk('settings'),settings);updatePills();const s=$('net-mode');if(s)s.value=internetMode});
$('think-btn').addEventListener('click',function(){if(fastMode)return;thinkOn=!thinkOn;if(thinkOn)thinkArtOn=false;saveBool(sk('think_on'),thinkOn);saveBool(sk('think_art_on'),thinkArtOn);updatePills()});
$('think-art-btn').addEventListener('click',function(){if(fastMode)return;thinkArtOn=!thinkArtOn;if(thinkArtOn)thinkOn=false;saveBool(sk('think_art_on'),thinkArtOn);saveBool(sk('think_on'),thinkOn);updatePills()});
$('tools-btn').addEventListener('click',function(){if(fastMode)return;toolsOn=!toolsOn;saveBool(sk('tools_on'),toolsOn);settings.tools=toolsOn;save(sk('settings'),settings);updatePills()});
$('fast-btn').addEventListener('click',function(){fastMode=!fastMode;saveBool(sk('fast_mode'),fastMode);settings.fast_mode=fastMode;save(sk('settings'),settings);updatePills();const cb=$('fast-cb');if(cb)cb.checked=fastMode});
$('forms-btn').addEventListener('click',function(){if(fastMode)return;formsOn=!formsOn;saveBool(sk('forms_on'),formsOn);settings.forms_enabled=formsOn;save(sk('settings'),settings);updatePills();const cb=$('forms-cb');if(cb)cb.checked=formsOn});
$('raw-prompt-btn').addEventListener('click',function(){rawPromptMode=!rawPromptMode;saveBool(sk('raw_prompt_mode'),rawPromptMode);updatePills()});
$('animation-btn').addEventListener('click',function(){
textAnimationOn=!textAnimationOn;
saveBool(sk('text_animation'),textAnimationOn);
// The active response stream observes this flag in its next typewriter tick.
updatePills();
});
$('g4f-btn').addEventListener('click',function(){g4fOn=!g4fOn;saveBool(sk('g4f_on'),g4fOn);settings.g4f_enabled=g4fOn;save(sk('settings'),settings);updatePills();const cb=$('g4f-cb');if(cb)cb.checked=g4fOn});
function updatePerfPicker(){document.querySelectorAll('#perf-picker button').forEach(function(btn){btn.classList.remove('sel-low','sel-medium','sel-high');if(btn.dataset.mode===perfMode)btn.classList.add('sel-'+perfMode)})}
function updatePerfNote(){$('perf-note').textContent=PERF[perfMode].note}
document.querySelectorAll('#perf-picker button').forEach(function(btn){btn.addEventListener('click',function(){perfMode=btn.dataset.mode;settings.perf_mode=perfMode;saveStr(sk('perf_mode'),perfMode);save(sk('settings'),settings);applyPerfToSettings();updatePerfPicker();updatePerfNote();updatePills()})});
$('diag-btn').addEventListener('click',async function(){const b=$('diag-box');b.style.display='block';b.textContent='проверяю…';try{const d=await(await fetch('/diag')).json();b.textContent='=== ollama ps ===\n'+(d.ps||'пусто')+'\n\n=== version ===\n'+(d.version||'—')+'\n\n=== env ===\n'+(d.env||'—')+'\n\n=== проверка ===\n'+(d.check||'—')}catch(e){b.textContent='ошибка: '+e.message}});
async function loadStorage(){try{const d=await(await fetch('/storage')).json();$('storage-path').textContent=d.path||'—';$('storage-size').textContent=fmtBytes(d.size);const t=d.disk_total||0;const u=t-(d.free||0);$('storage-free').textContent=fmtBytes(d.free)+' из '+fmtBytes(t);const p=t>0?Math.min(100,Math.round(u/t*100)):0;$('storage-fill').style.width=p+'%';if(p>90)$('storage-fill').style.background='var(--err)';else if(p>75)$('storage-fill').style.background='var(--acc)';else $('storage-fill').style.background='var(--ok)'}catch(e){$('storage-path').textContent='ошибка: '+e.message}}
$('storage-refresh').addEventListener('click',loadStorage);
$('storage-move').addEventListener('click',async function(){const t=$('move-target').value.trim();if(!t){alert('Укажите путь');return}const s=$('move-status');if(!confirm('Скопировать?'))return;const b=$('storage-move');b.disabled=true;s.textContent='копирую…';try{const d=await(await fetch('/move_models',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({target:t})})).json();if(d.error){s.textContent='ошибка: '+d.error;s.style.color='var(--err)'}else{s.textContent='скопировано в '+d.to;s.style.color='var(--ok)';loadStorage()}}catch(e){s.textContent='ошибка: '+e.message;s.style.color='var(--err)'}finally{b.disabled=false}});
function updateComposerPresetUI(){
 const ctx=CONTEXT_PRESETS[settings.context_mode]||CONTEXT_PRESETS.medium;
 const trigger=$('context-trigger');
 if(trigger){trigger.textContent='Контекст · '+ctx.label+' ▴';trigger.setAttribute('aria-expanded',String($('context-menu').classList.contains('open')))}
 document.querySelectorAll('[data-context]').forEach(function(b){b.classList.toggle('active',b.dataset.context===(settings.context_mode||'medium'))});
 const ts=$('temperature-preset');if(ts)ts.value=settings.temperature_mode||'medium';
 const ls=$('length-preset');if(ls)ls.value=settings.length_mode||'medium';
}
function renderComposerModelSelect(){
 const s=$('chat-model-select');if(!s)return;
 const installed=(modelList||[]).filter(function(m){return m.installed});
 s.innerHTML='';
 if(!installed.length){const o=document.createElement('option');o.value='';o.textContent='нет установленных моделей';s.appendChild(o);s.disabled=true;return}
 s.disabled=false;
 installed.forEach(function(m){const o=document.createElement('option');o.value=m.name;o.textContent=m.name+(m.parameter_size?' · '+m.parameter_size:'');s.appendChild(o)});
 const selected=installed.some(function(m){return m.name===settings.model})?settings.model:installed[0].name;
 s.value=selected;
 if(settings.model!==selected){settings.model=selected;save(sk('settings'),settings)}
}
async function loadModels(){
 const managementChoice=$('model-select')&&$('model-select').value;
 try{modelList=await(await fetch('/models')).json()}catch(e){modelList=[]}
 renderModelSelect();
 // Keep the settings selector on the model the user was managing (including models not yet installed).
 if(managementChoice&&modelList.some(function(m){return m.name===managementChoice})){$('model-select').value=managementChoice;updateModelStatus()}
 renderComposerModelSelect();
}
function renderModelSelect(){
const s=$('model-select');s.innerHTML='';
if(!modelList.length){const o=document.createElement('option');o.textContent='нет моделей';o.value='';s.appendChild(o);updateModelStatus();return}
let found=false;
for(const m of modelList){const o=document.createElement('option');o.value=m.name;o.textContent=m.name+(m.parameter_size?' · '+m.parameter_size:'')+(m.quantization?' · '+m.quantization:'')+(m.installed?'':'  ↓');if(m.name===settings.model){o.selected=true;found=true}s.appendChild(o)}
if(!found){s.selectedIndex=0;settings.model=s.value;save(sk('settings'),settings)}
updateModelStatus();
renderComposerModelSelect();
}
function updateModelStatus(){
const n=$('model-select').value;
const target=mapQuantizedModel(n,selectedQuant());
const f=modelList.find(function(m){return m.name===target})||modelList.find(function(m){return m.name===n});
const targetInstalled=!!modelList.find(function(m){return m.name===target&&m.installed});
const st=$('model-status'),pb=$('model-pull'),db=$('model-delete');
if(!n){st.textContent='';st.className='model-status';pb.disabled=true;db.disabled=true;return}
if(targetInstalled){const tf=modelList.find(function(m){return m.name===target});st.textContent='установлена'+(tf&&tf.quantization?' · '+tf.quantization:'');st.className='model-status ok';pb.disabled=true;db.disabled=false}
else if(target&&target!==n){st.textContent='к загрузке: '+target;st.className='model-status dl';pb.disabled=false;db.disabled=true}
else if(f&&f.installed){st.textContent='установлена'+(f.quantization?' · '+f.quantization:'');st.className='model-status ok';pb.disabled=true;db.disabled=false}
else{st.textContent='не установлена';st.className='model-status';pb.disabled=false;db.disabled=true}
}
$('chat-model-select').addEventListener('change',function(){
 const name=$('chat-model-select').value;if(!name)return;
 settings.model=name;save(sk('settings'),settings);
 if($('model-select')){$('model-select').value=name;updateModelStatus();updateComputeNote()}
});
$('context-trigger').addEventListener('click',function(e){e.stopPropagation();const m=$('context-menu');m.classList.toggle('open');$('context-trigger').setAttribute('aria-expanded',String(m.classList.contains('open')))});
document.querySelectorAll('[data-context]').forEach(function(b){b.addEventListener('click',function(){
 settings.context_mode=b.dataset.context;save(sk('settings'),settings);updateComposerPresetUI();$('context-menu').classList.remove('open');$('context-trigger').setAttribute('aria-expanded','false');
})});
document.addEventListener('click',function(e){if(!$('context-menu').contains(e.target)&&e.target!==$('context-trigger')){$('context-menu').classList.remove('open');$('context-trigger').setAttribute('aria-expanded','false')}});
$('temperature-preset').addEventListener('change',function(){settings.temperature_mode=this.value;save(sk('settings'),settings);updateComposerPresetUI()});
$('length-preset').addEventListener('change',function(){settings.length_mode=this.value;save(sk('settings'),settings);updateComposerPresetUI()});
$('model-select').addEventListener('change',function(){
 const selected=$('model-select').value;
 const info=modelList.find(function(m){return m.name===selected});
 // In settings this selector doubles as a model installer. Choosing an uninstalled
 // model must not replace the active chat model until the user selects it below.
 if(info&&info.installed){settings.model=selected;save(sk('settings'),settings);renderComposerModelSelect()}
 updateModelStatus();updateComputeNote();
});
$('model-refresh').addEventListener('click',loadModels);
$('model-delete').addEventListener('click',async function(){const n=$('model-select').value;if(!n||!confirm('Удалить '+n+'?'))return;const b=$('model-delete');b.disabled=true;b.textContent='удаляю…';try{const d=await(await fetch('/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:n})})).json();if(d.error)alert('Ошибка: '+d.error);await loadModels();loadStorage()}catch(e){alert('Ошибка: '+e.message)}finally{b.textContent='удалить';updateModelStatus()}});
$('model-pull').addEventListener('click',async function(){
const selected=$('model-select').value;if(!selected)return;
const q=selectedQuant();const n=mapQuantizedModel(selected,q);
if(!n){alert('Для этой модели нельзя автоматически подобрать такой квантованный тег. Выберите «авто» или укажите уже существующий тег с нужной квантизацией.');return}
if(q!=='auto'&&n===selected){const meta=modelList.find(function(m){return m.name===selected});const actual=(meta&&meta.quantization||'').toUpperCase();if(actual!==q&&!(q==='F16'&&actual==='FP16')){alert('Выбранная модель не имеет подтверждённого тега '+q+'. Ollama не переквантует её на лету. Для другой квантизации выберите поддерживаемую семью (Mixtral 8x7B или Qwen2.5 32B) либо режим «авто».');return}}
const pb=$('model-pull'),st=$('model-status'),pr=$('pull-progress'),b=$('pull-bar');
pb.disabled=true;pr.classList.add('on');b.style.width='0%';st.textContent='загрузка '+n+'…';st.className='model-status dl';
try{
const response=await fetch('/pull',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:n})});
if(!response.ok){let err={};try{err=await response.json()}catch(e){}throw new Error(err.error||('HTTP '+response.status))}
const r=response.body.getReader();
const d=new TextDecoder();let buf='';
while(true){
const rr=await r.read();if(rr.done)break;
buf+=d.decode(rr.value,{stream:true});
const lines=buf.split('\n\n');buf=lines.pop();
for(const line of lines){
if(line.indexOf('data: ')!==0)continue;
let dd;try{dd=JSON.parse(line.slice(6))}catch(e){continue}
if(dd.error){st.textContent='ошибка: '+dd.error;st.className='model-status err';pr.classList.remove('on');pb.disabled=false;return}
if(dd.grand_total&&dd.grand_done){b.style.width=(dd.percent||0)+'%';const s=dd.speed_bps?(dd.speed_bps/(1024*1024)).toFixed(1)+' MB/s':'—';st.textContent=(dd.percent||0).toFixed(1)+'% · '+fmtBytes(dd.grand_done)+' / '+fmtBytes(dd.grand_total)+' · '+s}
if(dd.status==='success'){b.style.width='100%';st.textContent='установлена: '+n;st.className='model-status ok';settings.model=n;save(sk('settings'),settings);setTimeout(function(){pr.classList.remove('on')},800);pb.disabled=true;await loadModels();loadStorage();updateComputeNote();return}
}
}
}catch(e){st.textContent='ошибка: '+e.message;pr.classList.remove('on');pb.disabled=false}
});

function buildSettingsUI(){
const g={basic:$('group-basic'),sampling:$('group-sampling'),mirostat:$('group-mirostat')};
for(const p of PARAMS){
const gr=g[p.g];if(!gr)continue;
if(p.t==='check'){const l=document.createElement('label');l.className='check-row';const i=document.createElement('input');i.type='checkbox';i.id='p_'+p.k;l.appendChild(i);l.appendChild(document.createTextNode(p.l));gr.appendChild(l)}
else{
const r=document.createElement('div');r.className='param';
const l=document.createElement('label');l.textContent=p.l;l.htmlFor='p_'+p.k;
const rg=document.createElement('input');rg.type='range';rg.id='p_'+p.k;rg.min=p.min;rg.max=p.max;rg.step=p.step;
const nm=document.createElement('input');nm.type='number';nm.id='n_'+p.k;nm.min=p.min;nm.max=p.max;nm.step=p.step;nm.className='num-input';
function sync(v){let x=parseFloat(v);if(isNaN(x))x=p.d;if(x<p.min)x=p.min;if(x>p.max)x=p.max;rg.value=x;nm.value=x}
rg.addEventListener('input',function(){sync(rg.value)});
nm.addEventListener('change',function(){sync(nm.value)});
nm.addEventListener('input',function(){const x=parseFloat(nm.value);if(!isNaN(x)&&x>=p.min&&x<=p.max)rg.value=x});
r.appendChild(l);r.appendChild(rg);r.appendChild(nm);gr.appendChild(r);
}
}
const rp=$('p_num_gpu_percent'),np=$('n_num_gpu_percent');
if(rp&&np){
rp.addEventListener('input',function(){np.value=rp.value;settings.num_gpu_percent=parseInt(rp.value,10)});
np.addEventListener('change',function(){let v=parseInt(np.value,10);if(isNaN(v))v=100;v=Math.max(0,Math.min(100,v));np.value=v;rp.value=v;settings.num_gpu_percent=v});
}
const fbE=$('group-fb-extra');
const fr=document.createElement('div');fr.className='param';
const fl=document.createElement('label');fl.textContent='feedback_max';
const fr2=document.createElement('input');fr2.type='range';fr2.id='p_feedback_max';fr2.min=1;fr2.max=10;fr2.step=1;
const fn=document.createElement('input');fn.type='number';fn.id='n_feedback_max';fn.min=1;fn.max=10;fn.step=1;fn.className='num-input';
fr2.addEventListener('input',function(){fn.value=fr2.value});
fn.addEventListener('change',function(){let v=parseInt(fn.value,10)||3;v=Math.max(1,Math.min(10,v));fn.value=v;fr2.value=v});
fr.appendChild(fl);fr.appendChild(fr2);fr.appendChild(fn);fbE.appendChild(fr);

$('think-native-cb').addEventListener('change',function(e){thinkOn=e.target.checked;if(thinkOn)thinkArtOn=false;saveBool(sk('think_on'),thinkOn);saveBool(sk('think_art_on'),thinkArtOn);updatePills()});
$('think-art-cb').addEventListener('change',function(e){thinkArtOn=e.target.checked;if(thinkArtOn)thinkOn=false;saveBool(sk('think_art_on'),thinkArtOn);saveBool(sk('think_on'),thinkOn);updatePills()});
$('tools-cb').addEventListener('change',function(e){toolsOn=e.target.checked;saveBool(sk('tools_on'),toolsOn);settings.tools=toolsOn;save(sk('settings'),settings);updatePills()});
$('auto-math-cb').addEventListener('change',function(e){autoMath=e.target.checked;saveBool(sk('auto_math'),autoMath);settings.auto_math=autoMath;save(sk('settings'),settings)});
$('fast-cb').addEventListener('change',function(e){fastMode=e.target.checked;saveBool(sk('fast_mode'),fastMode);settings.fast_mode=fastMode;save(sk('settings'),settings);updatePills()});
$('forms-cb').addEventListener('change',function(e){formsOn=e.target.checked;saveBool(sk('forms_on'),formsOn);settings.forms_enabled=formsOn;save(sk('settings'),settings);updatePills()});
$('g4f-cb').addEventListener('change',function(e){g4fOn=e.target.checked;saveBool(sk('g4f_on'),g4fOn);settings.g4f_enabled=g4fOn;save(sk('settings'),settings);updatePills()});
$('g4f-mode').addEventListener('change',function(e){settings.g4f_mode=e.target.value;save(sk('settings'),settings)});
$('bot-name').addEventListener('input',function(e){settings.bot_name=e.target.value;save(sk('settings'),settings)});
$('bot-name-enabled').addEventListener('change',function(e){settings.bot_name_enabled=e.target.checked;save(sk('settings'),settings)});
$('auto-translate').addEventListener('change',function(e){translateOn=e.target.checked;settings.auto_translate=translateOn;saveBool(sk('translate_on'),translateOn);save(sk('settings'),settings);updatePills()});
$('fix-typos').addEventListener('change',function(e){fixOn=e.target.checked;settings.fix_typos=fixOn;saveBool(sk('fix_on'),fixOn);save(sk('settings'),settings);updatePills()});
$('show-net-log').addEventListener('change',function(e){settings.show_net_log=e.target.checked;save(sk('settings'),settings)});
$('save-draft').addEventListener('change',function(e){settings.save_draft=e.target.checked;save(sk('settings'),settings);if(!settings.save_draft)localStorage.removeItem(sk('draft'))});
$('stream-think').addEventListener('change',function(e){streamThink=e.target.checked;saveBool(sk('stream_think'),streamThink)});
$('net-mode').addEventListener('change',function(e){internetMode=e.target.value;settings.net_mode=internetMode;saveStr(sk('net_mode'),internetMode);save(sk('settings'),settings);updatePills()});
$('target-lang').addEventListener('change',function(e){settings.target_lang=e.target.value;save(sk('settings'),settings)});
}
function fillSettings(){
if(!$('sys-prompt'))return;
$('sys-prompt').value=settings.system_prompt;
$('fb-enabled').checked=!!settings.feedback_enabled;
$('auto-translate').checked=!!translateOn;
$('fix-typos').checked=!!fixOn;
$('show-net-log').checked=settings.show_net_log!==false;
$('save-draft').checked=settings.save_draft!==false;
$('stream-think').checked=!!streamThink;
$('net-mode').value=internetMode;
$('target-lang').value=settings.target_lang||'auto';
$('think-native-cb').checked=thinkOn;
$('think-art-cb').checked=thinkArtOn;
$('tools-cb').checked=toolsOn;
$('auto-math-cb').checked=autoMath;
$('fast-cb').checked=fastMode;
$('forms-cb').checked=formsOn;
$('g4f-cb').checked=g4fOn;
$('g4f-mode').value=settings.g4f_mode||'off';
$('compute-device').value=settings.compute_device||'xpu';$('quantization-select').value=settings.quantization||'auto';updateComputeNote();
$('bot-name').value=settings.bot_name||'';
$('bot-name-enabled').checked=!!settings.bot_name_enabled;
for(const p of PARAMS){if(p.t==='check'){const i=$('p_'+p.k);if(i)i.checked=!!settings[p.k]}else{const r=$('p_'+p.k),n=$('n_'+p.k);if(r&&n){const v=parseFloat(settings[p.k]);r.value=v;n.value=v}}}
const rp=$('p_num_gpu_percent'),np=$('n_num_gpu_percent');if(rp&&np){const v=parseInt(settings.num_gpu_percent,10)||100;rp.value=v;np.value=v}
const fbR=$('p_feedback_max'),fbN=$('n_feedback_max');if(fbR&&fbN){fbR.value=settings.feedback_max;fbN.value=settings.feedback_max}
updatePerfPicker();updatePerfNote();
}
function readSettings(){
if(!$('sys-prompt'))return;
settings.system_prompt=$('sys-prompt').value;
settings.feedback_enabled=$('fb-enabled').checked;
settings.auto_translate=$('auto-translate').checked;
settings.fix_typos=$('fix-typos').checked;
settings.show_net_log=$('show-net-log').checked;
settings.save_draft=$('save-draft').checked;
settings.net_mode=$('net-mode').value;
settings.target_lang=$('target-lang').value;
settings.bot_name=$('bot-name').value;
settings.bot_name_enabled=$('bot-name-enabled').checked;
settings.g4f_mode=$('g4f-mode').value;
settings.compute_device=$('compute-device').value;settings.quantization=$('quantization-select').value;
const fbN=$('n_feedback_max');if(fbN)settings.feedback_max=parseInt(fbN.value,10)||3;
for(const p of PARAMS){if(p.t==='check'){const i=$('p_'+p.k);if(i)settings[p.k]=i.checked}else{const n=$('n_'+p.k);if(!n)continue;const v=parseFloat(n.value);if(!isNaN(v))settings[p.k]=String(p.step).includes('.')?v:Math.round(v)}}
const np=$('n_num_gpu_percent');if(np)settings.num_gpu_percent=Math.max(0,Math.min(100,parseInt(np.value,10)||100));
translateOn=settings.auto_translate;fixOn=settings.fix_typos;internetMode=settings.net_mode;
}

function init(){
buildSettingsUI();
settings.context_mode=CONTEXT_PRESETS[settings.context_mode]?settings.context_mode:'medium';
settings.temperature_mode=TEMPERATURE_PRESETS[settings.temperature_mode]?settings.temperature_mode:'medium';
settings.length_mode=LENGTH_PRESETS[settings.length_mode]?settings.length_mode:'medium';
updateComposerPresetUI();
loadModels();loadStorage();
if(chats.length===0){const c=newChat();activeId=c.id}else{const savedActive=loadStr(sk('active_chat'),'');activeId=chats.some(function(c){return c.id===savedActive})?savedActive:chats[0].id;}
renderList();
const c=getChat();
if(c){chatTitleEl.textContent=c.title;renderMessages(c.messages)}
applyPerfToSettings();
updatePills();updateCharCount();restoreDraft();
updateEmoBadges();
lastDecayTime=Date.now();
dbg('info','init','ready');
if(window.innerWidth<=720)sidebar.classList.add('hidden');
inputEl.focus();
}
init();
</script>
</body>
</html>'''

@app.route("/")
def index():
    return Response(HTML, mimetype="text/html; charset=utf-8")

@app.route("/diag", methods=["GET"])
def diag():
    env_keys = ["OLLAMA_VULKAN","OLLAMA_IGPU_ENABLE","OLLAMA_NUM_GPU","OLLAMA_NUM_PARALLEL","OLLAMA_MODELS","OPENVINO_MODEL_PATH"]
    env_lines = [f"{k}={os.environ.get(k,'—')}" for k in env_keys]
    dri = ", ".join(os.listdir("/dev/dri")) if os.path.isdir("/dev/dri") else "/dev/dri не виден приложению"
    docker_devices = run_cmd(["docker", "inspect", "-f", "{{json .HostConfig.Devices}}", "ollama-xpu"])
    ps = run_cmd(["docker", "exec", "ollama-xpu", "/ollama", "ps"])
    chk = []
    if "100% GPU" in ps: chk.append("✓ модель на GPU")
    elif "GPU/CPU" in ps: chk.append("✓ гибрид")
    elif "100% CPU" in ps: chk.append("✗ на CPU")
    elif not ps or "нет" in ps: chk.append("· не загружена")
    else: chk.append("? неизвестно")
    ver = run_cmd(["docker", "exec", "ollama-xpu", "/ollama", "--version"])
    chk.append("XPU /dev/dri: " + dri)
    chk.append("Docker devices: " + docker_devices)
    chk.append("NPU OpenVINO: " + ("путь задан" if os.environ.get("OPENVINO_MODEL_PATH") else "OPENVINO_MODEL_PATH не задан"))
    return jsonify({"ps": ps, "version": ver, "env": "\n".join(env_lines), "check": "\n".join(chk), "dri": dri, "docker_devices": docker_devices})

@app.route("/metrics", methods=["GET"])
def metrics_info():
    total, available = system_memory()
    models = []
    try:
        rr = requests.get(f"{OLLAMA_URL}/api/ps", timeout=2)
        if rr.ok: models = rr.json().get("models", [])
    except Exception:
        pass
    return jsonify({"ram_total": total, "ram_available": available,
                    "ram_used": max(0, total - available),
                    "ram_pct": (100.0 * (total - available) / total) if total else None,
                    "loaded_models": [{"name": m.get("name"), "size": m.get("size"), "size_vram": m.get("size_vram")} for m in models],
                    "compute_device": os.environ.get("COMPUTE_DEVICE", "xpu"),
                    "openvino_model_path_set": bool(os.environ.get("OPENVINO_MODEL_PATH"))})

@app.route("/storage", methods=["GET"])
def storage_info():
    p = models_dir()
    size = dir_size(p)
    free = 0; total = 0
    try:
        df = subprocess.run(["df","-B1", p if os.path.isdir(p) else "/"], capture_output=True, text=True, timeout=5).stdout
        lines = df.strip().split("\n")
        if len(lines) >= 2:
            parts = lines[1].split()
            total = int(parts[1]); free = int(parts[3])
    except: pass
    return jsonify({"path": p, "size": size, "free": free, "disk_total": total})

@app.route("/move_models", methods=["POST"])
def move_models():
    data = request.get_json(silent=True) or {}
    target = (data.get("target") or "").strip()
    if not target: return jsonify({"error": "target required"}), 400
    src = models_dir()
    if not os.path.isdir(src): return jsonify({"error": "источник не найден"}), 400
    try:
        os.makedirs(target, exist_ok=True)
        dst = os.path.join(target, "models") if not os.path.basename(target) == "models" else target
        os.makedirs(dst, exist_ok=True)
        shutil.copytree(src, dst, dirs_exist_ok=True)
        return jsonify({"ok": True, "from": src, "to": target})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/delete", methods=["POST"])
def delete_model():
    data = request.get_json(silent=True) or {}
    model = (data.get("model") or "").strip()
    if not model: return jsonify({"error": "model required"}), 400
    try:
        ollama_delete(model)
        return jsonify({"ok": True, "model": model})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/models", methods=["GET"])
def list_models():
    tags = ollama_tags()
    by_name = {(m.get("name") or m.get("model") or ""): m for m in tags if (m.get("name") or m.get("model"))}
    result = []; seen = set()
    for n in MODEL_CATALOG:
        m = by_name.get(n, {})
        details = m.get("details") or {}
        result.append({"name": n, "installed": n in by_name, "quantization": details.get("quantization_level", ""),
                       "parameter_size": details.get("parameter_size", ""), "size": m.get("size", 0)})
        seen.add(n)
    for n, m in by_name.items():
        if n and n not in seen:
            details = m.get("details") or {}
            result.append({"name": n, "installed": True, "quantization": details.get("quantization_level", ""),
                           "parameter_size": details.get("parameter_size", ""), "size": m.get("size", 0)})
    return jsonify(result)

@app.route("/pull", methods=["POST"])
def pull_model():
    data = request.get_json(silent=True) or {}
    model = (data.get("model") or "").strip()
    if not model: return jsonify({"error": "model required"}), 400
    def gen():
        dt = {}; dd = {}
        lt = time.time(); lb = 0; sp = 0.0
        try:
            for p in ollama_pull_stream(model):
                dg = p.get("digest"); t = p.get("total"); c = p.get("completed")
                if dg and t: dt[dg] = max(dt.get(dg, 0), int(t))
                if dg and c is not None: dd[dg] = int(c)
                gt = sum(dt.values()); gd = sum(dd.values())
                now = time.time(); d = now - lt
                if d > 0.3 and gd > lb:
                    ins = (gd - lb) / d
                    sp = ins if sp == 0 else (0.7 * ins + 0.3 * sp)
                    lb = gd; lt = now
                if gt > 0:
                    p["grand_total"] = gt; p["grand_done"] = gd
                    p["percent"] = round(gd / gt * 100, 1)
                    p["speed_bps"] = sp
                yield "data: " + json.dumps(p, default=str) + "\n\n"
                if p.get("status") == "success":
                    yield "data: " + json.dumps({"status": "final"}) + "\n\n"
                    return
        except Exception as e:
            yield "data: " + json.dumps({"error": str(e)}, default=str) + "\n\n"
    return Response(gen(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    raw_prompt_mode = bool(data.get("raw_prompt_mode", False))
    model = (data.get("model") or DEFAULT_MODEL).strip()
    compute_device = (data.get("compute_device") or "xpu").strip().lower()
    quantization = (data.get("quantization") or "auto").strip().upper()
    npu_model_path = os.environ.get("OPENVINO_MODEL_PATH", "")
    net_mode = (data.get("net_mode") or "auto").strip()
    if raw_prompt_mode:
        net_mode = "off"
    # Native model reasoning is an independent generation option: clean-prompt mode
    # removes app-injected instructions/history, but must not silently disable thinking.
    think = bool(data.get("think", False))
    think_art = bool(data.get("think_art", False)) and not raw_prompt_mode
    tools_on = bool(data.get("tools", False)) and not raw_prompt_mode
    auto_math = bool(data.get("auto_math", True)) and not raw_prompt_mode
    auto_translate = bool(data.get("auto_translate", False)) and not raw_prompt_mode
    target_lang = (data.get("target_lang") or "auto").strip()
    fix_typos = bool(data.get("fix_typos", True)) and not raw_prompt_mode
    show_net_log = bool(data.get("show_net_log", True)) and not raw_prompt_mode
    system_prompt = (data.get("system_prompt") or SYS).strip()
    history = data.get("history") or []
    feedback = data.get("feedback") or None
    feedback_enabled = bool(data.get("feedback_enabled", True))
    feedback_max = int(data.get("feedback_max", 3) or 3)
    params = data.get("params") or {}
    user_id = (data.get("user_id") or "default").strip()
    forms_enabled = bool(data.get("forms_enabled", True)) and not raw_prompt_mode
    g4f_enabled = bool(data.get("g4f_enabled", False)) and not raw_prompt_mode
    g4f_mode = "off" if raw_prompt_mode else (data.get("g4f_mode") or "off").strip()
    if think and think_art: think_art = False
    def opt(k, d, c):
        try: return c(params.get(k, d))
        except: return d
    temperature = opt("temperature", 0.6, float)
    num_predict = opt("num_predict", 4096, int)
    num_ctx = opt("num_ctx", 8192, int)
    num_thread = opt("num_thread", 12, int)
    thinking_time_limit = opt("thinking_time_limit", 180, int)
    top_k = opt("top_k", 40, int)
    top_p = opt("top_p", 0.9, float)
    repeat_penalty = opt("repeat_penalty", 1.15, float)
    repeat_last_n = opt("repeat_last_n", 256, int)
    seed = opt("seed", 0, int)
    mirostat = opt("mirostat", 0, int)
    num_batch = opt("num_batch", 512, int)
    num_gpu_percent = opt("num_gpu_percent", 75, int)
    if compute_device == "cpu":
        num_gpu = 0
    else:
        num_gpu = 999 if num_gpu_percent >= 100 else 999
    # 32 GB machines need conservative context and batch sizes for 32B/47B models.
    if compute_device != "npu" and ("mixtral:8x7b" in model.lower() or "qwen2.5:32b" in model.lower()):
        num_ctx = min(num_ctx, 4096)
        num_batch = min(num_batch, 128)
        num_predict = min(num_predict, 2048)
        num_thread = min(num_thread, max(4, (os.cpu_count() or 8) - 2))
    target_model = model
    quant_error = None
    if compute_device not in ("cpu", "xpu", "npu"):
        quant_error = "Неизвестный вычислитель: " + compute_device
    elif compute_device != "npu" and quantization != "AUTO":
        try:
            target_model = quantized_model_name(model, quantization)
            if not target_model:
                quant_error = ("Для выбранной пользовательской модели нельзя поменять формат на лету. "
                               "Выберите уже установленный тег с нужной квантизацией или режим «авто».")
            elif target_model != model:
                installed = {m.get("name") or m.get("model") for m in ollama_tags()}
                if target_model not in installed:
                    quant_error = "Нужный тег ещё не установлен: " + target_model + ". Откройте настройки модели и нажмите «скачать» при выбранной квантизации."
        except Exception as e:
            quant_error = str(e)
    if compute_device == "npu" and not npu_model_path:
        quant_error = "Для NPU задайте OPENVINO_MODEL_PATH на каталог заранее экспортированной OpenVINO GenAI модели."
    if compute_device != "npu":
        model = target_model
    precomputed = None
    if auto_math:
        e, r = extract_math(prompt)
        if r is not None: precomputed = (e, r)

    def gen():
        if not prompt:
            yield "data: " + json.dumps({"type": "error", "text": "пустой запрос"}) + "\n\n"
            return
        if quant_error:
            yield "data: " + json.dumps({"type": "error", "text": quant_error}, ensure_ascii=False) + "\n\n"
            return
        sc = system_prompt
        fbu = 0
        if not raw_prompt_mode:
            if feedback_enabled and feedback:
                pos = (feedback.get("positive") or [])[-feedback_max:]
                neg = (feedback.get("negative") or [])[-feedback_max:]
                if pos or neg:
                    lines = ["Оценки пользователя:"]
                    if pos:
                        lines.append("Одобрено:")
                        for i, t in enumerate(pos, 1): lines.append(f"{i}) {t}")
                    if neg:
                        lines.append("Отклонено:")
                        for i, t in enumerate(neg, 1): lines.append(f"{i}) {t}")
                    sc += "\n\n" + "\n".join(lines)
                    fbu = len(pos) + len(neg)
            if precomputed:
                sc += f"\n\nТочный результат: {precomputed[0]} = {precomputed[1]}."
            if think: sc += THINK_INSTR
            if tools_on: sc += TOOLS_INSTR
            if fix_typos:
                lh = layout_swap(prompt)
                fi = "\n\nЕсли опечатки или неверная раскладка — начни со строки [FIX]исправленный[/FIX] и сразу ответ."
                if lh and lh != prompt:
                    fi += f"\n\nПодсказка: «{prompt}» в русской раскладке даёт «{lh}»."
                sc += fi
            if think_art:
                sc += THINK_ART
                if fix_typos: sc += "\n\nПорядок: сначала [FIX], потом [THINK], потом ответ."
            if forms_enabled:
                sc += FORMATS
            else:
                sc += "\n\nНе используй специальные теги-блоки. Пиши обычным текстом. Разрешены только **жирный**, *курсив*, __подчёркнутый__, ~~зачёркнутый~~, ==выделение==, `код`, > цитата."
            if g4f_enabled and g4f_mode in ("auto","manual"):
                sc += "\n\nЕсли не справляешься (не хватает знаний, запутался) — можешь вызвать помощь: напиши ровно [HELP]вопрос[/HELP] и остановись."
            if auto_translate:
                if target_lang == "auto": sc += "\n\nЕсли пользователь не на русском, отвечай по-русски."
                elif target_lang in LANG_NAMES: sc += f"\n\nОтвечай на {LANG_NAMES[target_lang]} языке."
        do_search = (not raw_prompt_mode) and (net_mode == "on" or (net_mode == "auto" and should_search(prompt)))
        if do_search:
            if show_net_log:
                yield "data: " + json.dumps({"type": "net", "text": "→ " + prompt[:200]}) + "\n\n"
            yield "data: " + json.dumps({"type": "status", "text": "поиск..."}) + "\n\n"
            results, err = search(prompt)
            if results:
                if show_net_log:
                    yield "data: " + json.dumps({"type": "net", "text": "→ результатов: " + str(len(results))}) + "\n\n"
                    seen = set()
                    for r in results:
                        u = r.get("href") or r.get("url") or ""
                        try: dn = urlparse(u).netloc or u
                        except: dn = u
                        if dn and dn not in seen:
                            seen.add(dn)
                            yield "data: " + json.dumps({"type": "net", "text": "→ " + dn}) + "\n\n"
                ctx = web_ctx(results)
                if ctx:
                    sc += "\n\nДанные из интернета:\n" + ctx
                    yield "data: " + json.dumps({"type": "status", "text": "сеть: получено"}) + "\n\n"
            else:
                yield "data: " + json.dumps({"type": "status", "text": "сеть: нет"}) + "\n\n"
        # J-AI: не навязываем системный промпт приложения
        is_jai_model = str(model).lower().startswith("j-ai-4.2b")
        base = [] if (raw_prompt_mode or is_jai_model) else [{"role": "system", "content": sc}]
        for h in ([] if raw_prompt_mode else history):
            r = h.get("role"); c = h.get("content")
            if r in ("user", "assistant") and c: base.append({"role": r, "content": c})
        base.append({"role": "user", "content": prompt})
        options = {"num_thread": num_thread, "temperature": temperature, "repeat_penalty": repeat_penalty,
            "repeat_last_n": repeat_last_n, "num_ctx": num_ctx, "num_predict": num_predict,
            "top_k": top_k, "top_p": top_p, "seed": seed, "mirostat": mirostat,
            "num_batch": num_batch, "num_gpu": num_gpu}
        if str(model).lower().startswith("j-ai-4.2b"):
            options.update({
                "temperature": 0.7,
                "top_p": 0.9,
                "repeat_penalty": 1.05
            })
        start = time.time()
        tt = 0; etn = 0; tstart = None; tend = None; tstarted = False; lim = False; tu = 0
        g4f_used = False
        try:
            cur = list(base)
            maxr = 3 if tools_on else 1
            for ri in range(maxr):
                if time.time() - start > TIMEOUT:
                    yield "data: " + json.dumps({"type": "error", "text": "таймаут"}) + "\n\n"
                    return
                tbuf = ""; tdet = None; tchk = tools_on
                help_detected = None
                help_buf = ""
                help_check = g4f_enabled and g4f_mode in ("auto","manual")
                for ch in ollama_chat_stream(model, cur, options, think=think, device=compute_device, npu_model_path=npu_model_path):
                    msg = ch.get("message", {}) or {}
                    th = msg.get("thinking"); ct = msg.get("content", "")
                    if th:
                        if tstart is None:
                            tstart = time.time()
                            if not tstarted:
                                tstarted = True
                                yield "data: " + json.dumps({"type": "thinking_start"}) + "\n\n"
                        over = thinking_time_limit > 0 and (time.time() - tstart) > thinking_time_limit
                        if over:
                            if not lim:
                                lim = True
                                yield "data: " + json.dumps({"type": "status", "text": "лимит"}) + "\n\n"
                        else:
                            yield "data: " + json.dumps({"type": "thinking", "text": th}) + "\n\n"
                    if ct:
                        if tstart and tend is None:
                            tend = time.time()
                            yield "data: " + json.dumps({"type": "thinking_end"}) + "\n\n"
                        if tchk:
                            tbuf += ct
                            cm = CALC_FULL.match(tbuf)
                            if cm: tdet = cm.group(0).strip(); tchk = False; break
                            sm = TOOL_PFX.match(tbuf)
                            if sm and sm.group(1) in ("[TIME]","[TIMER_START]","[TIMER_NOW]","[TIMER_STOP]"):
                                tdet = sm.group(1); tchk = False; break
                            st = tbuf.lstrip()
                            if not st.startswith("["):
                                tchk = False
                                yield "data: " + json.dumps({"type": "content", "text": tbuf}) + "\n\n"
                                tbuf = ""; continue
                            cand = ["[TIME]","[CALC]","[TIMER_START]","[TIMER_NOW]","[TIMER_STOP]"]
                            could = any(c.startswith(st) for c in cand)
                            if st.startswith("[CALC]") and "[/CALC]" not in st: could = True
                            if could and len(tbuf) < 200: continue
                            tchk = False
                            yield "data: " + json.dumps({"type": "content", "text": tbuf}) + "\n\n"
                            tbuf = ""; continue
                        elif help_check:
                            help_buf += ct
                            hm = HELP_RE.match(help_buf)
                            if hm:
                                help_detected = hm.group(1).strip()
                                help_check = False
                                break
                            st = help_buf.lstrip()
                            if not st.startswith("[HELP]") and not "[HELP]".startswith(st):
                                help_check = False
                                yield "data: " + json.dumps({"type": "content", "text": help_buf}) + "\n\n"
                                help_buf = ""
                                continue
                            if len(help_buf) > 500:
                                help_check = False
                                yield "data: " + json.dumps({"type": "content", "text": help_buf}) + "\n\n"
                                help_buf = ""
                                continue
                            continue
                        else:
                            yield "data: " + json.dumps({"type": "content", "text": ct}) + "\n\n"
                    if "eval_count" in ch: tt = ch["eval_count"]
                    if "eval_duration" in ch: etn = ch["eval_duration"]
                if help_buf and not help_detected:
                    yield "data: " + json.dumps({"type": "content", "text": help_buf}) + "\n\n"
                    help_buf = ""
                if tbuf and not tdet:
                    yield "data: " + json.dumps({"type": "content", "text": tbuf}) + "\n\n"
                    tbuf = ""
                if help_detected:
                    g4f_used = True
                    yield "data: " + json.dumps({"type": "g4f_used", "text": "external help"}) + "\n\n"
                    yield "data: " + json.dumps({"type": "status", "text": "g4f: запрос"}) + "\n\n"
                    gmsgs = [{"role":"system","content":"Ты — полезный помощник."},{"role":"user","content":help_detected}]
                    gres = ask_g4f(gmsgs)
                    if gres:
                        yield "data: " + json.dumps({"type": "content", "text": "**g4f:** " + gres}) + "\n\n"
                    else:
                        yield "data: " + json.dumps({"type": "content", "text": "\n\n*g4f недоступен*\n\n"}) + "\n\n"
                    cur.append({"role": "assistant", "content": "[HELP]" + help_detected + "[/HELP]"})
                    cur.append({"role": "user", "content": "[РЕЗУЛЬТАТ g4f] " + (gres or "недоступен") + "\n\nПродолжи."})
                    if ri < maxr - 1: continue
                    else: break
                if tdet:
                    res = exec_tool(tdet, user_id)
                    tu += 1
                    yield "data: " + json.dumps({"type": "tool_call", "text": tdet}) + "\n\n"
                    yield "data: " + json.dumps({"type": "tool_result", "text": res}) + "\n\n"
                    cur.append({"role": "assistant", "content": tdet})
                    cur.append({"role": "user", "content": f"[РЕЗУЛЬТАТ] {res}\n\nПродолжи."})
                    if ri < maxr - 1: continue
                    else: break
                else: break
            if tstart and tend is None:
                tend = time.time()
                yield "data: " + json.dumps({"type": "thinking_end"}) + "\n\n"
            dur = time.time() - start
            td = (tend - tstart) if (tstart and tend) else 0.0
            st = {"duration": dur, "tokens": tt, "speed": 0.0, "feedback_used": fbu, "thinking_duration": td, "tools_used": tu, "g4f_used": g4f_used}
            if tt and etn: st["speed"] = tt / (etn / 1_000_000_000)
            yield "data: " + json.dumps({"type": "done", "stats": st}) + "\n\n"
        except GeneratorExit: pass
        except Exception as e:
            if g4f_enabled and g4f_mode == "auto":
                gres = ask_g4f([{"role":"system","content":"Ты — полезный помощник."},{"role":"user","content":prompt}])
                if gres:
                    yield "data: " + json.dumps({"type": "g4f_used", "text": "fallback"}) + "\n\n"
                    yield "data: " + json.dumps({"type": "content", "text": "**g4f:** " + gres}) + "\n\n"
                    yield "data: " + json.dumps({"type": "done", "stats": {"duration": time.time()-start, "tokens": 0, "speed": 0, "g4f_used": True}}) + "\n\n"
                    return
            try: yield "data: " + json.dumps({"type": "error", "text": str(e)}) + "\n\n"
            except: pass
    return Response(gen(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

def main():
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    ip = local_ip()
    print("=" * 60)
    print("  local/ai → docker ollama-xpu")
    print("=" * 60)
    print(f"  local:  http://127.0.0.1:{port}/")
    print(f"  lan:    http://{ip}:{port}/")
    print(f"  ollama: {OLLAMA_URL}")
    print(f"  модели: {models_dir()}")
    print(f"  /dev/dri: {' '.join(os.listdir('/dev/dri')) if os.path.isdir('/dev/dri') else 'не обнаружен'}")
    print(f"  OpenVINO NPU: {'путь задан' if os.environ.get('OPENVINO_MODEL_PATH') else 'OPENVINO_MODEL_PATH не задан'}")
    print(f"  g4f:    {'✓' if G4F_OK else '✗ (pip install g4f)'}")
    print("=" * 60)
    app.run(host=host, port=port, threaded=True, debug=False)

if __name__ == "__main__":
    main()
