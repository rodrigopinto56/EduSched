import streamlit as st
import pandas as pd
import io
from datetime import datetime, time, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import plotly.graph_objects as go

# Configuración de la página
st.set_page_config(
    page_title="Generador de Horarios Académicos",
    page_icon="📅",
    layout="wide"
)

# Inicializar session state
if 'horario_generado' not in st.session_state:
    st.session_state.horario_generado = None
if 'grupos_df' not in st.session_state:
    st.session_state.grupos_df = None
if 'maestros_df' not in st.session_state:
    st.session_state.maestros_df = None
if 'salones_df' not in st.session_state:
    st.session_state.salones_df = None
if 'horario_editado' not in st.session_state:
    st.session_state.horario_editado = None

# Constantes
DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
HORA_INICIO = 7
HORA_FIN = 21

# Título principal
st.title("📅 Generador de Horarios Académicos")
st.markdown("### Sistema inteligente de generación de horarios con priorización por semestre")

# Función para crear plantilla de ejemplo
def crear_plantilla_grupos():
    """Crea un DataFrame de ejemplo para grupos"""
    data = {
        'Grupo': ['Grupo A', 'Grupo B', 'Grupo C', 'Grupo D'],
        'Materia': ['Matemáticas', 'Física', 'Programación', 'Química'],
        'Semestre': [5, 3, 1, 7],
        'Maestro': ['Dr. García', 'Dra. López', 'Ing. Martínez', 'Dr. García'],
        'Duracion_Horas': [2, 1.5, 2, 1.5],
        'Sesiones_Semanales': [3, 2, 3, 2],
        'Num_Estudiantes': [30, 25, 35, 28]
    }
    return pd.DataFrame(data)

def crear_plantilla_maestros():
    """Crea un DataFrame de ejemplo para maestros"""
    data = {
        'Maestro': ['Dr. García', 'Dra. López', 'Ing. Martínez'],
        'Lunes': ['7-15', '9-18', '7-21'],
        'Martes': ['7-15', '9-18', '7-21'],
        'Miercoles': ['7-15', '9-18', '7-21'],
        'Jueves': ['7-15', '9-18', '7-21'],
        'Viernes': ['7-15', '9-18', '7-21']
    }
    return pd.DataFrame(data)

def crear_plantilla_salones():
    """Crea un DataFrame de ejemplo para salones"""
    data = {
        'Salon': ['A101', 'A102', 'B201'],
        'Capacidad': [40, 35, 50],
        'Tipo': ['Aula', 'Aula', 'Laboratorio']
    }
    return pd.DataFrame(data)

# Función para parsear horarios de disponibilidad
def parsear_horario(horario_str):
    """Convierte un string de horario '7-15' en una tupla (7, 15)"""
    if pd.isna(horario_str) or horario_str == '':
        return (HORA_INICIO, HORA_FIN)
    try:
        inicio, fin = map(int, horario_str.split('-'))
        return (inicio, fin)
    except:
        return (HORA_INICIO, HORA_FIN)

# Función para generar franjas horarias
def generar_franjas_horarias(duracion_horas):
    """Genera todas las posibles franjas horarias para una clase"""
    franjas = []
    
    hora = HORA_INICIO
    while hora + duracion_horas <= HORA_FIN:
        franjas.append((hora, hora + duracion_horas))
        hora += 0.5  # Incrementos de 30 minutos
    
    return franjas

# Función para verificar conflictos
def verificar_conflicto(horario_actual, dia, hora_inicio, hora_fin, maestro=None, salon=None, excluir_idx=None):
    """Verifica si hay conflicto de maestro o salón en el horario"""
    if horario_actual is None or len(horario_actual) == 0:
        return False
    
    for idx, clase in enumerate(horario_actual):
        if excluir_idx is not None and idx == excluir_idx:
            continue
            
        if clase['Dia'] == dia:
            # Verificar solapamiento de horas
            if not (hora_fin <= clase['Hora_Inicio'] or hora_inicio >= clase['Hora_Fin']):
                # Hay solapamiento de tiempo
                if maestro and clase['Maestro'] == maestro:
                    return True
                if salon and clase['Salon'] == salon:
                    return True
    
    return False

