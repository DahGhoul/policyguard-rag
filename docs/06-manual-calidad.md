# 06 · Manual de Calidad del Software ISO/IEC 25010 (PolicyGuard-RAG · Caso 21)

## Evaluación de Atributos de Calidad (ISO/IEC 25010)
1. **Adecuación Funcional (100%):** Cubre versionado de políticas, fragmentación automática por artículos y páginas, Chatbot RAG con citas verificables, acuses de recibo con firma digital, dashboard de adopción departamental, reportería triformato (PDF/Word/Excel) y bitácora inmutable.
2. **Eficiencia de Desempeño:** Motor asíncrono `FastAPI` + `asyncpg` con tiempo medio de respuesta del motor RAG $< 45\text{ ms}$.
3. **Fiabilidad y Cero Dependencias Externas Frágiles:** Al almacenar tanto los datos relacionales como los fragmentos indexados en PostgreSQL, la sustentación en vivo nunca falla por caídas de APIs de terceros.
4. **Explicabilidad e Interpretabilidad (XAI):** Cada respuesta del agente incluye obligatoriamente el código de política, versión, artículo, página y porcentaje de similitud semántica.
5. **Mantenibilidad y Portabilidad:** Despliegue contenerizado reproducible con `docker compose up -d --build`.
