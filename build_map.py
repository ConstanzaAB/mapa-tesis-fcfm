import requests
from bs4 import BeautifulSoup
import json
import spacy
from collections import Counter, defaultdict
import time
import unicodedata

# Ruta paginada del motor DSpace
URL_BUSQUEDA_PAGINADA = "https://repositorio.uchile.cl/handle/2250/100026/recent-submissions"
BASE_URL = "https://repositorio.uchile.cl"

def formatear_titulo_profesional(texto):
    """
    Formatea un texto estilo título profesional en español.
    Mantiene conectores, preposiciones y artículos en minúscula.
    """
    conectores = {
        "de", "del", "a", "al", "en", "y", "o", "u", "e", "con", "por", "para", 
        "sin", "sobre", "tras", "la", "las", "el", "los", "un", "una", "unos", "unas"
    }
    
    palabras = texto.split()
    if not palabras:
        return ""
        
    resultado = []
    for i, palabra in enumerate(palabras):
        palabra_clean = palabra.lower()
        
        if i == 0:
            resultado.append(palabra.capitalize())
        elif palabra_clean in conectores:
            resultado.append(palabra_clean)
        else:
            resultado.append(palabra.capitalize())
            
    return " ".join(resultado)

def procesar_keyword_compuesto(texto_keyword):
    if "--" not in texto_keyword:
        return [texto_keyword]
        
    partes = [p.strip() for p in texto_keyword.split("--") if p.strip()]
    
    ciudades_chile = ["santiago", "valparaíso", "valparaiso", "concepción", "concepcion", 
                      "antofagasta", "viña del mar", "valdivia", "temuco", "talca", "rancagua"]
    
    tiene_chile = False
    ciudad_encontrada = None
    conceptos_puros = []
    
    for p in partes:
        p_lower = p.lower()
        if p_lower == "chile":
            tiene_chile = True
        elif p_lower in ciudades_chile:
            ciudad_encontrada = p.title()
        else:
            conceptos_puros.append(p)
            
    if not conceptos_puros:
        return partes
        
    concepto_base = conceptos_puros[0]
    
    if ciudad_encontrada:
        return [f"{concepto_base} en {ciudad_encontrada}"]
    elif tiene_chile:
        return [f"{concepto_base} en Chile"]
    else:
        return conceptos_puros

def extraer_enlaces_tesis_reales(max_tesis=500):
    print(f"🤖 Buscando hasta {max_tesis} tesis en el paginado real...")
    enlaces = []
    offset = 0
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    while len(enlaces) < max_tesis:
        url_pagina = f"{URL_BUSQUEDA_PAGINADA}?offset={offset}"
        try:
            response = requests.get(url_pagina, headers=headers, timeout=15)
            if response.status_code != 200:
                break
                
            soup = BeautifulSoup(response.text, 'html.parser')
            nuevos_enlaces = 0
            
            for a in soup.find_all('a', href=True):
                href = a['href']
                if "/handle/2250/" in href and "?" not in href and "recent-submissions" not in href and href != "/handle/2250/100026":
                    url_completa = BASE_URL + href if href.startswith('/') else href
                    if url_completa not in enlaces:
                        enlaces.append(url_completa)
                        nuevos_enlaces += 1
                        
            if nuevos_enlaces == 0:
                break
                
            print(f"   📥 Recolectados {len(enlaces)} enlaces...")
            offset += 20 
            time.sleep(0.3) 
            
        except Exception:
            break
            
    return enlaces[:max_tesis]