# Función para calcular huecos en el horario de un grupo
def calcular_huecos_grupo(horario_grupo):
    """Calcula el número de horas de hueco en el horario de un grupo"""
    huecos = 0
    
    for dia in DIAS:
        clases_dia = [c for c in horario_grupo if c['Dia'] == dia]
        if len(clases_dia) > 1:
            clases_dia_sorted = sorted(clases_dia, key=lambda x: x['Hora_Inicio'])
            for i in range(len(clases_dia_sorted) - 1):
                hueco = clases_dia_sorted[i+1]['Hora_Inicio'] - clases_dia_sorted[i]['Hora_Fin']
                if hueco > 0:
                    huecos += hueco
    
    return huecos

# Función para calcular score de una asignación (menor es mejor)
def calcular_score_asignacion(horario_actual, grupo_nombre, nueva_clase):
    """Calcula un score para evaluar qué tan buena es una asignación (menor = mejor)"""
    # Obtener todas las clases del grupo
    clases_grupo = [c for c in horario_actual if c['Grupo'] == grupo_nombre]
    clases_grupo.append(nueva_clase)
    
    # Calcular huecos
    huecos = calcular_huecos_grupo(clases_grupo)
    
    # Penalizar clases muy tempranas o muy tardías
    hora_penalizacion = 0
    if nueva_clase['Hora_Inicio'] < 8:
        hora_penalizacion += 2
    if nueva_clase['Hora_Fin'] > 19:
        hora_penalizacion += 2
    
    # Preferir clases más temprano en la semana
    dia_penalizacion = DIAS.index(nueva_clase['Dia']) * 0.1
    
    return huecos + hora_penalizacion + dia_penalizacion

# Algoritmo mejorado de generación de horarios con minimización de huecos
def generar_horario(grupos_df, maestros_df, salones_df):
    """Genera un horario optimizado priorizando semestres avanzados y minimizando huecos"""
    
    # Ordenar grupos por semestre (descendente)
    grupos_ordenados = grupos_df.sort_values('Semestre', ascending=False).reset_index(drop=True)
    
    horario = []
    salones_lista = salones_df['Salon'].tolist()
    
    for idx, grupo in grupos_ordenados.iterrows():
        grupo_nombre = grupo['Grupo']
        materia = grupo['Materia']
        maestro = grupo['Maestro']
        duracion = grupo['Duracion_Horas']
        sesiones = int(grupo['Sesiones_Semanales'])
        num_estudiantes = grupo['Num_Estudiantes']
        
        # Obtener disponibilidad del maestro
        maestro_info = maestros_df[maestros_df['Maestro'] == maestro]
        if len(maestro_info) == 0:
            st.warning(f"Maestro {maestro} no encontrado en la lista de disponibilidad")
            continue
        
        maestro_info = maestro_info.iloc[0]
        
        # Buscar salón adecuado
        salon_asignado = None
        for salon in salones_lista:
            salon_info = salones_df[salones_df['Salon'] == salon].iloc[0]
            if salon_info['Capacidad'] >= num_estudiantes:
                salon_asignado = salon
                break
        
        if salon_asignado is None:
            st.warning(f"No se encontró salón con capacidad para {grupo_nombre}")
            salon_asignado = salones_lista[0]
        
        # Estrategia: earliest-fit con minimización de huecos
        sesiones_asignadas = 0
        
        # Generar todas las posibles asignaciones
        opciones = []
        
        for dia in DIAS:
            # Obtener disponibilidad del maestro para ese día
            dia_col = 'Miercoles' if dia == 'Miércoles' else dia
            disponibilidad = parsear_horario(maestro_info[dia_col])
            
            # Generar franjas posibles
            franjas = generar_franjas_horarias(duracion)
            franjas_validas = [f for f in franjas if f[0] >= disponibilidad[0] and f[1] <= disponibilidad[1]]
            
            for franja in franjas_validas:
                hora_inicio, hora_fin = franja
                
                # Verificar si hay conflicto
                if not verificar_conflicto(horario, dia, hora_inicio, hora_fin, maestro, salon_asignado):
                    nueva_clase = {
                        'Grupo': grupo_nombre,
                        'Materia': materia,
                        'Maestro': maestro,
                        'Salon': salon_asignado,
                        'Dia': dia,
                        'Hora_Inicio': hora_inicio,
                        'Hora_Fin': hora_fin,
                        'Semestre': grupo['Semestre']
                    }
                    
                    # Calcular score
                    score = calcular_score_asignacion(horario, grupo_nombre, nueva_clase)
                    opciones.append((score, nueva_clase))
        
        # Ordenar opciones por score (menor primero)
        opciones.sort(key=lambda x: x[0])
        
        # Asignar las mejores opciones
        dias_usados = set()
        for score, clase in opciones:
            if sesiones_asignadas >= sesiones:
                break
            
            # Evitar asignar múltiples sesiones el mismo día cuando sea posible
            if len(opciones) >= sesiones * 2 and clase['Dia'] in dias_usados:
                continue
            
            # Verificar nuevamente conflictos (por si acaso)
            if not verificar_conflicto(horario, clase['Dia'], clase['Hora_Inicio'], 
                                      clase['Hora_Fin'], maestro, salon_asignado):
                horario.append(clase)
                sesiones_asignadas += 1
                dias_usados.add(clase['Dia'])
        
        if sesiones_asignadas < sesiones:
            st.warning(f"Solo se asignaron {sesiones_asignadas} de {sesiones} sesiones para {grupo_nombre}")
    
    return pd.DataFrame(horario)

