# 05 · Manual de Pruebas (PolicyGuard-RAG · Caso 21)

## 1. Matriz de Casos de Prueba Ejecutados y Aprobados (End-to-End)

| ID | Módulo | Caso de Prueba | Endpoint | Resultado Obtenido | Estado |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **CP-01** | Infraestructura | Salud de API y PostgreSQL 15 | `GET /api/v1/health` | `status=ok`, `indexed_policies=5`, `indexed_chunks=16` | **APROBADO** |
| **CP-02** | Autenticación | Login JWT y resolución RBAC | `POST /api/v1/auth/login` (`admin`) | Emite token `HS256` con rol `admin` y 12 permisos | **APROBADO** |
| **CP-03** | Dashboard | KPIs de adopción y departamentos | `GET /api/v1/dashboard/summary` | Adopción global `55.0%`, 5 políticas, 16 chunks | **APROBADO** |
| **CP-04** | Chatbot RAG | Consulta con Cita Exacta (Artículo y Página) | `POST /api/v1/rag/ask` (Ransomware) | Cita `POL-SEG-004 v2.0`, `Artículo 2`, `Página 2`, activa flag `RESTRICTED` | **APROBADO** |
| **CP-05** | Políticas | Firma digital de Acuse de Recibo | `POST /api/v1/policies/5/acknowledge` | Firma SHA-256 `8c5483a31efdd57a...` registrada | **APROBADO** |
| **CP-06** | Políticas | Publicación y auto-chunking de política | `POST /api/v1/policies` | Divide texto por `## Artículo X` e indexa chunks en vivo | **APROBADO** |
| **CP-07** | Auditoría | Bloqueo de `DELETE` por Trigger PostgreSQL | `POST /api/v1/audit/test-immutability` | `blocked=True` por `trg_audit_log_no_update_delete` | **APROBADO** |
| **CP-08** | Auditoría | Verificación matemática de cadena SHA-256 | `GET /api/v1/audit/verify-chain` | `intact=True`, `broken_links=[]`, 13 bloques verificados | **APROBADO** |
| **CP-09** | Reportes | Exportación oficial en PDF, Word y Excel | `GET /api/v1/reports/export?format=pdf\|docx\|xlsx` | Genera `.pdf` (4.5 KB), `.docx` (38.8 KB) y `.xlsx` (9.4 KB) | **APROBADO** |
