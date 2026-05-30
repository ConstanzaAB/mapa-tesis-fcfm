import requests
from bs4 import BeautifulSoup
import json
import spacy
from collections import defaultdict
import time
import unicodedata
import random
import os
from langdetect import detect, DetectorFactory
import spacy


# ==============================================================================
# CONFIGURACIÓN DEL SISTEMA Y BASE DE DATOS
# ==============================================================================
DB_FILE = "bd_tesis.json"  
LIMITE_NUEVAS = 2000      

URL_PREGRADO = "https://repositorio.uchile.cl/handle/2250/100026/browse?type=dateissued&sort_by=2&order=DESC"
URL_POSTGRADO = "https://repositorio.uchile.cl/handle/2250/100027/browse?type=dateissued&sort_by=2&order=DESC"
BASE_URL = "https://repositorio.uchile.cl"

# ==============================================================================
# DICCIONARIOS DE EXCLUSIÓN
# ==============================================================================

# =========================================================================
# 🛑 EXCLUSIONES ESPECÍFICAS PARA EL INGLÉS (Papers, abstracts y keywords)
# =========================================================================
EXCLUSIONES_INGLES = [
    'study', 'analysis', 'research', 'development', 'objective', 'result',
    'university', 'engineering', 'science', 'design', 'implementation', 
    'evaluation', 'model', 'system', 'case', 'application', 'project', 'work', 'methodology',
    'data', 'process', 'performance', 'based', 'approach', 'using', 'method', 
    'effect', 'impact', 'review', 'control', 'framework', 'thesis', 'proposal',
    'chapter', 'introduction', 'conclusion', 'abstract', 'summary', 
    'literature', 'background', 'future', 'proposed', 'parameter', 
    'variable', 'experiment', 'experimental', 'test', 'testing', 
    'measurement', 'comparison', 'comparative', 'state', 'art',
    'algorithm', 'technique', 'solution', 'problem', 'future work',
    'main objective'
]

# =========================================================================
# 🛑 EXCLUSIONES SIMPLES (Español - Plurales)
# =========================================================================
EXCLUSIONES_SIMPLES = [
    'tesis', 'estudio', 'estudios', 'análisis', 'investigación', 'investigaciones', 
    'desarrollo', 'desarrollos', 'objetivo', 'objetivos', 'e', 'resultado', 'resultados', 
    'facultad', 'chile', 'universidad', 'universidades', 'ingeniería', 'ingenierias', 
    'ingeniero', 'ingenieros', 'civil', 'civiles', 'ciencia', 'ciencias', 'física', 'físicas', 
    'matemática', 'matemáticas', 'fcfm', 'departamento', 'departamentos', 'propuesta', 'propuestas', 
    'diseño', 'diseños', 'implementación', 'implementaciones', 'evaluación', 'evaluaciones', 
    'modelo', 'modelos', 'sistema', 'sistemas', 'plataforma', 'plataformas', 'caso', 'casos', 
    'uso', 'usos', 'aplicación', 'aplicaciones', 'proyecto', 'proyectos', 'trabajo', 'trabajos', 
    'título', 'títulos', 'contexto', 'metodología', 'metodologias', 'año', 'años', 'forma', 'formas', 
    'manera', 'maneras', 'medio', 'medios', 'parte', 'partes', 'tipo', 'tipos', 'información', 
    'presente', 'grado', 'grados', 'enfoque', 'enfoques', 'solución', 'soluciones', 'herramienta', 
    'herramientas', 'mejor', 'mejores', 'mejora', 'mejoras', 'cliente', 'clientes', 'base', 'bases', 
    'dato', 'datos', 'proceso', 'procesos', 'servicio', 'servicios', 'empresa', 'empresas', 
    'usuario', 'usuarios', 'nivel', 'niveles', 'etapa', 'etapas', 'fase', 'fases', 'valor', 'valores', 
    'control', 'controles', 'área', 'áreas', 'operación', 'operaciones', 'plan', 'planes', 
    'estrategia', 'estrategias', 'impacto', 'impactos', 'prueba', 'pruebas', 'capítulo', 'capitulos', 
    'introducción', 'introduccion', 'conclusión', 'conclusiones', 'anexo', 'anexos', 'bibliografía', 
    'bibliografias', 'figura', 'figuras', 'tabla', 'tablas', 'ecuación', 'ecuaciones', 'índice', 
    'indices', 'glosario', 'abstract', 'resumen', 'resúmenes', 'página', 'paginas', 'sección', 
    'secciones', 'gráfico', 'graficos', 'documento', 'documentos', 'paper', 'papers', 'artículo', 
    'articulos', 'autor', 'autores', 'profesor', 'profesores', 'guía', 'guias', 'alumno', 'alumnos', 
    'estudiante', 'estudiantes', 'magíster', 'magister', 'doctorado', 'doctor', 'marco', 'teórico', 
    'teorico', 'arte', 'literatura', 'revisión', 'revision', 'variable', 'variables', 'parámetro', 
    'parametros', 'criterio', 'criterios', 'hipótesis', 'hipotesis', 'experimento', 'experimentos', 
    'ensayo', 'ensayos', 'medición', 'mediciones', 'comparación', 'comparaciones', 'problema', 
    'problemas', 'técnica', 'tecnicas', 'algoritmo', 'algoritmos', 'factor', 'factores', 'condición', 
    'condiciones', 'característica', 'caracteristicas', 'comportamiento', 'comportamientos', 
    'requerimiento', 'requerimientos', 'desempeño', 'santiago', 'valparaíso', 'valparaiso', 
    'concepción', 'concepcion', 'antofagasta', 'temuco', 'valdivia', 'rancagua', 'talca', 'iquique', 
    'serena', 'coquimbo'
]

