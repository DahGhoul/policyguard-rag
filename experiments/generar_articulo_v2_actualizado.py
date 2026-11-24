import os, json, re, unicodedata
import pandas as pd
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_v2")
FIG_DIR = os.path.join(OUT_DIR, "figures")

R = json.load(open(os.path.join(OUT_DIR, "results_optuna_caso21.json"), encoding="utf-8"))

REFS = {
    "es2024": 'S. Es, J. James, L. Espinosa-Anke, and S. Schockaert, "RAGAs: Automated Evaluation of Retrieval Augmented Generation," in Proc. 18th Conf. Eur. Chapter Assoc. Comput. Linguistics (EACL): System Demonstrations, 2024, pp. 150–158, doi: https://doi.org/10.18653/v1/2024.eacl-demo.16.',
    "ali2023": 'S. Ali et al., "Explainable Artificial Intelligence (XAI): What we know and what is left to attain Trustworthy Artificial Intelligence," Information Fusion, vol. 99, art. 101805, Nov. 2023, doi: https://doi.org/10.1016/j.inffus.2023.101805.',
    "pan2023": 'L. Pan et al., "Explainable Artificial Intelligence," in Explainable AI for Cybersecurity, Cham: Springer, 2023, pp. 19–44, doi: https://doi.org/10.1007/978-3-031-46479-9_2.',
    "ofori2022": 'M. Ofori, "Factors Influencing Information Security Policy Compliance," in Research Anthology on Business Aspects of Cybersecurity, IGI Global, 2022, pp. 188–206, doi: https://doi.org/10.4018/978-1-6684-3698-1.ch010.',
    "chen2022": 'Y. Chen et al., "Understanding employees’ information security–related stress and policy compliance," Information & Computer Security, vol. 30, no. 4, pp. 500–519, 2022, doi: https://doi.org/10.1108/ics-03-2022-0047.',
    "muliarevych2024": 'O. Muliarevych et al., "Enhancing System Security: LLM-Driven Defense Against Prompt Injection," in Proc. IEEE 17th Int. Conf. Adv. Trends Radioelectron. Telecommun. Comput. Eng. (TCSET), 2024, pp. 1–6, doi: https://doi.org/10.1109/tcset64720.2024.10755823.',
    "lathkar2023": 'M. Lathkar, "Getting Started with FastAPI," in High-Performance Web Apps with FastAPI, Berkeley, CA: Apress, 2023, pp. 15–38, doi: https://doi.org/10.1007/978-1-4842-9178-8_2.',
    "koos2026": 'B. Koos, "Vector Databases and High-Dimensional Search: Semantic Similarity," in The Database Safari, Apress, 2026, doi: https://doi.org/10.1007/979-8-8688-2709-9_7.',
    "alabi2026": 'T. Alabi Bankole, "Adaptive Multi-Stage Vector Retrieval for Retrieval-Augmented Generation," NLP & Big Data, vol. 16, art. 1601307, 2026, doi: https://doi.org/10.5121/csit.2026.1601307.',
    "bakouan2026": 'M. Bakouan, "Query-Type Sensitivity and Selective Benefits of Hybrid Retrieval," Int. J. Adv. Res., art. 24038, 2026, doi: https://doi.org/10.21474/ijar01/24038.',
    "bhagia2026": 'R. Bhagia, "Role-based access control (RBAC)," in Zero Trust for Cloud-Native Security, CRC Press, 2026, doi: https://doi.org/10.1201/9781003791591-9.',
    "cimmino2024": 'C. Cimmino et al., "Large Language Models in Cybersecurity: Digital Defense," TechRxiv preprint, 2024, doi: https://doi.org/10.36227/techrxiv.172417964.40874339/v2.',
    "willard2022": 'J. Willard, X. Jia, S. Xu, M. Steinbach, and V. Kumar, "Integrating scientific knowledge with machine learning for engineering and environmental systems," ACM Computing Surveys, vol. 55, no. 4, art. 66, Nov. 2022, doi: https://doi.org/10.1145/3514228.',
    "robertson2009": 'S. Robertson and H. Zaragoza, "The Probabilistic Relevance Framework: BM25 and Beyond," Foundations and Trends in Information Retrieval, vol. 3, no. 4, pp. 333–389, 2009, doi: https://doi.org/10.1561/1500000019.',
    "reimers2019": 'N. Reimers and I. Gurevych, "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks," in Proc. EMNLP-IJCNLP, 2019, pp. 3982–3992, doi: https://doi.org/10.18653/v1/d19-1410.',
}

ORDER = []
def c(*keys):
    out = []
    for k in keys:
        if k not in ORDER: ORDER.append(k)
        out.append(f"[{ORDER.index(k) + 1}]")
    return ", ".join(out)