# Función para crear visualización de cuadrícula semanal
def crear_cuadricula_horario(horario_df, filtro_grupo=None, filtro_maestro=None, filtro_salon=None):
    """Crea una visualización de cuadrícula semanal del horario usando Plotly"""
    
    if horario_df is None or len(horario_df) == 0:
        st.info("No hay horario generado aún")
        return
    
    # Aplicar filtros
    df_filtrado = horario_df.copy()
    if filtro_grupo and filtro_grupo != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Grupo'] == filtro_grupo]
    if filtro_maestro and filtro_maestro != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Maestro'] == filtro_maestro]
    if filtro_salon and filtro_salon != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Salon'] == filtro_salon]
    
    # Crear matriz para la cuadrícula
    horas_rango = [h for h in range(HORA_INICIO, HORA_FIN)]
    
    # Crear figura con subplots
    fig = go.Figure()
    
    # Colores para diferentes grupos
    grupos_unicos = df_filtrado['Grupo'].unique()
    colores = {}
    palette = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2']
    for i, grupo in enumerate(grupos_unicos):
        colores[grupo] = palette[i % len(palette)]
    
    # Agregar barras para cada clase
    for _, clase in df_filtrado.iterrows():
        dia_idx = DIAS.index(clase['Dia'])
        
        # Crear texto para mostrar en la barra
        hora_inicio_str = f"{int(clase['Hora_Inicio'])}:{int((clase['Hora_Inicio'] % 1) * 60):02d}"
        hora_fin_str = f"{int(clase['Hora_Fin'])}:{int((clase['Hora_Fin'] % 1) * 60):02d}"
        
        texto = f"{clase['Materia']}<br>{clase['Grupo']}<br>{hora_inicio_str}-{hora_fin_str}<br>{clase['Maestro']}<br>{clase['Salon']}"
        
        fig.add_trace(go.Bar(
            name=clase['Grupo'],
            x=[clase['Dia']],
            y=[clase['Hora_Fin'] - clase['Hora_Inicio']],
            base=[clase['Hora_Inicio']],
            marker=dict(color=colores.get(clase['Grupo'], '#999999')),
            text=texto,
            textposition='inside',
            hovertemplate='<b>%{text}</b><extra></extra>',
            showlegend=False
        ))
    
    fig.update_layout(
        title="Cuadrícula Semanal del Horario",
        xaxis=dict(
            title="Día de la Semana",
            categoryorder='array',
            categoryarray=DIAS
        ),
        yaxis=dict(
            title="Hora del Día",
            range=[HORA_INICIO, HORA_FIN],
            tickmode='linear',
            tick0=HORA_INICIO,
            dtick=1
        ),
        barmode='overlay',
        height=600,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Función para visualizar horario como lista
def visualizar_horario_lista(horario_df, filtro_grupo=None, filtro_maestro=None, filtro_salon=None):
    """Visualiza el horario en formato de lista por día"""
    
    if horario_df is None or len(horario_df) == 0:
        st.info("No hay horario generado aún")
        return
    
    # Aplicar filtros
    df_filtrado = horario_df.copy()
    if filtro_grupo and filtro_grupo != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Grupo'] == filtro_grupo]
    if filtro_maestro and filtro_maestro != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Maestro'] == filtro_maestro]
    if filtro_salon and filtro_salon != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Salon'] == filtro_salon]
    
    for dia in DIAS:
        st.markdown(f"#### {dia}")
        clases_dia = df_filtrado[df_filtrado['Dia'] == dia].sort_values('Hora_Inicio')
        
        if len(clases_dia) > 0:
            for _, clase in clases_dia.iterrows():
                col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 1, 1])
                
                hora_inicio_str = f"{int(clase['Hora_Inicio'])}:{int((clase['Hora_Inicio'] % 1) * 60):02d}"
                hora_fin_str = f"{int(clase['Hora_Fin'])}:{int((clase['Hora_Fin'] % 1) * 60):02d}"
                
                with col1:
                    st.write(f"**{hora_inicio_str} - {hora_fin_str}**")
                with col2:
                    st.write(f"📚 {clase['Materia']}")
                with col3:
                    st.write(f"👥 {clase['Grupo']}")
                with col4:
                    st.write(f"👨‍🏫 {clase['Maestro']}")
                with col5:
                    st.write(f"🏫 {clase['Salon']}")
        else:
            st.write("Sin clases programadas")
        
        st.divider()