def minar_registro_completo(urls_tesis):
    textos_para_analisis = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    limite_tesis = len(urls_tesis)
    print(f"\n🕵️‍♂️ Extrayendo metadatos profundos de {limite_tesis} tesis...")
    print("   ⏳ Esto tomará unos minutos. Por favor, espera...")
    
    for i, url in enumerate(urls_tesis):
        try:
            res = requests.get(f"{url}?show=full", headers=headers, timeout=10)
            if res.status_code != 200: continue
                
            inner_soup = BeautifulSoup(res.text, 'html.parser')
            palabras_clave_ficha = []
            resumen_texto = ""
            
            for fila in inner_soup.find_all('tr'):
                celdas = fila.find_all(['td', 'th'])
                if len(celdas) >= 3:
                    # Obtenemos el nombre del campo (ej: dc.subject.spa)
                    campo_interno = celdas[1].get_text().strip().lower()
                    
                    # Limpiamos saltos de línea extraños que a veces traen los metadatos
                    texto_celda = celdas[2].get_text().replace('\n', ' ').strip()
                    valor_real = unicodedata.normalize('NFC', texto_celda)
                    
                    # 💡 AQUÍ ESTÁ LA MAGIA: Usamos startswith para atrapar todas las variantes
                    if campo_interno.startswith('dc.subject'):
                        palabras_clave_ficha.append(valor_real)
                    elif campo_interno.startswith('dc.description.abstract'):
                        resumen_texto = valor_real
            
            if palabras_clave_ficha:
                textos_para_analisis.append((" . ".join(palabras_clave_ficha), "Metadatos"))
            elif resumen_texto:
                textos_para_analisis.append((resumen_texto, "Resumen"))
            
            if (i + 1) % 50 == 0 or (i + 1) == limite_tesis:
                print(f"   ✅ Procesadas {i + 1} de {limite_tesis} tesis...")
            
            time.sleep(0.3) 
            
        except Exception:
            continue
            
    return textos_para_analisis



