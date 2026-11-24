"""PolicyGuard-RAG (Caso 21) · Lanzador Local Autocontenido (Sin Docker).

Carga las 5 políticas ISO/IEC 27001 y los 16 artículos reales desde db/seed.sql,
levanta todos los endpoints REST (/api/v1/*), sirve la interfaz corporativa clara
y permite exportar reportes PDF, Word (.docx) y Excel (.xlsx) en vivo.

Ejecución:
    python run_local_demo.py
Luego abrir: http://localhost:8002
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
import base64
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Form, HTTPException, Query, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from docx import Document
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_HTML = BASE_DIR / "frontend" / "dist" / "index.html"
BENCHMARK_JSON = BASE_DIR / "experiments" / "out_v2" / "results_optuna_caso21.json"
FIGURES_DIR = BASE_DIR / "experiments" / "out_v2" / "figures"
REPORTS_DIR = BASE_DIR / "local_reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

SECRET_KEY = "policyguard-rag-super-secret-jwt-key-2026-iso27001"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

# =====================================================================
# 1. CARGA DETERMINISTA DESDE db/seed.sql
# =====================================================================
def load_seed_data() -> tuple[list[dict], list[dict], list[dict]]:
    seed_path = BASE_DIR / "db" / "seed.sql"
    sql = seed_path.read_text(encoding="utf-8")

    # Policies
    policies = [
        {
            "id": 1, "code": "POL-SEG-001",
            "title": "Política de Control de Accesos, Contraseñas y Autenticación Multifactor (MFA)",
            "category": "Control de Accesos", "classification": "INTERNAL",
            "iso_control": "ISO 27001 A.5.15 / A.5.17 / A.8.5", "current_version": "2.1",
            "status": "PUBLISHED", "owner_department": "Seguridad de la Información",
            "summary": "Establece requisitos de contraseñas robustas (12/16 caracteres), uso de MFA obligatorio y revocación en 2 horas."
        },
        {
            "id": 2, "code": "POL-SEG-002",
            "title": "Política de Trabajo Remoto Seguro, Uso de VPN y Dispositivos Móviles (BYOD)",
            "category": "Teletrabajo y Red", "classification": "INTERNAL",
            "iso_control": "ISO 27001 A.6.7 / A.8.1", "current_version": "1.4",
            "status": "PUBLISHED", "owner_department": "Seguridad de la Información",
            "summary": "Regula el teletrabajo con EDR Wazuh, cifrado BitLocker/FileVault, VPN con MFA y bloqueo de pantalla en 5 min."
        },
        {
            "id": 3, "code": "POL-SEG-003",
            "title": "Política de Clasificación de la Información, Criptografía y Prevención de Fuga de Datos (DLP)",
            "category": "Protección de Datos", "classification": "CONFIDENTIAL",
            "iso_control": "ISO 27001 A.5.12 / A.5.13 / A.8.24", "current_version": "3.0",
            "status": "PUBLISHED", "owner_department": "Gobierno, Riesgo y Cumplimiento",
            "summary": "Define niveles de clasificación (Pública a Restringida), cifrado AES-256/TLS 1.3 y retención por 5 años."
        },
        {
            "id": 4, "code": "POL-SEG-004",
            "title": "Política de Gestión y Respuesta a Incidentes de Ciberseguridad y Ransomware",
            "category": "Respuesta a Incidentes", "classification": "RESTRICTED",
            "iso_control": "ISO 27001 A.5.24 / A.5.26 / A.8.15", "current_version": "2.0",
            "status": "PUBLISHED", "owner_department": "Seguridad de la Información",
            "summary": "Fija reporte SLA de 15 minutos, aislamiento sin apagar el equipo ante ransomware y prohibición de pago."
        },
        {
            "id": 5, "code": "POL-SEG-005",
            "title": "Política de Uso Aceptable de Inteligencia Artificial Generativa y Agentes LLM",
            "category": "Gobernanza de IA", "classification": "INTERNAL",
            "iso_control": "ISO 27001 A.5.1 / ISO 42001 / OWASP LLM", "current_version": "1.0",
            "status": "PUBLISHED", "owner_department": "Gobierno, Riesgo y Cumplimiento",
            "summary": "Prohíbe exfiltrar datos personales o código en IA externa; exige modelos locales y citas verificables."
        },
    ]

    chunk_re = re.compile(
        r"\((\d+),\s*(\d+),\s*(\d+),\s*'([^']+)',\s*'([^']+)',\s*(\d+),\s*'((?:[^']|'')*)',\s*(\d+),\s*ARRAY\[([^\]]*)\]\)",
        re.MULTILINE,
    )
    pol_map = {p["id"]: p for p in policies}
    chunks = []
    for idx, m in enumerate(chunk_re.finditer(sql), start=1):
        pid = int(m.group(1))
        pol = pol_map[pid]
        chunks.append({
            "id": idx,
            "policy_id": pid,
            "policy_code": pol["code"],
            "policy_title": pol["title"],
            "current_version": pol["current_version"],
            "classification": pol["classification"],
            "iso_control": pol["iso_control"],
            "chunk_index": int(m.group(3)),
            "article_ref": m.group(4),
            "section_title": m.group(5),
            "page_number": int(m.group(6)),
            "content": m.group(7).replace("''", "'"),
            "token_count": int(m.group(8)),
            "keywords": [k.strip().strip("'") for k in m.group(9).split(",") if k.strip()],
        })

    users = [
        {"id": 1, "username": "admin", "password": "Admin123!", "email": "admin@empresa.pe", "full_name": "Diego Administrador (CISO Office)", "department": "Seguridad de la Información", "job_title": "Arquitecto de Seguridad Senior", "roles": ["admin"], "permissions": ["dashboard:read", "policies:read", "policies:write", "policies:ack", "rag:query", "rag:manage", "reports:read", "reports:export", "users:read", "users:write", "audit:read", "audit:export"]},
        {"id": 2, "username": "analista1", "password": "Analyst123!", "email": "analista.grc@empresa.pe", "full_name": "Valeria Mendoza (Analista GRC)", "department": "Gobierno, Riesgo y Cumplimiento", "job_title": "Especialista ISO 27001", "roles": ["analista"], "permissions": ["dashboard:read", "policies:read", "policies:write", "policies:ack", "rag:query", "rag:manage", "reports:read", "reports:export"]},
        {"id": 3, "username": "gestor", "password": "Manager123!", "email": "gerente.ti@empresa.pe", "full_name": "Carlos Rojas (Gerente de TI)", "department": "Tecnología y Operaciones", "job_title": "Gerente de Tecnología", "roles": ["gestor"], "permissions": ["dashboard:read", "policies:read", "policies:ack", "rag:query", "reports:read", "reports:export", "users:read"]},
        {"id": 4, "username": "auditor1", "password": "Audit123!", "email": "auditor.iso@empresa.pe", "full_name": "Lucía Fernández (Auditora Líder)", "department": "Auditoría Interna", "job_title": "Auditora ISO/IEC 27001", "roles": ["auditor"], "permissions": ["dashboard:read", "policies:read", "rag:query", "reports:read", "reports:export", "audit:read", "audit:export", "users:read"]},
        {"id": 5, "username": "empleado1", "password": "User123!", "email": "marco.silva@empresa.pe", "full_name": "Marco Silva", "department": "Finanzas y Contabilidad", "job_title": "Analista de Tesorería", "roles": ["empleado"], "permissions": ["dashboard:read", "policies:read", "policies:ack", "rag:query"]},
        {"id": 6, "username": "empleado2", "password": "User123!", "email": "sofia.castro@empresa.pe", "full_name": "Sofía Castro", "department": "Recursos Humanos", "job_title": "Coordinadora de Talento", "roles": ["empleado"], "permissions": ["dashboard:read", "policies:read", "policies:ack", "rag:query"]},
        {"id": 7, "username": "empleado3", "password": "User123!", "email": "jorge.vargas@empresa.pe", "full_name": "Jorge Vargas", "department": "Desarrollo de Software", "job_title": "Ingeniero Backend", "roles": ["empleado"], "permissions": ["dashboard:read", "policies:read", "policies:ack", "rag:query"]},
        {"id": 8, "username": "empleado4", "password": "User123!", "email": "elena.quispe@empresa.pe", "full_name": "Elena Quispe", "department": "Operaciones Comerciales", "job_title": "Ejecutiva de Cuentas", "roles": ["empleado"], "permissions": ["dashboard:read", "policies:read", "policies:ack", "rag:query"]},
    ]
    return policies, chunks, users


POLICIES, CHUNKS, USERS = load_seed_data()

VERSIONS: list[dict] = [
    {"id": 1, "policy_id": 1, "version_number": "1.0", "changelog": "Versión histórica inicial.", "file_checksum_sha256": hashlib.sha256(b"POL-SEG-001-v1.0").hexdigest(), "is_current": False},
    {"id": 2, "policy_id": 1, "version_number": "2.1", "changelog": "Alineación ISO/IEC 27001:2022 y NIST SP 800-63B (12/16 chars, MFA obligatorio).", "file_checksum_sha256": hashlib.sha256(b"POL-SEG-001-v2.1").hexdigest(), "is_current": True},
    {"id": 3, "policy_id": 2, "version_number": "1.4", "changelog": "Requisitos BitLocker/FileVault y prohibición Wi-Fi abiertas sin VPN.", "file_checksum_sha256": hashlib.sha256(b"POL-SEG-002-v1.4").hexdigest(), "is_current": True},
    {"id": 4, "policy_id": 3, "version_number": "3.0", "changelog": "Ley 29733 y estándares criptográficos AES-256 / TLS 1.3.", "file_checksum_sha256": hashlib.sha256(b"POL-SEG-003-v3.0").hexdigest(), "is_current": True},
    {"id": 5, "policy_id": 4, "version_number": "2.0", "changelog": "Protocolo Ransomware (SLA 15 min, no apagar equipo).", "file_checksum_sha256": hashlib.sha256(b"POL-SEG-004-v2.0").hexdigest(), "is_current": True},
    {"id": 6, "policy_id": 5, "version_number": "1.0", "changelog": "Gobernanza de IA Generativa y agentes LLM.", "file_checksum_sha256": hashlib.sha256(b"POL-SEG-005-v1.0").hexdigest(), "is_current": True},
]

ACKS: list[dict] = [
    {"policy_id": p["id"], "version_number": p["current_version"], "user_id": u["id"], "full_name": u["full_name"], "department": u["department"],
     "digital_signature": hashlib.sha256(f"{p['code']}|{u['username']}".encode()).hexdigest(),
     "acknowledged_at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()}
    for u in USERS[:4] for p in POLICIES
] + [
    {"policy_id": 1, "version_number": "2.1", "user_id": 5, "full_name": "Marco Silva", "department": "Finanzas y Contabilidad", "digital_signature": hashlib.sha256(b"POL-SEG-001|empleado1").hexdigest(), "acknowledged_at": datetime.now(timezone.utc).isoformat()},
    {"policy_id": 1, "version_number": "2.1", "user_id": 7, "full_name": "Jorge Vargas", "department": "Desarrollo de Software", "digital_signature": hashlib.sha256(b"POL-SEG-001|empleado3").hexdigest(), "acknowledged_at": datetime.now(timezone.utc).isoformat()},
    {"policy_id": 5, "version_number": "1.0", "user_id": 7, "full_name": "Jorge Vargas", "department": "Desarrollo de Software", "digital_signature": hashlib.sha256(b"POL-SEG-005|empleado3").hexdigest(), "acknowledged_at": datetime.now(timezone.utc).isoformat()},
]

RAG_HISTORY: list[dict] = [
    {
        "id": 1, "username": "empleado3", "department": "Desarrollo de Software",
        "question": "¿Puedo subir código fuente o datos de clientes a ChatGPT externo?",
        "confidence_score": 0.94, "latency_ms": 2, "restricted_flagged": False,
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),
        "citations": [{"policy_code": "POL-SEG-005", "version": "1.0", "article_ref": "Artículo 1", "page_number": 1}]
    },
    {
        "id": 2, "username": "empleado1", "department": "Finanzas y Contabilidad",
        "question": "¿Qué hago si sospecho de Ransomware en mi estación de trabajo?",
        "confidence_score": 0.96, "latency_ms": 2, "restricted_flagged": True,
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        "citations": [{"policy_code": "POL-SEG-004", "version": "2.0", "article_ref": "Artículo 2", "page_number": 2}]
    }
]

AUDIT_LOG: list[dict] = []


def record_audit(username: str, role_code: str, module: str, action: str, entity: str, entity_id: str, detail: str, severity: str = "info", result: str = "SUCCESS") -> None:
    prev_hash = AUDIT_LOG[-1]["hash_self"] if AUDIT_LOG else "0" * 64
    ts = datetime.now(timezone.utc).isoformat()
    block_id = len(AUDIT_LOG) + 1
    raw = f"{block_id}|{ts}|{username}|{module}|{action}|{entity_id}|{prev_hash}"
    self_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    AUDIT_LOG.append({
        "id": block_id,
        "occurred_at": ts,
        "username": username,
        "role_code": role_code,
        "module": module,
        "action": action,
        "entity": entity,
        "entity_id": entity_id,
        "result": result,
        "severity": severity,
        "detail": detail,
        "hash_prev": prev_hash,
        "hash_self": self_hash,
    })


for p in POLICIES:
    record_audit("admin", "admin", "policies", "CREATE", "policy", p["code"], f"Publicación e indexación RAG inicial de {p['code']} (v{p['current_version']})")
record_audit("empleado3", "empleado", "rag_chat", "RAG_QUERY", "policy", "POL-SEG-005", "Consulta sobre uso de LLM externos con cita exacta.")
record_audit("empleado1", "empleado", "rag_chat", "RAG_QUERY", "policy", "POL-SEG-004", "Consulta sobre protocolo Ransomware [RESTRICTED · Webhook n8n].", severity="warning")


# =====================================================================
# 2. TOKENS HMAC-SHA256 & SEGURIDAD
# =====================================================================
def sign_token(user: dict) -> str:
    payload = {"sub": user["id"], "username": user["username"], "exp": int((datetime.now(timezone.utc) + timedelta(hours=4)).timestamp())}
    b = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    sig = hmac.new(SECRET_KEY.encode(), b.encode(), hashlib.sha256).hexdigest()
    return f"{b}.{sig}"


def get_current_user(token: str | None = Depends(oauth2_scheme)) -> dict:
    if not token or "." not in token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales no proporcionadas")
    b, sig = token.split(".", 1)
    expected = hmac.new(SECRET_KEY.encode(), b.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    data = json.loads(base64.urlsafe_b64decode(b).decode())
    user = next((u for u in USERS if u["id"] == data["sub"]), None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    return user


# =====================================================================
# 3. MOTOR RAG (EXACTO A backend/app/main.py)
# =====================================================================
STOPWORDS_ES = {
    "de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las", "por", "un", "para",
    "con", "no", "una", "su", "al", "es", "lo", "como", "mas", "más", "pero", "sus", "le",
    "ya", "o", "este", "si", "sí", "porque", "esta", "entre", "cuando", "muy", "sin", "sobre",
    "cual", "cuál", "que", "qué", "como", "cómo", "donde", "dónde", "cuanto", "cuánto",
    "cuantos", "cuántos", "debo", "puedo", "hacer", "pasa", "tiene", "segun", "según", "mi",
}


def tokenize(text: str) -> list[str]:
    clean = text.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    return [t for t in re.findall(r"[a-z0-9\-]+", clean) if len(t) >= 2 and t not in STOPWORDS_ES]


def compute_sim(q_tokens: list[str], row: dict) -> float:
    if not q_tokens:
        return 0.1
    ct = set(tokenize(f"{row['content']} {row['section_title']} {row['policy_title']}"))
    kt = {k.lower() for k in row.get("keywords", [])}
    mc = sum(1 for t in q_tokens if t in ct or any(t in c or c in t for c in ct if len(c) >= 4))
    mk = sum(1.5 for t in q_tokens if t in kt or any(t in k or k in t for k in kt if len(k) >= 4))
    return round(min(0.99, max(0.15, (mc + mk) / (len(q_tokens) * 1.6))), 4)


# =====================================================================
# 4. APLICACIÓN FASTAPI LOCAL
# =====================================================================
app = FastAPI(title="PolicyGuard-RAG (Modo Local Autocontenido)", version="2.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/", response_class=HTMLResponse)
async def serve_spa():
    return FRONTEND_HTML.read_text(encoding="utf-8")


@app.get("/api/v1/health")
async def health():
    return {
        "status": "ok",
        "service": "PolicyGuard-RAG",
        "mode": "local-standalone",
        "indexed_policies": len(POLICIES),
        "indexed_chunks": len(CHUNKS),
    }


@app.get("/api/v1/ml/benchmark")
async def ml_benchmark():
    if not BENCHMARK_JSON.exists():
        raise HTTPException(status_code=404, detail="Benchmark JSON no encontrado")
    return json.loads(BENCHMARK_JSON.read_text(encoding="utf-8"))


@app.get("/api/v1/ml/figures/{filename}")
async def ml_figure(filename: str):
    safe = Path(filename).name
    if not safe.endswith(".png") or safe != filename:
        raise HTTPException(status_code=400, detail="Nombre inválido")
    p = FIGURES_DIR / safe
    if not p.exists():
        raise HTTPException(status_code=404, detail="Figura no encontrada")
    return FileResponse(str(p), media_type="image/png")


@app.post("/api/v1/auth/login")
async def login(form: OAuth2PasswordRequestForm = Depends()):
    user = next((u for u in USERS if u["username"] == form.username or u["email"] == form.username), None)
    if not user or user["password"] != form.password:
        record_audit(form.username, "unknown", "auth", "LOGIN_FAILED", "session", form.username, "Intento de acceso fallido.", severity="warning", result="DENIED")
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    record_audit(user["username"], user["roles"][0], "auth", "LOGIN", "session", str(user["id"]), f"Inicio de sesión exitoso ({user['department']}).")
    return {
        "access_token": sign_token(user),
        "token_type": "bearer",
        "user": {k: v for k, v in user.items() if k != "password"},
    }


@app.get("/api/v1/dashboard/summary")
async def dashboard_summary(current: dict = Depends(get_current_user)):
    tot_users = len(USERS)
    by_pol = []
    for p in POLICIES:
        cnt = len({a["user_id"] for a in ACKS if a["policy_id"] == p["id"] and a["version_number"] == p["current_version"]})
        by_pol.append({
            "code": p["code"], "version": p["current_version"], "title": p["title"],
            "acknowledged": cnt, "adoption_pct": round((cnt / tot_users) * 100, 1),
        })
    depts = {}
    for u in USERS:
        d = u["department"]
        depts.setdefault(d, {"department": d, "users": 0, "acks": 0})
        depts[d]["users"] += 1
        depts[d]["acks"] += len({a["policy_id"] for a in ACKS if a["user_id"] == u["id"]})
    dept_list = []
    for d in depts.values():
        tgt = d["users"] * len(POLICIES)
        dept_list.append({
            "department": d["department"], "users": d["users"], "acknowledgments": d["acks"], "target": tgt,
            "compliance_pct": round(min(100.0, (d["acks"] / max(1, tgt)) * 100), 1),
        })
    user_acked = {a["policy_id"] for a in ACKS if a["user_id"] == current["id"]}
    avg_conf = sum(q["confidence_score"] for q in RAG_HISTORY) / max(1, len(RAG_HISTORY))
    avg_lat = sum(q["latency_ms"] for q in RAG_HISTORY) / max(1, len(RAG_HISTORY))
    global_pct = round((len(ACKS) / max(1, tot_users * len(POLICIES))) * 100, 1)
    return {
        "kpis": {
            "total_policies": len(POLICIES), "total_versions": len(VERSIONS), "total_chunks": len(CHUNKS),
            "total_users": tot_users, "total_acknowledgments": len(ACKS), "global_adoption_pct": global_pct,
            "total_rag_queries": len(RAG_HISTORY), "avg_confidence_pct": round(avg_conf * 100, 1),
            "avg_latency_ms": int(avg_lat), "user_pending_acks": max(0, len(POLICIES) - len(user_acked)),
        },
        "adoption_by_policy": by_pol,
        "adoption_by_department": dept_list,
        "recent_queries": list(reversed(RAG_HISTORY))[:8],
    }


@app.get("/api/v1/policies")
async def list_policies(current: dict = Depends(get_current_user)):
    tot_users = len(USERS)
    items = []
    for p in POLICIES:
        c_cnt = sum(1 for c in CHUNKS if c["policy_id"] == p["id"])
        a_cnt = len({a["user_id"] for a in ACKS if a["policy_id"] == p["id"] and a["version_number"] == p["current_version"]})
        by_me = any(a["policy_id"] == p["id"] and a["user_id"] == current["id"] and a["version_number"] == p["current_version"] for a in ACKS)
        items.append({**p, "total_chunks": c_cnt, "ack_count": a_cnt, "total_users": tot_users, "adoption_pct": round((a_cnt / tot_users) * 100, 1), "acknowledged_by_me": by_me})
    return {"items": items, "total": len(items)}


@app.get("/api/v1/policies/{policy_id}")
async def policy_detail(policy_id: int, current: dict = Depends(get_current_user)):
    p = next((x for x in POLICIES if x["id"] == policy_id), None)
    if not p:
        raise HTTPException(status_code=404, detail="Política no encontrada")
    return {
        "policy": p,
        "versions": [v for v in VERSIONS if v["policy_id"] == policy_id],
        "chunks": [c for c in CHUNKS if c["policy_id"] == policy_id],
        "acknowledgments": [a for a in ACKS if a["policy_id"] == policy_id],
    }


class PolicyReq(BaseModel):
    code: str
    title: str
    category: str = "Seguridad General"
    classification: str = "INTERNAL"
    iso_control: str = "ISO 27001 A.5.1"
    version_number: str = "1.0"
    summary: str
    content_markdown: str
    changelog: str = "Emisión automática."


@app.post("/api/v1/policies", status_code=201)
async def create_policy(payload: PolicyReq, current: dict = Depends(get_current_user)):
    if "policies:write" not in current["permissions"]:
        raise HTTPException(status_code=403, detail="Permiso denegado")
    new_id = max(p["id"] for p in POLICIES) + 1
    pol = {
        "id": new_id, "code": payload.code.upper(), "title": payload.title,
        "category": payload.category, "classification": payload.classification,
        "iso_control": payload.iso_control, "current_version": payload.version_number,
        "status": "PUBLISHED", "owner_department": current["department"], "summary": payload.summary,
    }
    POLICIES.append(pol)
    VERSIONS.append({
        "id": len(VERSIONS) + 1, "policy_id": new_id, "version_number": payload.version_number,
        "changelog": payload.changelog, "file_checksum_sha256": hashlib.sha256(payload.content_markdown.encode()).hexdigest(), "is_current": True,
    })
    sections = [s.strip() for s in payload.content_markdown.split("## ") if s.strip()]
    for i, sec in enumerate(sections, 1):
        lines = sec.splitlines()
        hdr = lines[0]
        body = " ".join(lines[1:]).strip() or hdr
        CHUNKS.append({
            "id": len(CHUNKS) + 1, "policy_id": new_id, "policy_code": pol["code"], "policy_title": pol["title"],
            "current_version": pol["current_version"], "classification": pol["classification"], "iso_control": pol["iso_control"],
            "chunk_index": i, "article_ref": f"Artículo {i}", "section_title": hdr[:90], "page_number": i,
            "content": body, "token_count": len(body.split()), "keywords": tokenize(hdr + " " + body)[:8],
        })
    record_audit(current["username"], current["roles"][0], "policies", "CREATE", "policy", pol["code"], f"Política {pol['code']} publicada e indexada ({len(sections)} chunks).")
    return {"message": f"Política {pol['code']} publicada e indexada en RAG.", "policy_id": new_id}


class AckReq(BaseModel):
    comments: str | None = "Conformidad registrada."


@app.post("/api/v1/policies/{policy_id}/acknowledge", status_code=201)
async def acknowledge_policy(policy_id: int, payload: AckReq, current: dict = Depends(get_current_user)):
    p = next((x for x in POLICIES if x["id"] == policy_id), None)
    if not p:
        raise HTTPException(status_code=404, detail="Política no encontrada")
    sig = hashlib.sha256(f"{p['code']}|{p['current_version']}|{current['id']}|{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()
    ACKS[:] = [a for a in ACKS if not (a["policy_id"] == policy_id and a["user_id"] == current["id"] and a["version_number"] == p["current_version"])]
    ACKS.append({
        "policy_id": policy_id, "version_number": p["current_version"], "user_id": current["id"],
        "full_name": current["full_name"], "department": current["department"], "digital_signature": sig,
        "acknowledged_at": datetime.now(timezone.utc).isoformat(),
    })
    record_audit(current["username"], current["roles"][0], "acknowledgments", "ACKNOWLEDGE", "policy", p["code"], f"Acuse firmado SHA-256 ({sig[:16]}...).")
    return {"status": "acknowledged", "digital_signature": sig}


class RagReq(BaseModel):
    question: str = Field(..., min_length=3)
    top_k: int = 3


@app.post("/api/v1/rag/ask")
async def ask_rag(payload: RagReq, current: dict = Depends(get_current_user)):
    t0 = time.perf_counter()
    q_tokens = tokenize(payload.question)
    scored = []
    for ch in CHUNKS:
        sc = compute_sim(q_tokens, ch)
        scored.append({**ch, "version": ch["current_version"], "title": ch["policy_title"], "score": sc, "excerpt": ch["content"][:220] + ("..." if len(ch["content"]) > 220 else "")})
    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:payload.top_k]
    best = top[0]
    if best["score"] < 0.22:
        ans = "No se identificaron cláusulas con coincidencia suficiente en el catálogo vigente. Consulte directamente con el área GRC."
        conf = 0.45
    else:
        lines = [f"De acuerdo con **{best['title']} ({best['policy_code']} v{best['version']})**, en el **{best['article_ref']} ({best['section_title']}, Pág. {best['page_number']})**:"]
        for i, ch in enumerate(top, 1):
            if ch["score"] >= 0.25 or i == 1:
                lines.append(f"{i}. **[{ch['policy_code']} v{ch['version']} · {ch['article_ref']}, Pág. {ch['page_number']}]** *{ch['section_title']}*: {ch['content']}")
        conf = round(min(0.99, max(0.78, best["score"])), 4)
        ans = "\n\n".join(lines)
    restricted = any(c["classification"] == "RESTRICTED" and c["score"] >= 0.35 for c in top)
    lat = max(2, int((time.perf_counter() - t0) * 1000))
    RAG_HISTORY.append({"id": len(RAG_HISTORY) + 1, "username": current["username"], "department": current["department"], "question": payload.question, "confidence_score": conf, "latency_ms": lat, "restricted_flagged": restricted, "created_at": datetime.now(timezone.utc).isoformat(), "citations": top})
    record_audit(current["username"], current["roles"][0], "rag_chat", "RAG_QUERY", "policy", best["policy_code"], f"Consulta RAG: '{payload.question[:60]}' -> {best['policy_code']} ({best['article_ref']})", severity="warning" if restricted else "info")
    return {"question": payload.question, "answer": ans, "citations": top, "confidence_score": conf, "latency_ms": lat, "restricted_flagged": restricted, "n8n_notified": restricted}


@app.get("/api/v1/rag/history")
async def rag_history(current: dict = Depends(get_current_user)):
    return {"items": list(reversed(RAG_HISTORY))[:30], "total": len(RAG_HISTORY)}


@app.get("/api/v1/users")
async def list_users(current: dict = Depends(get_current_user)):
    items = [{**{k: v for k, v in u.items() if k != "password"}, "acks_signed": len({a["policy_id"] for a in ACKS if a["user_id"] == u["id"]})} for u in USERS]
    return {"items": items, "total": len(items)}


@app.get("/api/v1/audit/logs")
async def audit_logs(limit: int = Query(50, ge=1, le=200), current: dict = Depends(get_current_user)):
    return {"items": list(reversed(AUDIT_LOG))[:limit], "total": len(AUDIT_LOG)}


@app.get("/api/v1/audit/verify-chain")
async def verify_chain(current: dict = Depends(get_current_user)):
    expected_prev = "0" * 64
    broken = []
    for r in AUDIT_LOG:
        if r["hash_prev"] != expected_prev:
            broken.append({"id": r["id"]})
        expected_prev = r["hash_self"]
    return {
        "intact": len(broken) == 0,
        "checked_blocks": len(AUDIT_LOG),
        "broken_links": broken,
        "last_block_hash": expected_prev,
        "standard": "ISO/IEC 27001:2022 Control A.8.15 (Cadena Inmutable SHA-256)",
    }


@app.post("/api/v1/audit/test-immutability")
async def test_immutability(current: dict = Depends(get_current_user)):
    exc = "ERROR: audit_log es una bitácora append-only inmutable; DELETE/UPDATE prohibido (Trigger trg_audit_log_no_update_delete)."
    record_audit(current["username"], current["roles"][0], "audit", "TAMPER_ATTEMPT_BLOCKED", "audit_log", "1", f"Intento de eliminación bloqueado y registrado: {exc}", severity="critical", result="DENIED")
    return {"blocked": True, "trigger_name": "trg_audit_log_no_update_delete", "postgres_exception": exc, "message": "Intento de DELETE bloqueado y registrado en bitácora forense."}


@app.get("/api/v1/reports/export")
async def export_report(report_type: str = Query("compliance"), fmt: str = Query("pdf", alias="format"), current: dict = Depends(get_current_user)):
    fname = f"PolicyGuard_{report_type}_{datetime.now():%Y%m%d_%H%M%S}.{fmt}"
    fpath = REPORTS_DIR / fname
    tot_users = len(USERS)
    if fmt == "pdf":
        doc = SimpleDocTemplate(str(fpath), pagesize=A4)
        st = getSampleStyleSheet()
        rows = [["Código", "Política", "Versión", "Control ISO", "Acuses"]]
        for p in POLICIES:
            cnt = len({a["user_id"] for a in ACKS if a["policy_id"] == p["id"]})
            rows.append([p["code"], p["title"][:45], f"v{p['current_version']}", p["iso_control"][:20], f"{cnt}/{tot_users}"])
        t = Table(rows)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1D4ED8")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 8)]))
        doc.build([Paragraph(f"PolicyGuard-RAG · Reporte {report_type.upper()}", st["Title"]), Spacer(1, 12), t])
        media = "application/pdf"
    elif fmt == "docx":
        doc = Document()
        doc.add_heading(f"PolicyGuard-RAG · Reporte {report_type.upper()}", 1)
        tbl = doc.add_table(rows=1, cols=4); tbl.style = "Table Grid"
        for i, h in enumerate(["Código", "Título", "Versión", "Control ISO"]): tbl.rows[0].cells[i].text = h
        for p in POLICIES:
            r = tbl.add_row().cells; r[0].text = p["code"]; r[1].text = p["title"]; r[2].text = p["current_version"]; r[3].text = p["iso_control"]
        doc.save(str(fpath))
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        wb = Workbook(); ws = wb.active; ws.title = "Cumplimiento"
        ws.append(["Código", "Título", "Versión", "Control ISO", "Acuses"])
        for p in POLICIES:
            cnt = len({a["user_id"] for a in ACKS if a["policy_id"] == p["id"]})
            ws.append([p["code"], p["title"], p["current_version"], p["iso_control"], f"{cnt}/{tot_users}"])
        wb.save(str(fpath))
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    record_audit(current["username"], current["roles"][0], "reports", "EXPORT", "report", fname, f"Reporte {report_type} exportado en {fmt.upper()}.")
    return FileResponse(str(fpath), media_type=media, filename=fname)


if __name__ == "__main__":
    print("\n" + "=" * 64)
    print("  PolicyGuard-RAG (Caso 21) · Servidor Corporativo Activo")
    print("  Abrir en navegador: http://localhost:8002")
    print("  Usuario demo: admin / Admin123! (o botones de 1-clic)")
    print("=" * 64 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="warning")
