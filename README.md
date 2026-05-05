# Sistema de Análisis Farmacológico Automatizado con LLM y PubMed
## Descripción

Este proyecto implementa un pipeline automatizado para el análisis de medicamentos combinando datos oficiales, un modelo de lenguaje instalado localmente y evidencia científica reciente. A partir del nombre de un fármaco, el sistema consulta la API de AEMPS, genera un resumen técnico, traduce principios activos a nomenclatura internacional y analiza publicaciones recientes en PubMed para identificar estudios relevantes.

El resultado final es un informe estructurado en PDF orientado a un uso técnico, clínico o exploratorio.

PD:  este programa es una fusion,  evolucion y desde luego mejora de 2 proyectos anteriores que pueden consultarse por separado aqui:

https://github.com/fenris123/Python-Using-NCBI-API-to-find-scientific-articles-by-selected-terms
https://github.com/fenris123/API-LLM-to-obtain-a-resume-about-properties-of-a-medicament

# Funcionalidades
## Consulta de datos oficiales

Obtiene información del medicamento desde la API de la AEMPS (Agencia Española de Medicamentos y Productos Sanitarios), incluyendo nombre, composición y metadatos disponibles.

## Generación de resumen técnico

Utiliza un modelo LLM para sintetizar la información en un formato estructurado:

Principio activo, forma farmacéutica y vía
Indicaciones y posología
Advertencias
Traducción farmacológica


Traduce el nombre de los principios activos al ingles para facilitar la búsqueda científica posterior.

## Búsqueda en PubMed

Consulta los 20 artículos cientificos más recientes relacionados con los principios activos utilizando la API del NCBI.

## Selección de evidencia relevante

Un segundo agente LLM evalúa los títulos de los artículos y selecciona los más relevantes desde el punto de vista clínico.

## Generación de informe en PDF

Construye automáticamente un informe en formato Quarto (.qmd) y lo renderiza a PDF, incluyendo:


Resumen técnico
Tabla de principios activos
Listado de artículos analizados
Selección de estudios relevantes con resumen
Tecnologías utilizadas

## Lenguaje y entorno
Python 3

## Librerías principales

requests
ollama
xml.etree.ElementTree
json
subprocess

## APIs externas
API de la AEMPS (Agencia Española de Medicamentos y Productos Sanitarios)
NCBI E-utilities (PubMed)

## Modelos LLM
llama3.1:8b (ejecutado en local mediante Ollama)

## Generación de informes
Quarto

## Requisitos
Python 3.x

Ollama

Quarto

llama3.1:8b


# COMO EMPLEARLO
Introducir el nombre del medicamento
Seleccionar la presentación concreta del medicamento (Sucede si hay múltiples resultados por ejemplo, presentaciones con distintas dosis, o en capsulas y pastillas)

El sistema:

Consulta AEMPS

Genera resumen con LLM

Traduce principios activos al ingles

Busca artículos en PubMed

Selecciona los más relevantes

Genera informe en PDF


## Salida
Informe en PDF generado automáticamente

Archivo intermedio .qmd

Salida por consola con resultados y tiempos de ejecución



# Limitaciones
Dependencia de la calidad de los datos de AEMPS y NCBI
Selección de artículos basada solo en títulos
Rendimiento condicionado por el modelo LLM utilizado


# Disclaimer

Este sistema genera contenido automáticamente con fines informativos y educativos. No constituye consejo médico ni sustituye la consulta con un profesional sanitario. El uso de esta herramienta es responsabilidad exclusiva del usuario.