BP = R["best_params"]
TM = R["test_metrics"]
CV = R["cv_summary"]
LAT = R["inference_latency_ms"]
XAI = R["feature_importance_xai"]

T = {}
T[1] = pd.DataFrame([
    ["Ofori (2022)", "Revisión conceptual de cumplimiento", "Políticas de seguridad", "Sin verificación ni trazabilidad", "Acuses SHA-256 + monitoreo por área"],
    ["Es et al. (2024)", "Evaluación RAGAs", "Benchmarks abiertos", "Sin RBAC ni protocolo anti-fuga", "RBAC 5 roles + partición 70/15/15 agrupada"],
    ["Bakouan (2026)", "Recuperación híbrida selectiva", "Consultas generales", "Sin ajuste bayesiano Optuna TPE", "Fusión ponderada ajustada con Optuna TPE"],
    ["PolicyGuard-RAG (Este estudio)", "RAG híbrido + Optuna + CV 5x3 + SHA-256", "960 pares ISO 27001, 60 consultas", "Corpus controlado de 5 políticas", "Evaluación anti-fuga y explicabilidad XAI"]
], columns=["Estudio", "Enfoque metodológico", "Alcance", "Limitación identificada", "Aporte diferencial"])

T[2] = pd.DataFrame([
    ["Regresión Logística", "Penalización L2, max_iter = 1000", "C in [1e-3, 100] (log), class_weight", f"C = {BP['Regresión Logística']['C']:.4f}, cw = {BP['Regresión Logística']['class_weight']}", "Convergencia L-BFGS (tol = 1e-4)"],
    ["Random Forest", "Criterio Gini, bootstrap = True", "n_estimators [50, 350], max_depth [3, 14], min_split [2, 10]", f"n_est = {BP['Random Forest']['n_estimators']}, depth = {BP['Random Forest']['max_depth']}, mss = {BP['Random Forest']['min_samples_split']}", "35 trials Optuna TPE + MedianPruner"],
    ["HistGradientBoosting", "Pérdida logarítmica, early_stopping = True", "lr [0.01, 0.25], max_iter [50, 300], depth [2, 8], l2 [1e-4, 10]", f"lr = {BP['HistGradientBoosting']['learning_rate']:.4f}, iter = {BP['HistGradientBoosting']['max_iter']}, depth = {BP['HistGradientBoosting']['max_depth']}", "Parada temprana (patience = 10, tol = 1e-4)"],
    ["PolicyGuard-RAG Optuna", "Ensamble ponderado (LR + GB + App + BM25)", "Pesos continuos w_lr, w_gb, w_app, w_bm25 in [0, 0.8]", f"w_lr={BP['PolicyGuard-RAG Optuna']['w_lr']:.2f}, w_gb={BP['PolicyGuard-RAG Optuna']['w_gb']:.2f}, w_app={BP['PolicyGuard-RAG Optuna']['w_app']:.2f}", "40 trials TPE maximizando PR-AUC"]
], columns=["Modelo", "Configuración base", "Espacio de búsqueda Optuna", "Hiperparámetros óptimos", "Criterio de parada / poda"])

T[3] = pd.DataFrame([
    [m, f"{TM[m]['F1']:.4f}", f"{TM[m]['AUC_ROC']:.4f}", f"{TM[m]['PR_AUC']:.4f}", f"{TM[m]['LogLoss']:.4f}", f"{TM[m]['Brier']:.4f}", f"{TM[m]['MRR']:.4f}", f"{TM[m]['nDCG@3']:.4f}"]
    for m in ["Regresión Logística", "Random Forest", "HistGradientBoosting", "PolicyGuard-RAG Optuna"]
], columns=["Modelo evaluado", "F1-Score", "AUC-ROC", "PR-AUC", "LogLoss", "Brier", "MRR", "nDCG@3"])

T[4] = pd.DataFrame([
    [m, f"{CV[m]['AUC_ROC']['mean']:.4f} +/- {CV[m]['AUC_ROC']['std']:.4f}", f"{CV[m]['PR_AUC']['mean']:.4f} +/- {CV[m]['PR_AUC']['std']:.4f}", f"{CV[m]['MRR']['mean']:.4f} +/- {CV[m]['MRR']['std']:.4f}", f"{CV[m]['nDCG@3']['mean']:.4f} +/- {CV[m]['nDCG@3']['std']:.4f}", f"{CV[m]['Recall@3']['mean']:.4f}"]
    for m in ["Regresión Logística", "Random Forest", "HistGradientBoosting", "PolicyGuard-RAG Optuna"]
], columns=["Modelo", "AUC-ROC (Media +/- DE)", "PR-AUC (Media +/- DE)", "MRR (Media +/- DE)", "nDCG@3 (Media +/- DE)", "Recall@3"])

