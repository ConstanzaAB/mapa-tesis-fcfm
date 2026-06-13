import requests
import xml.etree.ElementTree as ET
import time
import json

# URL de la base de datos cruda de la U. de Chile
OAI_URL = "https://repositorio.uchile.cl/oai/request"

# Diccionarios de lectura de XML
NAMESPACES = {
    'oai': 'http://www.openarchives.org/OAI/2.0/',
    'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
    'dc': 'http://purl.org/dc/elements/1.1/'
}

def llenar_base_historica(archivo_json="bd_tesis.json"):
    # 1. Cargar la base de datos que ya tienes para NO duplicar nada
    try:
        with open(archivo_json, 'r', encoding='utf-8') as f:
            bd_actual = json.load(f)
    except FileNotFoundError:
        bd_actual = {}
        
    print(f"📦 Tu base actual tiene {len(bd_actual)} tesis. Buscando historial faltante...")
    
    # 2. Le decimos al servidor que queremos los metadatos estructurados
    params = {"verb": "ListRecords", "metadataPrefix": "oai_dc"}
    
    nuevas_agregadas = 0
    bloques_procesados = 0
    
    while True:
        try:
            # Hacemos la petición a la API
            response = requests.get(OAI_URL, params=params, timeout=30)
            
            if response.status_code != 200:
                print(f"⚠️ Servidor UChile saturado (Error {response.status_code}). Pausa de 10 seg...")
                time.sleep(10)
                continue
                
            bloques_procesados += 1
            root = ET.fromstring(response.content)
            
            # Recorremos todas las tesis que vienen en este bloque (generalmente 100 de golpe)
            records = root.findall('.//oai:record', NAMESPACES)
            
            for record in records:
                # Omitir si la universidad borró este registro
                header = record.find('oai:header', NAMESPACES)
                if header is not None and header.get('status') == 'deleted': continue
                    
                metadata = record.find('.//oai_dc:dc', NAMESPACES)
                if metadata is None: continue
                
                # A. Buscar el enlace oficial (handle)
                url = None
                for identifier in metadata.findall('dc:identifier', NAMESPACES):
                    if identifier.text and "handle/2250/100004" in identifier.text:
                        url = identifier.text.strip()
                        break
                        
                # Si no tiene enlace o YA la tienes guardada, saltamos instantáneamente
                if not url or url in bd_actual:
                    continue
                
                # B. Filtro estricto: ¿Es una tesis académica?
                es_tesis = False
                grado_estimado = "Tesis"
                for tipo in metadata.findall('dc:type', NAMESPACES):
                    if tipo.text:
                        tipo_txt = tipo.text.lower()
                        if "tesis" in tipo_txt or "memoria" in tipo_txt:
                            es_tesis = True
                            if "magíster" in tipo_txt or "doctorado" in tipo_txt:
                                grado_estimado = "Postgrado"
                            elif "civil" in tipo_txt or "licenciatura" in tipo_txt or "título" in tipo_txt:
                                grado_estimado = "Pregrado"
                
                if not es_tesis: continue # Ignoramos papers, revistas, boletines, etc.
                
                # C. Extraer los datos crudos
                titulo_node = metadata.find('dc:title', NAMESPACES)
                titulo = titulo_node.text.strip() if titulo_node is not None and titulo_node.text else "Tesis sin título"
                
                anio_node = metadata.find('dc:date', NAMESPACES)
                anio = anio_node.text[:4] if anio_node is not None and anio_node.text else "Desconocido"
                
                resumen = ""
                for desc in metadata.findall('dc:description', NAMESPACES):
                    if desc.text and len(desc.text) > 40: 
                        resumen = desc.text.strip()
                        break
                        
                palabras_clave = [subj.text.strip() for subj in metadata.findall('dc:subject', NAMESPACES) if subj.text]
                
                es_embargada = False
                for rights in metadata.findall('dc:rights', NAMESPACES):
                    if rights.text and ("embargo" in rights.text.lower() or "restringido" in rights.text.lower()):
                        es_embargada = True
                
                # D. Misma lógica de guardado de tu script de automatización
                texto_final = ""
                origen = ""
                
                if palabras_clave:
                    texto_final = " . ".join(palabras_clave)
                    origen = "Metadatos (Historial OAI)"
                elif resumen:
                    texto_final = resumen
                    origen = "Resumen (Historial OAI)"
                elif es_embargada or titulo != "Tesis sin título":
                    # Rescate seguro desde el título
                    stopwords = {'de', 'la', 'el', 'en', 'para', 'y', 'los', 'las', 'un', 'una', 'con', 'del', 'al', 'sobre', 'sus', 'por', 'a', 'o', 'e', 'u'}
                    titulo_limpio = titulo.lower().replace(':', '').replace('(', '').replace(')', '').replace(',', '')
                    pal_titulo = [p for p in titulo_limpio.split() if p not in stopwords and len(p) > 2]
                    texto_final = " . ".join(pal_titulo) if pal_titulo else "Documento sin datos textuales"
                    origen = "Embargada/Título (Historial OAI)" if es_embargada else "Solo Título (Historial OAI)"
                
                if texto_final:
                    bd_actual[url] = {
                        "texto": texto_final,
                        "origen": origen,
                        "anio": anio,
                        "grado": grado_estimado,
                        "titulo": titulo
                    }
                    nuevas_agregadas += 1
            
            print(f"   ⏳ Navegando páginas internas... (Bloques extraídos: {bloques_procesados}) | Tesis rescatadas hasta ahora: {nuevas_agregadas}")
            
            # 3. La Paginación Mágica (resumptionToken)
            resumption_token_node = root.find('.//oai:resumptionToken', NAMESPACES)
            
            if resumption_token_node is not None and resumption_token_node.text:
                params = {"verb": "ListRecords", "resumptionToken": resumption_token_node.text}
            else:
                print("\n🏁 ¡Llegamos al inicio de los tiempos de la Universidad de Chile!")
                break
                
            time.sleep(1) # Pausa por cortesía al servidor
            
        except Exception as e:
            print(f"❌ Error en la conexión: {e}. Intentando guardar progreso...")
            break
            
    # Guardar en tu JSON de forma segura
    if nuevas_agregadas > 0:
        with open(archivo_json, 'w', encoding='utf-8') as f:
            json.dump(bd_actual, f, ensure_ascii=False, indent=4)
        print(f"\n💾 ¡MISIÓN CUMPLIDA! {nuevas_agregadas} tesis antiguas añadidas a tu base de datos.")
    else:
        print("\nℹ️ No se encontraron tesis faltantes. Tu base de datos ya tiene todo el historial.")

# Ejecuta el escaneo llamando a la función
if __name__ == "__main__":
    llenar_base_historica("bd_tesis.json")