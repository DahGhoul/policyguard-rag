-- =====================================================================
-- PolicyGuard-RAG (Caso 21: Gestor de Políticas con Chat RAG)
-- Datos Semilla (Seed) — Idempotente
-- Credenciales demo:
--   admin / Admin123!          gestor / Manager123!
--   analista1 / Analyst123!    auditor1 / Audit123!
--   empleado1 / User123!       empleado2 / User123!
-- =====================================================================
BEGIN;
SET search_path TO policyrag, public;

-- 1. Permisos
INSERT INTO permissions (code, module, action, description) VALUES
 ('dashboard:read', 'dashboard', 'read', 'Ver dashboard de adopción y métricas RAG'),
 ('policies:read', 'policies', 'read', 'Consultar catálogo y versiones de políticas'),
 ('policies:write', 'policies', 'write', 'Crear, versionar y publicar políticas (re-indexa RAG)'),
 ('policies:ack', 'policies', 'ack', 'Firmar acuse de recibo digital de políticas'),
 ('rag:query', 'rag', 'query', 'Consultar el Chatbot RAG con citas de artículos y páginas'),
 ('rag:manage', 'rag', 'manage', 'Re-indexar fragmentos y ver historial global de preguntas'),
 ('reports:read', 'reports', 'read', 'Ver reportes generados'),
 ('reports:export', 'reports', 'export', 'Exportar reportes en PDF, Word y Excel'),
 ('users:read', 'users', 'read', 'Consultar usuarios y departamentos'),
 ('users:write', 'users', 'write', 'Crear y editar usuarios y asignaciones de rol'),
 ('audit:read', 'audit', 'read', 'Consultar bitácora inmutable y verificar cadena SHA-256'),
 ('audit:export', 'audit', 'export', 'Exportar evidencias forenses de auditoría')
ON CONFLICT (code) DO NOTHING;

-- 2. Roles (4 obligatorios de la Plataforma Común + Empleado)
INSERT INTO roles (code, name, description, is_system) VALUES
 ('admin', 'Administrador', 'Control total del sistema, usuarios, políticas, RAG y auditoría', TRUE),
 ('analista', 'Analista GRC / Seguridad', 'Redacción de políticas, indexación RAG, seguimiento de acuses y consultas', TRUE),
 ('gestor', 'Gestor / CISO', 'Supervisión de dashboards de adopción y descarga de reportes ejecutivos', TRUE),
 ('auditor', 'Auditor ISO 27001', 'Acceso de solo lectura a bitácora inmutable, cadena SHA-256 y evidencias de acuse', TRUE),
 ('empleado', 'Colaborador', 'Lectura de políticas vigentes, firma de acuse de recibo y consulta al Chatbot RAG', TRUE)
ON CONFLICT (code) DO NOTHING;

-- Asignación de permisos a roles
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r CROSS JOIN permissions p WHERE r.code = 'admin'
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r JOIN permissions p ON p.code IN (
 'dashboard:read','policies:read','policies:write','policies:ack','rag:query','rag:manage','reports:read','reports:export'
) WHERE r.code = 'analista' ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r JOIN permissions p ON p.code IN (
 'dashboard:read','policies:read','policies:ack','rag:query','reports:read','reports:export','users:read'
) WHERE r.code = 'gestor' ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r JOIN permissions p ON p.code IN (
 'dashboard:read','policies:read','rag:query','reports:read','reports:export','audit:read','audit:export','users:read'
) WHERE r.code = 'auditor' ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r JOIN permissions p ON p.code IN (
 'dashboard:read','policies:read','policies:ack','rag:query'
) WHERE r.code = 'empleado' ON CONFLICT DO NOTHING;

-- 3. Usuarios Demo (bcrypt factor 12 vía pgcrypto)
INSERT INTO users (username, email, full_name, hashed_password, department, job_title, is_active) VALUES
 ('admin', 'admin@empresa.pe', 'Diego Administrador (CISO Office)', crypt('Admin123!', gen_salt('bf', 12)), 'Seguridad de la Información', 'Arquitecto de Seguridad Senior', TRUE),
 ('analista1', 'analista.grc@empresa.pe', 'Valeria Mendoza (Analista GRC)', crypt('Analyst123!', gen_salt('bf', 12)), 'Gobierno, Riesgo y Cumplimiento', 'Especialista ISO 27001', TRUE),
 ('gestor', 'gerente.ti@empresa.pe', 'Carlos Rojas (Gerente de TI)', crypt('Manager123!', gen_salt('bf', 12)), 'Tecnología y Operaciones', 'Gerente de Tecnología', TRUE),
 ('auditor1', 'auditor.iso@empresa.pe', 'Lucía Fernández (Auditora Líder)', crypt('Audit123!', gen_salt('bf', 12)), 'Auditoría Interna', 'Auditora ISO/IEC 27001', TRUE),
 ('empleado1', 'marco.silva@empresa.pe', 'Marco Silva', crypt('User123!', gen_salt('bf', 12)), 'Finanzas y Contabilidad', 'Analista de Tesorería', TRUE),
 ('empleado2', 'sofia.castro@empresa.pe', 'Sofía Castro', crypt('User123!', gen_salt('bf', 12)), 'Recursos Humanos', 'Coordinadora de Talento', TRUE),
 ('empleado3', 'jorge.vargas@empresa.pe', 'Jorge Vargas', crypt('User123!', gen_salt('bf', 12)), 'Desarrollo de Software', 'Ingeniero Backend', TRUE),
 ('empleado4', 'elena.quispe@empresa.pe', 'Elena Quispe', crypt('User123!', gen_salt('bf', 12)), 'Operaciones Comerciales', 'Ejecutiva de Cuentas', TRUE)