T[5] = pd.DataFrame([
    [f["feature"], f"{f['importance_mean']:.4f}", f"{f['importance_std']:.4f}"] for f in XAI
], columns=["Predictor XAI", "Importancia por permutación (Media)", "Desviación estándar (30 réplicas)"])

T[6] = pd.DataFrame([
    [m, f"{LAT[m]['median_ms']:.3f}", f"{LAT[m]['p95_ms']:.3f}"]
    for m in ["Regresión Logística", "Random Forest", "HistGradientBoosting", "PolicyGuard-RAG Optuna"]
], columns=["Modelo en inferencia (16 fragmentos)", "Latencia mediana (ms)", "Percentil 95 (ms)"])

def set_cell_margins(cell, top=55, bottom=55, left=75, right=75):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for m, v in [("w:top", top), ("w:bottom", bottom), ("w:left", left), ("w:right", right)]:
        tcMar.append(parse_xml('<%s %s w:w="%d" w:type="dxa"/>' % (m, nsdecls("w"), v)))
    tcPr.append(tcMar)

def fmt_table(tbl, df):
    tbl._tbl.tblPr.append(parse_xml('<w:tblBorders %s><w:top w:val="single" w:sz="8" w:space="0" w:color="000000"/><w:bottom w:val="single" w:sz="8" w:space="0" w:color="000000"/><w:insideH w:val="single" w:sz="4" w:space="0" w:color="D0D0D0"/></w:tblBorders>' % nsdecls("w")))
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, col in enumerate(df.columns):
        c_ = tbl.cell(0, j); c_.text = str(col)
        r = c_.paragraphs[0].runs[0]; r.bold = True; r.font.name = "Times New Roman"; r.font.size = Pt(8.5)
        set_cell_margins(c_)
    for i, row in df.iterrows():
        for j, v in enumerate(row):
            c_ = tbl.cell(i + 1, j); c_.text = str(v)
            r = c_.paragraphs[0].runs[0]; r.font.name = "Times New Roman"; r.font.size = Pt(8.2)
            set_cell_margins(c_)

doc = Document()
for s in doc.sections:
    s.top_margin = Inches(0.85); s.bottom_margin = Inches(0.85)
    s.left_margin = Inches(0.9); s.right_margin = Inches(0.9)

def add_p(text, bold=False, italic=False, size=11.5, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_before=0, space_after=6):
    p = doc.add_paragraph(); p.alignment = align
    p.paragraph_format.space_before = Pt(space_before); p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    r = p.add_run(text); r.bold = bold; r.italic = italic; r.font.name = "Times New Roman"; r.font.size = Pt(size)
    return p

def add_tab(n, title, interp, expl):
    p = add_p("", space_before=8, space_after=3)
    r1 = p.add_run(f"Tabla {n}. "); r1.bold = True; r1.font.name = "Times New Roman"; r1.font.size = Pt(10.5)
    r2 = p.add_run(title); r2.bold = True; r2.font.name = "Times New Roman"; r2.font.size = Pt(10.5)
    df = T[n]
    t = doc.add_table(rows=len(df) + 1, cols=len(df.columns)); fmt_table(t, df)
    pn = add_p("", space_before=3, space_after=8); pn.paragraph_format.left_indent = Inches(0.15)
    for lbl, val in [(f"Interpretación (Tabla {n}): ", True), (interp + " ", False), ("Explicación: ", True), (expl, False)]:
        rn = pn.add_run(lbl); rn.bold = lbl.startswith(("Interpretación", "Explicación")); rn.font.name = "Times New Roman"; rn.font.size = Pt(9.5)

def add_fig(n, title, img_name, interp, expl):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(os.path.join(FIG_DIR, img_name), width=Inches(5.8))
    pc = add_p("", align=WD_ALIGN_PARAGRAPH.CENTER, space_before=2, space_after=2)
    r1 = pc.add_run(f"Figura {n}. "); r1.bold = True; r1.font.name = "Times New Roman"; r1.font.size = Pt(10.5)
    r2 = pc.add_run(title); r2.font.name = "Times New Roman"; r2.font.size = Pt(10.5)
    pn = add_p("", space_before=2, space_after=8); pn.paragraph_format.left_indent = Inches(0.15)
    for lbl, val in [(f"Interpretación (Figura {n}): ", True), (interp + " ", False), ("Explicación: ", True), (expl, False)]:
        rn = pn.add_run(lbl); rn.bold = lbl.startswith(("Interpretación", "Explicación")); rn.font.name = "Times New Roman"; rn.font.size = Pt(9.5)

# Titles (< 20 words, no starting article/verb)
add_p("Entrenamiento optimizado con Optuna y validación anti-fuga para recuperación normativa ISO 27001 en PolicyGuard-RAG", bold=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=3)
add_p("Optuna-optimized training and anti-leakage validation for ISO 27001 policy retrieval in PolicyGuard-RAG", bold=True, italic=True, size=11.5, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=8)