# Función para detectar conflictos
def detectar_conflictos(horario_df):
    """Detecta conflictos en el horario generado"""
    conflictos = []
    
    if horario_df is None or len(horario_df) == 0:
        return conflictos
    
    for i, clase1 in horario_df.iterrows():
        for j, clase2 in horario_df.iterrows():
            if i >= j:
                continue
            
            if clase1['Dia'] == clase2['Dia']:
                # Verificar solapamiento
                if not (clase1['Hora_Fin'] <= clase2['Hora_Inicio'] or clase1['Hora_Inicio'] >= clase2['Hora_Fin']):
                    # Conflicto de maestro
                    if clase1['Maestro'] == clase2['Maestro']:
                        conflictos.append({
                            'Tipo': 'Maestro',
                            'Recurso': clase1['Maestro'],
                            'Dia': clase1['Dia'],
                            'Hora': f"{clase1['Hora_Inicio']}-{clase1['Hora_Fin']}",
                            'Grupos': f"{clase1['Grupo']} y {clase2['Grupo']}"
                        })
                    
                    # Conflicto de salón
                    if clase1['Salon'] == clase2['Salon']:
                        conflictos.append({
                            'Tipo': 'Salón',
                            'Recurso': clase1['Salon'],
                            'Dia': clase1['Dia'],
                            'Hora': f"{clase1['Hora_Inicio']}-{clase1['Hora_Fin']}",
                            'Grupos': f"{clase1['Grupo']} y {clase2['Grupo']}"
                        })
    
    return conflictos