ON CONFLICT (username) DO NOTHING;

-- Vincular usuarios a roles
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id FROM users u JOIN roles r ON
 (u.username = 'admin' AND r.code = 'admin') OR
 (u.username = 'analista1' AND r.code = 'analista') OR
 (u.username = 'gestor' AND r.code = 'gestor') OR
 (u.username = 'auditor1' AND r.code = 'auditor') OR
 (u.username IN ('empleado1','empleado2','empleado3','empleado4') AND r.code = 'empleado')
ON CONFLICT DO NOTHING;

-- 4. Políticas Corporativas ISO/IEC 27001:2022
INSERT INTO policies (code, title, category, classification, iso_control, nist_function, current_version, status, summary, owner_department, mandatory_ack, effective_date, review_due_date, created_by) VALUES
 ('POL-SEG-001', 'Política de Control de Accesos, Contraseñas y Autenticación Multifactor (MFA)', 'Control de Accesos', 'INTERNAL', 'ISO 27001 A.5.15 / A.5.17 / A.8.5', 'PR.AA (Identity & Access)', '2.1', 'PUBLISHED',
  'Establece los requisitos obligatorios para creación de contraseñas robustas, uso de MFA, bloqueo de sesiones y revisión trimestral de privilegios.',
  'Seguridad de la Información', TRUE, CURRENT_DATE - INTERVAL '60 days', CURRENT_DATE + INTERVAL '305 days', 1),

 ('POL-SEG-002', 'Política de Trabajo Remoto Seguro, Uso de VPN y Dispositivos Móviles (BYOD)', 'Teletrabajo y Red', 'INTERNAL', 'ISO 27001 A.6.7 / A.8.1', 'PR.AC / PR.PT', '1.4', 'PUBLISHED',
  'Regula las condiciones de seguridad para el teletrabajo, uso obligatorio de VPN WireGuard/IPsec con MFA, prohibición de redes Wi-Fi públicas sin túnel y cifrado de disco BitLocker/FileVault.',
  'Seguridad de la Información', TRUE, CURRENT_DATE - INTERVAL '45 days', CURRENT_DATE + INTERVAL '320 days', 1),

 ('POL-SEG-003', 'Política de Clasificación de la Información, Criptografía y Prevención de Fuga de Datos (DLP)', 'Protección de Datos', 'CONFIDENTIAL', 'ISO 27001 A.5.12 / A.5.13 / A.8.24', 'PR.DS (Data Security)', '3.0', 'PUBLISHED',
  'Define los 4 niveles de clasificación (Pública, Interna, Confidencial, Restringida), algoritmos criptográficos autorizados (AES-256, TLS 1.3, SHA-256) y reglas de compartición externa.',
  'Gobierno, Riesgo y Cumplimiento', TRUE, CURRENT_DATE - INTERVAL '30 days', CURRENT_DATE + INTERVAL '335 days', 2),

 ('POL-SEG-004', 'Política de Gestión y Respuesta a Incidentes de Ciberseguridad y Ransomware', 'Respuesta a Incidentes', 'RESTRICTED', 'ISO 27001 A.5.24 / A.5.26 / A.8.15', 'RS.MA / RS.MI (Respond)', '2.0', 'PUBLISHED',
  'Establece los tiempos máximos de reporte interno (15 minutos para incidentes críticos), prohibición estricta de pago de rescates de ransomware, preservación de evidencia forense y cadena de custodia.',
  'Seguridad de la Información', TRUE, CURRENT_DATE - INTERVAL '20 days', CURRENT_DATE + INTERVAL '345 days', 1),

 ('POL-SEG-005', 'Política de Uso Aceptable de Inteligencia Artificial Generativa y Agentes LLM', 'Gobernanza de IA', 'INTERNAL', 'ISO 27001 A.5.1 / ISO 42001 / OWASP LLM', 'GV.PO (Policy & AI Risk)', '1.0', 'PUBLISHED',
  'Norma el uso seguro de herramientas de IA Generativa (ChatGPT, Claude, Copilot, Ollama local), prohibiendo subir datos personales (PII), código fuente propietario o secretos industriales a nubes públicas no autorizadas.',
  'Gobierno, Riesgo y Cumplimiento', TRUE, CURRENT_DATE - INTERVAL '10 days', CURRENT_DATE + INTERVAL '355 days', 2)
ON CONFLICT (code) DO NOTHING;

