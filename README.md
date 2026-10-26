# PolicyGuard-RAG (Caso 21: Gestor de Políticas con Chatbot RAG)

Plataforma de **Gestión de Políticas Corporativas (ISO/IEC 27001:2022 Control A.5.1 / A.6.3)** con **Chatbot RAG explicable (LangChain + LangFlow)**, **Acuses de Recibo con Firma Digital SHA-256** y **Bitácora Forense Inmutable**.

Desarrollado para la **Cartera de Proyectos de Ingeniería de Software Agéntica**.

---

## 🚀 Características Principales

- **Frontend Web SPA**: React / TailwindCSS interactivo con Dashboard de adopción por departamento, visores de políticas y consola del Chatbot RAG.
- **Backend API REST**: FastAPI asíncrono con SQLAlchemy / AsyncPG, autenticación JWT y control de acceso RBAC estricto (5 roles: *Administrador, Analista, Gestor, Auditor, Colaborador*).
- **Motor RAG Híbrido**: Fragmentación (*chunking*) automática por Artículos y Páginas, recuperación semántica y citas exactas `[Código · Artículo · Página]` con guardarraíl contra alucinaciones.
- **Orquestación SOAR (n8n)**: Flujo automatizado de 6 nodos para alertas de consultas sobre normativas restringidas y recordatorio de acuses pendientes.
- **Pipeline Visual (LangFlow)**: Especificación exportable del flujo de ingestión, embeddings y generación contextual.
- **Reportería Oficial**: Exportación en tiempo real en formatos **PDF** (ReportLab), **Word** (python-docx) y **Excel** (openpyxl) con firma criptográfica.
- **Bitácora Inmutable (ISO 27001 A.8.15)**: Cadena de bloques SHA-256 (`hash_prev` $\rightarrow$ `hash_self`) con **Trigger PostgreSQL** que bloquea cualquier intento de `UPDATE` o `DELETE`.

---

## 🛠️ Despliegue Rápido en Docker

```bash
docker compose up -d --build
```

- **Consola Web**: [http://localhost:5174](http://localhost:5174)
- **Documentación OpenAPI / Swagger**: [http://localhost:8002/docs](http://localhost:8002/docs)

### Credenciales Demo
- `admin` / `Admin123!` (Administrador)
- `analista1` / `Analyst123!` (Analista GRC)
- `gestor` / `Manager123!` (Gestor / CISO)
- `auditor1` / `Audit123!` (Auditor ISO 27001)
- `empleado1` / `User123!` (Colaborador)

---

## 📚 Documentación Técnica
Todos los manuales y arquitectura detallada se encuentran en [`docs/`](docs/):
- `01-arquitectura-y-arbol.md`: Diagrama Mermaid, modelo relacional y árbol de directorios.
- `02-manual-instalacion.md`: Pasos de despliegue y variables de entorno.
- `03-manual-usuario.md`: Guía de uso de módulos y preguntas sugeridas.
- `04-manual-errores.md`: Catálogo de códigos y guardarraíles XAI.
- `05-manual-pruebas.md`: Matriz de 9 pruebas E2E aprobadas.
- `06-manual-calidad.md`: Evaluación bajo norma ISO/IEC 25010.
- `07-manual-seguridad.md`: Controles ISO 27001 y OWASP LLM Top 10.