# =========================================================================
# 🛑 EXCLUSIONES COMPUESTAS (Español - Plurales)
# =========================================================================
EXCLUSIONES_COMPUESTAS = [
    # --- Zonas y Geografía Genérica ---
    'zona norte', 'zona centro', 'zona sur', 'zona central', 'cordillera costa',
    
    # --- Solicitadas por el usuario ---
    'necesidad especifica', 'necesidades especificas', 'necesidad específica', 'necesidades específicas',
    'costos asociados', 'costo asociado', 'costos operativos', 'costo operativo', 
    'costos operacionales', 'costo operacional', 'costos totales', 'costo total',
    'objetivo estrategico', 'objetivos estrategicos', 'objetivo estratégico', 'objetivos estratégicos',
    'objetivo principal', 'objetivos principales', 'situacion actual', 'situación actual', 'objetivo planteado', 
    'objetivos planteados', 'objetivo general', 'presente memoria', 'presente estudio',
    'objetivo propuesto', 'objetivos propuestos', 'principal objetivo',
    'mercado potencial', 'nivel mundial', 'aprendizaje profundo', 'plan estratégico', 'planificación estratégica',
    'objetivo específico', 'objetivos específicos', 'aumento significativo', 'avance significativo',
    'diferencia significativa', 'diferencias significativas', 'creciente demanda',
    'electrico nacional sen', 'eléctrico nacional sen', 'alto costo', 'altos costos', 'papel crucial', 
    'desafíos significativos', 'costos marginales', 'costo marginal',
    'riesgos asociados', 'marco conceptual', 'desafíos técnicos', 'variable clave', 'variables clave',
    'alta variabilidad', 'tiempo real', 'tiempos reales', 'tiempo asociado', 'tiempos asociados',
    'decisiones estratégicas', 'decisión estratégica', 'correcto funcionamiento', 'competencia local',
    'esfuerzos totales', 'posibles efectos', 'posible efecto', 'nivel global','impacto positivo',
    'nivel nacional', 'universidad de chile', 'mejores condiciones', 'solución innovadora',
    'alta calidad', 'mejora continua', 'mejoras continuas', 'empresa chilena', 'empresas chilenas', 'desarrollo sostenible',
    'sostenibilidad ambiental', 'sostenibilidad económica', 'mercado potencial', 'mercado objetivo',
    'alta precisión', 'alta demanda', 'potenciales clientes', 'alto potencial',

    # --- Jerga de Estructura de Tesis e Investigación ---
    'toma decisiones', 'toma de decisiones', 'revision bibliografica', 'revisión bibliográfica',
    'conclusiones generales', 'conclusion general', 'conclusiones finales', 'conclusion final',
    'futuras investigaciones', 'futura investigacion', 'futuros estudios', 'futuro estudio',
    'caso estudio', 'casos estudio', 'recoleccion datos', 'recolección datos', 
    'principales resultados', 'principal resultado', 'marco referencia', 'marco de referencia',
    'marco teorico', 'marco teórico', 'estado arte', 'trabajo futuro', 'punto vista',
    'variables analizadas', 'variable analizada', 'principales factores', 'principal factor',
    'diversos factores', 'diversas variables', 'aspectos clave', 'aspecto clave', 'puntos clave', 'punto clave',
    'analisis cuantitativo', 'analisis cualitativo', 'análisis cuantitativo', 'análisis cualitativo', 'efectos causales',
    'ejecución real', 'presente trabajo','presente investigación', 'resultados obtenidos', 
    'metodología propuesta','segmento objetivo', 'metodología empleada', 'metodología utilizada',
    'presente proyecto', 'tercer año', 'caso base', 'presente tesis', 'estudio de factibilidad', 
    'base sólida', 'escala regional', 'criterios claros', 'datos históricos', 'ajuste fino',
    'introducción general', 'hipótesis trabajo', 'hipótesis de trabajo', 'método propuesto', 
    'metodo propuesto', 'resultados esperados', 'trabajo título', 'trabajo de título', 
    'memoria título', 'memoria de título', 'grado magíster', 'grado de magíster', 
    'grado doctor', 'grado de doctor', 'ingeniero civil', 'ingenieros civiles', 'ingeniería civil', 
    'ciencias físicas', 'revisión literatura', 'revisión de literatura', 'análisis resultados', 
    'análisis de resultados', 'diseño metodológico', 'diseño metodologico', 
    'materiales métodos', 'materiales y métodos', 'trabajos futuros', 'referencias bibliográficas', 
    'análisis estadístico', 'estudio comparativo', 'presente documento', 'presente artículo',
    'revisión sistemática', 'literatura existente', 'evaluación desempeño', 'evaluacion de desempeño',
    'bajos niveles', 'bajo rendimiento','bajo nivel', 'datos reales', 'modelo propuesto', 'valor actual',
    'información relevante', 'presente informe', 'estrategia del desarrollo', 'estrategia de desarrollo',
    'desarrollo futuro', 'solución propuesta', 'solución innovadora', 'solución efectiva', 'solución eficiente', 'solución sostenible',
    'estudios previos', 'información valiosa', 'proceso actual', 'principales hallazgos', 'áreas críticas',
    'mejoras significativas', 'eficiencia operativa', 'principales conclusiones', 'comprensión profunda',
    'forma manual', 'segmentos objetivos', 'futuros trabajos', 'plan operativo', 'control gestión',
    'nivel local', 'peso chileno', 'valor público', 'propiedades dinámicas', 'modelos propuestos',
    'crecimiento anual', 'resultados experimentales', 'pesos chilenos', 'caso particular',
    'escenario descrito', 'decisiones estratégicas', 'decisiones tácticas', 'decisiones informadas',
    'datos experimentales', 'contexto actual', 'análisis interno',

    # --- Relleno Corporativo / Jargon de Gestión ---
    'sector publico', 'sector público', 'sector privado', 'sector industrial',
    'ventaja competitiva', 'ventajas competitivas', 'mejora continua', 'largo plazo', 
    'corto plazo', 'mediano plazo', 'vida util', 'vida útil', 'gran importancia',
    'herramienta tecnologica', 'herramientas tecnologicas', 'herramienta tecnológica', 'herramientas tecnológicas',
    'relevancia significativa', 'gran relevancia', 'importancia significativa', 'gran cantidad',
    'desempeño operacional', 'desempeño operativo', 'desempeño general', 'buen desempeño', 'mal desempeño',
    'optimizacion procesos', 'optimización procesos', 'mayor eficiencia', 'menor costo', 'alta calidad',
    'alto nivel', 'bajo nivel', 'amplia gama', 'gran medida', 'materia primo', 'materia prima', 'costo nivelado',
    'desafio critico', 'desafío crítico', 'desafio significativo', 'gran impacto', 'mejores resultados',
    'análisis comparativo', 'análisis exhaustivo', 'resultados positivos', 'quinto año', 'cuarto año',
    'análisis detallado', 'futuras mejoras', 'capacidad instalada', 'resultado obtenido',
    'alta calidad', 'público objetivo', 'audiencia objetivo',


    # --- Filtro de Regiones Chilenas ---
    'region metropolitana', 'región metropolitana', 'region valparaiso', 'región valparaíso',
    'region antofagasta', 'región antofagasta', 'region biobio', 'región bío bío', 
    'region coquimbo', 'región coquimbo', 'region atacama', 'región de atacama', 
    'region tarapaca', 'región tarapacá', 'region araucania', 'región araucanía', 
    'region lago', 'región lago', 'region rio', 'región río', 'region magallanes', 
    'región magallanes', 'region aysen', 'región aysén', 'region maule', 'región maule', 
    'region o higgins', 'region arica', 'region nuble', 'región ñuble', 'santiago', 'chile',

    #-- Zonas y Geografía Genérica ---
    'zona norte', 'zona centro', 'zona sur', 'zona central', 'cordillera costa',
]