-- 5. Versiones de Políticas
INSERT INTO policy_versions (policy_id, version_number, changelog, content_markdown, file_name, file_checksum_sha256, total_chunks, published_by, is_current) VALUES
 (1, '1.0', 'Emisión inicial de la política de contraseñas corporativas.',
  '# POL-SEG-001 v1.0 (Histórica)\nLongitud mínima de 8 caracteres y cambio cada 90 días.',
  'POL-SEG-001_v1.0.pdf', encode(digest('POL-SEG-001-v1.0', 'sha256'), 'hex'), 1, 1, FALSE),

 (1, '2.1', 'Actualización alineada a ISO/IEC 27001:2022 y NIST SP 800-63B: longitud mínima de 12 caracteres, MFA obligatorio en accesos privilegiados y bloqueo tras 5 intentos.',
  '# POL-SEG-001 v2.1 · Control de Accesos, Contraseñas y MFA\n\n## Artículo 1. Objetivo y Alcance (Página 1)\nGarantizar que únicamente usuarios autorizados accedan a los sistemas de información de la organización, aplicando el principio de mínimo privilegio y autenticación robusta.\n\n## Artículo 2. Estándar de Contraseñas Corporativas (Página 2)\nToda cuenta de usuario estándar debe tener una contraseña de al menos **12 caracteres**, combinando mayúsculas, minúsculas, números y símbolos especiales. Las cuentas de Administrador deben tener al menos **16 caracteres**. Queda prohibido reutilizar las últimas 10 contraseñas.\n\n## Artículo 3. Autenticación Multifactor (MFA) y Bloqueo (Página 3)\nEl uso de **MFA (TOTP o llave FIDO2)** es estrictamente obligatorio para correo corporativo, VPN, paneles cloud (AWS/Azure) y cuentas privilegiadas. Tras **5 intentos fallidos consecutivos**, la cuenta se bloqueará automáticamente por **15 minutos** y se registrará en la bitácora de auditoría.\n\n## Artículo 4. Revisión y Revocación de Accesos (Página 4)\nAnte el cese o desvinculación de un colaborador, Recursos Humanos debe notificar de inmediato para revocar todos los accesos en un plazo máximo de **2 horas**. Los privilegios administrativos se recertifican cada **90 días**.',
  'POL-SEG-001_v2.1.pdf', encode(digest('POL-SEG-001-v2.1', 'sha256'), 'hex'), 4, 1, TRUE),

 (2, '1.4', 'Incorporación de requisitos de cifrado BitLocker y prohibición de redes Wi-Fi abiertas.',
  '# POL-SEG-002 v1.4 · Trabajo Remoto Seguro, VPN y BYOD\n\n## Artículo 1. Condiciones de Teletrabajo (Página 1)\nTodo colaborador en modalidad remota o híbrida debe conectarse exclusivamente mediante equipos corporativos inventariados con EDR Wazuh activo y cifrado de disco completo (**BitLocker en Windows o FileVault en macOS**).\n\n## Artículo 2. Uso Obligatorio de VPN y Redes Wi-Fi (Página 2)\nPara acceder a servidores internos, bases de datos o repositorios de código desde fuera de la oficina, es obligatorio establecer túnel **VPN corporativo con MFA**. Está terminantemente prohibido conectarse a redes Wi-Fi públicas (aeropuertos, cafeterías, hoteles) sin activar previamente la VPN institucional.\n\n## Artículo 3. Bloqueo de Pantalla y Dispositivos Personales BYOD (Página 3)\nEl bloqueo automático de pantalla por inactividad no debe superar los **5 minutos**. Los dispositivos personales (BYOD) solo pueden acceder al correo web encapsulado y nunca almacenar bases de datos o archivos clasificados como Confidenciales o Restringidos.',
  'POL-SEG-002_v1.4.pdf', encode(digest('POL-SEG-002-v1.4', 'sha256'), 'hex'), 3, 1, TRUE),

 (3, '3.0', 'Alineación con Ley de Protección de Datos Personales N° 29733 y estándares criptográficos AES-256 / TLS 1.3.',
  '# POL-SEG-003 v3.0 · Clasificación de la Información y Criptografía\n\n## Artículo 1. Niveles de Clasificación (Página 1)\nToda información de la empresa se clasifica en cuatro niveles: **1) Pública** (material comercial aprobado), **2) Interna** (manuales y comunicados operativos), **3) Confidencial** (contratos, datos personales PII, estados financieros) y **4) Restringida** (secretos criptográficos, arquitectura de seguridad, investigaciones forenses).\n\n## Artículo 2. Estándares Criptográficos Autorizados (Página 2)\nLos datos clasificados como Confidenciales o Restringidos deben cifrarse en reposo utilizando **AES-256** y en tránsito mediante **TLS 1.2 o TLS 1.3**. Para integridad documental y bitácoras de auditoría se exige **SHA-256**. Queda prohibido el uso de MD5, SHA-1, DES o 3DES.\n\n## Artículo 3. Retención y Destrucción Segura (Página 3)\nLos registros de auditoría de seguridad y acuses de políticas deben conservarse de manera inmutable por un mínimo de **5 años**. Los medios físicos dados de baja deben someterse a borrado seguro NIST SP 800-88.',
  'POL-SEG-003_v3.0.pdf', encode(digest('POL-SEG-003-v3.0', 'sha256'), 'hex'), 3, 2, TRUE),

 (4, '2.0', 'Protocolo actualizado de respuesta ante Ransomware y tiempos SLA de notificación.',
  '# POL-SEG-004 v2.0 · Gestión y Respuesta a Incidentes de Ciberseguridad\n\n## Artículo 1. Plazos de Reporte de Incidentes (Página 1)\nCualquier empleado que detecte un comportamiento anómalo, correo de phishing exitoso, pérdida de equipo o sospecha de malware debe reportarlo al SOC/CSIRT en un plazo máximo de **15 minutos** para eventos críticos y **60 minutos** para eventos de severidad media.\n\n## Artículo 2. Protocolo ante Ransomware y Prohibición de Pago (Página 2)\nAnte una infección por **Ransomware**, el equipo afectado debe ser **aislado inmediatamente de la red (desconexión de cable Ethernet y Wi-Fi)**, pero **NO debe apagarse** para no perder evidencia volátil en memoria RAM. La organización **prohíbe estrictamente el pago de rescates (ransom)** a grupos extorsivos.\n\n## Artículo 3. Preservación Forense y Cadena de Custodia (Página 3)\nToda evidencia digital recolectada durante un incidente debe calcular su hash **SHA-256** en el momento de su adquisición y registrarse en la bitácora inmutable del sistema.',
  'POL-SEG-004_v2.0.pdf', encode(digest('POL-SEG-004-v2.0', 'sha256'), 'hex'), 3, 1, TRUE),

 (5, '1.0', 'Primera edición de la política de gobernanza de IA Generativa y agentes autónomos.',
  '# POL-SEG-005 v1.0 · Uso Aceptable de Inteligencia Artificial Generativa y LLMs\n\n## Artículo 1. Uso Autorizado y Prohibición de Exfiltración de Datos (Página 1)\nLos colaboradores pueden emplear asistentes de IA aprobados para redacción, síntesis y apoyo técnico. Está **estrictamente prohibido ingresar datos personales de clientes (DNI, cuentas bancarias, historias clínicas), contraseñas, llaves API o código fuente confidencial** en modelos de IA públicos externos.\n\n## Artículo 2. Procesamiento Local y Sistemas RAG Internos (Página 2)\nPara el procesamiento de documentos internos o normativos se debe utilizar la plataforma corporativa **PolicyGuard-RAG** o motores LLM locales (**Ollama**) desplegados dentro de la infraestructura de la organización, garantizando que ningún documento salga a internet.\n\n## Artículo 3. Supervisión Humana (Human-in-the-Loop) y Explicabilidad (Página 3)\nNinguna decisión crítica de seguridad, legal o financiera puede ejecutarse de forma 100% autónoma por un modelo de IA sin validación humana previa y sin que el sistema muestre las **citas verificables (artículo y página)** que sustentan su respuesta.',
  'POL-SEG-005_v1.0.pdf', encode(digest('POL-SEG-005-v1.0', 'sha256'), 'hex'), 3, 2, TRUE)
