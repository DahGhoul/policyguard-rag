# 04 · Manual de Errores y Guardarraíles XAI (PolicyGuard-RAG · Caso 21)

## 1. Catálogo de Códigos de Error Estándar
| Código HTTP | Escenario | Mensaje al Usuario | Causa y Solución |
| :---: | :--- | :--- | :--- |
| **401** | `UNAUTHENTICATED` | Usuario o contraseña incorrectos / Token expirado. | Verificar credenciales o volver a iniciar sesión en `/login`. |
| **403** | `FORBIDDEN` | No tiene permisos para publicar o versionar políticas. | El usuario tiene rol `empleado`, `gestor` o `auditor`. Iniciar sesión con `admin` o `analista1`. |
| **404** | `NOT_FOUND` | Política no encontrada. | El ID consultado no existe en `policyrag.policies`. |
| **422** | `VALIDATION_ERROR` | Pregunta demasiado corta (< 3 caracteres) o campos faltantes. | Completar los campos requeridos del formulario. |
| **500 / P0001** | `VIOLACIÓN DE SEGURIDAD FORENSE` | La tabla `policyrag.audit_log` es inmutable (ISO 27001 A.8.15). | Excepción intencional lanzada por el *trigger* `trg_audit_log_no_update_delete` cuando alguien intenta modificar o eliminar registros de auditoría. |

## 2. Guardarraíl contra Alucinaciones en el Chatbot RAG (`guardrail-no-match`)
Cuando un usuario realiza una pregunta ajena a las políticas corporativas (similitud semántica $< 0.22$), el motor RAG **no inventa respuestas**: activa automáticamente el guardarraíl de abstención explicable e indica que no existen artículos aplicables en el catálogo vigente, registrando el evento con confianza controlada (`0.45`).