NORMALIZADOR_MANUAL = {
    # Estos a singular porque suenan bien:
    "modelos matemáticos": "modelo matemático",
    "evaluaciones de impacto": "evaluacion de impacto",
    "modelos predictivos": "modelo predictivo",

    # Estos a plural porque son la convención del rubro:
    "red neuronal": "redes neuronales", 
    "base de datos": "bases de datos" 
}

# ==============================================================================
# FUNCIONES DE BASE DE DATOS Y UTILIDADES
# ==============================================================================

def cargar_base_datos():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def guardar_base_datos(bd_actual):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(bd_actual, f, ensure_ascii=False, indent=2)

def es_concepto_valido(concepto):
    t_clean = concepto.strip().lower()
    if len(t_clean) <= 3 or t_clean.isdigit(): return False
    
    # =========================================================================
    # 🇨🇱 FILTRO ANTI-GEOGRAFÍA SOLITARIA
    # =========================================================================
    # Si el concepto está hecho SÓLO por combinaciones de estas palabras, se elimina.
    # Si trae cualquier otra palabra ("Recursos", "Hídricos", "Simulación"), se conserva.
    geografia_solitaria = {
        'santiago', 'chile', 'region', 'región', 'metropolitana', 
        'central', 'zona', 'norte', 'sur'
    }
    palabras_concepto = set(t_clean.split())
    
    if palabras_concepto.issubset(geografia_solitaria):
        return False # Se descarta porque es solo ruido geográfico aislado
        
    # Filtros tradicionales por lista de exclusión
    if t_clean in EXCLUSIONES_SIMPLES or t_clean in EXCLUSIONES_INGLES or t_clean in EXCLUSIONES_COMPUESTAS:
        return False

    if "rapa nui" in t_clean or "isla de pascua" in t_clean:
        if t_clean in ["geografia de rapa nui", "geografía de rapa nui"]: return True 
        return False 
        
    return True

def es_enlace_tesis(href):
    if '?' in href or '#' in href: return False
    partes = [p for p in href.split('/') if p]
    if len(partes) == 3 and partes[0] == 'handle':
        if partes[2] in ["100026", "100027"]: return False
        return True
    return False

def formatear_titulo_profesional(texto):
    conectores = {"de", "del", "a", "al", "en", "y", "o", "u", "e", "con", "por", "para", 
                  "sin", "sobre", "tras", "la", "las", "el", "los", "un", "una", "unos", "unas",
                  "of", "the", "and", "in", "to", "for", "with", "on", "at", "by", "from", "a", "an"}
    
    # 🎯 DICCIONARIO DE ACRÓNIMOS (Forzamos a que salgan en mayúscula)
    acronimos = {
        "er": "ER", "ia": "IA", "fcfm": "FCFM", "sql": "SQL", 
        "api": "API", "rna": "RNA", "svm": "SVM", "ti": "TI", "it": "IT"
    }
    
    palabras = texto.split()
    if not palabras: return ""
    
    resultado = []
    for i, palabra in enumerate(palabras):
        p_clean = palabra.lower()
        
        # 1. Si es un acrónimo conocido, lo ponemos en mayúscula sin importar su posición
        if p_clean in acronimos:
            resultado.append(acronimos[p_clean])
        # 2. Si es la primera palabra, siempre va capitalizada
        elif i == 0: 
            resultado.append(palabra.capitalize())
        # 3. Si es un conector intermedio, se queda en minúscula
        elif p_clean in conectores: 
            resultado.append(p_clean)
        # 4. El resto de palabras se capitalizan normal
        else: 
            resultado.append(palabra.capitalize())
            
    return " ".join(resultado)

def procesar_keyword_compuesto(texto_keyword):
    if "--" not in texto_keyword: return [texto_keyword]
    partes = [p.strip() for p in texto_keyword.split("--") if p.strip()]
    ciudades_chile = ["santiago", "valparaíso", "valparaiso", "concepción", "concepcion", 
                      "antofagasta", "viña del mar", "valdivia", "temuco", "talca", "rancagua"]
    tiene_chile = False
    ciudad_encontrada = None
    conceptos_puros = []
    for p in partes:
        p_lower = p.lower()
        if p_lower == "chile": tiene_chile = True
        elif p_lower in ciudades_chile: ciudad_encontrada = p.title()
        else: conceptos_puros.append(p)
    if not conceptos_puros: return partes
    concepto_base = conceptos_puros[0]
    if ciudad_encontrada: return [f"{concepto_base} en {ciudad_encontrada}"]
    elif tiene_chile: return [f"{concepto_base} en Chile"]
    return conceptos_puros

def limpiar_superposiciones(lista_conceptos):
    """
    Recibe una lista de conceptos de UNA tesis y elimina los que son 
    subcadenas redundantes de otros más largos.
    Ejemplo: ['inteligencia artificial', 'inteligencia'] -> ['inteligencia artificial']
    """
    # 1. Ordenamos de mayor a menor longitud (los más largos primero)
    conceptos_ordenados = sorted(list(set(lista_conceptos)), key=len, reverse=True)
    conceptos_limpios = []
    
    for concepto in conceptos_ordenados:
        # Verificamos si este concepto ya está contenido en alguno de los más largos
        es_subcadena = any(f" {concepto} " in f" {largo} " for largo in conceptos_limpios)
        
        if not es_subcadena:
            conceptos_limpios.append(concepto)
            
    return conceptos_limpios