ON CONFLICT (policy_id, version_number) DO NOTHING;

-- 6. Fragmentos Indexados (Chunks RAG con referencia exacta a Artículo y Página)
INSERT INTO policy_chunks (policy_id, version_id, chunk_index, article_ref, section_title, page_number, content, token_count, keywords) VALUES
 (1, 2, 1, 'Artículo 1', 'Objetivo y Alcance del Control de Accesos', 1,
  'Garantizar que únicamente usuarios autorizados accedan a los sistemas de información de la organización, aplicando el principio de mínimo privilegio y autenticación robusta según ISO 27001 A.5.15.', 42,
  ARRAY['acceso','autorizados','minimo','privilegio','iso','27001']),

 (1, 2, 2, 'Artículo 2', 'Estándar de Contraseñas Corporativas (12 y 16 caracteres)', 2,
  'Toda cuenta de usuario estándar debe tener una contraseña de al menos 12 caracteres, combinando mayúsculas, minúsculas, números y símbolos especiales. Las cuentas de Administrador deben tener al menos 16 caracteres. Queda prohibido reutilizar las últimas 10 contraseñas.', 54,
  ARRAY['contraseña','contraseñas','password','longitud','minima','12','16','caracteres','administrador','reutilizar']),

 (1, 2, 3, 'Artículo 3', 'Autenticación Multifactor (MFA) y Bloqueo por Intentos Fallidos', 3,
  'El uso de MFA (TOTP o llave FIDO2) es estrictamente obligatorio para correo corporativo, VPN, paneles cloud (AWS/Azure) y cuentas privilegiadas. Tras 5 intentos fallidos consecutivos, la cuenta se bloqueará automáticamente por 15 minutos y se registrará en la bitácora de auditoría.', 58,
  ARRAY['mfa','multifactor','doble','factor','totp','fido2','bloqueo','intentos','fallidos','5','15','minutos','vpn','correo']),

 (1, 2, 4, 'Artículo 4', 'Revisión y Revocación de Accesos por Cese (2 horas / 90 días)', 4,
  'Ante el cese o desvinculación de un colaborador, Recursos Humanos debe notificar de inmediato para revocar todos los accesos en un plazo máximo de 2 horas. Los privilegios administrativos se recertifican cada 90 días.', 48,
  ARRAY['cese','desvinculacion','despido','renuncia','revocar','accesos','2','horas','90','dias','recertificacion','rrhh']),

 (2, 3, 1, 'Artículo 1', 'Condiciones de Teletrabajo y Cifrado BitLocker / FileVault', 1,
  'Todo colaborador en modalidad remota o híbrida debe conectarse exclusivamente mediante equipos corporativos inventariados con EDR Wazuh activo y cifrado de disco completo (BitLocker en Windows o FileVault en macOS).', 46,
  ARRAY['teletrabajo','remoto','hibrido','casa','bitlocker','fileVault','cifrado','disco','wazuh','edr','equipo']),

 (2, 3, 2, 'Artículo 2', 'Uso Obligatorio de VPN y Prohibición de Wi-Fi Públicas', 2,
  'Para acceder a servidores internos, bases de datos o repositorios de código desde fuera de la oficina, es obligatorio establecer túnel VPN corporativo con MFA. Está terminantemente prohibido conectarse a redes Wi-Fi públicas (aeropuertos, cafeterías, hoteles) sin activar previamente la VPN institucional.', 56,
  ARRAY['vpn','wifi','wi-fi','publica','aeropuerto','cafeteria','hotel','remoto','tunel','servidores','fuera','oficina']),

 (2, 3, 3, 'Artículo 3', 'Bloqueo de Pantalla (5 min) y Dispositivos Personales BYOD', 3,
  'El bloqueo automático de pantalla por inactividad no debe superar los 5 minutos. Los dispositivos personales (BYOD) solo pueden acceder al correo web encapsulado y nunca almacenar bases de datos o archivos clasificados como Confidenciales o Restringidos.', 50,
  ARRAY['bloqueo','pantalla','inactividad','5','minutos','byod','personal','celular','laptop','confidencial']),

 (3, 4, 1, 'Artículo 1', 'Cuatro Niveles de Clasificación de la Información', 1,
  'Toda información de la empresa se clasifica en cuatro niveles: 1) Pública (material comercial aprobado), 2) Interna (manuales y comunicados operativos), 3) Confidencial (contratos, datos personales PII, estados financieros) y 4) Restringida (secretos criptográficos, arquitectura de seguridad, investigaciones forenses).', 55,
  ARRAY['clasificacion','niveles','publica','interna','confidencial','restringida','pii','datos','personales','etiquetado']),

 (3, 4, 2, 'Artículo 2', 'Estándares Criptográficos Autorizados (AES-256, TLS 1.3, SHA-256)', 2,
  'Los datos clasificados como Confidenciales o Restringidos deben cifrarse en reposo utilizando AES-256 y en tránsito mediante TLS 1.2 o TLS 1.3. Para integridad documental y bitácoras de auditoría se exige SHA-256. Queda prohibido el uso de MD5, SHA-1, DES o 3DES.', 56,
  ARRAY['criptografia','cifrado','aes-256','aes','tls','sha-256','md5','sha-1','reposo','transito','algoritmo']),

 (3, 4, 3, 'Artículo 3', 'Retención de Evidencias (5 años) y Borrado Seguro NIST 800-88', 3,
  'Los registros de auditoría de seguridad y acuses de políticas deben conservarse de manera inmutable por un mínimo de 5 años. Los medios físicos dados de baja deben someterse a borrado seguro NIST SP 800-88.', 46,
  ARRAY['retencion','conservacion','5','años','auditoria','bitacora','borrado','seguro','nist','800-88','destruccion']),

 (4, 5, 1, 'Artículo 1', 'Plazos SLA de Reporte de Incidentes (15 minutos críticos)', 1,
  'Cualquier empleado que detecte un comportamiento anómalo, correo de phishing exitoso, pérdida de equipo o sospecha de malware debe reportarlo al SOC/CSIRT en un plazo máximo de 15 minutos para eventos críticos y 60 minutos para eventos de severidad media.', 52,
  ARRAY['incidente','reportar','plazo','tiempo','15','minutos','60','critico','phishing','malware','perdida','robo','soc','csirt']),

 (4, 5, 2, 'Artículo 2', 'Protocolo ante Ransomware y Prohibición de Pago de Rescate', 2,
  'Ante una infección por Ransomware, el equipo afectado debe ser aislado inmediatamente de la red (desconexión de cable Ethernet y Wi-Fi), pero NO debe apagarse para no perder evidencia volátil en memoria RAM. La organización prohíbe estrictamente el pago de rescates (ransom) a grupos extorsivos.', 58,
  ARRAY['ransomware','secuestro','rescate','pagar','pago','apagar','aislar','red','ethernet','ram','memoria','infeccion','virus']),

 (4, 5, 3, 'Artículo 3', 'Preservación Forense y Cadena de Custodia con SHA-256', 3,
  'Toda evidencia digital recolectada durante un incidente debe calcular su hash SHA-256 en el momento de su adquisición y registrarse en la bitácora inmutable del sistema para preservar la cadena de custodia.', 44,
  ARRAY['forense','evidencia','cadena','custodia','hash','sha-256','adquisicion','inmutable']),

 (5, 6, 1, 'Artículo 1', 'Uso de IA Generativa (ChatGPT/Claude) y Prohibición de Subir PII/Código', 1,
  'Los colaboradores pueden emplear asistentes de IA aprobados para redacción, síntesis y apoyo técnico. Está estrictamente prohibido ingresar datos personales de clientes (DNI, cuentas bancarias, historias clínicas), contraseñas, llaves API o código fuente confidencial en modelos de IA públicos externos.', 55,
  ARRAY['ia','inteligencia','artificial','chatgpt','claude','copilot','llm','datos','personales','dni','codigo','fuente','subir','secreto']),

 (5, 6, 2, 'Artículo 2', 'Uso de Plataforma Interna PolicyGuard-RAG y Modelos Locales Ollama', 2,
  'Para el procesamiento de documentos internos o normativos se debe utilizar la plataforma corporativa PolicyGuard-RAG o motores LLM locales (Ollama) desplegados dentro de la infraestructura de la organización, garantizando que ningún documento salga a internet.', 48,
  ARRAY['ollama','local','policyguard','rag','interno','nube','privacidad','soberania','documentos']),

 (5, 6, 3, 'Artículo 3', 'Supervisión Humana (Human-in-the-Loop) y Citas Verificables', 3,
  'Ninguna decisión crítica de seguridad, legal o financiera puede ejecutarse de forma 100% autónoma por un modelo de IA sin validación humana previa y sin que el sistema muestre las citas verificables (artículo y página) que sustentan su respuesta.', 50,
  ARRAY['human-in-the-loop','humano','supervision','citas','explicabilidad','xai','autonomo','decision','articulo','pagina']);

