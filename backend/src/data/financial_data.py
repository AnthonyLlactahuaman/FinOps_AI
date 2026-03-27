"""
Módulo de datos financieros - Lectura y análisis simple con pandas
"""
import pandas as pd
from typing import Optional, Dict, List


def load_excel(path: str = "data/Datos_Consolidados.xlsx") -> pd.DataFrame:
    """
    Carga el archivo Excel con datos financieros y retornar DataFrame
    """
    try:
        df = pd.read_excel(path)
        #print(f"Columnas disponibles: {df.columns.tolist()}")
        return df
    except Exception as e:
        print(f"Error al cargar Excel: {e}")
        raise


def analyze_with_filters(
    gerencia: Optional[str] = None,
    pais: Optional[str] = None,
    centro_costo: Optional[str] = None,
    id_value: Optional[str] = None,
    periodo: Optional[List[int]] = None
) -> Dict:
    """
    Analiza presupuesto vs real aplicando filtros dinámicos
    """
    df = load_excel()
    filtros_aplicados = []
    #print(f"Filtros: {gerencia}, {pais}, {centro_costo}, {id_value}, {periodo}")
    # Aplicar filtros dinámicamente
    if gerencia:
        gerencia = gerencia.upper().strip()
        df = df[df['TORRE'].str.upper() == gerencia]
        filtros_aplicados.append(f"GERENCIA={gerencia}")
    
    if pais:
        pais = pais.upper().strip()
        df = df[df['PAIS'].str.upper() == pais]
        filtros_aplicados.append(f"PAIS={pais}")
    
    if centro_costo:
        centro_costo = centro_costo.upper().strip()
        df = df[df['CENTRO DE COSTE'].str.upper() == centro_costo]
        filtros_aplicados.append(f"CECO={centro_costo}")
    
    if id_value:
        id_value = str(id_value).upper().strip()
        df = df[df['ID'].astype(str).str.upper() == id_value]
        filtros_aplicados.append(f"ID={id_value}")
    
    if periodo:
        df = df[df['PERIODO'].isin(periodo)]
        filtros_aplicados.append(f"PERIODO={','.join(map(str, periodo))}")
    
    if df.empty:
        return {
            "filtros": filtros_aplicados or ["Ninguno"],
            "encontrado": False,
            "mensaje": "No se encontraron datos con los filtros especificados"
        }
    
    # Calcular PB y REAL
    pb_data = df[df['TIPO BASE'] == 'PB']
    real_data = df[df['TIPO BASE'] == 'REAL']
    
    total_presupuesto = pb_data['MONTO USD'].sum() if not pb_data.empty else 0.0
    total_real = real_data['MONTO USD'].sum() if not real_data.empty else 0.0
    
    varianza = total_real - total_presupuesto
    varianza_porcentaje = (varianza / total_presupuesto * 100) if total_presupuesto != 0 else 0.0
    
    # Determinar severidad
    abs_varianza = abs(varianza_porcentaje)
    if abs_varianza > 50:
        severidad = "CRÍTICA"
    elif abs_varianza > 30:
        severidad = "MODERADA"
    elif abs_varianza > 10:
        severidad = "BAJA"
    else:
        severidad = "NINGUNA"
    
    return {
        "filtros": filtros_aplicados or ["Ninguno"],
        "presupuesto_pb": round(float(total_presupuesto), 2),
        "gasto_real": round(float(total_real), 2),
        "varianza": round(float(varianza), 2),
        "varianza_porcentaje": round(float(varianza_porcentaje), 2),
        "severidad": severidad,
        "registros_analizados": len(df),
        "moneda": "USD"
    }


def get_top_variances(
    top_n: int = 5, 
    threshold: Optional[float] = None,
    gerencia: Optional[str] = None,
    pais: Optional[str] = None,
    centro_costo: Optional[str] = None,
    periodo: Optional[List[int]] = None
) -> List[Dict]:
    """
    Identifica los N IDs con mayores desviaciones presupuestarias.
    Filtra por TORRE, PAIS, CENTRO DE COSTE y PERIODO, luego agrupa por ID
    para calcular varianzas y devuelve los top N con mayor desviación.
    Nota: No filtra por ID ya que el objetivo es descubrir cuáles tienen más varianza.
    """
    df = load_excel()
    
    # Aplicar filtros (NO se filtra por ID)
    if gerencia:
        df = df[df['TORRE'].str.upper() == gerencia.upper().strip()]
    if pais:
        df = df[df['PAIS'].str.upper() == pais.upper().strip()]
    if centro_costo:
        df = df[df['CENTRO DE COSTE'].str.upper() == centro_costo.upper().strip()]
    if periodo:
        df = df[df['PERIODO'].isin(periodo)]
    
    # Agrupar por ID para calcular varianzas
    ids = df['ID'].unique()
    
    resultados = []
    for id_val in ids:
        id_df = df[df['ID'] == id_val]
        
        pb_data = id_df[id_df['TIPO BASE'] == 'PB']
        real_data = id_df[id_df['TIPO BASE'] == 'REAL']
        
        total_pb = pb_data['MONTO USD'].sum() if not pb_data.empty else 0.0
        total_real = real_data['MONTO USD'].sum() if not real_data.empty else 0.0
        
        varianza = total_real - total_pb
        varianza_pct = (varianza / total_pb * 100) if total_pb != 0 else 0.0
        
        # Obtener TORRE asociada al ID para contexto
        torre = id_df['TORRE'].iloc[0] if not id_df.empty else "N/A"
        
        # Aplicar filtro de umbral
        if threshold is None or abs(varianza_pct) >= threshold:
            resultados.append({
                "id": str(id_val),
                "torre": torre,
                "presupuesto_pb": round(float(total_pb), 2),
                "gasto_real": round(float(total_real), 2),
                "varianza": round(float(varianza), 2),
                "varianza_porcentaje": round(float(varianza_pct), 2),
                "moneda": "USD"
            })
    
    # Ordenar por valor absoluto de varianza porcentual
    resultados.sort(key=lambda x: abs(x.get('varianza_porcentaje', 0)), reverse=True)
    
    return resultados[:top_n]