# ==============================================================================
# MOTORES DE EXTRACCIÓN INCREMENTAL
# ==============================================================================

def obtener_urls_pendientes(bd_actual):
    enlaces_pendientes = {"Pregrado": [], "Postgrado": []}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    fuentes = [("Pregrado", URL_PREGRADO), ("Postgrado", URL_POSTGRADO)]
    
    for tipo, url_base in fuentes:
        print(f"🤖 Escaneando repositorio buscando nuevas tesis de {tipo}...")
        offset = 0
        while True:
            separador = "&" if "?" in url_base else "?"
            url_pagina = f"{url_base}{separador}offset={offset}"
            try:
                response = requests.get(url_pagina, headers=headers, timeout=15)
                if response.status_code != 200: break
                soup = BeautifulSoup(response.text, 'html.parser')
                tesis_en_esta_pagina = 0
                
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if es_enlace_tesis(href):
                        tesis_en_esta_pagina += 1
                        url_completa = BASE_URL + href if href.startswith('/') else href
                        
                        if url_completa not in bd_actual and url_completa not in enlaces_pendientes[tipo]:
                            enlaces_pendientes[tipo].append(url_completa)
                            if len(enlaces_pendientes[tipo]) >= LIMITE_NUEVAS: break
                            
                if len(enlaces_pendientes[tipo]) >= LIMITE_NUEVAS: break
                if tesis_en_esta_pagina == 0: break
                
                offset += 20
                time.sleep(0.1) 
            except Exception:
                break
        print(f"   ✅ Se encontraron {len(enlaces_pendientes[tipo])} URLs nuevas para descargar.")
    return enlaces_pendientes

def minar_y_actualizar_bd(enlaces_pendientes, bd_actual):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    nuevas_agregadas = 0
    
    for grado, lista_urls in enlaces_pendientes.items():
        limite = len(lista_urls)
        if limite == 0: continue
        print(f"\n🕵️‍♂️ Extrayendo datos profundos para {grado} ({limite} tesis nuevas)...")
        
        for i, url in enumerate(lista_urls):
            try:
                res = requests.get(f"{url}?show=full", headers=headers, timeout=10)
                if res.status_code != 200: continue
                inner_soup = BeautifulSoup(res.text, 'html.parser')
                palabras_clave_ficha = []
                resumen_texto = ""
                
                meta_issued = inner_soup.find("meta", {"name": "DC.date.issued"}) or inner_soup.find("meta", {"name": "DCTERMS.issued"})
                anio_real = meta_issued["content"].strip()[:4] if meta_issued and meta_issued.get("content") else "Desconocido"
                
                meta_title = inner_soup.find("meta", {"name": "DC.title"}) or inner_soup.find("meta", {"name": "DCTERMS.title"})
                titulo_real = meta_title["content"].strip() if meta_title and meta_title.get("content") else "Tesis sin título"
                
                for fila in inner_soup.find_all('tr'):
                    celdas = fila.find_all(['td', 'th'])
                    if len(celdas) >= 3:
                        campo_interno = celdas[1].get_text().strip().lower()
                        texto_celda = celdas[2].get_text().replace('\n', ' ').strip()
                        valor_real = unicodedata.normalize('NFC', texto_celda)
                        if campo_interno.startswith('dc.subject'):
                            palabras_clave_ficha.append(valor_real)
                        elif campo_interno.startswith('dc.description.abstract'):
                            resumen_texto = valor_real
                
                if palabras_clave_ficha:
                    bd_actual[url] = {"texto": " . ".join(palabras_clave_ficha), "origen": "Metadatos", "anio": anio_real, "grado": grado, "titulo": titulo_real}
                    nuevas_agregadas += 1
                elif resumen_texto:
                    bd_actual[url] = {"texto": resumen_texto, "origen": "Resumen", "anio": anio_real, "grado": grado, "titulo": titulo_real}
                    nuevas_agregadas += 1
                
                if (i + 1) % 50 == 0 or (i + 1) == limite:
                    print(f"   📊 Descargadas {i + 1} de {limite}...")
                    guardar_base_datos(bd_actual) 
                    
                time.sleep(0.3) 
            except Exception:
                continue
                
    if nuevas_agregadas > 0:
        guardar_base_datos(bd_actual)
        print(f"💾 Base de datos actualizada: {nuevas_agregadas} tesis nuevas guardadas permanentemente.")
    else:
        print("ℹ️ No se descargaron tesis nuevas en esta ejecución.")
        
    return bd_actual

# ==============================================================================
# PIPELINE NLP E INYECCIÓN DE HTML 
# ==============================================================================
# Fijamos la semilla de langdetect para que las clasificaciones sean deterministas
DetectorFactory.seed = 0

