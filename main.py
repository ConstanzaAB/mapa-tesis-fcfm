from fastapi import FastAPI
from pydantic import BaseModel
from keybert import KeyBERT
from sklearn.cluster import KMeans
import numpy as np
from typing import List

app = FastAPI()
kw_model = KeyBERT()

class Document(BaseModel):
    text: str

@app.post("/get-map")
async def generate_vos_data(documents: List[Document]):
    all_texts = [doc.text for doc in documents]
    
    # 1. Extracción de Keywords con Embeddings
    # Extraemos las 5 palabras más representativas por documento
    doc_keywords = kw_model.extract_keywords(all_texts, keyphrase_ngram_range=(1, 1), stop_words='spanish', top_n=5)
    
    nodes_dict = {}
    links_dict = {}
    
    # 2. Construcción de la Red
    for keywords in doc_keywords:
        words = [k[0] for k in keywords]
        for i, word_a in enumerate(words):
            # Registrar Nodo
            nodes_dict[word_a] = nodes_dict.get(word_a, 0) + 1
            
            # Registrar Relaciones (Links)
            for word_b in words[i+1:]:
                pair = tuple(sorted((word_a, word_b)))
                links_dict[pair] = links_dict.get(pair, 0) + 1

    # 3. Formatear para Magnolia (D3.js)
    nodes = [{"id": word, "size": count, "group": 1} for word, count in nodes_dict.items()]
    links = [{"source": p[0], "target": p[1], "value": v} for p, v in links_dict.items()]

    return {"nodes": nodes, "links": links}