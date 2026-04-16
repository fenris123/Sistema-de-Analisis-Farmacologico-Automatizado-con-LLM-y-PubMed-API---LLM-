# -*- coding: utf-8 -*-
# "Codificado en UTF-8 por Guillermo Ferrer"

import json
import requests
import sys
import ollama
import time
import re
import xml.etree.ElementTree as ET

# --- CONFIGURACIÓN TÉCNICA ---
MODEL = "llama3.1:8b"


# --- DEFINICIÓN DE AGENTES (SYSTEM ROLES) ---
# Separar la configuración de la ejecución mejora la mantenibilidad y legibilidad.
ROLE_FARMACEUTICO = (
    "Eres un farmacéutico clínico experto. Tu tono es técnico y directo. "
    "Priorizas la precisión y eliminas advertencias legales o avisos médicos genéricos."
)

ROLE_TRADUCTOR = "Eres experto en nomenclatura farmacológica internacional (DCI/INN)."

ROLE_INVESTIGADOR = (
    "Eres un experto en medicina basada en la evidencia y farmacología clínica. "
    "Tu objetivo es determinar si de entre un listado de articulos cientificos, "
    "alguno es particularmente relevante para los medicos. "
    "Responde siempre de forma escueta, enviando exclusivamente los números solicitados."
)

# -----------------------------
# DISCLAIMER FIJO
# -----------------------------
DISCLAIMER = """
⚠️ AVISO IMPORTANTE:
Este contenido se genera automáticamente con fines educativos e informativos.
No constituye consejo médico ni sustituye la consulta con un profesional sanitario.
El uso de esta información es responsabilidad exclusiva del usuario.
"""

# -----------------------------
# ADVERTENCIAS DINÁMICAS
# -----------------------------
ADVERTENCIA_RECETA = "El medicamento debe ser utilizado bajo la supervisión de un médico."

ADVERTENCIA_SIN_RECETA = (
    "Aunque este medicamento no requiere receta médica, se recomienda seguir las indicaciones "
    "del prospecto y consultar con un profesional sanitario en caso de duda."
)

# -----------------------------
# INICIO TOTAL
# -----------------------------
t_inicio_total = time.time()

print("\n Introduciendo medicamento...")
medicamento = input("Introduce el nombre del medicamento: ").strip()

# -----------------------------
# API AEMPS
# -----------------------------
print("\n[ Consultando API de AEMPS...")
t0 = time.time()
API_URL = "https://cima.aemps.es/cima/rest/medicamentos"

try:
    r = requests.get(
        API_URL,
        params={"nombre": medicamento},
        timeout=10
    )
    r.raise_for_status()
    datos = r.json()
except Exception as e:
    print("Error en la consulta a la API:", e)
    sys.exit()

t1 = time.time()
print(f"Tiempo API: {t1 - t0:.2f} s")

# -----------------------------
# RESULTADOS
# -----------------------------
print("\n Verificando resultados...")
resultados = datos.get("resultados", [])

if not resultados:
    print(f"No se han encontrado datos para '{medicamento}'.")
    sys.exit()

print(f"Resultados encontrados: {len(resultados)}")

# -----------------------------
# SELECCIÓN DE MEDICAMENTO
# -----------------------------
if len(resultados) == 1:
    seleccionado = resultados[0]
    print("\nSolo hay un resultado. Seleccionado automáticamente.")
else:
    print("\n===== LISTA DE MEDICAMENTOS =====\n")
    for i, med in enumerate(resultados, start=1):
        print(f"{i}. {med.get('nombre')}")

    print("\nIntroduce el número del medicamento que quieres analizar:")
    while True:
        try:
            opcion = int(input("> "))
            if 1 <= opcion <= len(resultados):
                seleccionado = resultados[opcion - 1]
                break
            else:
                print("Número fuera de rango.")
        except ValueError:
            print("Introduce un número válido.")

# -----------------------------
# RESUMEN DE LA INFORMACION DE AEMPS
# -----------------------------
print("\n Generando resumen técnico con LLM...")
t0 = time.time()

prompt_user = f"""
Resume el siguiente JSON siguiendo esta estructura:
- Principio activo, Forma farmacéutica y Vía
- Indicaciones y Posología
- Advertencias (Sustituye 'mg' por 'miligramos')

Regla: Si el dato no existe, indica 'No disponible'. No inventes información.

DATOS:
{json.dumps(seleccionado, ensure_ascii=False)}
"""

try:
    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": ROLE_FARMACEUTICO},
            {"role": "user", "content": prompt_user}
        ],
        options={"num_predict": 512, "temperature": 0.2}
    )

    resumen = response["message"]["content"]
    print(f"Tiempo de ejecución: {time.time() - t0:.2f} s")
    print("Resumen de los datos disponibles a traves de la API de la AEMPS")
    print("\n" + "="*40 + "\n" + resumen + "\n" + "="*40)
