import requests
from bs4 import BeautifulSoup
import json
import spacy
from collections import Counter, defaultdict
import time
import unicodedata

# ==============================================================================
# CONFIGURACIÓN DE COLECCIONES REALES (Paginación Infinita)
# ==============================================================================
# Cambiamos recent-submissions por browse?type=dateissued para evitar el límite del servidor
URL_PREGRADO = "https://repositorio.uchile.cl/handle/2250/100026/browse?type=dateissued"
URL_POSTGRADO = "https://repositorio.uchile.cl/handle/2250/100027/browse?type=dateissued"
BASE_URL = "https://repositorio.uchile.cl"

# ⏱️ CONTROL DE TIEMPO: Limita la cantidad de tesis a procesar por categoría.
# 2000 por grado (4000 total) tomará aproximadamente 30-45 minutos.
LIMITE_POR_GRADO = 2000

EXCLUSIONES_SIMPLES = [
        'tesis', 'estudio', 'análisis', 'investigación', 'desarrollo', 'objetivo', 'e',
        'resultado', 'resultados', 'facultad', 'chile', 'universidad', 'ingeniería', 
        'ingeniero', 'civil', 'ciencias', 'físicas', 'matemáticas', 'fcfm', 'departamento',
        'propuesta', 'diseño', 'implementación', 'evaluación', 'modelo', 'sistema', 'plataforma',
        'caso', 'uso', 'aplicación', 'proyecto', 'trabajo', 'título', 'contexto', 'metodología',
        'año', 'años', 'forma', 'manera', 'medio', 'parte', 'tipo', 'información', 'presente',
        'grados', 'metodologias', 'enfoque', 'solución', 'herramienta', 'herramientas',
        'mejor', 'mejora', 'cliente', 'clientes', 'base', 'bases', 'dato', 'datos', 
        'proceso', 'procesos', 'servicio', 'servicios', 'empresa', 'empresas', 'usuario',
        'usuarios', 'nivel', 'niveles', 'etapa', 'etapas', 'fase', 'fases', 'valor', 'control',
        'área', 'áreas', 'operación', 'operaciones', 'plan', 'estrategia', 'impacto'
]

EXCLUSIONES_COMPUESTAS = [
    # --- Zonas y Geografía Genérica ---
    'zona norte', 'zona centro', 'zona sur', 'zona central', 'cordillera costa',
    
    # --- Solicitadas por el usuario (Variaciones + Plurales + Tildes) ---
    'necesidad especifica', 'necesidades especificas', 'necesidad específica', 'necesidades específicas',
    'costos asociados', 'costo asociado', 'costos operativos', 'costo operativo', 
    'costos operacionales', 'costo operacional', 'costos totales', 'costo total',
    'objetivo estrategico', 'objetivos estrategicos', 'objetivo estratégico', 'objetivos estratégicos',
    'situacion actual', 'situación actual', 'objetivo planteado', 'objetivos planteados',
    'objetivo específico', 'objetivos específicos', 'aumento significativo', 'avance significativo',
    'diferencia significativa', 'diferencias significativas', 'creciente demanda',
    'electrico nacional sen', 'eléctrico nacional sen', 'alto costo', 'altos costos', 'papel crucial', 
    'desafíos significativos', 'planificación estratégica', 'costos marginales', 'costo marginal',
    'riesgos asociados', 'marco conceptual', 'desafíos técnicos', 'variable clave', 'variables clave',
    'alta variabilidad', 'tiempo real', 'tiempos reales', 'tiempo asociado', 'tiempos asociados',
    'decisiones estratégicas', 'decisión estratégica', 'correcto funcionamiento', 'competencia local',
    'esfuerzos totales', 'posibles efectos', 'posible efecto'

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
    'ejecución real'

    # --- Relleno Corporativo / Jargon de Gestión ---
    'sector publico', 'sector público', 'sector privado', 'sector industrial',
    'ventaja competitiva', 'ventajas competitivas', 'mejora continua', 'largo plazo', 
    'corto plazo', 'mediano plazo', 'vida util', 'vida útil', 'gran importancia',
    'herramienta tecnologica', 'herramientas tecnologicas', 'herramienta tecnológica', 'herramientas tecnológicas',
    'relevancia significativa', 'gran relevancia', 'importancia significativa', 'gran cantidad',
    'desempeño operacional', 'desempeño operativo', 'desempeño general', 'buen desempeño', 'mal desempeño',
    'optimizacion procesos', 'optimización procesos', 'mayor eficiencia', 'menor costo', 'alta calidad',
    'alto nivel', 'bajo nivel', 'amplia gama', 'gran medida', 'materia primo', 'materia prima', 'costo nivelado',
    'desafio critico', 'desafío crítico', 'desafio significativo', 'desafío significativo', 'gran impacto',

    # --- Filtro de Regiones Chilenas (Aisladas post-stopwords) ---
    'region metropolitana', 'región metropolitana', 'region valparaiso', 'región valparaíso',
    'region antofagasta', 'región antofagasta', 'region biobio', 'región bío bío', 
    'region coquimbo', 'región coquimbo', 'region atacama', 'región de atacama', 
    'region tarapaca', 'región tarapacá', 'region araucania', 'región araucanía', 
    'region lagos', 'región lagos', 'region rios', 'región ríos', 'region magallanes', 
    'región magallanes', 'region aysen', 'región aysén', 'region maule', 'región maule', 
    'region o higgins', 'region arica', 'region nuble', 'región ñuble'
]

