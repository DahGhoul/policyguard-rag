# 02 · Manual de Instalación (PolicyGuard-RAG · Caso 21)

## 1. Requisitos del Sistema
- **Sistema Operativo:** Windows 10/11 Pro (con WSL2), Linux (Ubuntu 22.04+) o macOS.
- **Motor de Contenedores:** Docker Desktop 24+ y Docker Compose v2+.
- **Recursos Mínimos:** 2 vCPU, 4 GB de RAM libres y 5 GB de espacio en disco (el sistema es 100% autocontenido y no requiere GPUs ni servidores externos pesados).

## 2. Despliegue en 1 Solo Comando con Docker Compose
Desde la carpeta `policy-rag`, ejecute:

```powershell
cd "c:\Users\Diego\Downloads\tarea nose\policy-rag"
docker compose up -d --build
```

## 3. Puertos y Servicios Desplegados
| Contenedor | Servicio | Puerto Local | Descripción |
| :--- | :--- | :---: | :--- |
| `policy-rag-frontend` | Consola Web SPA + Nginx Proxy | **`5174`** | Interfaz principal en `http://localhost:5174` |
| `policy-rag-backend` | API FastAPI + Motor RAG + Reportes | **`8002`** | Swagger UI en `http://localhost:8002/docs` |
| `policy-rag-postgres` | Base de Datos PostgreSQL 15 | **`5433`** | Esquema `policyrag` con trigger inmutable |
| `policy-rag-redis` | Caché en Memoria Redis 7 | **`6380`** | Sesiones y control de tasa |

## 4. Inicialización Manual de Base de Datos (si se requiere recargar semilla)
```powershell
Get-Content .\db\schema.sql -Raw | docker exec -i policy-rag-postgres psql -U policyrag -d policyrag
Get-Content .\db\seed.sql -Raw | docker exec -i policy-rag-postgres psql -U policyrag -d policyrag
```

## 5. Verificación de Salud (Health Check)
```powershell
Invoke-RestMethod -Uri "http://localhost:5174/api/v1/health"
```
Debe retornar `"status": "ok"`, `"indexed_policies": 5` e `"indexed_chunks": 16`.