except Exception as e:
    print(f"\n[ERROR EN LA GENERACIÓN]: {e}")

# =========================================================
# PRINCIPIOS ACTIVOS + TRADUCCIÓN LLM
# =========================================================
print("\n Extrayendo y traduciendo principios activos...")

vtm_texto = seleccionado.get("vtm", {}).get("nombre", "")
principios_activos = [x.strip() for x in vtm_texto.split("+")]

prompt_trad = f"""
Traduce al inglés farmacológico estándar los siguientes principios activos.

REGLAS:
- Devuelve SOLO una lista separada por comas
- No explicaciones
- Mantén el orden

Lista:
{principios_activos}
"""

response = ollama.chat(
    model=MODEL,
    messages=[
        {"role": "system", "content": ROLE_TRADUCTOR},
        {"role": "user", "content": prompt_trad}
    ],
    options={"num_predict": 512, "temperature": 0.2}
)

resultado = response["message"]["content"]
principios_activos_en = [x.strip() for x in resultado.split(",") if x.strip()]
traduccion_map = dict(zip(principios_activos, principios_activos_en))

print("\n=== principios activos: ES → EN ===")
for es, en in traduccion_map.items():
    print(f"{es} → {en}")

# -----------------------------
# BÚSQUEDA EN PUBMED
# -----------------------------
base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
principios_test = principios_activos_en if principios_activos_en else principios_activos

terminos_or = " OR ".join(principios_test)
query_completa = f"({terminos_or})"

params_search = {
    "db": "pubmed",
    "term": query_completa,
    "retmax": 20,
    "retmode": "json",
    "sort": "pub_date"
}

r_search = requests.get(base_url + "esearch.fcgi", params=params_search)
ids = r_search.json().get("esearchresult", {}).get("idlist", [])

print(f"\n IDs de los articulos encontrados: {ids}")

if ids:
    time.sleep(0.5)
    ids_str = ",".join(ids)
    fetch_url = f"{base_url}efetch.fcgi?db=pubmed&id={ids_str}&rettype=abstract&retmode=xml"
    r_fetch = requests.get(fetch_url)
    root = ET.fromstring(r_fetch.content)
    articulos = root.findall(".//PubmedArticle")

    print(f"\n{'='*70}")
    print(f"ARTÍCULOS MAS RECIENTES: {len(articulos)}")
    print(f"{'='*70}")

    for i, art in enumerate(articulos, start=1):
        titulo = art.find(".//ArticleTitle").text
        print(f"{i}. {titulo}")
else:
    print("No se hallaron resultados.")
    articulos = []

# =========================================================================
# SELECCIÓN DE ARTÍCULOS RELEVANTES (LLM - AGENTE INVESTIGADOR)
# =========================================================================
indices_elegidos = []
pubmed_seleccion_md = ""

if ids and articulos:
    lista_titulos_prompt = "\n".join([f"{i+1}. {art.find('.//ArticleTitle').text}" for i, art in enumerate(articulos)])
    print("\n [AI] EVALUANDO RELEVANCIA CLÍNICA...")

    prompt_usuario = f"""
    Analiza los siguientes 20 títulos de estudios sobre {principios_test}.
    Selecciona los 3 artículos con mayor relevancia para un médico clínico.

    Títulos:
    {lista_titulos_prompt}

    REGLA: Responde ÚNICAMENTE con los 3 números de los índices elegidos separados por comas.
    """

    try:
        response = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": ROLE_INVESTIGADOR},
                {"role": "user", "content": prompt_usuario}
            ],
            options={"num_predict": 512, "temperature": 0.2}
        )

        seleccion_txt = response["message"]["content"]
        indices_elegidos = [int(n) for n in re.findall(r'\d+', seleccion_txt)][:3]

        print(f"Indices seleccionados por la IA: {indices_elegidos}\n")

        for idx in indices_elegidos:
            if 1 <= idx <= len(articulos):
                nodo_art = articulos[idx-1]
                titulo_final = nodo_art.find(".//ArticleTitle").text
                revista_nombre = nodo_art.find(".//Title").text
                year_node = nodo_art.find(".//PubDate/Year")
                year_text = year_node.text if year_node is not None else "N/A"
                abstract_nodes = nodo_art.findall(".//AbstractText")
                abstract_completo = " ".join([n.text for n in abstract_nodes if n.text]) or "[Abstract no disponible]"

                print(f"--- SELECCIÓN RELEVANTE: ARTÍCULO {idx} ---")
                print(f"TÍTULO: {titulo_final}\n")

                # Formateo para Quarto
                pubmed_seleccion_md += f"### Selección {idx}: {titulo_final}\n"
                pubmed_seleccion_md += f"* **Revista:** {revista_nombre} ({year_text})\n"
                pubmed_seleccion_md += f"* **Enlace:** [Ver en PubMed](https://pubmed.ncbi.nlm.nih.gov/{ids[idx-1]}/)\n\n"
                pubmed_seleccion_md += f"**Resumen del Abstract:**\n{abstract_completo[:1500]}...\n\n---\n"

    except Exception as e:
        print(f"Error en la fase del LLM: {e}")