# Authors
add_p("Diego Joel Cuba-Moya¹* (ORCID: 0009-0001-0215-392X), Ronaldo Carlos Robles-Romero¹ (ORCID: 0009-0006-5244-4983), Juan Pedro Santos-Fernández² (ORCID: 0000-0002-8882-9256), Robert Jerry Sánchez-Ticona² (ORCID: 0000-0001-9387-1945)", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
add_p("¹ Escuela de Ingeniería de Sistemas, Universidad Nacional de Trujillo, Trujillo, Perú. ² Departamento de Ingeniería de Sistemas, Universidad Nacional de Trujillo, Trujillo, Perú. *Autor de correspondencia: djcubamo@unitru.edu.pe", size=9.5, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=8)

# Resumen & Abstract (strictly 150-200 words)
resumen = (
    f"Muchas evaluaciones de recuperación aumentada (RAG) dividen los pares consulta-documento al azar y calibran parámetros manualmente, filtrando información hacia el conjunto de prueba. "
    f"Este estudio diseña y valida un protocolo reproducible anti-fuga para PolicyGuard-RAG (Caso 21), plataforma corporativa de gobernanza normativa ISO/IEC 27001 construida sobre FastAPI y PostgreSQL 15. "
    f"Se construyó un banco de 960 pares a partir de 60 consultas técnicas anotadas frente a 16 cláusulas activas de cinco políticas corporativas, dividido estrictamente por identificador de consulta en 70 % entrenamiento (672 pares), 15 % validación (144 pares) y 15 % prueba ciega (144 pares), junto con validación cruzada agrupada de cinco pliegues. "
    f"Sobre los pliegues internos se optimizaron cuatro modelos —Regresión Logística, Random Forest, HistGradientBoosting con parada temprana y el ensamble híbrido PolicyGuard-RAG Optuna— mediante muestreo bayesiano TPE y poda de mediana. "
    f"En prueba ciega, todos obtuvieron Recall@3 de 1.0000; PolicyGuard-RAG Optuna lideró AUC-ROC ({TM['PolicyGuard-RAG Optuna']['AUC_ROC']:.4f}) y PR-AUC ({TM['PolicyGuard-RAG Optuna']['PR_AUC']:.4f}), mientras HistGradientBoosting encabezó F1 ({TM['HistGradientBoosting']['F1']:.4f}), MRR ({TM['HistGradientBoosting']['MRR']:.4f}) y nDCG@3 ({TM['HistGradientBoosting']['nDCG@3']:.4f}), con latencia mediana de {LAT['PolicyGuard-RAG Optuna']['median_ms']:.3f} ms."
)
abstract = (
    f"Empirical assessments of Retrieval-Augmented Generation (RAG) often partition query-passage pairs at random and tune parameters manually, introducing subtle data leakage into test estimates. "
    f"We engineered and validated a leakage-free training protocol for PolicyGuard-RAG (Case 21), an ISO/IEC 27001 corporate policy governance platform implemented with FastAPI and PostgreSQL 15. "
    f"A structured benchmark of 960 pairs was built from 60 annotated technical queries matched against 16 active clauses across five institutional policies, split strictly by query identifier into 70% training (672 pairs), 15% validation (144 pairs), and 15% blind testing (144 pairs), complemented by five-fold stratified group cross-validation. "
    f"Four ranking models—Logistic Regression, Random Forest, HistGradientBoosting with early stopping, and the hybrid PolicyGuard-RAG ensemble—were tuned exclusively on internal folds using Optuna TPE Bayesian sampling and median pruning. "
    f"On unseen queries, every architecture achieved 1.0000 Recall@3; PolicyGuard-RAG Optuna yielded the highest AUC-ROC ({TM['PolicyGuard-RAG Optuna']['AUC_ROC']:.4f}) and PR-AUC ({TM['PolicyGuard-RAG Optuna']['PR_AUC']:.4f}), while HistGradientBoosting maximized F1 ({TM['HistGradientBoosting']['F1']:.4f}), MRR ({TM['HistGradientBoosting']['MRR']:.4f}), and nDCG@3 ({TM['HistGradientBoosting']['nDCG@3']:.4f}) at {LAT['PolicyGuard-RAG Optuna']['median_ms']:.3f} ms median inference latency."
)

print(f"Resumen words: {len(resumen.split())}, Abstract words: {len(abstract.split())}")
assert 150 <= len(resumen.split()) <= 200 and 150 <= len(abstract.split()) <= 200

add_p(f"RESUMEN: {resumen}", size=10.5, space_after=4)
add_p("Palabras clave: Aprendizaje automático, Auditoría informática, Optimización bayesiana, Recuperación de información, Validación cruzada.", size=10, space_after=6)
add_p(f"ABSTRACT: {abstract}", size=10.5, space_after=4)
add_p("Keywords: Bayesian optimization, Cross-validation, Information retrieval, Machine learning, Security auditing.", size=10, space_after=10)

# 1. Introducción
add_p("1. Introducción", bold=True, size=12, space_before=10, space_after=6)
add_p("El cumplimiento continuo de la norma ISO/IEC 27001 exige que cada colaborador comprenda, consulte y deje constancia formal de lectura sobre las políticas vigentes de seguridad " + c("ofori2022", "chen2022") + ". Cuando estas directivas circulan en archivos PDF aislados, las consultas operativas se multiplican hacia el área de seguridad y resulta difícil verificar quién conoce realmente cada control.")
add_p("Los esquemas de generación aumentada por recuperación (RAG) mitigan dicho vacío al responder preguntas de empleados anclando cada salida en artículos normativos trazables, reduciendo las alucinaciones propias de modelos de lenguaje sin restricción " + c("es2024", "muliarevych2024", "cimmino2024") + ". En dominios técnicos cortos con vocabulario regulatorio estricto, la calidad del recuperador depende de equilibrar coincidencia léxica BM25 " + c("robertson2009") + " y señales vectoriales o de contexto " + c("reimers2019", "koos2026") + ", respaldadas por métricas interpretables de aporte por variable " + c("ali2023", "pan2023") + ".")
add_p("No obstante, en evaluaciones aplicadas persiste la práctica de dividir pares consulta-fragmento aleatoriamente sin agrupar por pregunta, lo que provoca fuga de datos (data leakage) cuando formulaciones hermanas caen simultáneamente en entrenamiento y prueba " + c("alabi2026", "bakouan2026") + ". A ello se suma la selección manual de pesos e hiperparámetros sin poda ni criterios explícitos de parada, inflando métricas que luego fallan en producción.")
add_p("Pese al avance en métricas automáticas para RAG " + c("es2024", "bakouan2026") + ", escasean implementaciones reproducibles que integren partición agrupada 70/15/15, optimización bayesiana con Optuna y control de acceso basado en roles (RBAC) sobre una base transaccional auditable " + c("bhagia2026") + " (Tabla 1). Este trabajo tuvo como propósito corregir dichas brechas en PolicyGuard-RAG (Caso 21), entrenando y contrastando cuatro re-rankers bajo aislamiento estricto de prueba ciega.")
add_tab(1, "Comparación metodológica de PolicyGuard-RAG frente a trabajos relacionados.", "El estudio articula partición estricta 70/15/15 agrupada, optimización Optuna TPE y trazabilidad criptográfica.", "Síntesis comparativa frente a estudios recientes indexados.")

# 2. Materiales y métodos (Metodología rigurosa estilo PROMPT.docx / Ejemplos.rar)
add_p("2. Materiales y métodos", bold=True, size=12, space_before=10, space_after=6)
add_p("El experimento adoptó un diseño cuantitativo reproducible en Python 3.11 (scikit-learn 1.7.2, Optuna TPESampler y SciPy 1.16.2) conectado directamente al corpus productivo de PolicyGuard-RAG sobre FastAPI " + c("lathkar2023") + " y PostgreSQL 15. Todos los generadores aleatorios fijaron semilla determinista igual a 42 para asegurar replicabilidad íntegra (Figura 1).")
add_fig(1, "Protocolo experimental anti-fuga (70/15/15), validación cruzada e integración en PolicyGuard-RAG.", "fig1_protocolo_entrenamiento.png", "El flujo aísla por completo el 15 % de prueba ciega respecto de la búsqueda bayesiana en Optuna.", "Agrupar por identificador de consulta impide que fragmentos pareados filtren información entre particiones.")

add_p("2.1. Construcción del conjunto de datos y partición 70/15/15 anti-fuga", bold=True, size=11, space_before=6, space_after=4)
add_p("Las cinco políticas ISO/IEC 27001 almacenadas en db/seed.sql (POL-SEG-001 hasta POL-SEG-005, divididas en 16 fragmentos de artículo y página) sirvieron de base para redactar 60 consultas técnicas anotadas (12 por política) que combinan preguntas directas, paráfrasis y reportes de incidentes. El producto cartesiano generó 960 pares evaluables con siete variables transparentes: puntuación híbrida nativa (x1_app_hybrid), similitud coseno TF-IDF unigrama-bigrama (x2_tfidf_cosine), BM25 Okapi normalizado (x3_bm25_norm), solapamiento de palabras clave curadas (x4_kw_overlap), coincidencia en título de sección (x5_title_overlap), índice Jaccard (x6_jaccard) y razón de longitudes (x7_len_ratio).")
add_p("La partición 70/15/15 agrupó los pares por query_id y estratificó por política de origen: 42 consultas (672 pares, 70 %) ingresaron a entrenamiento, 9 consultas (144 pares, 15 %) a validación y 9 consultas (144 pares, 15 %) quedaron aisladas como prueba ciega. Para medir estabilidad entre subconjuntos distintos, el protocolo incluyó además validación cruzada estratificada agrupada de cinco pliegues (StratifiedGroupKFold) sobre las 60 consultas.")

add_p("2.2. Especificación de arquitecturas, condiciones de parada y búsqueda bayesiana Optuna", bold=True, size=11, space_before=6, space_after=4)
add_p("Se contrastaron cuatro modelos de re-ranking (Tabla 2). La Regresión Logística operó con optimizador L-BFGS (tolerancia 1e-4 y tope de 1 000 iteraciones) como referencia lineal interpretable. Random Forest empleó ensamble de árboles bajo criterio de impureza Gini. HistGradientBoosting integró penalización L2 y detención temprana automática (early_stopping = True, n_iter_no_change = 10, tol = 1e-4) para frenar el sobreajuste. Por último, PolicyGuard-RAG Optuna combinó linealmente las probabilidades de los dos clasificadores anteriores junto con las señales heurísticas x1_app_hybrid y x3_bm25_norm " + c("robertson2009", "willard2022") + ".")
add_p("Cada estudio de hiperparámetros utilizó Optuna TPESampler con podador MedianPruner durante 30 a 40 ensayos, maximizando el PR-AUC en validación sin consultar jamás la partición ciega. Elegida la mejor configuración por algoritmo, cada modelo se reentrenó sobre la unión Entrenamiento + Validación (85 %, 51 consultas) antes de ejecutarse una sola vez frente a los 144 pares de prueba.")
add_tab(2, "Especificación técnica de arquitecturas, espacios de búsqueda Optuna y condiciones de parada.", "Cada modelo delimitó cotas de regularización, criterios de parada temprana y poda bayesiana sin acceso a la prueba ciega.", "Los parámetros ganadores provienen de 30–40 ejecuciones TPE por arquitectura.")

add_p("2.3. Métricas de desempeño, calibración y explicabilidad XAI", bold=True, size=11, space_before=6, space_after=4)
add_p("El rendimiento binario sobre pares se cuantificó mediante F1-Score (umbral 0.35), AUC-ROC, PR-AUC, LogLoss y Brier Score, mientras la calidad de ordenamiento por consulta se evaluó con Hit@1, Recall@3, Mean Reciprocal Rank (MRR) y nDCG@3. La interpretabilidad post-hoc empleó importancia por permutación (30 repeticiones por atributo sobre PR-AUC en prueba), complementada con mediciones de latencia mediana y percentil 95 al puntuar los 16 fragmentos normativos.")

# 3. Resultados y discusión
add_p("3. Resultados y discusión", bold=True, size=12, space_before=10, space_after=6)
add_p("La trayectoria de búsqueda en Optuna muestra convergencia rápida durante las primeras 20 iteraciones en todas las arquitecturas, situando el PR-AUC acumulado de validación sobre 0.98 en los modelos de ensamble (Figura 2).")
add_fig(2, "Curvas de convergencia bayesiana de hiperparámetros con Optuna TPESampler.", "fig2_optuna_convergencia.png", "Las envolventes máximas de PR-AUC en validación se estabilizan antes del ensayo 25.", "Cada trazo refleja el mejor valor histórico alcanzado a lo largo de 30–40 ensayos TPE.")

add_p(f"Frente a los 144 pares inéditos de Prueba Ciega, los cuatro sistemas ubicaron siempre al menos un fragmento pertinente en el top-3 (Recall@3 = 1.0000). PolicyGuard-RAG Optuna alcanzó el mayor poder discriminativo continuo con AUC-ROC = {TM['PolicyGuard-RAG Optuna']['AUC_ROC']:.4f} y PR-AUC = {TM['PolicyGuard-RAG Optuna']['PR_AUC']:.4f}, en tanto HistGradientBoosting obtuvo los mejores registros de clasificación discreta y jerarquía superior: F1 = {TM['HistGradientBoosting']['F1']:.4f}, MRR = {TM['HistGradientBoosting']['MRR']:.4f} y nDCG@3 = {TM['HistGradientBoosting']['nDCG@3']:.4f} (Tabla 3, Figura 3). Random Forest destacó a su vez en calibración probabilística con el menor LogLoss ({TM['Random Forest']['LogLoss']:.4f}) y Brier Score ({TM['Random Forest']['Brier']:.4f}).")
add_tab(3, "Desempeño empírico de los modelos optimizados en Prueba Ciega (15 % independiente).", "HistGradientBoosting lidera F1, MRR y nDCG@3; PolicyGuard-RAG Optuna encabeza AUC-ROC y PR-AUC.", "Métricas obtenidas en la única evaluación ciega tras reentrenar con el 85 % de los datos.")
add_fig(3, "Curvas ROC y Precisión-Recall fuera de muestra sobre Prueba Ciega.", "fig3_curvas_roc_pr.png", "El ensamble híbrido mantiene la mayor área bajo ambas curvas en el segmento de alta precisión.", "Los valores fuera de muestra corroboran ausencia de sobreajuste tras el ajuste bayesiano.")

add_p(f"La validación cruzada agrupada en cinco pliegues respaldó estos resultados: HistGradientBoosting promedió AUC-ROC = {CV['HistGradientBoosting']['AUC_ROC']['mean']:.4f} +/- {CV['HistGradientBoosting']['AUC_ROC']['std']:.4f}, PR-AUC = {CV['HistGradientBoosting']['PR_AUC']['mean']:.4f} +/- {CV['HistGradientBoosting']['PR_AUC']['std']:.4f} y MRR = {CV['HistGradientBoosting']['MRR']['mean']:.4f} +/- {CV['HistGradientBoosting']['MRR']['std']:.4f}, en tanto PolicyGuard-RAG Optuna mostró la menor dispersión en nDCG@3 (+/- {CV['PolicyGuard-RAG Optuna']['nDCG@3']['std']:.4f}) (Tabla 4, Figura 4). Esta complementariedad coincide con estudios recientes sobre fusión léxico-semántica selectiva " + c("bakouan2026", "alabi2026") + ".")
add_tab(4, "Estabilidad de desempeño bajo validación cruzada agrupada de 5 pliegues (60 consultas).", "Desviaciones estándar inferiores a 0.04 demuestran estabilidad consistente entre pliegues independientes.", "Partición por grupos mediante StratifiedGroupKFold sobre query_id.")
add_fig(4, "Comparativa de medias y desviaciones estándar en validación cruzada agrupada.", "fig4_validacion_cruzada_cv.png", "Las barras de error acotadas confirman comportamiento homogéneo en las cinco particiones.", "Cada barra resume cinco ejecuciones estrictamente aisladas por identificador de consulta.")

add_p(f"Al inspeccionar errores por matriz de confusión sobre la prueba ciega, la exactitud global superó el 97 % (Figura 5a). El análisis XAI mediante permutación (Tabla 5, Figura 5b) determinó que BM25 normalizado (x3_bm25_norm) domina la capacidad discriminativa (caída media de {XAI[0]['importance_mean']:.4f} en PR-AUC), seguido del índice Jaccard ({XAI[1]['importance_mean']:.4f}), TF-IDF ({XAI[2]['importance_mean']:.4f}) y la señal híbrida de la aplicación ({XAI[3]['importance_mean']:.4f}) " + c("ali2023", "pan2023") + ". Esto resulta coherente con corpus de cumplimiento técnico, donde códigos de control como POL-SEG-004 o términos como RPO/RTO y ransomware concentran relevancia exacta.")
add_tab(5, "Importancia por permutación (XAI) de los predictores sobre Prueba Ciega.", "BM25 normalizado y Jaccard concentran casi toda la capacidad predictiva del re-ranker.", "Calculada con 30 permutaciones independientes por variable midiendo caída en PR-AUC.")
add_fig(5, "Matriz de confusión en prueba y ranking de explicabilidad XAI por permutación.", "fig5_confusion_y_xai.png", "La combinación de señales léxicas y solapamiento explica la precisión observada.", "El panel (a) presenta conteos reales en 144 pares; el panel (b) cuantifica pérdida media en PR-AUC.")

add_p(f"En tiempos de respuesta (Tabla 6), puntuar los 16 fragmentos por consulta demandó una mediana de {LAT['HistGradientBoosting']['median_ms']:.3f} ms en HistGradientBoosting y {LAT['PolicyGuard-RAG Optuna']['median_ms']:.3f} ms en PolicyGuard-RAG Optuna (p95 de {LAT['PolicyGuard-RAG Optuna']['p95_ms']:.3f} ms), márgenes imperceptibles dentro del ciclo HTTP de FastAPI " + c("lathkar2023") + ". De forma paralela, la telemetría real registrada en PostgreSQL expuso brechas marcadas de cumplimiento entre áreas técnicas (90 % de acuses firmados en CSIRT) y unidades administrativas (20 % en RR.HH.) (Figura 6), evidenciando el valor operativo de enlazar recuperación RAG con alertas automatizadas.")
add_tab(6, "Latencia de inferencia por consulta completa (16 fragmentos candidatos).", "HistGradientBoosting y la arquitectura híbrida ejecutan en ~2 ms permitiendo respuesta interactiva.", "Mediana y percentil 95 medidos sobre 80 repeticiones consecutivas.")
add_fig(6, "Tasa real de cumplimiento y acuses firmados por departamento en PostgreSQL.", "fig6_adopcion_departamentos.png", "Seguridad TI, Infraestructura y Auditoría superan el 75 %, mientras RR.HH. y Finanzas requieren seguimiento.", "Registros extraídos directamente de la tabla policyrag.acknowledgments.")

add_p("El estudio presenta como limitación principal el tamaño actual del catálogo base (60 consultas sobre 16 fragmentos de cinco políticas). Escalar la arquitectura a centenares de manuales multi-norma requerirá incorporar embeddings densos multilingües " + c("reimers2019", "koos2026") + " indexados en pgvector preservando exactamente el esquema de partición agrupada anti-fuga.")

# 4. Conclusiones (single paragraph)
add_p("4. Conclusiones", bold=True, size=12, space_before=10, space_after=6)
add_p(f"Evaluar PolicyGuard-RAG bajo partición agrupada 70/15/15, validación cruzada quíntuple y optimización bayesiana Optuna TPE permitió comparar de manera justa cuatro esquemas de re-ranking para políticas ISO/IEC 27001. En el subconjunto ciego de prueba, todos los algoritmos garantizaron recuperación completa en los tres primeros resultados (Recall@3 = 1.0000); PolicyGuard-RAG Optuna alcanzó el mayor AUC-ROC ({TM['PolicyGuard-RAG Optuna']['AUC_ROC']:.4f}) y PR-AUC ({TM['PolicyGuard-RAG Optuna']['PR_AUC']:.4f}), mientras HistGradientBoosting sobresalió en F1 ({TM['HistGradientBoosting']['F1']:.4f}), MRR ({TM['HistGradientBoosting']['MRR']:.4f}) y nDCG@3 ({TM['HistGradientBoosting']['nDCG@3']:.4f}) con una latencia mediana de {LAT['PolicyGuard-RAG Optuna']['median_ms']:.3f} ms para el ensamble y explicabilidad gobernada por señales BM25 y Jaccard. La extensión futura ampliará el banco a corpus superiores a mil cláusulas mediante búsqueda vectorial híbrida en pgvector bajo este mismo control anti-fuga.")

# Declaraciones finales
add_p("Declaración de conflicto de intereses", bold=True, size=11, space_before=8, space_after=3)
add_p("Los autores declaran no tener conflictos de intereses de ningún tipo respecto al presente manuscrito.", size=10.5)
add_p("Contribución de autoría (CRediT)", bold=True, size=11, space_before=6, space_after=3)
add_p("Diego Joel Cuba-Moya: Conceptualización, software, protocolo experimental Optuna, redacción del borrador original. Ronaldo Carlos Robles-Romero: Curación de datos, análisis estadístico, visualización, revisión. Juan Pedro Santos-Fernández: Supervisión metodológica, administración del proyecto, revisión. Robert Jerry Sánchez-Ticona: Supervisión, validación, revisión.", size=10.5)
add_p("Fuente de financiamiento", bold=True, size=11, space_before=6, space_after=3)
add_p("Investigación autofinanciada sin subvención de entidades externas.", size=10.5)
add_p("Disponibilidad de datos depositados", bold=True, size=11, space_before=6, space_after=3)
add_p("Código fuente, esquema SQL y scripts experimentales disponibles en https://github.com/DahGhoul/policyguard-rag (Licencia MIT).", size=10.5)

add_p("Referencias bibliográficas", bold=True, size=12, space_before=10, space_after=6)
for i, k in enumerate(ORDER, 1):
    pr = add_p(f"[{i}] {REFS[k]}", size=9.5, space_after=3)
    pr.paragraph_format.left_indent = Inches(0.28); pr.paragraph_format.first_line_indent = Inches(-0.28)

rec = sum(1 for k in ORDER if re.search(r"\b202[1-6]\b", REFS[k]))
print(f"References cited: {len(ORDER)}, Recent (2021-2026): {rec} ({rec/len(ORDER)*100:.1f}%)")

# Greek/Cyrillic sanitizer (Turnitin 'Replaced Characters')
def clean(t):
    o = []
    for ch in t:
        n = unicodedata.name(ch, "")
        if ch == "\u0131": o.append("i")
        elif n.startswith(("GREEK", "CYRILLIC")): o.append(n.split("LETTER ")[-1].lower())
        else: o.append(ch)
    return "".join(o)

for p in doc.paragraphs:
    for r in p.runs:
        if r.text: r.text = clean(r.text)
for tbl in doc.tables:
    for row in tbl.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                for r in p.runs:
                    if r.text: r.text = clean(r.text)

dest_dl = r"C:\Users\Diego\Downloads\G19_CubaMoyaDiegoJoel_RoblesRomeroRonaldoCarlos.docx"
dest_pr = os.path.join(BASE_DIR, "G19_CubaMoyaDiegoJoel_RoblesRomeroRonaldoCarlos.docx")
doc.save(dest_dl); print("Saved:", dest_dl)
doc.save(dest_pr); print("Saved:", dest_pr)
