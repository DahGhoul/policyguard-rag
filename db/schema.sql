-- =====================================================================
-- PolicyGuard-RAG (Caso 21: Gestor de Políticas con Chat RAG)
-- Esquema Relacional + Vectorial / Híbrido · PostgreSQL 15/16
-- Cumplimiento: ISO/IEC 27001 A.5.1, A.5.15, A.8.15 · NIST CSF GV.PO
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS policyrag;
SET search_path TO policyrag, public;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------
-- 1. RBAC: Roles, Permisos y Usuarios
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS policyrag.roles (
    id              BIGSERIAL PRIMARY KEY,
    code            VARCHAR(48) UNIQUE NOT NULL,
    name            VARCHAR(96) NOT NULL,
    description     TEXT,
    is_system       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS policyrag.permissions (
    id              BIGSERIAL PRIMARY KEY,
    code            VARCHAR(64) UNIQUE NOT NULL,
    module          VARCHAR(48) NOT NULL,
    action          VARCHAR(48) NOT NULL,
    description     TEXT
);

CREATE TABLE IF NOT EXISTS policyrag.role_permissions (
    role_id         BIGINT NOT NULL REFERENCES policyrag.roles(id) ON DELETE CASCADE,
    permission_id   BIGINT NOT NULL REFERENCES policyrag.permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS policyrag.users (
    id              BIGSERIAL PRIMARY KEY,
    username        VARCHAR(64) UNIQUE NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    full_name       VARCHAR(160) NOT NULL,
    hashed_password TEXT NOT NULL,
    department      VARCHAR(120) NOT NULL DEFAULT 'Tecnología y Seguridad',
    job_title       VARCHAR(120) DEFAULT 'Especialista',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    failed_attempts SMALLINT NOT NULL DEFAULT 0,
    locked_until    TIMESTAMPTZ,
    last_login_at   TIMESTAMPTZ,
    last_login_ip   VARCHAR(64),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS policyrag.user_roles (
    user_id         BIGINT NOT NULL REFERENCES policyrag.users(id) ON DELETE CASCADE,
    role_id         BIGINT NOT NULL REFERENCES policyrag.roles(id) ON DELETE CASCADE,
    granted_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS policyrag.refresh_tokens (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES policyrag.users(id) ON DELETE CASCADE,
    jti             UUID UNIQUE NOT NULL,
    token_hash      TEXT NOT NULL,
    issued_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ,
    ip_address      VARCHAR(64),
    user_agent      TEXT
);

-- ---------------------------------------------------------------------
-- 2. Gestión de Políticas y Versionado (ISO 27001 A.5.1)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS policyrag.policies (
    id                  BIGSERIAL PRIMARY KEY,
    code                VARCHAR(32) UNIQUE NOT NULL,          -- Ej: POL-SEG-001
    title               VARCHAR(255) NOT NULL,
    category            VARCHAR(96) NOT NULL,                 -- Acceso, Criptografía, Teletrabajo, Incidentes, IA, Datos
    classification      VARCHAR(32) NOT NULL DEFAULT 'INTERNAL', -- PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED
    iso_control         VARCHAR(64) NOT NULL,                 -- Ej: ISO 27001 A.5.15 / A.8.5
    nist_function       VARCHAR(64) DEFAULT 'GV.PO / PR.AC',
    current_version     VARCHAR(24) NOT NULL DEFAULT '1.0',
    status              VARCHAR(32) NOT NULL DEFAULT 'PUBLISHED', -- DRAFT, IN_REVIEW, PUBLISHED, ARCHIVED
    summary             TEXT NOT NULL,
    owner_department    VARCHAR(120) NOT NULL DEFAULT 'Seguridad de la Información (CISO)',
    mandatory_ack       BOOLEAN NOT NULL DEFAULT TRUE,
    effective_date      DATE NOT NULL DEFAULT CURRENT_DATE,
    review_due_date     DATE NOT NULL DEFAULT (CURRENT_DATE + INTERVAL '365 days'),
    created_by          BIGINT REFERENCES policyrag.users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS policyrag.policy_versions (
    id                  BIGSERIAL PRIMARY KEY,
    policy_id           BIGINT NOT NULL REFERENCES policyrag.policies(id) ON DELETE CASCADE,
    version_number      VARCHAR(24) NOT NULL,
    changelog           TEXT NOT NULL,
    content_markdown    TEXT NOT NULL,
    file_name           VARCHAR(255),
    file_checksum_sha256 VARCHAR(64),
    total_chunks        INT NOT NULL DEFAULT 0,
    published_by        BIGINT REFERENCES policyrag.users(id) ON DELETE SET NULL,
    published_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_current          BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (policy_id, version_number)
);

-- ---------------------------------------------------------------------
-- 3. Fragmentos Indexados (Chunks RAG con Vector de Embeddings + Full-Text)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS policyrag.policy_chunks (
    id                  BIGSERIAL PRIMARY KEY,
    policy_id           BIGINT NOT NULL REFERENCES policyrag.policies(id) ON DELETE CASCADE,
    version_id          BIGINT NOT NULL REFERENCES policyrag.policy_versions(id) ON DELETE CASCADE,
    chunk_index         INT NOT NULL,
    article_ref         VARCHAR(120) NOT NULL,                -- Ej: Artículo 4.2 - Uso de Contraseñas y MFA
    section_title       VARCHAR(200) NOT NULL,
    page_number         INT NOT NULL DEFAULT 1,
    content             TEXT NOT NULL,
    token_count         INT NOT NULL DEFAULT 120,
    keywords            TEXT[] DEFAULT '{}',
    embedding_json      JSONB NOT NULL DEFAULT '[]'::jsonb,   -- Vector denso 384-d / TF-IDF normalizado para similitud coseno
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_policy_chunks_policy ON policyrag.policy_chunks(policy_id);

-- ---------------------------------------------------------------------
-- 4. Acuses de Recibo y Compromiso de Lectura (ISO 27001 A.5.1 / A.6.3)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS policyrag.acknowledgments (
    id                  BIGSERIAL PRIMARY KEY,
    policy_id           BIGINT NOT NULL REFERENCES policyrag.policies(id) ON DELETE CASCADE,
    version_number      VARCHAR(24) NOT NULL,
    user_id             BIGINT NOT NULL REFERENCES policyrag.users(id) ON DELETE CASCADE,
    department          VARCHAR(120) NOT NULL,
    acknowledged_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_address          VARCHAR(64),
    digital_signature   VARCHAR(64) NOT NULL,                 -- Hash SHA-256 de firma de conformidad
    comments            TEXT,
    UNIQUE (policy_id, version_number, user_id)
);

-- ---------------------------------------------------------------------
-- 5. Historial de Consultas al Chatbot RAG y Explicabilidad (XAI)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS policyrag.rag_sessions (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL REFERENCES policyrag.users(id) ON DELETE CASCADE,
    title               VARCHAR(200) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS policyrag.rag_queries (
    id                  BIGSERIAL PRIMARY KEY,
    session_id          BIGINT REFERENCES policyrag.rag_sessions(id) ON DELETE SET NULL,
    user_id             BIGINT REFERENCES policyrag.users(id) ON DELETE SET NULL,
    username            VARCHAR(64) NOT NULL,
    department          VARCHAR(120),
    question            TEXT NOT NULL,
    answer              TEXT NOT NULL,
    citations           JSONB NOT NULL DEFAULT '[]'::jsonb,   -- [{policy_code, title, article_ref, page_number, score, excerpt}]
    confidence_score    NUMERIC(5,4) NOT NULL DEFAULT 0.9200,
    model_used          VARCHAR(96) NOT NULL DEFAULT 'langchain-rag-hybrid-v1',
    latency_ms          INT NOT NULL DEFAULT 45,
    restricted_flagged  BOOLEAN NOT NULL DEFAULT FALSE,       -- True si consultó temas sensibles / restringidos
    n8n_notified        BOOLEAN NOT NULL DEFAULT FALSE,
    helpful_feedback    BOOLEAN,
    feedback_comment    TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- 6. Registro de Reportes Exportados (PDF, Word, Excel)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS policyrag.generated_reports (
    id                  BIGSERIAL PRIMARY KEY,
    report_type         VARCHAR(48) NOT NULL,                 -- operational, management, audit
    report_format       VARCHAR(16) NOT NULL,                 -- pdf, docx, xlsx
    title               VARCHAR(255) NOT NULL,
    file_path           TEXT NOT NULL,
    file_size           BIGINT NOT NULL DEFAULT 0,
    checksum_sha256     VARCHAR(64) NOT NULL,
    requested_by        BIGINT REFERENCES policyrag.users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- 7. Bitácora Forense Inmutable con Cadena de Bloques SHA-256
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS policyrag.audit_log (
    id                  BIGSERIAL PRIMARY KEY,
    occurred_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id             BIGINT,
    username            VARCHAR(64) NOT NULL DEFAULT 'anonymous',
    role_code           VARCHAR(64) DEFAULT 'guest',
    module              VARCHAR(48) NOT NULL,                 -- auth, policies, rag_chat, acknowledgments, reports, users, audit
    action              VARCHAR(48) NOT NULL,                 -- LOGIN, LOGOUT, CREATE, READ, UPDATE, ACKNOWLEDGE, RAG_QUERY, EXPORT
    entity              VARCHAR(64),
    entity_id           VARCHAR(64),
    result              VARCHAR(24) NOT NULL DEFAULT 'SUCCESS', -- SUCCESS, DENIED, FAILURE
    severity            VARCHAR(24) NOT NULL DEFAULT 'info',    -- info, warning, critical
    detail              TEXT,
    ip_address          VARCHAR(64),
    user_agent          TEXT,
    http_method         VARCHAR(16),
    http_path           VARCHAR(255),
    http_status         INT,
    before_data         JSONB,
    after_data          JSONB,
    hash_prev           VARCHAR(64) NOT NULL,
    hash_self           VARCHAR(64) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_log_occurred ON policyrag.audit_log(occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_module ON policyrag.audit_log(module);

-- Función que calcula automáticamente el hash SHA-256 encadenado al insertar en audit_log
CREATE OR REPLACE FUNCTION policyrag.fn_audit_log_hash_chain()
RETURNS TRIGGER AS $$
DECLARE
    v_prev_hash VARCHAR(64);
    v_payload   TEXT;
BEGIN
    SELECT hash_self INTO v_prev_hash
    FROM policyrag.audit_log
    ORDER BY id DESC
    LIMIT 1;

    IF v_prev_hash IS NULL THEN
        v_prev_hash := repeat('0', 64);
    END IF;

    NEW.hash_prev := v_prev_hash;
    IF NEW.occurred_at IS NULL THEN
        NEW.occurred_at := NOW();
    END IF;

    v_payload := COALESCE(NEW.hash_prev, '') || '|' ||
                 COALESCE(to_char(NEW.occurred_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'), '') || '|' ||
                 COALESCE(NEW.username, '') || '|' ||
                 COALESCE(NEW.module, '') || '|' ||
                 COALESCE(NEW.action, '') || '|' ||
                 COALESCE(NEW.entity, '') || '|' ||
                 COALESCE(NEW.entity_id, '') || '|' ||
                 COALESCE(NEW.result, '') || '|' ||
                 COALESCE(NEW.detail, '');

    NEW.hash_self := encode(digest(v_payload, 'sha256'), 'hex');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_log_hash ON policyrag.audit_log;
CREATE TRIGGER trg_audit_log_hash
BEFORE INSERT ON policyrag.audit_log
FOR EACH ROW EXECUTE FUNCTION policyrag.fn_audit_log_hash_chain();

-- Trigger de Inmutabilidad Estricta: PROHÍBE UPDATE y DELETE en audit_log (ISO 27001 A.8.15)
CREATE OR REPLACE FUNCTION policyrag.fn_audit_log_immutable()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'VIOLACIÓN DE SEGURIDAD FORENSE: La tabla policyrag.audit_log es inmutable (ISO 27001 A.8.15). No se permite % sobre registros de auditoría.', TG_OP;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_log_no_update_delete ON policyrag.audit_log;
CREATE TRIGGER trg_audit_log_no_update_delete
BEFORE UPDATE OR DELETE ON policyrag.audit_log
FOR EACH ROW EXECUTE FUNCTION policyrag.fn_audit_log_immutable();