# -----------------------------
# PREPARACIÓN DE ADVERTENCIAS
# -----------------------------
receta = str(seleccionado.get("receta", "")).upper()
advertencia_final = ADVERTENCIA_RECETA if receta == "S" else ADVERTENCIA_SIN_RECETA

print("\n===== ADVERTENCIA =====\n")
print(advertencia_final)
print("\n===== DISCLAIMER =====\n")
print(DISCLAIMER)

# =========================================================
# GENERACIÓN DE INFORME EN PDF (QUARTO)
# =========================================================
print("\n Generando informe PDF dinámico...")

nombre_med = seleccionado.get('nombre', 'Medicamento').upper()
nombre_archivo = "".join(x for x in nombre_med if x.isalnum() or x in "._- ").strip().replace(" ", "_")
articulos_txt = "\n".join([f"{i}. {a.find('.//ArticleTitle').text}" for i, a in enumerate(articulos, 1)])

# 1. Preparar la selección de PubMed para el cuerpo del PDF
pubmed_seleccion_md = ""
for idx in indices_elegidos:
    if 1 <= idx <= len(articulos):
        nodo = articulos[idx-1]
        titulo_art = nodo.find(".//ArticleTitle").text
        revista = nodo.find(".//Title").text
        # Año
        y_node = nodo.find(".//PubDate/Year")
        y_text = y_node.text if y_node is not None else "N/A"
        # Abstract
        abs_nodes = nodo.findall(".//AbstractText")
        abstract_txt = " ".join([n.text for n in abs_nodes if n.text]) or "No disponible"

        pubmed_seleccion_md += f"""
### Selección {idx}: {titulo_art}
* **Revista:** {revista} ({y_text})
* **Enlace:** [Ver en PubMed](https://pubmed.ncbi.nlm.nih.gov/{ids[idx-1]}/)

**Resumen del Abstract:**
{abstract_txt[:1500]}...

---
"""

# 2. Crear el contenido del archivo .qmd con el título dinámico
quarto_content = f"""---
title: "Informe Técnico: {nombre_med}"
subtitle: "Análisis Farmacológico y Evidencia Científica"
author: "Sistema de Análisis Inteligente"
date: "{time.strftime('%d/%m/%Y')}"
format:
  pdf:
    toc: true
    number-sections: true
    colorlinks: true
    papersize: a4
---

{DISCLAIMER}

# Resumen de Información (AEMPS)
{resumen}

# Principios Activos Identificados
Identificación de componentes y su correspondencia en nomenclatura internacional.

| Nombre en Castellano | Equivalente Inglés (DCI/INN) |
|----------------------|-----------------------------|
"""

for es, en in traduccion_map.items():
    quarto_content += f"| {es} | {en} |\n"

quarto_content += f"""

# Análisis de Literatura Científica (PubMed)
Se han recuperado los últimos {len(articulos)} títulos publicados para su triaje agéntico.

## Listado de publicaciones analizadas
{articulos_txt}

# Estudios de Mayor Relevancia Clínica
El modelo {MODEL} ha seleccionado los siguientes artículos basándose en su impacto potencial en la práctica clínica y calidad de evidencia:

{pubmed_seleccion_md}

# Información de Dispensación
**Tipo de prescripción:** {"Sujeto a receta médica" if receta == "S" else "No requiere receta médica"}

{advertencia_final}
"""

# 3. Escritura y Renderizado
nombre_qmd = f"informe_{nombre_archivo}.qmd"
with open(nombre_qmd, "w", encoding="utf-8") as f:
    f.write(quarto_content)

try:
    import subprocess
    print(f"Renderizando PDF para {nombre_med}...")
    # Ejecuta el comando de Quarto para convertir el .qmd en .pdf
    subprocess.run(["quarto", "render", nombre_qmd, "--to", "pdf"], check=True)
    print(f"\n Informe generado con éxito: informe_{nombre_archivo}.pdf")
except Exception as e:
    print(f"\n[ERROR] No se pudo generar el PDF: {e}")
