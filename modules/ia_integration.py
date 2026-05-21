"""
Módulo de integración con IA (Groq) para análisis ambiental.
Proporciona funciones de análisis de texto y preparación de datos.
"""

import os
import json
import random
from typing import Optional, Dict, Any, List, Tuple, Union
import pandas as pd
import numpy as np

GROQ_API_KEY: Optional[str] = os.environ.get("GROQ_API_KEY")
client = None
available_models: List[str] = []

if GROQ_API_KEY:
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        available_models = [
            "llama3-70b-8192",
            "llama3-8b-8192",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ]
    except ImportError:
        client = None
        available_models = []
else:
    client = None
    available_models = []


def preparar_resumen(resultados: Dict) -> Tuple[pd.DataFrame, Dict]:
    stats = {
        "area_total_ha": resultados.get("area_total_ha", 0),
        "carbono_total_ton": resultados.get("carbono_total_ton", 0),
        "co2_total_ton": resultados.get("co2_total_ton", 0),
        "shannon_promedio": resultados.get("shannon_promedio", 0),
        "ndvi_promedio": resultados.get("ndvi_promedio", 0),
        "ndwi_promedio": resultados.get("ndwi_promedio", 0),
        "tipo_ecosistema": resultados.get("tipo_ecosistema", "N/A"),
        "num_puntos": resultados.get("num_puntos", 0),
    }
    filas = []
    for i, p in enumerate(resultados.get("puntos_carbono", [])):
        filas.append(
            {
                "punto": i + 1,
                "lat": p["lat"],
                "lon": p["lon"],
                "carbono_ton_ha": p.get("carbono_ton_ha", 0),
                "ndvi_est": p.get("ndvi", 0),
            }
        )
    df = pd.DataFrame(filas)
    return df, stats


def _consulta_ia(prompt: str, model: str = "llama3-70b-8192") -> str:
    if client is None:
        return _generar_simulado(prompt)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un experto en análisis ambiental, cambio climático,"
                        " biodiversidad, sistemas forrajeros y Pastoreo Racional Voisin (PRV)."
                        " Responde en español técnico pero accesible. Máximo 300 palabras."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=800,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return _generar_simulado(prompt)


def _generar_simulado(prompt: str) -> str:
    frases = [
        "El análisis de los datos sugiere que el ecosistema presenta condiciones favorables para el secuestro de carbono, con valores dentro del rango esperado para el tipo de vegetación evaluado.",
        "Se recomienda implementar prácticas de manejo sostenible que favorezcan la regeneración natural y el aumento de la materia orgánica del suelo.",
        "La biodiversidad del área refleja un estado de conservación moderado, con oportunidades de mejora mediante la restauración de corredores biológicos.",
        "Para el sistema forrajero, la productividad estimada permite una carga animal moderada. Se sugiere pastoreo rotativo con períodos de descanso adecuados.",
        "Los índices espectrales (NDVI, NDWI) indican una cobertura vegetal heterogénea. Las zonas con mayor NDVI coinciden con mayor almacenamiento de carbono.",
        "El potencial de créditos de carbono es significativo si se implementan prácticas de manejo mejoradas como sistemas silvopastoriles o regeneración asistida.",
    ]
    return (
        "📋 **Análisis automático (IA no disponible):**\n\n"
        + "\n\n".join(random.sample(frases, min(3, len(frases))))
        + "\n\n*Para un análisis detallado con IA, configure la variable GROQ_API_KEY.*"
    )


def generar_analisis_carbono(df: pd.DataFrame, stats: Dict) -> str:
    prompt = (
        f"Analiza los siguientes datos de carbono de un área de {stats['area_total_ha']:.1f} ha "
        f"con {stats['num_puntos']} puntos de muestreo. "
        f"Carbono total: {stats['carbono_total_ton']:.0f} ton C, "
        f"CO2 equivalente: {stats['co2_total_ton']:.0f} ton CO2e. "
        f"Proporciona una interpretación técnica breve."
    )
    return _consulta_ia(prompt)


def generar_analisis_biodiversidad(df: pd.DataFrame, stats: Dict) -> str:
    prompt = (
        f"Interpreta el índice de Shannon promedio de {stats['shannon_promedio']:.3f} "
        f"para un área de {stats['area_total_ha']:.1f} ha de tipo {stats['tipo_ecosistema']}. "
        f"Explica el nivel de biodiversidad y recomendaciones de manejo."
    )
    return _consulta_ia(prompt)


def generar_analisis_espectral(df: pd.DataFrame, stats: Dict) -> str:
    prompt = (
        f"Analiza los índices espectrales: NDVI promedio {stats['ndvi_promedio']:.3f}, "
        f"NDWI promedio {stats['ndwi_promedio']:.3f}. "
        f"¿Qué indican sobre la salud de la vegetación y disponibilidad hídrica?"
    )
    return _consulta_ia(prompt)