-- 7. Acuses de Recibo firmados digitalmente (para nutrir los gráficos de adopción)
INSERT INTO acknowledgments (policy_id, version_number, user_id, department, acknowledged_at, ip_address, digital_signature, comments) VALUES
 (1, '2.1', 1, 'Seguridad de la Información', NOW() - INTERVAL '15 days', '10.0.10.11', encode(digest('ack-1-1', 'sha256'), 'hex'), 'Conforme con el estándar MFA y longitud de 12/16 caracteres.'),
 (1, '2.1', 2, 'Gobierno, Riesgo y Cumplimiento', NOW() - INTERVAL '14 days', '10.0.10.12', encode(digest('ack-1-2', 'sha256'), 'hex'), 'Revisado y validado según ISO 27001 A.5.17.'),
 (1, '2.1', 3, 'Tecnología y Operaciones', NOW() - INTERVAL '12 days', '10.0.10.20', encode(digest('ack-1-3', 'sha256'), 'hex'), 'Aplicado en Active Directory corporativo.'),
 (1, '2.1', 4, 'Auditoría Interna', NOW() - INTERVAL '10 days', '10.0.10.30', encode(digest('ack-1-4', 'sha256'), 'hex'), 'Evidencia verificada.'),
 (1, '2.1', 5, 'Finanzas y Contabilidad', NOW() - INTERVAL '8 days', '10.0.20.15', encode(digest('ack-1-5', 'sha256'), 'hex'), 'Leído y comprendido.'),
 (1, '2.1', 6, 'Recursos Humanos', NOW() - INTERVAL '7 days', '10.0.30.18', encode(digest('ack-1-6', 'sha256'), 'hex'), 'Alineado con protocolo de bajas en 2 horas.'),
 (1, '2.1', 7, 'Desarrollo de Software', NOW() - INTERVAL '5 days', '10.0.40.22', encode(digest('ack-1-7', 'sha256'), 'hex'), 'MFA configurado en GitHub y AWS.'),

 (2, '1.4', 1, 'Seguridad de la Información', NOW() - INTERVAL '14 days', '10.0.10.11', encode(digest('ack-2-1', 'sha256'), 'hex'), 'Conforme.'),
 (2, '1.4', 2, 'Gobierno, Riesgo y Cumplimiento', NOW() - INTERVAL '13 days', '10.0.10.12', encode(digest('ack-2-2', 'sha256'), 'hex'), 'Conforme.'),
 (2, '1.4', 3, 'Tecnología y Operaciones', NOW() - INTERVAL '11 days', '10.0.10.20', encode(digest('ack-2-3', 'sha256'), 'hex'), 'VPN WireGuard activa.'),
 (2, '1.4', 5, 'Finanzas y Contabilidad', NOW() - INTERVAL '6 days', '10.0.20.15', encode(digest('ack-2-5', 'sha256'), 'hex'), 'BitLocker verificado.'),
 (2, '1.4', 7, 'Desarrollo de Software', NOW() - INTERVAL '4 days', '10.0.40.22', encode(digest('ack-2-7', 'sha256'), 'hex'), 'Conforme.'),

 (3, '3.0', 1, 'Seguridad de la Información', NOW() - INTERVAL '10 days', '10.0.10.11', encode(digest('ack-3-1', 'sha256'), 'hex'), 'Conforme.'),
 (3, '3.0', 2, 'Gobierno, Riesgo y Cumplimiento', NOW() - INTERVAL '9 days', '10.0.10.12', encode(digest('ack-3-2', 'sha256'), 'hex'), 'Conforme.'),
 (3, '3.0', 4, 'Auditoría Interna', NOW() - INTERVAL '8 days', '10.0.10.30', encode(digest('ack-3-4', 'sha256'), 'hex'), 'Conforme.'),
 (3, '3.0', 6, 'Recursos Humanos', NOW() - INTERVAL '3 days', '10.0.30.18', encode(digest('ack-3-6', 'sha256'), 'hex'), 'Aplicado a legajos de personal.'),

 (4, '2.0', 1, 'Seguridad de la Información', NOW() - INTERVAL '9 days', '10.0.10.11', encode(digest('ack-4-1', 'sha256'), 'hex'), 'Conforme.'),
 (4, '2.0', 3, 'Tecnología y Operaciones', NOW() - INTERVAL '7 days', '10.0.10.20', encode(digest('ack-4-3', 'sha256'), 'hex'), 'Playbook CSIRT sincronizado.'),
 (4, '2.0', 7, 'Desarrollo de Software', NOW() - INTERVAL '2 days', '10.0.40.22', encode(digest('ack-4-7', 'sha256'), 'hex'), 'Entendido el protocolo de no apagar el host ante ransomware.'),

 (5, '1.0', 1, 'Seguridad de la Información', NOW() - INTERVAL '5 days', '10.0.10.11', encode(digest('ack-5-1', 'sha256'), 'hex'), 'Conforme.'),
 (5, '1.0', 2, 'Gobierno, Riesgo y Cumplimiento', NOW() - INTERVAL '4 days', '10.0.10.12', encode(digest('ack-5-2', 'sha256'), 'hex'), 'Conforme.'),
 (5, '1.0', 7, 'Desarrollo de Software', NOW() - INTERVAL '1 day', '10.0.40.22', encode(digest('ack-5-7', 'sha256'), 'hex'), 'Uso exclusivo de Ollama local para código interno.')
