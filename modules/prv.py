"""
Módulo de Pastoreo Racional Voisin (PRV).
Sistema de planificación de pastoreo basado en los principios de André Voisin:
períodos cortos de ocupación, descanso según recuperación del pasto,
alta densidad de carga y división en potreros.
"""

import math
import random
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


class ModeloPRV:
    """
    Modelo de Pastoreo Racional Voisin.
    Planifica la división de potreros, ciclos de pastoreo/descanso
    y carga animal según productividad forrajera.
    """

    def __init__(self):
        # Parámetros fisiológicos del pasto (Voisin)
        self.tasa_recuperacion_base = 1.0        # cm/día en condiciones óptimas
        self.tasa_recuperacion_min = 0.3          # cm/día en condiciones adversas
        self.altura_entrada = 25                  # cm (altura ideal para entrar al pastoreo)
        self.altura_salida = 7                    # cm (altura de salida - residual)
        self.altura_minima_descanso = 5           # cm (mínimo para no dañar planta)

        # Consumo animal
        self.consumo_ev_diario_kg = 12.0          # kg MS/EV/día
        self.aprovechamiento = 0.55               # tasa de aprovechamiento
        self.eficiencia_cosecha = 0.6             # eficiencia de cosecha del animal

        # Factores de ajuste por estación
        self.factores_estacionales = {
            "primavera": {"temperatura_optima": 22, "crecimiento": 1.3, "descanso_min": 25},
            "verano":    {"temperatura_optima": 28, "crecimiento": 1.0, "descanso_min": 30},
            "otoño":     {"temperatura_optima": 18, "crecimiento": 0.7, "descanso_min": 40},
            "invierno":  {"temperatura_optima": 12, "crecimiento": 0.4, "descanso_min": 60},
        }

    def determinar_estacion(self, mes: int = None) -> str:
        if mes is None:
            mes = datetime.now().month
        if mes in [9, 10, 11]:
            return "primavera"
        elif mes in [12, 1, 2]:
            return "verano"
        elif mes in [3, 4, 5]:
            return "otoño"
        else:
            return "invierno"

    def calcular_periodo_descanso(
        self, temperatura: float = 22, precipitacion: float = 100, mes: int = None
    ) -> int:
        """
        Calcula el período de descanso necesario (días) según Voisin.
        El descanso depende de: temperatura, humedad, fertilidad y tipo de pasto.
        Regla de Voisin: descanso = tiempo para que el pasto alcance altura de entrada.
        """
        estacion = self.determinar_estacion(mes)
        factor_est = self.factores_estacionales[estacion]

        # Ajuste por temperatura (curva óptima)
        temp_opt = factor_est["temperatura_optima"]
        factor_temp = max(0.2, 1.0 - abs(temperatura - temp_opt) / 40)

        # Ajuste por precipitación
        factor_precip = min(1.5, max(0.2, precipitacion / 100))

        # Tasa de recuperación efectiva (cm/día)
        tasa_efectiva = (
            self.tasa_recuperacion_base
            * factor_est["crecimiento"]
            * factor_temp
            * factor_precip
        )

        # Días para recuperar altura de pastoreo (entrada - salida)
        altura_recuperar = self.altura_entrada - self.altura_salida
        descanso_base = altura_recuperar / max(tasa_efectiva, 0.05)

        # Aplicar descanso mínimo estacional
        descanso_min = factor_est["descanso_min"]
        descanso = max(descanso_min, int(descanso_base * 1.2))  # +20% seguridad

        return min(120, descanso)  # máximo 120 días

    def calcular_periodo_ocupacion(
        self,
        forraje_disponible_kg_ms_ha: float,
        densidad_forraje_kg_ms_cm: float = 250,
        num_ev: float = 100,
        area_ha: float = 10,
    ) -> int:
        """
        Calcula el período de ocupación óptimo (días) para un potrero.
        Voisin recomienda máximo 3 días, ideal 1 día.
        """
        forraje_aprovechable = forraje_disponible_kg_ms_ha * area_ha * self.aprovechamiento
        consumo_total = num_ev * self.consumo_ev_diario_kg
        if consumo_total <= 0:
            return 1
        ocupacion = forraje_aprovechable / consumo_total
        return max(1, min(3, int(round(ocupacion))))

    def calcular_numero_potreros(self, descanso_dias: int, ocupacion_dias: int = 1) -> int:
        """
        Fórmula de Voisin: N = (P / O) + 1
        donde N = número de potreros, P = días de descanso, O = días de ocupación.
        """
        if ocupacion_dias <= 0:
            ocupacion_dias = 1
        num = int(math.ceil(descanso_dias / ocupacion_dias)) + 1
        return max(4, min(60, num))

    def calcular_carga_animal(
        self,
        forraje_total_aprovechable_kg: float,
        area_total_ha: float,
        periodo_dias: int = 30,
    ) -> Dict:
        """
        Calcula la carga animal en EV para un período y área determinados.
        Retorna carga instantánea y carga promedio.
        """
        consumo_diario_total = forraje_total_aprovechable_kg / max(periodo_dias, 1)
        ev_totales = consumo_diario_total / self.consumo_ev_diario_kg
        carga_instantanea_ev_ha = ev_totales / max(area_total_ha, 0.1)
        carga_promedio_ev_ha = carga_instantanea_ev_ha / periodo_dias

        return {
            "ev_totales": round(ev_totales, 1),
            "carga_instantanea_ev_ha": round(carga_instantanea_ev_ha, 2),
            "carga_promedio_ev_ha": round(carga_promedio_ev_ha, 2),
            "area_total_ha": round(area_total_ha, 2),
            "periodo_dias": periodo_dias,
        }

    def generar_potreros_desde_cuadricula(
        self,
        gdf_cuadricula,
        num_potreros: int = 20,
        poligono_limite=None,
    ):
        """
        Agrupa las celdas de la cuadrícula forrajera en potreros PRV,
        priorizando que cada potrero tenga productividad homogénea.
        Retorna un GeoDataFrame con los potreros.
        """
        import geopandas as gpd
        from shapely.geometry import Polygon, MultiPolygon
        from shapely.ops import unary_union

        if gdf_cuadricula is None or gdf_cuadricula.empty:
            return None

        if len(gdf_cuadricula) < num_potreros:
            num_potreros = max(4, len(gdf_cuadricula))

        gdf = gdf_cuadricula.copy()
        gdf["prod_rank"] = gdf["productividad_kg_ms_ha"].rank(pct=True)
        gdf["potrero_id"] = pd.qcut(
            gdf["prod_rank"], q=num_potreros, labels=False, duplicates="drop"
        ) + 1

        potreros = gdf.dissolve(by="potrero_id", aggfunc={
            "productividad_kg_ms_ha": "mean",
        }).reset_index()
        potreros.columns = ["potrero_id", "geometry", "productividad_prom_kg_ms_ha"]

        potreros["area_ha"] = potreros.geometry.area * 111000 * 111000 / 10000
        potreros["productividad_relativa"] = (
            potreros["productividad_prom_kg_ms_ha"]
            / potreros["productividad_prom_kg_ms_ha"].mean()
        )

        potreros = potreros.sort_values("potrero_id").reset_index(drop=True)
        return potreros

    def dividir_poligono_en_potreros(
        self, poligono, num_potreros: int = 20, productividades: List[float] = None
    ):
        """
        Divide un polígono en N potreros delimitados por franjas.
        Si se proporcionan productividades, agrupa zonas de productividad similar.
        """
        from shapely.geometry import Polygon, box
        import geopandas as gpd

        bounds = poligono.bounds
        minx, miny, maxx, maxy = bounds

        ancho = maxx - minx
        alto = maxy - miny

        if ancho >= alto:
            num_filas = 1
            num_columnas = num_potreros
        else:
            num_filas = num_potreros
            num_columnas = 1

        # Mejor distribución: tratar de hacerlo lo más cuadrado posible
        ratio = ancho / alto if alto > 0 else 1
        num_columnas = max(1, int(round(math.sqrt(num_potreros * ratio))))
        num_filas = max(1, int(round(num_potreros / num_columnas)))

        while num_columnas * num_filas < num_potreros:
            if num_columnas <= num_filas:
                num_columnas += 1
            else:
                num_filas += 1

        potreros = []
        dx = ancho / num_columnas
        dy = alto / num_filas

        idx = 0
        for i in range(num_filas):
            for j in range(num_columnas):
                if idx >= num_potreros:
                    break
                cell_minx = minx + j * dx
                cell_maxx = minx + (j + 1) * dx
                cell_miny = miny + i * dy
                cell_maxy = miny + (i + 1) * dy

                cell_box = box(cell_minx, cell_miny, cell_maxx, cell_maxy)
                intersection = poligono.intersection(cell_box)

                if intersection.is_empty or intersection.area == 0:
                    continue

                if productividades and idx < len(productividades):
                    prod = productividades[idx]
                else:
                    prod = 2500 + random.uniform(-500, 500)

                area_m2 = intersection.area * 111000 * 111000
                area_ha = area_m2 / 10000

                potreros.append({
                    "potrero_id": idx + 1,
                    "geometry": intersection,
                    "productividad_kg_ms_ha": round(prod, 0),
                    "area_ha": round(area_ha, 2),
                })
                idx += 1

        if not potreros:
            return None

        gdf_potreros = gpd.GeoDataFrame(potreros, crs="EPSG:4326")
        gdf_potreros["productividad_relativa"] = (
            gdf_potreros["productividad_kg_ms_ha"]
            / gdf_potreros["productividad_kg_ms_ha"].mean()
        )
        return gdf_potreros

    def planificar_ciclo_prv(
        self,
        num_potreros: int,
        descanso_dias: int,
        ocupacion_dias: int = 1,
        fecha_inicio: datetime = None,
        num_ciclos: int = 4,
    ) -> pd.DataFrame:
        """
        Genera el plan de pastoreo para N ciclos siguiendo PRV.
        Cada fila = evento de pastoreo para un potrero.
        """
        if fecha_inicio is None:
            fecha_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        registros = []
        fecha_actual = fecha_inicio

        for ciclo in range(1, num_ciclos + 1):
            for potrero in range(1, num_potreros + 1):
                fecha_ocupacion = fecha_actual + timedelta(days=(potrero - 1) * ocupacion_dias)
                fecha_salida = fecha_ocupacion + timedelta(days=ocupacion_dias)
                fecha_prox_entrada = fecha_salida + timedelta(days=descanso_dias)

                registros.append({
                    "ciclo": ciclo,
                    "potrero_id": potrero,
                    "fecha_entrada": fecha_ocupacion,
                    "fecha_salida": fecha_salida,
                    "dias_ocupacion": ocupacion_dias,
                    "dias_descanso_siguiente": descanso_dias,
                    "fecha_proxima_entrada": fecha_prox_entrada,
                    "estado": "pastoreo",
                })

            fecha_actual += timedelta(days=num_potreros * ocupacion_dias)

        df = pd.DataFrame(registros)
        return df

    def calcular_estado_potreros(
        self,
        gdf_potreros,
        plan_pastoreo: pd.DataFrame,
        fecha_referencia: datetime = None,
    ) -> pd.DataFrame:
        """
        Determina el estado actual de cada potrero según el plan de pastoreo:
        - 'pastoreo': se está pastoreando ahora
        - 'descanso': está en período de descanso
        - 'listo': completó descanso y está listo para pastorear
        - 'por_pastorear': aún no ha sido pastoreado en este ciclo
        """
        if fecha_referencia is None:
            fecha_referencia = datetime.now()

        estados = []
        for _, potrero in gdf_potreros.iterrows():
            pid = potrero["potrero_id"]

            # Filtrar eventos de este potrero
            eventos = plan_pastoreo[plan_pastoreo["potrero_id"] == pid].copy()

            if eventos.empty:
                estados.append({
                    "potrero_id": pid,
                    "estado": "sin_planificar",
                    "dias_restantes": 0,
                    "forraje_acumulado_kg_ms": 0,
                })
                continue

            # Buscar evento activo
            evento_activo = None
            for _, ev in eventos.iterrows():
                if ev["fecha_entrada"] <= fecha_referencia <= ev["fecha_salida"]:
                    evento_activo = ev
                    estado = "pastoreo"
                    dias_restantes = (ev["fecha_salida"] - fecha_referencia).days
                    forraje_acumulado = 0
                    break

            if evento_activo is None:
                # Buscar el último evento completado
                eventos_pasados = eventos[eventos["fecha_salida"] <= fecha_referencia]
                if not eventos_pasados.empty:
                    ultimo = eventos_pasados.iloc[-1]
                    dias_desde_salida = (fecha_referencia - ultimo["fecha_salida"]).days
                    if dias_desde_salida >= ultimo["dias_descanso_siguiente"]:
                        estado = "listo"
                        dias_restantes = 0
                    else:
                        estado = "descanso"
                        dias_restantes = ultimo["dias_descanso_siguiente"] - dias_desde_salida
                    # Forraje acumulado estimado
                    tasa = 30  # kg MS/ha/día (estimado)
                    forraje_acumulado = min(
                        potrero.get("productividad_kg_ms_ha", 3000),
                        max(0, dias_desde_salida) * tasa * potrero.get("area_ha", 1),
                    )
                else:
                    # Aún no se ha pastoreado (primer ciclo)
                    estado = "por_pastorear"
                    dias_restantes = (eventos.iloc[0]["fecha_entrada"] - fecha_referencia).days
                    forraje_acumulado = potrero.get("productividad_kg_ms_ha", 3000) * potrero.get("area_ha", 1)

            estados.append({
                "potrero_id": pid,
                "estado": estado,
                "dias_restantes": max(0, dias_restantes) if "dias_restantes" in dir() else 0,
                "forraje_acumulado_kg_ms": round(forraje_acumulado),
            })

        return pd.DataFrame(estados)

    def generar_recomendaciones_prv(
        self,
        gdf_potreros,
        estados_df: pd.DataFrame,
        temperatura: float = 22,
        precipitacion: float = 100,
    ) -> str:
        """Genera recomendaciones de manejo PRV en texto."""
        num_potreros = len(gdf_potreros)
        en_pastoreo = len(estados_df[estados_df["estado"] == "pastoreo"])
        en_descanso = len(estados_df[estados_df["estado"] == "descanso"])
        listos = len(estados_df[estados_df["estado"] == "listo"])
        sin_plan = len(estados_df[estados_df["estado"] == "sin_planificar"])

        area_total = gdf_potreros["area_ha"].sum()
        prod_prom = gdf_potreros["productividad_kg_ms_ha"].mean()

        lineas = [
            f"📋 **Plan de Pastoreo Racional Voisin**",
            f"",
            f"**Potreros:** {num_potreros} en {area_total:.1f} ha",
            f"**Productividad media:** {prod_prom:,.0f} kg MS/ha",
            f"**Estado actual:** {en_pastoreo} en pastoreo | {en_descanso} en descanso | {listos} listos | {sin_plan} sin planificar",
            f"**Temperatura:** {temperatura:.0f}°C | **Precipitación:** {precipitacion:.0f} mm",
            f"",
            f"**Recomendaciones:**",
        ]

        descanso_est = self.calcular_periodo_descanso(temperatura, precipitacion)

        if listos > 0:
            lineas.append(
                f"  ✅ {listos} potrero(s) listos para pastorear. "
                f"Considere rotar al potrero con mayor forraje acumulado."
            )
        if en_pastoreo > 1:
            lineas.append(
                f"  ⚠️ Hay {en_pastoreo} potreros en pastoreo simultáneo. "
                f"PRV ideal: 1 potrero a la vez."
            )
        lineas.append(
            f"  💡 Período de descanso estimado: {descanso_est} días "
            f"(ajustar según rebrote observado)."
        )
        lineas.append(
            f"  📐 Carga instantánea recomendada: alta densidad (>50 EV/ha) "
            f"con ocupación máxima de 3 días."
        )
        lineas.append(
            f"  🌱 Altura de entrada: {self.altura_entrada} cm | "
            f"Altura de salida: {self.altura_salida} cm (respetar para no sobrepastorear)."
        )

        return "\n".join(lineas)

    def a_forraje_acumulado_curva(self, dias_descanso: int, productividad_base: float) -> List[float]:
        """
        Genera la curva de acumulación de forraje (kg MS/ha) durante el período de descanso.
        Sigue una curva sigmoidea típica de crecimiento de pasturas.
        """
        curva = []
        for d in range(1, dias_descanso + 1):
            t = d / dias_descanso
            acum = productividad_base * (1 / (1 + math.exp(-10 * (t - 0.4))))
            curva.append(round(acum, 0))
        return curva

    def resumen_ejecutivo(self, gdf_potreros, estados_df, plan_pastoreo) -> Dict:
        """Retorna métricas clave del sistema PRV."""
        if gdf_potreros is None or gdf_potreros.empty:
            return {}

        area_total = gdf_potreros["area_ha"].sum()
        prod_total = (gdf_potreros["productividad_kg_ms_ha"] * gdf_potreros["area_ha"]).sum()
        prod_prom = prod_total / area_total if area_total > 0 else 0

        forraje_total_est = estados_df["forraje_acumulado_kg_ms"].sum()
        ev_soportables = forraje_total_est / (self.consumo_ev_diario_kg * 30) if forraje_total_est > 0 else 0

        return {
            "num_potreros": len(gdf_potreros),
            "area_total_ha": round(area_total, 2),
            "productividad_prom_kg_ms_ha": round(prod_prom, 0),
            "forraje_total_estimado_kg_ms": round(prod_total, 0),
            "forraje_disponible_actual_kg_ms": round(forraje_total_est, 0),
            "ev_soportables_30d": round(ev_soportables, 1),
            "potreros_en_pastoreo": int((estados_df["estado"] == "pastoreo").sum()),
            "potreros_en_descanso": int((estados_df["estado"] == "descanso").sum()),
            "potreros_listos": int((estados_df["estado"] == "listo").sum()),
            "potreros_por_pastorear": int((estados_df["estado"] == "por_pastorear").sum()),
        }
