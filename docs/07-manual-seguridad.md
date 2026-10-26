# 07 · Manual de Seguridad y Cumplimiento ISO 27001 (PolicyGuard-RAG · Caso 21)

## 1. Controles de Seguridad Implementados
1. **ISO/IEC 27001:2022 Control A.5.1 (Políticas para la Seguridad de la Información):** Control de versiones con hash `SHA-256` del documento y evidencia nominal de acuse de recibo firmado digitalmente por cada colaborador.
2. **ISO/IEC 27001:2022 Control A.5.15 y A.5.17 (Control de Acceso y Autenticación):** Contraseñas cifradas con `bcrypt` (coste 12), tokens JWT firmados con `HS256` (`jti` UUIDv4) y matriz RBAC de 5 roles (`admin`, `analista`, `gestor`, `auditor`, `empleado`).
3. **ISO/IEC 27001:2022 Control A.8.15 (Registros de Auditoría Inmutables):**
   - **Cadena de Bloques Criptográfica (`hash_prev` $\rightarrow$ `hash_self`):** El trigger `trg_audit_log_hash` calcula en PostgreSQL el hash `SHA-256` de cada evento encadenado con el bloque anterior.
   - **Prohibición de Alteración o Borrado (`trg_audit_log_no_update_delete`):** Cualquier intento de `UPDATE` o `DELETE` sobre `policyrag.audit_log` es rechazado por el motor de base de datos y registrado como alerta crítica `TAMPER_ATTEMPT_BLOCKED`.
4. **Seguridad en Sistemas RAG / LLMs (OWASP LLM Top 10):** Soberanía de datos local, clasificación de políticas (`PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`) y disparo de alerta a `n8n` cuando se consultan normativas restringidas.