ON CONFLICT (policy_id, version_number, user_id) DO NOTHING;

-- 8. Consultas Históricas al Chatbot RAG con Citas Verificables
INSERT INTO rag_queries (user_id, username, department, question, answer, citations, confidence_score, model_used, latency_ms, restricted_flagged, n8n_notified, helpful_feedback) VALUES
 (5, 'empleado1', 'Finanzas y Contabilidad',
  '¿Cuántos caracteres como mínimo debe tener mi contraseña y qué pasa si me equivoco varias veces?',
  'De acuerdo con la **Política de Control de Accesos, Contraseñas y MFA (POL-SEG-001 v2.1)**:\n\n1. **Longitud mínima**: Tu cuenta de usuario estándar debe tener una contraseña de al menos **12 caracteres** (combinando mayúsculas, minúsculas, números y símbolos), mientras que las cuentas de Administrador exigen **16 caracteres** (*Artículo 2, Página 2*).\n2. **Bloqueo automático**: Si ingresas una contraseña incorrecta **5 veces consecutivas**, tu cuenta se bloqueará automáticamente durante **15 minutos** y el evento quedará registrado en la bitácora de auditoría (*Artículo 3, Página 3*).',
  '[{"policy_code":"POL-SEG-001","version":"2.1","title":"Política de Control de Accesos, Contraseñas y Autenticación Multifactor (MFA)","article_ref":"Artículo 2","page_number":2,"score":0.96,"excerpt":"Toda cuenta de usuario estándar debe tener una contraseña de al menos 12 caracteres... Las cuentas de Administrador deben tener al menos 16 caracteres."},{"policy_code":"POL-SEG-001","version":"2.1","title":"Política de Control de Accesos, Contraseñas y Autenticación Multifactor (MFA)","article_ref":"Artículo 3","page_number":3,"score":0.91,"excerpt":"Tras 5 intentos fallidos consecutivos, la cuenta se bloqueará automáticamente por 15 minutos."}]'::jsonb,
  0.9600, 'langchain-rag-hybrid-v1', 38, FALSE, FALSE, TRUE),

 (7, 'empleado3', 'Desarrollo de Software',
  '¿Qué debo hacer si detecto una infección de Ransomware en mi estación de trabajo? ¿Debo apagar la computadora?',
  'Según la **Política de Gestión y Respuesta a Incidentes de Ciberseguridad (POL-SEG-004 v2.0)**:\n\n* **NO debes apagar el equipo**: Apagarlo destruiría evidencia volátil crítica alojada en la memoria RAM (*Artículo 2, Página 2*).\n* **Aislamiento inmediato de red**: Debes desconectar de inmediato el cable de red Ethernet y desactivar la conexión Wi-Fi (*Artículo 2, Página 2*).\n* **Reporte en máximo 15 minutos**: Debes notificar al SOC/CSIRT en un plazo no mayor a **15 minutos** por tratarse de un incidente crítico (*Artículo 1, Página 1*).\n* **Prohibición de pago**: La organización prohíbe estrictamente el pago de rescates (*Artículo 2, Página 2*).',
  '[{"policy_code":"POL-SEG-004","version":"2.0","title":"Política de Gestión y Respuesta a Incidentes de Ciberseguridad y Ransomware","article_ref":"Artículo 2","page_number":2,"score":0.98,"excerpt":"Ante una infección por Ransomware, el equipo afectado debe ser aislado inmediatamente de la red... pero NO debe apagarse para no perder evidencia volátil en memoria RAM."},{"policy_code":"POL-SEG-004","version":"2.0","title":"Política de Gestión y Respuesta a Incidentes de Ciberseguridad y Ransomware","article_ref":"Artículo 1","page_number":1,"score":0.89,"excerpt":"Reportarlo al SOC/CSIRT en un plazo máximo de 15 minutos para eventos críticos."}]'::jsonb,
  0.9800, 'langchain-rag-hybrid-v1', 42, TRUE, TRUE, TRUE),

 (6, 'empleado2', 'Recursos Humanos',
  '¿En cuánto tiempo debemos revocar los accesos cuando un trabajador cesa o renuncia?',
  'Conforme a la **Política de Control de Accesos (POL-SEG-001 v2.1, Artículo 4, Página 4)**:\n\n* Ante el cese o desvinculación de un colaborador, Recursos Humanos debe notificar de inmediato a TI/Seguridad para que todos sus accesos sean revocados en un **plazo máximo de 2 horas**.\n* Adicionalmente, los privilegios administrativos deben pasar por recertificación cada **90 días**.',
  '[{"policy_code":"POL-SEG-001","version":"2.1","title":"Política de Control de Accesos, Contraseñas y Autenticación Multifactor (MFA)","article_ref":"Artículo 4","page_number":4,"score":0.95,"excerpt":"Ante el cese o desvinculación de un colaborador, Recursos Humanos debe notificar de inmediato para revocar todos los accesos en un plazo máximo de 2 horas."}]'::jsonb,
  0.9500, 'langchain-rag-hybrid-v1', 31, FALSE, FALSE, TRUE),

 (8, 'empleado4', 'Operaciones Comerciales',
  '¿Puedo subir contratos de clientes con DNI a ChatGPT para hacer un resumen rápido?',
  '**No, está estrictamente prohibido.** De acuerdo con la **Política de Uso Aceptable de Inteligencia Artificial Generativa (POL-SEG-005 v1.0)**:\n\n* **Prohibición de exfiltración de PII**: Queda prohibido ingresar datos personales de clientes (DNI, cuentas bancarias), contraseñas o información confidencial en modelos de IA públicos externos como ChatGPT (*Artículo 1, Página 1*).\n* **Alternativa autorizada**: Para resumir o consultar documentos internos debes emplear la plataforma corporativa **PolicyGuard-RAG** o motores **Ollama locales** dentro de la red de la empresa (*Artículo 2, Página 2*).',
  '[{"policy_code":"POL-SEG-005","version":"1.0","title":"Política de Uso Aceptable de Inteligencia Artificial Generativa y Agentes LLM","article_ref":"Artículo 1","page_number":1,"score":0.97,"excerpt":"Está estrictamente prohibido ingresar datos personales de clientes (DNI, cuentas bancarias, historias clínicas), contraseñas, llaves API o código fuente confidencial en modelos de IA públicos externos."},{"policy_code":"POL-SEG-005","version":"1.0","title":"Política de Uso Aceptable de Inteligencia Artificial Generativa y Agentes LLM","article_ref":"Artículo 2","page_number":2,"score":0.90,"excerpt":"Se debe utilizar la plataforma corporativa PolicyGuard-RAG o motores LLM locales (Ollama)."}]'::jsonb,
  0.9700, 'langchain-rag-hybrid-v1', 35, FALSE, FALSE, TRUE);