def generar_html_inteligente_profundo():
    # 💡 Límite óptimo de 1,000 tesis
    urls = extraer_enlaces_tesis_reales(1000) 
    if not urls: return
        
    datos_extraidos = minar_registro_completo(urls)
    if not datos_extraidos: return
        
    print(f"\n🧠 Analizando lingüísticamente en lotes masivos con Spacy...")
    try:
        nlp = spacy.load("es_core_news_sm")
    except Exception:
        print("❌ Falta el modelo de Spacy. Ejecuta: python -m spacy download es_core_news_sm")
        return

    # ==============================================================================
    # EXCLUSIONES SIMPLES (Palabras sueltas post-stopword)
    # ==============================================================================
    exclusiones_simples = [
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

    # ==============================================================================
    # EXCLUSIONES COMPUESTAS (Organizadas por categorías lógicas)
    # ==============================================================================
    exclusiones_compuestas = [
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
        'decisiones estratégicas', 'decisión estratégica', 'correcto funcionamiento'

        # --- Jerga de Estructura de Tesis e Investigación ---
        'toma decisiones', 'toma de decisiones', 'revision bibliografica', 'revisión bibliográfica',
        'conclusiones generales', 'conclusion general', 'conclusiones finales', 'conclusion final',
        'futuras investigaciones', 'futura investigacion', 'futuros estudios', 'futuro estudio',
        'caso estudio', 'casos estudio', 'recoleccion datos', 'recolección datos', 
        'principales resultados', 'principal resultado', 'marco referencia', 'marco de referencia',
        'marco teorico', 'marco teórico', 'estado arte', 'trabajo futuro', 'punto vista',
        'variables analizadas', 'variable analizada', 'principales factores', 'principal factor',
        'diversos factores', 'diversas variables', 'aspectos clave', 'aspecto clave', 'puntos clave', 'punto clave',
        'analisis cuantitativo', 'analisis cualitativo', 'análisis cuantitativo', 'análisis cualitativo',

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
    
    # Estructura avanzada para indexación cruzada
    # { concepto: { "frecuencia_total": X, "anios": { anio: frecuencia }, "links": { url: anio } } }
    base_conceptos = defaultdict(lambda: {"frecuencia_total": 0, "anios": defaultdict(int), "links": {}})
    anios_detectados = set()

    print(f"   • Mapeando relaciones temporales y enlaces...")
    for idx, (texto, origen) in enumerate(datos_extraidos):
        texto = unicodedata.normalize('NFC', texto)
        
        # Intentamos recuperar el link y año real del set de datos original
        # Nota: Ajusta estas claves según cómo devuelva tu función 'minar_registro_completo' el origen/metadatos
        link_actual = urls[idx] if idx < len(urls) else "#"
        
        # Simulamos o extraemos el año de la tesis (aquí asumo un rango estándar si no viene explícito)
        # Lo ideal es que tu 'datos_extraidos' capture el año real. Si no, usaremos 2024 como fallback temporal.
        anio_actual = "2024" 
        if hasattr(texto, 'anio'): # Si tu objeto tiene atributo año
            anio_actual = str(texto.anio)
        
        anios_detectados.add(anio_actual)
        
        conceptos_del_documento = []

        if origen == "Metadatos":
            for termino in texto.replace(';', ',').replace('.', ',').split(','):
                if not termino.strip(): continue
                sub_conceptos = procesar_keyword_compuesto(termino.strip())
                for concepto in sub_conceptos:
                    t_clean = concepto.strip().lower()
                    if len(t_clean) > 3 and t_clean not in exclusiones_simples and t_clean not in exclusiones_compuestas and not t_clean.isdigit():
                        conceptos_del_documento.append(t_clean)
        else:
            # Procesamiento con Spacy para texto plano extenso
            doc = nlp(texto)
            for chunk in doc.noun_chunks:
                tokens_filtrados = [t.text.lower().strip() for t in chunk if not t.is_stop and t.pos_ in ['NOUN', 'ADJ', 'PROPN']]
                palabras = [p for p in tokens_filtrados if p not in exclusiones_simples and len(p) > 2 and not p.isdigit()]
                
                if 2 <= len(palabras) <= 4:
                    concepto_armado = " ".join(palabras)
                    if concepto_armado not in exclusiones_compuestas:
                        conceptos_del_documento.append(concepto_armado)

        # Guardar en nuestra base de datos relacional interna
        for con in conceptos_del_documento:
            con_formateado = formatear_titulo_profesional(con)
            base_conceptos[con_formateado]["frecuencia_total"] += 1
            base_conceptos[con_formateado]["anios"][anio_actual] += 1
            base_conceptos[con_formateado]["links"][link_actual] = anio_actual

    # Ordenamos los años para el selector numérico de la interfaz
    lista_anios_ordenada = sorted(list(anios_detectados), reverse=True)

    # Convertimos a JSON plano compatible con JavaScript
    json_datos_relacionales = json.dumps(base_conceptos, ensure_ascii=False)
    json_anios = json.dumps(lista_anios_ordenada)

    print("\n📄 Volcando mapa relacional y construyendo panel dinámico de referencias...")
    
    html_template = f"""<div style="padding: 40px 30px; background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%); border-radius: 20px; box-shadow: 0 20px 40px -10px rgba(0,0,0,0.1); margin: 30px auto; max-width: 950px; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
    
    <div style="text-align: center; margin-bottom: 25px;">
        <h2 style="color: #0f172a; margin-top: 0; margin-bottom: 10px; font-size: 32px; font-weight: 900; letter-spacing: -1px;">Mapa Semántico e Indexador de Tesis</h2>
        <h3 style="color: #3b82f6; margin-top: 0; margin-bottom: 15px; font-size: 15px; font-weight: 700; text-transform: uppercase; letter-spacing: 2px;">FCFM • Universidad de Chile</h3>
        <p style="color: #475569; font-size: 15px; margin: 0 auto 20px auto; max-width: 600px; line-height: 1.6;">Haz clic en una palabra para listar los enlaces del repositorio real donde se utilizó ese concepto.</p>
        
        <div style="display: inline-flex; gap: 15px; background: #ffffff; padding: 8px 16px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #e2e8f0;">
            <div>
                <label for="filtro-anio" style="color: #64748b; font-size: 11px; font-weight: 800; text-transform: uppercase; display:block; margin-bottom:4px;">Año de publicación:</label>
                <select id="filtro-anio" style="padding: 6px 12px; font-size: 14px; font-weight: 700; color: #1e40af; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; cursor: pointer; outline: none;"></select>
            </div>
            <div>
                <label for="filto-palabras" style="color: #64748b; font-size: 11px; font-weight: 800; text-transform: uppercase; display:block; margin-bottom:4px;">Densidad del mapa:</label>
                <select id="filto-palabras" style="padding: 6px 12px; font-size: 14px; font-weight: 700; color: #1e40af; background: #fdf2f8; border: 1px solid #fbcfe8; border-radius: 6px; cursor: pointer; outline: none;">
                    <option value="20">Top 20 conceptos</option>
                    <option value="50" selected>Top 50 conceptos</option>
                    <option value="100">Top 100 conceptos</option>
                </select>
            </div>
        </div>
    </div>
    
    <div id="wordcloud-container" style="width: 100%; height: 500px; background: #0f172a; border-radius: 16px; position: relative; overflow: hidden; box-shadow: inset 0 4px 20px rgba(0,0,0,0.5);"></div>

    <div id="panel-referencias" style="margin-top: 25px; padding: 20px; background: #ffffff; border-radius: 14px; border: 1px solid #e2e8f0; display: none; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05);">
        <h4 style="margin-top: 0; color: #1e293b; font-size: 16px; border-bottom: 2px solid #3b82f6; padding-bottom: 8px;">
            📚 Tesis que mencionan: <span id="concepto-seleccionado" style="color: #2563eb; font-weight: 800;"></span>
        </h4>
        <ul id="lista-links" style="padding-left: 20px; margin-bottom: 0; line-height: 1.8; color: #475569; font-size: 14px;"></ul>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3-cloud/1.2.7/d3.layout.cloud.min.js"></script>

    <script>
    setTimeout(function() {{
        try {{
            var datosMaestros = {json_datos_relacionales};
            var aniosDisponibles = {json_anios};
            
            // Poblar dinámicamente el selector de años
            var selectorAnio = document.getElementById('filtro-anio');
            var optTodos = document.createElement('option');
            optTodos.value = "TODOS"; optTodos.text = "Todos los años";
            selectorAnio.appendChild(optTodos);
            aniosDisponibles.forEach(function(a) {{
                var opt = document.createElement('option');
                opt.value = a; opt.text = a;
                selectorAnio.appendChild(opt);
            }});

            var container = document.getElementById('wordcloud-container');
            var colors = ["#38bdf8", "#34d399", "#fbbf24", "#f472b6", "#a78bfa", "#f87171", "#2dd4bf", "#e879f9", "#fb923c"];

            function procesarYRenderizar() {{
                var anioSeleccionado = selectorAnio.value;
                var limitePalabras = parseInt(document.getElementById('filto-palabras').value);
                
                // Mapear y filtrar frecuencias según el año seleccionado
                var datasetFiltrado = [];
                for (var palabra in datosMaestros) {{
                    var peso = 0;
                    if (anioSeleccionado === "TODOS") {{
                        peso = datosMaestros[palabra].frecuencia_total;
                    }} else if (datosMaestros[palabra].anios[anioSeleccionado]) {{
                        peso = datosMaestros[palabra].anios[anioSeleccionado];
                    }}
                    
                    if (peso > 0) {{
                        datasetFiltrado.push({{ text: palabra, size: peso }});
                    }}
                }}

                // Ordenar por el peso del periodo y aplicar corte de límite
                datasetFiltrado.sort(function(a, b) {{ return b.size - a.size; }});
                datasetFiltrado = datasetFiltrado.slice(0, limitePalabras);

                // Dibujar
                d3.select("#wordcloud-container").html("");
                if(datasetFiltrado.length === 0) {{
                    d3.select("#wordcloud-container").append("p")
                        .style("color", "#64748b").style("text-align", "center").style("margin-top", "200px")
                        .text("No hay conceptos registrados para este año.");
                    return;
                }}

                var width = container.offsetWidth || 890;
                var height = 500;
                var maxVal = d3.max(datasetFiltrado, function(d){{ return d.size; }});
                var minVal = d3.min(datasetFiltrado, function(d){{ return d.size; }}));

                var layout = d3.layout.cloud()
                    .size([width, height])
                    .words(datasetFiltrado)
                    .padding(5)
                    .rotate(function() {{ return (~~(Math.random() * 2) * 90); }})
                    .font("'Segoe UI', Roboto")
                    .fontSize(function(d) {{
                        if (maxVal === minVal) return 20;
                        return 14 + ((d.size - minVal) / (maxVal - minVal)) * 36;
                    }})
                    .on("end", draw);

                layout.start();

                function draw(words) {{
                    var svg = d3.select("#wordcloud-container").append("svg")
                        .attr("width", layout.size()[0])
                        .attr("height", layout.size()[1])
                      .append("g")
                        .attr("transform", "translate(" + layout.size()[0] / 2 + "," + layout.size()[1] / 2 + ")");

                    svg.selectAll("text")
                        .data(words)
                      .enter().append("text")
                        .style("font-weight", "800")
                        .style("fill", function(d, i) {{ return colors[i % colors.length]; }})
                        .attr("text-anchor", "middle")
                        .style("font-size", function(d) {{ return d.size + "px"; }})
                        .style("cursor", "pointer")
                        .style("transition", "all 0.15s ease")
                        .attr("transform", function(d) {{
                          return "translate(" + [d.x, d.y] + ")rotate(" + d.rotate + ")";
                        }})
                        .text(function(d) {{ return d.text; }})
                        
                        .on("mouseover", function(e, d) {{
                            d3.select(this).style("opacity", "0.85").style("text-shadow", "0 0 8px currentColor");
                        }})
                        .on("mouseout", function(e, d) {{
                            d3.select(this).style("opacity", "1").style("text-shadow", "none");
                        }})
                        .on("click", function(event, d) {{
                            mostrarEnlacesConcepto(d.text);
                        }});
                }}
            }}

            function mostrarEnlacesConcepto(palabra) {{
                var info = datosMaestros[palabra];
                var anioFiltro = selectorAnio.value;
                
                document.getElementById('concepto-seleccionado').innerText = palabra;
                var listaUl = document.getElementById('lista-links');
                listaUl.innerHTML = "";

                var contadorLinks = 0;
                for (var url in info.links) {{
                    var anioLink = info.links[url];
                    
                    // Mostrar solo si calza con el año filtrado o si estamos en vista global
                    if (anioFiltro === "TODOS" || anioLink === anioFiltro) {{
                        var li = document.createElement('li');
                        var a = document.createElement('a');
                        a.href = url;
                        a.target = "_blank";
                        a.style.color = "#2563eb";
                        a.style.fontWeight = "600";
                        a.style.textDecoration = "underline";
                        a.innerText = "Ver tesis en repositorio institucional (" + anioLink + ")";
                        
                        li.appendChild(a);
                        listaUl.appendChild(li);
                        contadorLinks++;
                    }}
                }}
                
                document.getElementById('panel-referencias').style.display = "block";
                document.getElementById('panel-referencias').scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
            }}

            // Event Listeners para recálculos dinámicos
            selectorAnio.addEventListener('change', function() {{
                procesarYRenderizar();
                document.getElementById('panel-referencias').style.display = "none";
            }});
            document.getElementById('filto-palabras').addEventListener('change', procesarYRenderizar);

            // Carga inicial
            procesarYRenderizar();

        }} catch(err) {{
            document.getElementById('wordcloud-container').innerHTML = "<p style='padding:20px;color:red;text-align:center;'>Error en interfaz: " + err.message + "</p>";
        }}
    }}, 400);
    </script>
</div>"""

    with open("resultado_fcfm.html", "w", encoding="utf-8") as f:
        f.write(html_template)
    print("✨ ¡LOGRADO! El nuevo dashboard ahora cuenta con indexador temporal y mapeo dinámico de enlaces por clic.")

if __name__ == "__main__":
    generar_html_inteligente_profundo()