def get_expense_trend(
    gerencia: Optional[str] = None,
    pais: Optional[str] = None,
    centro_costo: Optional[str] = None,
    periodo: Optional[List[int]] = None
) -> Dict:
    """
    Analiza la tendencia de gastos aplicando filtros dinámicos.
    Si se proporciona un solo periodo, analiza desde ese mes hasta 3 meses después.
    Si se proporcionan varios periodos, analiza exactamente esos meses.
    Si no se proporciona periodo, analiza todos los periodos disponibles.
    """
    df = load_excel()
    
    # Solo gastos REALES
    filtered = df[df['TIPO BASE'] == 'REAL'].copy()
    
    filtros_aplicados = []
    
    # Aplicar filtros
    if gerencia:
        gerencia = gerencia.upper().strip()
        filtered = filtered[filtered['TORRE'].str.upper() == gerencia]
        filtros_aplicados.append(f"GERENCIA={gerencia}")
    
    if pais:
        pais = pais.upper().strip()
        filtered = filtered[filtered['PAIS'].str.upper() == pais]
        filtros_aplicados.append(f"PAIS={pais}")
    
    if centro_costo:
        centro_costo = centro_costo.upper().strip()
        filtered = filtered[filtered['CENTRO DE COSTE'].str.upper() == centro_costo]
        filtros_aplicados.append(f"CECO={centro_costo}")
    
    # Lógica de periodos
    if periodo:
        if len(periodo) == 1:
            # Un solo periodo: expandir a ese mes + 3 meses siguientes
            inicio = periodo[0]
            periodos_expandidos = [m for m in range(inicio, min(inicio + 4, 13))]
            filtered = filtered[filtered['PERIODO'].isin(periodos_expandidos)]
            filtros_aplicados.append(f"PERIODO={','.join(map(str, periodos_expandidos))} (expandido desde mes {inicio})")
        else:
            # Múltiples periodos: usar exactamente esos
            filtered = filtered[filtered['PERIODO'].isin(periodo)]
            filtros_aplicados.append(f"PERIODO={','.join(map(str, periodo))}")
    
    if filtered.empty:
        return {
            "filtros": filtros_aplicados or ["Ninguno"],
            "encontrado": False,
            "mensaje": "No se encontraron datos REALES con los filtros especificados"
        }
    
    # Agrupar por periodo y sumar
    tendencia = filtered.groupby('PERIODO')['MONTO USD'].sum().sort_index()
    
    if len(tendencia) < 2:
        return {
            "filtros": filtros_aplicados or ["Ninguno"],
            "meses_analizados": len(tendencia),
            "datos_insuficientes": True,
            "mensaje": "Se necesitan al menos 2 periodos para análisis de tendencia"
        }
    
    # Calcular cambios mes a mes
    periodos_lista = tendencia.index.tolist()
    valores_lista = tendencia.values.tolist()
    
    cambios = []
    for i in range(1, len(valores_lista)):
        valor_anterior = valores_lista[i-1]
        valor_actual = valores_lista[i]
        cambio_pct = ((valor_actual - valor_anterior) / valor_anterior * 100) if valor_anterior != 0 else 0
        cambios.append(cambio_pct)
    
    # Determinar tendencia general
    if len(cambios) >= 3:
        cambios_recientes = cambios[-3:]
        if all(c > 0 for c in cambios_recientes):
            tendencia_general = "AUMENTANDO (3 meses consecutivos al alza)"
        elif all(c < 0 for c in cambios_recientes):
            tendencia_general = "DISMINUYENDO (3 meses consecutivos a la baja)"
        else:
            tendencia_general = "ESTABLE"
    else:
        promedio_cambio = sum(cambios) / len(cambios)
        if promedio_cambio > 5:
            tendencia_general = "AUMENTANDO"
        elif promedio_cambio < -5:
            tendencia_general = "DISMINUYENDO"
        else:
            tendencia_general = "ESTABLE"
    
    # Detectar volatilidad excesiva (> 30%)
    alertas_volatilidad = [
        f"Periodo {periodos_lista[i]} → {periodos_lista[i+1]}: {cambios[i]:.2f}%"
        for i, cambio in enumerate(cambios)
        if abs(cambio) > 30
    ]
    
    return {
        "filtros": filtros_aplicados or ["Ninguno"],
        "meses_analizados": len(tendencia),
        "periodos": periodos_lista,
        "valores_usd": [round(float(v), 2) for v in valores_lista],
        "cambios_mes_a_mes_porcentaje": [round(c, 2) for c in cambios],
        "tendencia": tendencia_general,
        "alertas_volatilidad": alertas_volatilidad if alertas_volatilidad else None,
        "moneda": "USD"
    }


