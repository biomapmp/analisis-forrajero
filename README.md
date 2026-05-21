---
title: Análisis Forrajero Satelital
emoji: 🌿
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
---

# 🌿 Sistema Satelital de Análisis Ambiental Integral

**Carbono + Biodiversidad + Análisis Forrajero + Pastoreo Racional Voisin**

## 🚀 Despliegue en Hugging Face Spaces

1. Crea un nuevo Space en [huggingface.co/spaces](https://huggingface.co/spaces)
2. Selecciona **Docker** como SDK (o sube este repositorio directamente)
3. Configura las variables de entorno (secrets):
   - `GROQ_API_KEY`: Para activar análisis con IA
   - `GEE_SERVICE_ACCOUNT`: Para datos satelitales reales de Google Earth Engine

## Funcionalidades

| Módulo | Descripción |
|--------|-------------|
| 🗺️ **Mapas de Calor** | Interpolación KNN de carbono, NDVI, NDWI, biodiversidad y forraje |
| 📊 **Dashboard** | KPIs ejecutivos con métricas ambientales clave |
| 🌳 **Carbono** | Metodología Verra VCS con 5 pools de carbono |
| 🦋 **Biodiversidad** | Índice de Shannon y distribución de especies |
| 🐮 **Forrajero** | Productividad, carga animal, sublotes |
| 🐄 **Pastoreo Racional Voisin** | División en parcelas, ciclos de pastoreo/descanso, planificación |
| 📥 **Informes** | PDF, DOCX, GeoJSON y análisis con IA (Groq) |

## 📁 Estructura

```
├── app.py                    # Aplicación Streamlit principal
├── Dockerfile                # Configuración del contenedor (HF Spaces)
├── modules/
│   ├── __init__.py
│   ├── ia_integration.py     # Integración con IA Groq
│   └── prv.py                # Modelo de Pastoreo Racional Voisin
├── requirements.txt          # Dependencias Python
├── packages.txt              # Dependencias sistema
└── README.md
```

## 🔧 Variables de Entorno (opcionales)

- `GROQ_API_KEY`: Clave API de Groq para análisis con IA
- `GEE_SERVICE_ACCOUNT`: JSON de cuenta de servicio de Google Earth Engine

## 📋 Formatos de carga soportados

- KML / KMZ
- GeoJSON
- Shapefile (ZIP)