def generar_html_universal(bd_actual):
    if not bd_actual:
        print("❌ La base de datos está vacía.")
        return
    
    print(f"\n🧠 Inicializando motores bilingües de Spacy...")
    try:
        nlp_es = spacy.load("es_core_news_sm")
        nlp_en = spacy.load("en_core_web_sm")
    except Exception:
        print("❌ Error cargando modelos. Asegúrate de ejecutar:")
        print("   python -m spacy download es_core_news_sm")
        print("   python -m spacy download en_core_web_sm")
        return

    # =========================================================================
    # 🛑 FILTROS GLOBALES DE SEGURIDAD (Se aplican post-procesamiento)
    # =========================================================================
    FRASES_PROHIBIDAS = {
        'presente trabajo', 'este trabajo', 'la presente', 'presente estudio', 
        'este estudio', 'el presente', 'this thesis', 'this study', 'the present',
        'universidad chile', 'universidad de chile' 
    }

    # Estructura unificada final
    estructura_maestra = {
        "Pregrado": defaultdict(lambda: {"frecuencia_total": 0, "anios": defaultdict(int), "links": {}}),
        "Postgrado": defaultdict(lambda: {"frecuencia_total": 0, "anios": defaultdict(int), "links": {}}),
        "Ambos": defaultdict(lambda: {"frecuencia_total": 0, "anios": defaultdict(int), "links": {}})
    }
    anios_detectados = set()

    def inyectar_relacion(grado, concepto, anio, link, titulo):
        for g in [grado, "Ambos"]:
            estructura_maestra[g][concepto]["frecuencia_total"] += 1
            estructura_maestra[g][concepto]["anios"][anio] += 1
            estructura_maestra[g][concepto]["links"][link] = {"anio": anio, "titulo": titulo}

    # Bolsas de procesamiento separadas por idioma
    textos_es, metadatos_es = [], []
    textos_en, metadatos_en = [], []

    print(f"   • Clasificando documentos por idioma...")
    for url, info in bd_actual.items():
        texto = info["texto"]
        origen = info["origen"]
        anio = info["anio"]
        grado = info["grado"]
        titulo = info["titulo"]
        
        if anio != "Desconocido": anios_detectados.add(anio)

        if origen == "Metadatos":
            # 1️⃣ CAMBIO EN METADATOS: Agrupamos por tesis antes de inyectar
            conceptos_tesis = []
            for termino in texto.replace(';', ',').replace('.', ',').split(','):
                if not termino.strip(): continue
                for sub_c in procesar_keyword_compuesto(termino.strip()):
                    sub_c_clean = sub_c.strip().lower()
                    if es_concepto_valido(sub_c_clean) and sub_c_clean not in FRASES_PROHIBIDAS:
                        if not any(any(c.isdigit() for c in p) and len(p) <= 5 for p in sub_c_clean.split()):
                            # Escudo 2: NORMALIZACIÓN MANUAL INSTANTÁNEA
                            # Si la palabra está en nuestro diccionario, la reemplazamos por su valor
                            if sub_c_clean in NORMALIZADOR_MANUAL:
                                sub_c_clean = NORMALIZADOR_MANUAL[sub_c_clean]
                            conceptos_tesis.append(sub_c_clean)
            
            # Limpiamos superposiciones de las palabras clave de esta tesis
            conceptos_limpios = limpiar_superposiciones(conceptos_tesis)
            for comp in conceptos_limpios:
                inyectar_relacion(grado, formatear_titulo_profesional(comp), anio, url, titulo)
        else:
            try:
                idioma = detect(texto)
            except:
                idioma = "es"
            
            if idioma == "en":
                textos_en.append(texto)
                metadatos_en.append({"link": url, "anio": anio, "grado": grado, "titulo": titulo})
            else:
                textos_es.append(texto)
                metadatos_es.append({"link": url, "anio": anio, "grado": grado, "titulo": titulo})

    # 🇪🇸 2️⃣ CAMBIO EN PIPELINE EN ESPAÑOL: Limpieza por documento
    if textos_es:
        print(f"   • Procesando {len(textos_es)} textos en Español...")
        for idx, doc in enumerate(nlp_es.pipe(textos_es, batch_size=50, disable=["ner"])):
            meta = metadatos_es[idx]
            conceptos_tesis = [] # Bolsa temporal para esta tesis
            
            for chunk in doc.noun_chunks:
                tokens = []
                for t in chunk:
                    token_limpio = t.text.lower().strip(".,[]()\"';:-+/*_¿?¡! ")
                    if any(c.isdigit() for c in token_limpio) and len(token_limpio) <= 5: continue
                    if (not t.is_stop and len(token_limpio) > 1 and t.pos_ in ['NOUN', 'ADJ', 'PROPN']):
                        # Escudo 2: NORMALIZACIÓN MANUAL INSTANTÁNEA
                        # Si la palabra está en nuestro diccionario, la reemplazamos por su valor
                        if token_limpio in NORMALIZADOR_MANUAL:
                            token_limpio = NORMALIZADOR_MANUAL[token_limpio]
                        tokens.append(token_limpio)

                if 2 <= len(tokens) <= 4:
                    compuesto = " ".join(tokens)
                    if es_concepto_valido(compuesto) and compuesto not in FRASES_PROHIBIDAS:
                        # Escudo 2: NORMALIZACIÓN MANUAL INSTANTÁNEA
                        # Si la palabra está en nuestro diccionario, la reemplazamos por su valor
                        if compuesto in NORMALIZADOR_MANUAL:
                            compuesto = NORMALIZADOR_MANUAL[compuesto]
                        conceptos_tesis.append(compuesto)
            
            # Filtramos palabras repetidas o contenidas en frases más largas para ESTA tesis
            conceptos_limpios = limpiar_superposiciones(conceptos_tesis)
            for comp in conceptos_limpios:
                inyectar_relacion(meta["grado"], formatear_titulo_profesional(comp), meta["anio"], meta["link"], meta["titulo"])

    # 🇬🇧 3️⃣ CAMBIO EN PIPELINE EN INGLÉS: Limpieza por documento
    if textos_en:
        print(f"   • Procesando {len(textos_en)} textos en Inglés...")
        for idx, doc in enumerate(nlp_en.pipe(textos_en, batch_size=50, disable=["ner"])):
            meta = metadatos_en[idx]
            conceptos_tesis = [] # Bolsa temporal para esta tesis inglesa
            
            for chunk in doc.noun_chunks:
                tokens = []
                for t in chunk:
                    token_limpio = t.lemma_.lower().strip(".,[]()\"';:-+/*_¿?¡! ")
                    if any(c.isdigit() for c in token_limpio) and len(token_limpio) <= 5: continue
                    if (not t.is_stop and len(token_limpio) > 1 and t.pos_ in ['NOUN', 'ADJ', 'PROPN']):
                        tokens.append(token_limpio)
                
                if 2 <= len(tokens) <= 4:
                    compuesto = " ".join(tokens)
                    if es_concepto_valido(compuesto) and compuesto not in FRASES_PROHIBIDAS:
                        conceptos_tesis.append(compuesto)
            
            # Filtramos superposiciones
            conceptos_limpios = limpiar_superposiciones(conceptos_tesis)
            for comp in conceptos_limpios:
                inyectar_relacion(meta["grado"], formatear_titulo_profesional(comp), meta["anio"], meta["link"], meta["titulo"])

    # =========================================================================
    # GENERACIÓN DEL HTML (Mismo template estable con Arial que ya tienes)
    # =========================================================================
    json_maestro = json.dumps(estructura_maestra, ensure_ascii=False)
    json_anios = json.dumps(sorted(list(anios_detectados), reverse=True))

    # ⚡ FUENTE CAMBIADA A ARIAL/SANS-SERIF EN TODO EL TEMPLATE
    html_template = """<div style="padding: 40px 30px; background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%); border-radius: 20px; box-shadow: 0 20px 40px -10px rgba(0,0,0,0.1); margin: 30px auto; width: 100%; max-width: 950px; font-family: Arial, Helvetica, sans-serif; box-sizing: border-box;">
        <style>
            .botones-container { display: flex; justify-content: center; gap: 8px; margin-bottom: 25px; flex-wrap: wrap; }
            .tab-btn { padding: 10px 18px; font-weight: bold; border-radius: 8px; border: none; cursor: pointer; transition: all 0.2s; font-family: Arial, sans-serif; font-size: 14px; }
            
            #wordcloud-container {
                width: 100%; 
                aspect-ratio: 16 / 9; 
                min-height: 350px; 
                max-height: 600px;
                background: #0f172a; 
                border-radius: 16px; 
                position: relative; 
                overflow: hidden; 
                box-shadow: inset 0 4px 20px rgba(0,0,0,0.5);
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            #wordcloud-container svg { width: 100%; height: 100%; display: block; }
        </style>
        
        <div style="text-align: center; margin-bottom: 25px;">
            <h2 style="color: #0f172a; margin-top: 0; margin-bottom: 5px; font-size: clamp(24px, 4vw, 32px); font-weight: bold; letter-spacing: -1px;">Analizador Semántico de Tesis FCFM</h2>
            <h3 style="color: #3b82f6; margin-top: 0; margin-bottom: 20px; font-size: clamp(11px, 2vw, 14px); font-weight: bold; text-transform: uppercase; letter-spacing: 2px;">Universidad de Chile</h3>
            
            <div class="botones-container">
                <button class="tab-btn" onclick="cambiarGrado('Ambos', this)" style="background: #3b82f6; color: white;">🎓 Todos los Grados</button>
                <button class="tab-btn" onclick="cambiarGrado('Pregrado', this)" style="background: #cbd5e1; color: #1e293b;">📄 Pregrado</button>
                <button class="tab-btn" onclick="cambiarGrado('Postgrado', this)" style="background: #cbd5e1; color: #1e293b;">🔬 Postgrado</button>
            </div>

            <div style="display: inline-flex; gap: 15px; background: #ffffff; padding: 8px 16px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; flex-wrap: wrap; justify-content: center;">
                <div>
                    <label for="filtro-anio" style="color: #64748b; font-size: 11px; font-weight: bold; text-transform: uppercase; display:block; margin-bottom:4px;">Año:</label>
                    <select id="filtro-anio" style="padding: 6px 12px; font-size: 14px; font-weight: bold; color: #1e40af; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; cursor: pointer; outline: none; font-family: Arial, sans-serif; text-align: center; text-align-last: center;"></select>
                </div>
                <div>
                    <label for="filto-palabras" style="color: #64748b; font-size: 11px; font-weight: bold; text-transform: uppercase; display:block; margin-bottom:4px;">Palabras:</label>
                    <select id="filto-palabras" style="padding: 6px 12px; font-size: 14px; font-weight: bold; color: #1e40af; background: #fdf2f8; border: 1px solid #fbcfe8; border-radius: 6px; cursor: pointer; outline: none; font-family: Arial, sans-serif; text-align: center; text-align-last: center;">
                        <option value="30" selected>Top 30</option>
                        <option value="60">Top 60</option>
                        <option value="120">Top 120</option>
                    </select>
                </div>
            </div>
        </div>
        
        <div id="wordcloud-container"></div>

        <div id="panel-referencias" style="margin-top: 35px; padding: 30px; padding-top: 25px; background: #ffffff; border-radius: 14px; border: 1px solid #e2e8f0; display: none; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05); position: relative; box-sizing: border-box;">
            <button onclick="document.getElementById('panel-referencias').style.display='none'" style="position: absolute; top: 15px; right: 15px; background: #ef4444; color: white; border: none; border-radius: 50%; width: 28px; height: 28px; font-size: 14px; font-weight: bold; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background 0.2s;" onmouseover="this.style.background='#dc2626'" onmouseout="this.style.background='#ef4444'">&times;</button>
            <h4 style="margin-top: 5px; color: #1e293b; font-size: 18px; border-bottom: 2px solid #3b82f6; padding-bottom: 12px; margin-bottom: 20px; font-family: Arial, sans-serif;">
                📚 Tesis indexadas para: <span id="concepto-seleccionado" style="color: #2563eb; font-weight: bold;"></span>
            </h4>
            <ul id="lista-links" style="padding-left: 20px; margin-bottom: 0; line-height: 1.6; color: #475569; font-size: 14px; max-height: 300px; overflow-y: auto;"></ul>
        </div>

        <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/d3-cloud/1.2.7/d3.layout.cloud.min.js"></script>

        <script>
        setTimeout(function() {
            try {
                console.log("WordCloud: Iniciando motor JS...");
                var datosMaestros = __JSON_MAESTRO__;
                var aniosDisponibles = __JSON_ANIOS__;
                var gradoActual = "Ambos"; 
                
                var selectorAnio = document.getElementById('filtro-anio');
                var aniosNum = aniosDisponibles.map(Number).filter(n => !isNaN(n)).sort((a,b) => b-a);
                
                var optTodos = document.createElement('option');
                optTodos.value = "TODOS"; optTodos.text = "Todos los años";
                selectorAnio.appendChild(optTodos);
                
                var ultimos = aniosNum.slice(0, 8);
                ultimos.forEach(function(a) {
                    var opt = document.createElement('option');
                    opt.value = a.toString(); opt.text = a.toString();
                    selectorAnio.appendChild(opt);
                });
                
                if (aniosNum.length > 8) {
                    var umbral = aniosNum[8]; 
                    var optResto = document.createElement('option');
                    optResto.value = "<=" + umbral; 
                    optResto.text = "Histórico (Hasta " + umbral + ")";
                    selectorAnio.appendChild(optResto);
                }

                var colors = ["#38bdf8", "#34d399", "#fbbf24", "#f472b6", "#a78bfa", "#f87171", "#2dd4bf"];

                window.cambiarGrado = function(nuevoGrado, btn) {
                    gradoActual = nuevoGrado;
                    document.querySelectorAll('.tab-btn').forEach(b => { b.style.background = "#cbd5e1"; b.style.color = "#1e293b"; });
                    btn.style.background = "#3b82f6"; btn.style.color = "white";
                    document.getElementById('panel-referencias').style.display = "none";
                    procesarYRenderizar();
                }

                function procesarYRenderizar() {
                    console.log("WordCloud: Procesando grado: " + gradoActual);
                    var container = document.getElementById('wordcloud-container');
                    var anioSel = selectorAnio.value;
                    var limite = parseInt(document.getElementById('filto-palabras').value);
                    var diccionarioContexto = datosMaestros[gradoActual];
                    
                    // ESCUDO PROTECTOR
                    if (!diccionarioContexto) {
                        console.error("WordCloud: ERROR CRÍTICO. No se encontraron datos en el JSON para la categoría: " + gradoActual);
                        d3.select("#wordcloud-container").html("");
                        d3.select("#wordcloud-container").append("p")
                            .style("color", "#94a3b8").style("text-align", "center").style("font-family", "Arial, sans-serif")
                            .text("No hay datos cargados para la categoría: " + gradoActual);
                        return; 
                    }
                    
                    var dataset = [];
                    for (var palabra in diccionarioContexto) {
                        var peso = 0;
                        if (anioSel === "TODOS") {
                            peso = diccionarioContexto[palabra].frecuencia_total;
                        } else if (anioSel.startsWith("<=")) {
                            var maxVal = parseInt(anioSel.substring(2));
                            for (var a in diccionarioContexto[palabra].anios) {
                                if (parseInt(a) <= maxVal) peso += diccionarioContexto[palabra].anios[a];
                            }
                        } else {
                            if (diccionarioContexto[palabra].anios[anioSel]) peso = diccionarioContexto[palabra].anios[anioSel];
                        }
                        if (peso > 0) dataset.push({ text: palabra, size: peso });
                    }

                    dataset.sort((a,b) => b.size - a.size);
                    dataset = dataset.slice(0, limite);
                    console.log("WordCloud: Palabras filtradas para renderizar: " + dataset.length);

                    d3.select("#wordcloud-container").html("");
                    if(dataset.length === 0) {
                        d3.select("#wordcloud-container").append("p")
                            .style("color", "#64748b").style("text-align", "center").style("font-family", "Arial, sans-serif").text("No hay registros en este periodo.");
                        return;
                    }

                    var internalWidth = 1100; 
                    var internalHeight = 600; 
                    var maxVal = d3.max(dataset, d => d.size), minVal = d3.min(dataset, d => d.size);

                    dataset.forEach(function(d) {
                        d.fontSizeCalculado = maxVal === minVal ? 24 : 12 + ((d.size - minVal) / (maxVal - minVal)) * 36;
                    });

                    // CONFIGURACIÓN CORREGIDA CON fontWeight("bold")
                    var layout = d3.layout.cloud()
                        .size([internalWidth, internalHeight])
                        .words(dataset)
                        .padding(20)                    
                        .rotate(function() { return (Math.random() > 0.5 ? 0 : 90); })
                        .font("Arial")
                        .fontWeight("bold")                  
                        .fontSize(function(d) { return d.fontSizeCalculado; }) 
                        .on("end", draw);

                    layout.start();

                    function draw(words) {
                        console.log("WordCloud: Dibujando SVG...");
                        var svg = d3.select("#wordcloud-container").append("svg")
                            .attr("viewBox", "0 0 " + internalWidth + " " + internalHeight)
                            .attr("preserveAspectRatio", "xMidYMid meet")
                        .append("g")
                            .attr("transform", "translate(" + internalWidth/2 + "," + internalHeight/2 + ")");

                        svg.selectAll("text").data(words).enter().append("text")
                            .style("font-family", "Arial, sans-serif")
                            .style("font-weight", "bold")
                            .style("fill", function(d,i) { return colors[i % colors.length]; })
                            .attr("text-anchor", "middle")
                            .style("font-size", function(d) { return d.size + "px"; }) 
                            .style("cursor", "pointer")
                            .attr("transform", function(d) { return "translate(" + [d.x, d.y] + ")rotate(" + d.rotate + ")"; })
                            .text(function(d) { return d.text; })
                            .on("click", function(e, d) { mostrarEnlaces(d.text); });
                    }
                }

                function mostrarEnlaces(palabra) {
                    var info = datosMaestros[gradoActual][palabra];
                    var anioFiltro = selectorAnio.value;
                    document.getElementById('concepto-seleccionado').innerText = palabra + " (" + gradoActual + ")";
                    var ul = document.getElementById('lista-links'); ul.innerHTML = "";

                    for (var url in info.links) {
                        var objDatos = info.links[url];
                        var anioLink = objDatos.anio;
                        var tituloTesis = objDatos.titulo;
                        var anioInt = parseInt(anioLink);
                        var mostrar = false;
                        
                        if (anioFiltro === "TODOS") mostrar = true;
                        else if (anioFiltro.startsWith("<=")) {
                            var maxVal = parseInt(anioFiltro.substring(2));
                            if (anioInt <= maxVal) mostrar = true;
                        } else if (anioLink === anioFiltro) mostrar = true;

                        if (mostrar) {
                            var li = document.createElement('li');
                            li.style.marginBottom = "10px";
                            
                            var a = document.createElement('a');
                            a.href = url; a.target = "_blank"; a.style.color = "#2563eb"; a.style.fontWeight = "bold"; a.style.textDecoration = "none";
                            a.onmouseover = function() { this.style.textDecoration = 'underline'; };
                            a.onmouseout = function() { this.style.textDecoration = 'none'; };
                            a.innerText = tituloTesis + " - Año " + anioLink;
                            
                            li.appendChild(a); ul.appendChild(li);
                        }
                    }
                    document.getElementById('panel-referencias').style.display = "block";
                    document.getElementById('panel-referencias').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }

                selectorAnio.addEventListener('change', function() { procesarYRenderizar(); document.getElementById('panel-referencias').style.display = "none"; });
                document.getElementById('filto-palabras').addEventListener('change', procesarYRenderizar);
                
                procesarYRenderizar();
                
            } catch(err) { console.error("WordCloud: Error fatal en setTimeout", err); }
        }, 200);
        </script>
    </div>"""

    html_template = html_template.replace("__JSON_MAESTRO__", json_maestro).replace("__JSON_ANIOS__", json_anios)

    with open("resultado_fcfm.html", "w", encoding="utf-8") as f:
        f.write(html_template)
    print("\n✨ ¡ÉXITO! HTML estable con Arial generado para Magnolia.")