# ==============================================================================
# FUNCIONES DE FORMATEO Y VALIDACIÓN
# ==============================================================================

def es_concepto_valido(concepto):
    t_clean = concepto.strip().lower()
    if len(t_clean) <= 3 or t_clean.isdigit(): return False
    if t_clean in EXCLUSIONES_SIMPLES or t_clean in EXCLUSIONES_COMPUESTAS: return False
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
                  "sin", "sobre", "tras", "la", "las", "el", "los", "un", "una", "unos", "unas"}
    palabras = texto.split()
    if not palabras: return ""
    resultado = []
    for i, palabra in enumerate(palabras):
        p_clean = palabra.lower()
        if i == 0: resultado.append(palabra.capitalize())
        elif p_clean in conectores: resultado.append(p_clean)
        else: resultado.append(palabra.capitalize())
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

# ==============================================================================
# MOTORES DE EXTRACCIÓN
# ==============================================================================

def extraer_enlaces_con_limite():
    enlaces_por_grado = {"Pregrado": [], "Postgrado": []}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    fuentes = [("Pregrado", URL_PREGRADO), ("Postgrado", URL_POSTGRADO)]
    
    for tipo, url_base in fuentes:
        print(f"🤖 Buscando tesis de {tipo} (Máximo {LIMITE_POR_GRADO} para ahorrar tiempo)...")
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
                        if url_completa not in enlaces_por_grado[tipo]:
                            enlaces_por_grado[tipo].append(url_completa)
                            if len(enlaces_por_grado[tipo]) >= LIMITE_POR_GRADO: break
                if len(enlaces_por_grado[tipo]) >= LIMITE_POR_GRADO:
                    print(f"   🛑 Se alcanzó el límite de {LIMITE_POR_GRADO} para {tipo}.")
                    break
                if tesis_en_esta_pagina == 0: break
                offset += 20
                time.sleep(0.2)
            except Exception as e:
                break
        print(f"   ✅ Total {tipo} a descargar: {len(enlaces_por_grado[tipo])} URLs.")
    return enlaces_por_grado

def minar_bloque_total(diccionario_urls):
    datos_estructurados = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    for grado, lista_urls in diccionario_urls.items():
        limite = len(lista_urls)
        if limite == 0: continue
        print(f"\n🕵️‍♂️ Extrayendo metadatos profundos para {grado} ({limite} tesis)...")
        for i, url in enumerate(lista_urls):
            try:
                res = requests.get(f"{url}?show=full", headers=headers, timeout=10)
                if res.status_code != 200: continue
                inner_soup = BeautifulSoup(res.text, 'html.parser')
                palabras_clave_ficha = []
                resumen_texto = ""
                
                # Extracción de Año
                meta_issued = inner_soup.find("meta", {"name": "DC.date.issued"}) or inner_soup.find("meta", {"name": "DCTERMS.issued"})
                anio_real = meta_issued["content"].strip()[:4] if meta_issued and meta_issued.get("content") else "Desconocido"
                
                # Extracción de Título
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
                    datos_estructurados.append({"texto": " . ".join(palabras_clave_ficha), "origen": "Metadatos", "url": url, "anio": anio_real, "grado": grado, "titulo": titulo_real})
                elif resumen_texto:
                    datos_estructurados.append({"texto": resumen_texto, "origen": "Resumen", "url": url, "anio": anio_real, "grado": grado, "titulo": titulo_real})
                
                if (i + 1) % 100 == 0 or (i + 1) == limite:
                    print(f"   📊 Procesadas {i + 1} de {limite} en {grado}...")
                time.sleep(0.2)
            except Exception:
                continue
    return datos_estructurados