# Función para exportar a PDF
def exportar_pdf(horario_df):
    """Exporta el horario a PDF"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    elements = []
    
    styles = getSampleStyleSheet()
    
    # Título
    title = Paragraph("Horario Académico Generado", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Crear tabla por día
    for dia in DIAS:
        clases_dia = horario_df[horario_df['Dia'] == dia].sort_values('Hora_Inicio')
        
        if len(clases_dia) > 0:
            # Subtítulo del día
            day_title = Paragraph(f"<b>{dia}</b>", styles['Heading2'])
            elements.append(day_title)
            elements.append(Spacer(1, 6))
            
            # Datos de la tabla
            data = [['Hora', 'Materia', 'Grupo', 'Maestro', 'Salón']]
            
            for _, clase in clases_dia.iterrows():
                hora_inicio_str = f"{int(clase['Hora_Inicio'])}:{int((clase['Hora_Inicio'] % 1) * 60):02d}"
                hora_fin_str = f"{int(clase['Hora_Fin'])}:{int((clase['Hora_Fin'] % 1) * 60):02d}"
                
                data.append([
                    f"{hora_inicio_str}-{hora_fin_str}",
                    clase['Materia'],
                    clase['Grupo'],
                    clase['Maestro'],
                    clase['Salon']
                ])
            
            # Crear tabla
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 12))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# Interfaz principal
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📥 Cargar Datos", "🤖 Generar Horario", "📊 Ver Horario", "✏️ Editar Horario", "📤 Exportar"])

with tab1:
    st.header("Cargar Información")
    
    st.markdown("### Descargar Plantillas de Ejemplo")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        plantilla_grupos = crear_plantilla_grupos()
        csv_grupos = plantilla_grupos.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Plantilla Grupos",
            data=csv_grupos,
            file_name="plantilla_grupos.csv",
            mime="text/csv"
        )
    
    with col2:
        plantilla_maestros = crear_plantilla_maestros()
        csv_maestros = plantilla_maestros.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Plantilla Maestros",
            data=csv_maestros,
            file_name="plantilla_maestros.csv",
            mime="text/csv"
        )
    
    with col3:
        plantilla_salones = crear_plantilla_salones()
        csv_salones = plantilla_salones.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Plantilla Salones",
            data=csv_salones,
            file_name="plantilla_salones.csv",
            mime="text/csv"
        )
    
    st.divider()
    
    st.markdown("### Subir Archivos CSV")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### Grupos")
        archivo_grupos = st.file_uploader("Subir archivo de grupos", type=['csv'], key='grupos')
        if archivo_grupos:
            st.session_state.grupos_df = pd.read_csv(archivo_grupos)
            st.success(f"✅ {len(st.session_state.grupos_df)} grupos cargados")
            st.dataframe(st.session_state.grupos_df)
    
    with col2:
        st.markdown("#### Maestros")
        archivo_maestros = st.file_uploader("Subir archivo de maestros", type=['csv'], key='maestros')
        if archivo_maestros:
            st.session_state.maestros_df = pd.read_csv(archivo_maestros)
            st.success(f"✅ {len(st.session_state.maestros_df)} maestros cargados")
            st.dataframe(st.session_state.maestros_df)
    
    with col3:
        st.markdown("#### Salones")
        archivo_salones = st.file_uploader("Subir archivo de salones", type=['csv'], key='salones')
        if archivo_salones:
            st.session_state.salones_df = pd.read_csv(archivo_salones)
            st.success(f"✅ {len(st.session_state.salones_df)} salones cargados")
            st.dataframe(st.session_state.salones_df)
    
    st.divider()
    
    if st.button("🧪 Usar Datos de Ejemplo"):
        st.session_state.grupos_df = crear_plantilla_grupos()
        st.session_state.maestros_df = crear_plantilla_maestros()
        st.session_state.salones_df = crear_plantilla_salones()
        st.success("✅ Datos de ejemplo cargados correctamente")
        st.rerun()

with tab2:
    st.header("Generar Horario")
    
    if st.session_state.grupos_df is None or st.session_state.maestros_df is None or st.session_state.salones_df is None:
        st.warning("⚠️ Por favor, carga primero los datos de grupos, maestros y salones en la pestaña 'Cargar Datos'")
    else:
        st.success("✅ Todos los datos necesarios están cargados")
        
        st.markdown("### Información Cargada")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Grupos", len(st.session_state.grupos_df))
        with col2:
            st.metric("Maestros", len(st.session_state.maestros_df))
        with col3:
            st.metric("Salones", len(st.session_state.salones_df))
        
        st.divider()
        
        st.markdown("### Priorización por Semestre")
        st.info("El algoritmo prioriza automáticamente a los estudiantes de semestres más avanzados y minimiza los huecos entre clases.")
        
        grupos_ordenados = st.session_state.grupos_df.sort_values('Semestre', ascending=False)
        st.dataframe(grupos_ordenados[['Grupo', 'Semestre', 'Materia']], use_container_width=True)
        
        st.divider()
        
        if st.button("🤖 Generar Horario Automático", type="primary"):
            with st.spinner("Generando horario optimizado con minimización de huecos..."):
                st.session_state.horario_generado = generar_horario(
                    st.session_state.grupos_df,
                    st.session_state.maestros_df,
                    st.session_state.salones_df
                )
                st.session_state.horario_editado = st.session_state.horario_generado.copy()
                st.success(f"✅ Horario generado con {len(st.session_state.horario_generado)} clases programadas")
                
                # Calcular huecos totales
                huecos_totales = 0
                for grupo in st.session_state.grupos_df['Grupo']:
                    clases_grupo = st.session_state.horario_generado[st.session_state.horario_generado['Grupo'] == grupo].to_dict('records')
                    huecos_totales += calcular_huecos_grupo(clases_grupo)
                
                st.info(f"📊 Total de horas de hueco en todos los grupos: {huecos_totales:.1f} horas")
                
                # Detectar conflictos
                conflictos = detectar_conflictos(st.session_state.horario_generado)
                if len(conflictos) > 0:
                    st.warning(f"⚠️ Se detectaron {len(conflictos)} conflictos")
                    st.dataframe(pd.DataFrame(conflictos))
                else:
                    st.success("✅ No se detectaron conflictos en el horario")
                
                st.balloons()

with tab3:
    st.header("Visualizar Horario")
    
    horario_actual = st.session_state.horario_editado if st.session_state.horario_editado is not None else st.session_state.horario_generado
    
    if horario_actual is None or len(horario_actual) == 0:
        st.info("ℹ️ No hay horario generado. Ve a la pestaña 'Generar Horario' para crear uno.")
    else:
        st.success(f"✅ Mostrando horario con {len(horario_actual)} clases")
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        
        with col1:
            grupos_unicos = ['Todos'] + sorted(horario_actual['Grupo'].unique().tolist())
            filtro_grupo = st.selectbox("Filtrar por Grupo", grupos_unicos)
        
        with col2:
            maestros_unicos = ['Todos'] + sorted(horario_actual['Maestro'].unique().tolist())
            filtro_maestro = st.selectbox("Filtrar por Maestro", maestros_unicos)
        
        with col3:
            salones_unicos = ['Todos'] + sorted(horario_actual['Salon'].unique().tolist())
            filtro_salon = st.selectbox("Filtrar por Salón", salones_unicos)
        
        st.divider()
        
        # Visualización de cuadrícula
        st.markdown("### 📊 Cuadrícula Semanal")
        crear_cuadricula_horario(horario_actual, filtro_grupo, filtro_maestro, filtro_salon)
        
        st.divider()
        
        # Visualización de lista
        st.markdown("### 📋 Vista Detallada por Día")
        visualizar_horario_lista(horario_actual, filtro_grupo, filtro_maestro, filtro_salon)
        
        st.divider()
        
        # Estadísticas
        st.markdown("### 📈 Estadísticas")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total de Clases", len(horario_actual))
        
        with col2:
            grupos_programados = horario_actual['Grupo'].nunique()
            st.metric("Grupos Programados", grupos_programados)
        
        with col3:
            conflictos = detectar_conflictos(horario_actual)
            st.metric("Conflictos Detectados", len(conflictos))
        
        with col4:
            horas_totales = (horario_actual['Hora_Fin'] - horario_actual['Hora_Inicio']).sum()
            st.metric("Horas Totales", f"{horas_totales:.1f}")

with tab4:
    st.header("Editar Horario Manualmente")
    
    horario_actual = st.session_state.horario_editado if st.session_state.horario_editado is not None else st.session_state.horario_generado
    
    if horario_actual is None or len(horario_actual) == 0:
        st.info("ℹ️ No hay horario para editar. Genera un horario primero.")
    else:
        st.markdown("### 🛠️ Editor de Horario")
        st.info("Edita las clases directamente en la tabla. Los cambios se validarán automáticamente para detectar conflictos.")
        
        # Crear tabla editable
        st.markdown("#### Tabla Editable del Horario")
        
        # Preparar DataFrame para edición
        df_editable = horario_actual.copy()
        
        # Formatear horas para mejor visualización
        df_editable['Hora_Inicio_Str'] = df_editable['Hora_Inicio'].apply(
            lambda x: f"{int(x)}:{int((x % 1) * 60):02d}"
        )
        df_editable['Hora_Fin_Str'] = df_editable['Hora_Fin'].apply(
            lambda x: f"{int(x)}:{int((x % 1) * 60):02d}"
        )
        
        # Mostrar DataFrame editable
        df_display = df_editable[['Grupo', 'Materia', 'Dia', 'Hora_Inicio_Str', 'Hora_Fin_Str', 'Maestro', 'Salon']]
        df_display.columns = ['Grupo', 'Materia', 'Día', 'Hora Inicio', 'Hora Fin', 'Maestro', 'Salón']
        
        edited_df = st.data_editor(
            df_display,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "Día": st.column_config.SelectboxColumn(
                    "Día",
                    options=DIAS,
                    required=True
                ),
                "Maestro": st.column_config.TextColumn("Maestro", required=True),
                "Salón": st.column_config.TextColumn("Salón", required=True),
            }
        )
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 Guardar Cambios", type="primary"):
                try:
                    # Convertir de vuelta a formato original
                    df_nuevo = edited_df.copy()
                    df_nuevo.columns = ['Grupo', 'Materia', 'Dia', 'Hora_Inicio_Str', 'Hora_Fin_Str', 'Maestro', 'Salon']
                    
                    # Parsear horas
                    def parsear_hora_str(hora_str):
                        try:
                            partes = hora_str.split(':')
                            return int(partes[0]) + int(partes[1]) / 60
                        except:
                            return 7.0
                    
                    df_nuevo['Hora_Inicio'] = df_nuevo['Hora_Inicio_Str'].apply(parsear_hora_str)
                    df_nuevo['Hora_Fin'] = df_nuevo['Hora_Fin_Str'].apply(parsear_hora_str)
                    
                    # Agregar columna Semestre
                    df_nuevo = df_nuevo.merge(
                        st.session_state.grupos_df[['Grupo', 'Semestre']],
                        on='Grupo',
                        how='left'
                    )
                    
                    # Eliminar columnas temporales
                    df_nuevo = df_nuevo.drop(['Hora_Inicio_Str', 'Hora_Fin_Str'], axis=1)
                    
                    # Validar conflictos
                    conflictos = detectar_conflictos(df_nuevo)
                    
                    if len(conflictos) > 0:
                        st.warning(f"⚠️ Se detectaron {len(conflictos)} conflictos en el horario editado:")
                        st.dataframe(pd.DataFrame(conflictos))
                        st.info("Puedes guardar de todos modos, pero se recomienda resolver los conflictos.")
                    
                    # Guardar
                    st.session_state.horario_editado = df_nuevo
                    st.success("✅ Cambios guardados correctamente")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error al guardar cambios: {str(e)}")
        
        with col2:
            if st.button("🔄 Restaurar Horario Original"):
                st.session_state.horario_editado = st.session_state.horario_generado.copy()
                st.success("✅ Horario restaurado al original generado")
                st.rerun()
        
        st.divider()
        
        # Mostrar conflictos actuales
        st.markdown("### 🔍 Detección de Conflictos")
        conflictos_actuales = detectar_conflictos(horario_actual)
        
        if len(conflictos_actuales) > 0:
            st.warning(f"⚠️ {len(conflictos_actuales)} conflictos detectados:")
            st.dataframe(pd.DataFrame(conflictos_actuales), use_container_width=True)
        else:
            st.success("✅ No hay conflictos en el horario actual")

with tab5:
    st.header("Exportar Horario")
    
    horario_actual = st.session_state.horario_editado if st.session_state.horario_editado is not None else st.session_state.horario_generado
    
    if horario_actual is None or len(horario_actual) == 0:
        st.info("ℹ️ No hay horario para exportar. Genera un horario primero.")
    else:
        st.success("✅ Horario listo para exportar")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📄 Exportar a CSV")
            csv_export = horario_actual.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar CSV",
                data=csv_export,
                file_name=f"horario_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                type="primary"
            )
        
        with col2:
            st.markdown("### 📄 Exportar a PDF")
            pdf_buffer = exportar_pdf(horario_actual)
            st.download_button(
                label="📥 Descargar PDF",
                data=pdf_buffer,
                file_name=f"horario_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
                type="primary"
            )

# Pie de página
st.divider()
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>Generador de Horarios Académicos v2.0 | Optimización con minimización de huecos y edición manual</p>
</div>
""", unsafe_allow_html=True)