def generar_base_datos_prueba(cantidad=350):
    """
    Genera un diccionario sintético que simula perfectamente la base de datos
    de tesis reales de la FCFM para pruebas locales.
    """
    print(f"🎲 Generando {cantidad} registros de prueba artificiales...")
    
    # Repositorio de variables realistas de la FCFM
    estructuras_titulo = [
        "Optimización de {recurso} mediante {tecnica} en Chile",
        "Análisis estructural de {recurso} usando {tecnica}",
        "Diseño e implementación de un sistema basado en {tecnica} para {recurso}",
        "Evaluación del impacto de {recurso} en el ecosistema usando {tecnica}",
        "Modelamiento matemático de {recurso} aplicado a {tecnica}"
    ]
    
    recursos = [
        "redes eléctricas inteligentes", "cuencas hidrográficas en el norte", 
        "algoritmos de machine learning", "estructuras antisísmicas", 
        "procesos metalúrgicos", "redes de transporte urbano", 
        "datos astronómicos masivos", "sistemas autónomos de drones"
    ]
    
    tecnicas = [
        "aprendizaje profundo", "modelos estocásticos", "inteligencia artificial",
        "analítica de datos", "aisladores elastoméricos", "algoritmos genéticos",
        "procesamiento de lenguaje natural", "simulaciones de Montecarlo"
    ]
    
    # Palabras clave para simular la sección de "Metadatos"
    # ¡Ojo! Incluimos las palabras prohibidas a propósito para testear el filtro
    palabras_clave_pool = [
        "inteligencia artificial", "minería de datos", "optimización", "redes neuronales", 
        "cambio climático", "energías renovables", "sistemas de control", "aprendizaje profundo",
        "of the system", "presente trabajo", "este estudio", "the power grid", "ingeniería industrial"
    ]
    
    # Párrafos base para simular la extracción de "Texto Completo"
    parrafos_pool = [
        "En el presente trabajo se analiza rigurosamente el comportamiento de la infraestructura. El diseño de este estudio abarca la optimización de recursos energéticos.",
        "This thesis presents a comprehensive study of the main components of the system. We evaluate the performance and efficiency of the neural network.",
        "El objetivo principal de esta investigación es proponer un modelo predictivo eficiente para mitigar fallas operacionales en la industria minera chilena.",
        "Se presenta un marco metodológico avanzado enfocado en resolver problemas complejos de asignación de recursos mediante analítica de datos a gran escala."
    ]
    
    anios_pool = [str(anio) for anio in range(2016, 2027)] # Abarca hasta el actual 2026
    grados_pool = ["Pregrado", "Postgrado"]
    origenes_pool = ["Metadatos", "Texto Completo"]
    
    bd_sintetica = {}
    
    for i in range(cantidad):
        # Generar una URL única correlativa
        url = f"https://repositorio.uchile.cl/handle/2250/test_mock_{1000 + i}"
        
        # Armar un título aleatorio pero coherente
        titulo = random.choice(estructuras_titulo).format(
            recurso=random.choice(recursos),
            tecnica=random.choice(tecnicas)
        ) + f" (Caso de Estudio #{i})"
        
        origen = random.choice(origenes_pool)
        anio = random.choice(anios_pool)
        grado = random.choice(grados_pool)
        
        # Simular el campo 'texto' según su origen
        if origen == "Metadatos":
            # Formato clásico de palabras clave separadas por punto y coma
            texto = "; ".join(random.sample(palabras_clave_pool, k=random.randint(2, 4)))
        else:
            # Texto descriptivo largo
            texto = random.choice(parrafos_pool) + f" Datos adicionales de la muestra número {i}."
            
        bd_sintetica[url] = {
            "texto": texto,
            "origen": origen,
            "anio": anio,
            "grado": grado,
            "titulo": titulo
        }
        
    print("✅ Base de datos de prueba creada con éxito.")
    return bd_sintetica