-- 9. Registros Iniciales en la Bitácora Inmutable (el trigger calcula automáticamente hash_prev y hash_self SHA-256)
INSERT INTO audit_log (user_id, username, role_code, module, action, entity, entity_id, result, severity, detail, ip_address, http_method, http_path, http_status) VALUES
 (1, 'admin', 'admin', 'system', 'INIT', 'database', 'schema_v1', 'SUCCESS', 'info', 'Inicialización de esquema policyrag y controles ISO/IEC 27001 A.8.15', '127.0.0.1', 'SYSTEM', '/db/init', 200),
 (1, 'admin', 'admin', 'policies', 'CREATE', 'policy', 'POL-SEG-001', 'SUCCESS', 'info', 'Publicación e indexación RAG de POL-SEG-001 v2.1 (4 chunks)', '10.0.10.11', 'POST', '/api/v1/policies', 201),
 (1, 'admin', 'admin', 'policies', 'CREATE', 'policy', 'POL-SEG-002', 'SUCCESS', 'info', 'Publicación e indexación RAG de POL-SEG-002 v1.4 (3 chunks)', '10.0.10.11', 'POST', '/api/v1/policies', 201),
 (2, 'analista1', 'analista', 'policies', 'CREATE', 'policy', 'POL-SEG-003', 'SUCCESS', 'info', 'Publicación e indexación RAG de POL-SEG-003 v3.0 (3 chunks)', '10.0.10.12', 'POST', '/api/v1/policies', 201),
 (1, 'admin', 'admin', 'policies', 'CREATE', 'policy', 'POL-SEG-004', 'SUCCESS', 'warning', 'Publicación de política RESTRICTED POL-SEG-004 v2.0 (Respuesta a Ransomware)', '10.0.10.11', 'POST', '/api/v1/policies', 201),
 (2, 'analista1', 'analista', 'policies', 'CREATE', 'policy', 'POL-SEG-005', 'SUCCESS', 'info', 'Publicación e indexación RAG de POL-SEG-005 v1.0 (Gobernanza IA)', '10.0.10.12', 'POST', '/api/v1/policies', 201),
 (5, 'empleado1', 'empleado', 'acknowledgments', 'ACKNOWLEDGE', 'policy', 'POL-SEG-001:v2.1', 'SUCCESS', 'info', 'Firma digital de acuse de recibo de POL-SEG-001 v2.1 por empleado1', '10.0.20.15', 'POST', '/api/v1/policies/1/acknowledge', 201),
 (7, 'empleado3', 'empleado', 'rag_chat', 'RAG_QUERY', 'policy', 'POL-SEG-004', 'SUCCESS', 'warning', 'Consulta RAG sobre política RESTRICTED (Ransomware) notificada vía webhook n8n', '10.0.40.22', 'POST', '/api/v1/rag/ask', 200),
 (4, 'auditor1', 'auditor', 'audit', 'VERIFY_CHAIN', 'audit_log', 'all', 'SUCCESS', 'info', 'Verificación criptográfica SHA-256 de la cadena de bloques de auditoría: ÍNTEGRA', '10.0.10.30', 'GET', '/api/v1/audit/verify-chain', 200);

COMMIT;