def generar_analisis_forrajero(df: pd.DataFrame, stats: Dict) -> str:
    prompt = (
        f"Evalúa la productividad forrajera para un área de {stats['area_total_ha']:.1f} ha. "
        f"Recomienda estrategias de pastoreo rotativo y carga animal adecuada."
    )
    return _consulta_ia(prompt)


def generar_recomendaciones_integradas(df: pd.DataFrame, stats: Dict) -> str:
    prompt = (
        f"Genera recomendaciones de manejo integrado para un área de {stats['area_total_ha']:.1f} ha "
        f"con ecosistema {stats['tipo_ecosistema']}. "
        f"Considera carbono, biodiversidad y producción forrajera."
    )
    return _consulta_ia(prompt)


def generar_plan_transicion_prv(params: Dict[str, Any]) -> str:
    """
    Genera un plan de transición de ganadería convencional a PRV
    con enfoque de ganadería regenerativa.

    Parámetros:
        params: Diccionario con datos del establecimiento:
            - tipo_ganado (str): bovino, ovino, caprino, etc.
            - cabeza (int): cantidad de animales
            - area_ha (float): hectáreas totales
            - sistema_actual (str): pastoreo continuo, rotativo simple, estabulado, etc.
            - descanso_actual_dias (int): días de descanso actuales
            - ocupacion_actual_dias (int): días de ocupación actuales
            - tiene_agua (bool): disponibilidad de agua en potreros
            - tiene_divisiones (bool): si ya tiene potreros divididos
            - condicion_suelo (str): degradado, regular, bueno, excelente
            - objetivo_principal (str): carne, leche, mixto, regeneración
            - ecosistema (str): tipo de ecosistema
            - productividad_forraje (float): kg MS/ha estimado
    """
    tipo = params.get('tipo_ganado', 'bovino')
    cabeza = params.get('cabeza', 0)
    area = params.get('area_ha', 0)
    sistema = params.get('sistema_actual', 'pastoreo continuo')
    descanso = params.get('descanso_actual_dias', 0)
    ocupacion = params.get('ocupacion_actual_dias', 0)
    tiene_agua = params.get('tiene_agua', False)
    tiene_div = params.get('tiene_divisiones', False)
    suelo = params.get('condicion_suelo', 'regular')
    objetivo = params.get('objetivo_principal', 'carne')
    ecosistema = params.get('ecosistema', 'no especificado')
    prod_forraje = params.get('productividad_forraje', 0)

    prompt = f"""
Eres un especialista en Pastoreo Racional Voisin (PRV) y ganadería regenerativa con 30 años de experiencia en Latinoamérica.

Un productor quiere migrar de su sistema actual a PRV. Sus datos:

- **Tipo de ganado:** {tipo}
- **Cantidad de animales:** {cabeza} cabezas
- **Superficie total:** {area:.1f} ha
- **Sistema actual:** {sistema}
- **Descanso actual:** {descanso} días
- **Ocupación actual:** {ocupacion} días
- **Dispone de agua en potreros:** {'Sí' if tiene_agua else 'No'}
- **Divisiones existentes:** {'Sí' if tiene_div else 'No'}
- **Condición del suelo:** {suelo}
- **Objetivo principal:** {objetivo}
- **Ecosistema:** {ecosistema}
- **Productividad forrajera:** {prod_forraje:,.0f} kg MS/ha

Genera un plan de transición PRV estructurado en estas secciones:

1. **Diagnóstico rápido**: evalúa el punto de partida y las oportunidades principales.
2. **Diseño PRV propuesto**: número de potreros sugerido, días de descanso según estación, ocupación ideal, carga animal instantánea (EV/ha).
3. **Plan de transición por etapas** (6 a 18 meses):
   - Etapa 1 (0-3 meses): adecuaciones de infraestructura (agua, divisiones, sombra)
   - Etapa 2 (3-6 meses): implementación inicial con pocos potreros
   - Etapa 3 (6-12 meses): ajuste de carga y períodos
   - Etapa 4 (12-18 meses): consolidación PRV pleno
4. **Recomendaciones regenerativas específicas**: manejo de suelo, pasturas perennes, integración arbórea, abrevado rotativo.
5. **Indicadores de éxito**: qué medir y cómo saber si la transición va bien.

Responde en español claro y técnico. Usa viñetas y maximiza el contenido práctico. No des rodeos teóricos innecesarios. Máximo 600 palabras.
"""
    return _consulta_ia(prompt)