# ==============================================================================
# EJECUCIÓN PRINCIPAL
# ==============================================================================
# ==========================================
#  ⚙️ CONFIGURACIÓN DEL SCRIPT
# ==========================================
MODO_PRUEBA = True # 💡 Ponlo en True para diseñar/probar. En False para producción.

if __name__ == "__main__":
    
    if not MODO_PRUEBA:
        print("🌐 [MODO PRODUCCIÓN] Buscando nuevos links y extrayendo información de internet...")
        print("📁 Cargando base de datos local...")
        bd_actual = cargar_base_datos()
        print(f"✅ Se encontraron {len(bd_actual)} tesis ya procesadas en tu registro.")

        urls_nuevas = obtener_urls_pendientes(bd_actual)
        bd_actual = minar_y_actualizar_bd(urls_nuevas, bd_actual)
        generar_html_universal(bd_actual)
    else:
        print("📂 [MODO PRUEBA] ¡Extracción web saltada! Cargando copia local guardada para ahorrar tiempo...")
        # Aquí simplemente lees el JSON que ya generaste ayer o en ejecuciones pasadas
        bd_actual = cargar_base_datos()
        if not bd_actual:
            print("❌ No tienes un JSON local guardado. Debes ejecutar MODO_PRUEBA=False al menos una vez.")
            bd_actual = {}
        #bd_actual = generar_base_datos_prueba(cantidad=1000)  # Genera datos de prueba sintéticos

    # Llamamos a la función del HTML pasándole el modo prueba
    generar_html_universal(bd_actual)