# ==============================================================================
# PIPELINE NLP E INYECCIÓN DE HTML INTERACTIVO (CON FILTRO OPTIMIZADO)
# ==============================================================================

def generar_html_universal():
    dict_enlaces = extraer_enlaces_con_limite()
    datos_totales = minar_bloque_total(dict_enlaces)
    if not datos_totales: return
    
    print(f"\n🧠 Analizando conceptualmente con Spacy...")
    try:
        nlp = spacy.load("es_core_news_sm")
    except Exception:
        print("❌ Instala el modelo: python -m spacy download es_core_news_sm")
        return

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

    print(f"   • Mapeando y validando matriz...")
    textos_para_nlp = []
    metadatos_nlp = []

    for item in datos_totales:
        texto = item["texto"]
        origen = item["origen"]
        link = item["url"]
        anio = item["anio"]
        grado = item["grado"]
        titulo = item["titulo"]
        
        if anio != "Desconocido": anios_detectados.add(anio)

        if origen == "Metadatos":
            for termino in texto.replace(';', ',').replace('.', ',').split(','):
                if not termino.strip(): continue
                for sub_c in procesar_keyword_compuesto(termino.strip()):
                    if es_concepto_valido(sub_c):
                        inyectar_relacion(grado, formatear_titulo_profesional(sub_c.strip().lower()), anio, link, titulo)
        else:
            textos_para_nlp.append(texto)
            metadatos_nlp.append({"link": link, "anio": anio, "grado": grado, "titulo": titulo})

    if textos_para_nlp:
        for idx, doc in enumerate(nlp.pipe(textos_para_nlp, batch_size=50, disable=["ner"])):
            meta = metadatos_nlp[idx]
            for chunk in doc.noun_chunks:
                tokens = [t.text.lower().strip() for t in chunk if not t.is_stop and t.pos_ in ['NOUN', 'ADJ', 'PROPN']]
                if 2 <= len(tokens) <= 4:
                    compuesto = " ".join(tokens)
                    if es_concepto_valido(compuesto):
                        inyectar_relacion(meta["grado"], formatear_titulo_profesional(compuesto), meta["anio"], meta["link"], meta["titulo"])

    json_maestro = json.dumps(estructura_maestra, ensure_ascii=False)
    json_anios = json.dumps(sorted(list(anios_detectados), reverse=True))

    html_template = f"""<div style="padding: 40px 30px; background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%); border-radius: 20px; box-shadow: 0 20px 40px -10px rgba(0,0,0,0.1); margin: 30px auto; max-width: 950px; font-family: 'Segoe UI', Roboto, sans-serif;">
    
    <div style="text-align: center; margin-bottom: 25px;">
        <h2 style="color: #0f172a; margin-top: 0; margin-bottom: 5px; font-size: 32px; font-weight: 900; letter-spacing: -1px;">Analizador Semántico de Tesis FCFM</h2>
        <h3 style="color: #3b82f6; margin-top: 0; margin-bottom: 20px; font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 2px;">Universidad de Chile</h3>
        
        <div style="display: flex; justify-content: center; gap: 8px; margin-bottom: 25px;">
            <button class="tab-btn" onclick="cambiarGrado('Ambos', this)" style="padding: 10px 18px; font-weight: 700; border-radius: 8px; border: none; cursor: pointer; background: #3b82f6; color: white; transition: all 0.2s;">🎓 Todos los Grados</button>
            <button class="tab-btn" onclick="cambiarGrado('Pregrado', this)" style="padding: 10px 18px; font-weight: 700; border-radius: 8px; border: none; cursor: pointer; background: #cbd5e1; color: #1e293b; transition: all 0.2s;">📄 Pregrado</button>
            <button class="tab-btn" onclick="cambiarGrado('Postgrado', this)" style="padding: 10px 18px; font-weight: 700; border-radius: 8px; border: none; cursor: pointer; background: #cbd5e1; color: #1e293b; transition: all 0.2s;">🔬 Postgrado</button>
        </div>

        <div style="display: inline-flex; gap: 15px; background: #ffffff; padding: 8px 16px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #e2e8f0;">
            <div>
                <label for="filtro-anio" style="color: #64748b; font-size: 11px; font-weight: 800; text-transform: uppercase; display:block; margin-bottom:4px;">Año:</label>
                <select id="filtro-anio" style="padding: 6px 12px; font-size: 14px; font-weight: 700; color: #1e40af; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; cursor: pointer; outline: none;"></select>
            </div>
            <div>
                <label for="filto-palabras" style="color: #64748b; font-size: 11px; font-weight: 800; text-transform: uppercase; display:block; margin-bottom:4px;">Palabras:</label>
                <select id="filto-palabras" style="padding: 6px 12px; font-size: 14px; font-weight: 700; color: #1e40af; background: #fdf2f8; border: 1px solid #fbcfe8; border-radius: 6px; cursor: pointer; outline: none;">
                    <option value="30" selected>Top 30</option>
                    <option value="60">Top 60</option>
                    <option value="120">Top 120</option>
                </select>
            </div>
        </div>
    </div>
    
    <div id="wordcloud-container" style="width: 100%; height: 520px; background: #0f172a; border-radius: 16px; position: relative; overflow: hidden; box-shadow: inset 0 4px 20px rgba(0,0,0,0.5);"></div>

    <div id="panel-referencias" style="margin-top: 35px; padding: 30px; padding-top: 25px; background: #ffffff; border-radius: 14px; border: 1px solid #e2e8f0; display: none; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05); position: relative;">
        
        <button onclick="document.getElementById('panel-referencias').style.display='none'" style="position: absolute; top: 15px; right: 15px; background: #ef4444; color: white; border: none; border-radius: 50%; width: 28px; height: 28px; font-size: 14px; font-weight: bold; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background 0.2s;" onmouseover="this.style.background='#dc2626'" onmouseout="this.style.background='#ef4444'">✕</button>

        <h4 style="margin-top: 5px; color: #1e293b; font-size: 18px; border-bottom: 2px solid #3b82f6; padding-bottom: 12px; margin-bottom: 20px;">
            📚 Tesis indexadas para: <span id="concepto-seleccionado" style="color: #2563eb; font-weight: 800;"></span>
        </h4>
        <ul id="lista-links" style="padding-left: 20px; margin-bottom: 0; line-height: 1.6; color: #475569; font-size: 14px; max-height: 300px; overflow-y: auto;"></ul>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3-cloud/1.2.7/d3.layout.cloud.min.js"></script>

    <script>
    setTimeout(function() {{
        try {{
            var datosMaestros = {json_maestro};
            var aniosDisponibles = {json_anios};
            var gradoActual = "Ambos";
            
            var selectorAnio = document.getElementById('filtro-anio');
            var aniosNum = aniosDisponibles.map(Number).filter(n => !isNaN(n)).sort((a,b) => b-a);
            
            var optTodos = document.createElement('option');
            optTodos.value = "TODOS"; optTodos.text = "Todos los años";
            selectorAnio.appendChild(optTodos);
            
            var ultimos = aniosNum.slice(0, 8);
            ultimos.forEach(function(a) {{
                var opt = document.createElement('option');
                opt.value = a.toString(); opt.text = a.toString();
                selectorAnio.appendChild(opt);
            }});
            
            if (aniosNum.length > 8) {{
                var umbral = aniosNum[8]; 
                var optResto = document.createElement('option');
                optResto.value = "<=" + umbral; 
                optResto.text = "Histórico (Hasta " + umbral + ")";
                selectorAnio.appendChild(optResto);
            }}

            var container = document.getElementById('wordcloud-container');
            var colors = ["#38bdf8", "#34d399", "#fbbf24", "#f472b6", "#a78bfa", "#f87171", "#2dd4bf"];

            window.cambiarGrado = function(nuevoGrado, btn) {{
                gradoActual = nuevoGrado;
                document.querySelectorAll('.tab-btn').forEach(b => {{ b.style.background = "#cbd5e1"; b.style.color = "#1e293b"; }});
                btn.style.background = "#3b82f6"; btn.style.color = "white";
                document.getElementById('panel-referencias').style.display = "none";
                procesarYRenderizar();
            }}

            function procesarYRenderizar() {{
                var anioSel = selectorAnio.value;
                var limite = parseInt(document.getElementById('filto-palabras').value);
                var diccionarioContexto = datosMaestros[gradoActual];
                
                var dataset = [];
                for (var palabra in diccionarioContexto) {{
                    var peso = 0;
                    
                    if (anioSel === "TODOS") {{
                        peso = diccionarioContexto[palabra].frecuencia_total;
                    }} else if (anioSel.startsWith("<=")) {{
                        var maxVal = parseInt(anioSel.substring(2));
                        for (var a in diccionarioContexto[palabra].anios) {{
                            if (parseInt(a) <= maxVal) {{
                                peso += diccionarioContexto[palabra].anios[a];
                            }}
                        }}
                    }} else {{
                        if (diccionarioContexto[palabra].anios[anioSel]) {{
                            peso = diccionarioContexto[palabra].anios[anioSel];
                        }}
                    }}
                    
                    if (peso > 0) dataset.push({{ text: palabra, size: peso }});
                }}

                dataset.sort((a,b) => b.size - a.size);
                dataset = dataset.slice(0, limite);

                d3.select("#wordcloud-container").html("");
                if(dataset.length === 0) {{
                    d3.select("#wordcloud-container").append("p")
                        .style("color", "#64748b").style("text-align", "center").style("margin-top", "220px").text("No hay registros en este periodo.");
                    return;
                }}

                var width = container.offsetWidth || 890, height = 520;
                var maxVal = d3.max(dataset, d => d.size), minVal = d3.min(dataset, d => d.size);

                var layout = d3.layout.cloud()
                    .size([width, height])
                    .words(dataset)
                    .padding(6)
                    .rotate(() => (~~(Math.random() * 2) * 90))
                    .font("'Segoe UI', Roboto")
                    .fontSize(d => maxVal === minVal ? 22 : 14 + ((d.size - minVal) / (maxVal - minVal)) * 34)
                    .on("end", draw);

                layout.start();

                function draw(words) {{
                    var svg = d3.select("#wordcloud-container").append("svg")
                        .attr("width", layout.size()[0]).attr("height", layout.size()[1])
                      .append("g").attr("transform", "translate(" + layout.size()[0]/2 + "," + layout.size()[1]/2 + ")");

                    svg.selectAll("text").data(words).enter().append("text")
                        .style("font-weight", "800").style("fill", (d,i) => colors[i % colors.length])
                        .attr("text-anchor", "middle").style("font-size", d => d.size + "px").style("cursor", "pointer")
                        .attr("transform", d => "translate(" + [d.x, d.y] + ")rotate(" + d.rotate + ")")
                        .text(d => d.text)
                        .on("click", (e, d) => mostrarEnlaces(d.text));
                }}
            }}

            function mostrarEnlaces(palabra) {{
                var info = datosMaestros[gradoActual][palabra];
                var anioFiltro = selectorAnio.value;
                document.getElementById('concepto-seleccionado').innerText = palabra + " (" + gradoActual + ")";
                var ul = document.getElementById('lista-links'); ul.innerHTML = "";

                for (var url in info.links) {{
                    var objDatos = info.links[url];
                    var anioLink = objDatos.anio;
                    var tituloTesis = objDatos.titulo;
                    var anioInt = parseInt(anioLink);
                    var mostrar = false;
                    
                    if (anioFiltro === "TODOS") {{
                        mostrar = true;
                    }} else if (anioFiltro.startsWith("<=")) {{
                        var maxVal = parseInt(anioFiltro.substring(2));
                        if (anioInt <= maxVal) mostrar = true;
                    }} else if (anioLink === anioFiltro) {{
                        mostrar = true;
                    }}

                    if (mostrar) {{
                        var li = document.createElement('li');
                        li.style.marginBottom = "10px";
                        
                        var a = document.createElement('a');
                        a.href = url; 
                        a.target = "_blank"; 
                        a.style.color = "#2563eb"; 
                        a.style.fontWeight = "600";
                        a.style.textDecoration = "none";
                        
                        // Añadir efecto visual sutil al pasar el mouse
                        a.onmouseover = function() {{ this.style.textDecoration = 'underline'; }};
                        a.onmouseout = function() {{ this.style.textDecoration = 'none'; }};
                        
                        a.innerText = tituloTesis + " — Año " + anioLink;
                        
                        li.appendChild(a); 
                        ul.appendChild(li);
                    }}
                }}
                document.getElementById('panel-referencias').style.display = "block";
                
                // Hacer scroll automático hacia el panel
                document.getElementById('panel-referencias').scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
            }}

            selectorAnio.addEventListener('change', () => {{ procesarYRenderizar(); document.getElementById('panel-referencias').style.display = "none"; }});
            document.getElementById('filto-palabras').addEventListener('change', procesarYRenderizar);
            procesarYRenderizar();
        }} catch(err) {{ console.error(err); }}
    }}, 400);
    </script>
</div>"""

    with open("resultado_fcfm.html", "w", encoding="utf-8") as f:
        f.write(html_template)
    print("\n✨ ¡ÉXITO! Se generó 'resultado_fcfm.html' con títulos reales y diseño mejorado.")

if __name__ == "__main__":
    generar_html_universal()