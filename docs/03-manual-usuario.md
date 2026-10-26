# 03 · Manual de Usuario (PolicyGuard-RAG · Caso 21)

## 1. Acceso y Credenciales por Perfil (RBAC)
Ingrese desde su navegador a: **`http://localhost:5174`**

| Usuario | Contraseña | Rol | Funciones Habilitadas |
| :--- | :--- | :--- | :--- |
| `admin` | `Admin123!` | **Administrador** | Acceso total: publicar/versionar políticas, Chatbot RAG, acuses, reportes, bitácora SHA-256 y usuarios. |
| `analista1` | `Analyst123!` | **Analista GRC** | Creación y versionado de políticas (re-indexación automática RAG), seguimiento de adopción y reportes. |
| `gestor` | `Manager123!` | **Gestor / CISO** | Visualización del Dashboard de adopción por departamento y descarga de reportes PDF, Word y Excel. |
| `auditor1` | `Audit123!` | **Auditor ISO 27001** | Inspección de bitácora inmutable, verificación de cadena SHA-256 y prueba de bloqueo de borrado (`DELETE`). |
| `empleado1` | `User123!` | **Colaborador** | Lectura de políticas vigentes, firma digital de acuse de recibo y consultas al Chatbot RAG. |

## 2. Uso de los Módulos Principales

### 2.1 Dashboard de Adopción (`📊 Dashboard Adopción`)
Presenta en tiempo real:
- **KPIs Ejecutivos:** Políticas indexadas, fragmentos (`chunks`) en el motor RAG, porcentaje global de adopción de acuses, total de consultas atendidas por el Chatbot y latencia promedio en milisegundos.
- **Barras de Progreso por Política y Departamento:** Permite identificar qué áreas (Finanzas, RRHH, Desarrollo, Operaciones) tienen acuses pendientes.

### 2.2 Chatbot RAG con Citas Exactas (`🤖 Chatbot RAG (Citas)`)
- Escriba cualquier consulta en lenguaje natural o utilice los **6 botones de Preguntas Listas para Demo (1-Clic)** del panel derecho.
- El agente recupera los fragmentos normativos más relevantes y responde mostrando las tarjetas de **Fuentes Normativas Citadas** con el **Código de Política, Versión, Artículo exacto, Página y porcentaje de similitud**.
- Si la pregunta aborda una política clasificada como `RESTRICTED` (ej. protocolo ante Ransomware `POL-SEG-004`), se dispara y muestra el aviso de **Flujo n8n Notificado**.

### 2.3 Catálogo de Políticas, Versionado y Acuses (`📜 Políticas y Acuses`)
- Haga clic en **"Firmar Acuse de Recibo"** para registrar su conformidad digital con hash único `SHA-256`.
- Haga clic en **"Ver Texto Completo, Chunks y Versiones"** para inspeccionar cómo la política fue dividida en fragmentos por artículo y página, su historial de versiones y la lista nominal de empleados que ya firmaron.
- Los usuarios `admin` y `analista1` disponen del botón **"+ Publicar / Versionar Política"**, que divide automáticamente el nuevo texto en `chunks` y actualiza el índice RAG en vivo.

### 2.4 Exportación de Reportes (`📥 Reportes (PDF/Word/Excel)`)
Permite descargar con un clic cualquiera de los 3 reportes oficiales (**Cumplimiento ISO 27001**, **Operacional RAG** y **Forense de Auditoría**) en formatos **PDF**, **Word (`.docx`)** y **Excel (`.xlsx`)**.

### 2.5 Bitácora Inmutable SHA-256 (`⛓️ Bitácora SHA-256`)
- Botón **"🔗 Verificar Cadena Criptográfica SHA-256"**: Valida matemáticamente todos los bloques desde el bloque génesis (`0000...`).
- Botón **"🛡️ Probar Inmutabilidad (Intentar DELETE en BD)"**: Ejecuta en vivo un intento de `DELETE FROM policyrag.audit_log WHERE id = 1` y muestra en pantalla cómo el *trigger* de PostgreSQL lo bloquea instantáneamente.
