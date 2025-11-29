# Resumen

Este es un sistema el cual ayuda al usuario a crear horarios automaticos con un bot personalizado a plantillas especificas que pueda leer la informacion que el usuario cargue al sistema, se realizo con finalidad a Tecmilenio Chih. para exposicion en proyecto en la ExpoTecmi se realiza en forma general pero enfocado en zona administrativa encargados de realizar horarios hacia el alumnado, con la finalidad de recortar tiempos de creacion de horarios de 2 meses a una semana dando eficacia en este sistema completo.

# Arquitectura del Sistema
 
Este sistema realizado con lenguaje python para configurar el bot de una manera eficaz, tambien se le implemento terraform y ansible para otro proyecto.

## Frontend Arquitectura

**Tecnologia**: Streamlit web framework 
- **Enfoque**: Aplicación de una sola página con gestión del estado de la sesión para mantener los datos del usuario en todas las interacciones.
- **Características clave**:
- Capacidad de carga de archivos para la entrada de datos por lotes.
- Edición interactiva de datos con editores de datos.
- Visualización de horarios en tiempo real.
- Función de exportación de horarios generados.

**Gestión del estado de la sesión**
- Almacena horarios generados, datos de grupos, datos de profesores y datos de aulas.
- Mantiene el estado del horario editado para preservar las modificaciones del usuario.
- Permite un flujo de trabajo de varios pasos sin pérdida de datos.


## Backend Arquitectura

**Lógica de procesamiento**: Algoritmo de generación de horarios basado en Python
- **Restricciones gestionadas**:
- Conflictos de disponibilidad del profesorado
- Adaptación de la capacidad del aula
- Distribución de sesiones a lo largo de la semana
- Disponibilidad de franjas horarias
- Requisitos de duración

**Gestión del tiempo**
- Horario: de 7:00 a 21:00
- Duración de las sesiones configurable
- Compatibilidad con bloques de clases de varias horas

## Data Storage

**Data Models**:
1. **Groups**: Course sections with metadata (semester, teacher, duration, frequency, enrollment)
2. **Teachers**: Instructor information and assigned courses
3. **Classrooms**: Room details including capacity
4. **Schedules**: Generated timetables with day/time slot assignments


## Bibliotecas principales

1. **Streamlit** - Framework de aplicación web
- Propósito: Framework de interfaz de usuario principal para la aplicación
- Funciones utilizadas: Carga de archivos, editores de datos, estado de sesión, componentes de diseño

2. **Pandas** - Manipulación de datos
- Propósito: Procesamiento de datos tabulares y manejo de CSV
- Casos de uso: Estructuras de datos de programación, operaciones de importación/exportación

3. **ReportLab** - Generación de PDF
- Propósito: Creación de informes profesionales
- Componentes: SimpleDocTemplate, diseños de tabla, estilos

4. **Plotly** - Visualización de datos
- Propósito: Visualización interactiva de la línea de tiempo de la programación
- Tipo de gráfico: Diagramas de Gantt/línea de tiempo para la visualización de la programación

## Python Standard Library

- **datetime/time/timedelta**: Time-based calculations and schedule slot management
- **io**: In-memory file handling for PDF generation and downloads

## Sin servicios externos

- Sin conexiones a bases de datos (utiliza almacenamiento en memoria)
- Sin servicios de autenticación (aplicación monousuario)
- Sin API externas ni servicios en la nube
- Sin servicios de programación de tercerosg services
