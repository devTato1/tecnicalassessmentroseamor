# RoseAmor: Prueba Técnica - Leonardo Reascos

Este repositorio contiene la solución técnica para la posición de **Ingeniero de Datos Full Stack**. El proyecto implementa un ciclo de vida de datos completo: desde la ingesta de datos crudos (ETL) y el modelado relacional en PostgreSQL, hasta la visualización de inteligencia de negocios (BI) y una interfaz web transaccional.

---

## 1. Infraestructura del Proyecto

### Configuración de la Base de Datos

La solución utiliza **PostgreSQL** como sistema de gestión de bases de datos relacionales (RDBMS) central.

| Parámetro | Valor |
|-----------|-------|
| Base de Datos | `test` |
| Usuario | `dev` |
| Contraseña | `test` |
| Host/Puerto | `localhost:5432` |


### Estructura de Directorios
```
rosemoretecnicaltest/
├── data/                   # Archivos CSV origen (Capa Raw)
├── etl/                    # Scripts de Python para orquestación de datos
│   └── load_data.py        # Script principal de ejecución ETL
├── sql/                    # Scripts SQL DDL y DML
│   ├── 01_staging.sql      # Definiciones del área de staging
│   ├── 02_consumption.sql  # Modelo dimensional y vistas
│   └── kpis.sql            # Consultas analíticas para métricas de negocio
├── app/                    # Aplicación Web Flask
│   ├── app.py              # Lógica de backend y enrutamiento
│   ├── requirements.txt
│   └── templates/          # Componentes de Frontend HTML/CSS
│       ├── index.html
│       └── list.html
└── README.md
```

---

## 2. Arquitectura y Flujo de Datos

El proyecto sigue una **Arquitectura de Medallón**:
```
CSV Crudos (Bronce) → Tablas de Staging (Plata) → Modelo Dimensional (Oro) → Dashboard BI
```

- **Ingesta:** Python (módulo `csv` + `psycopg2`) lee los datos crudos del directorio `/data`.
- **Procesamiento:** Los datos se normalizan y cargan en tablas de staging (`stg_orders`, `stg_customers`, `stg_products`).
- **Modelado:** Se genera un esquema en estrella compuesto por dimensiones (`dim_customers`, `dim_products`) y una tabla de hechos centralizada (`fact_orders`).
- **Consumo:** Se proporciona una capa semántica a través de la vista `v_orders_full` para una integración fluida con herramientas de BI.

---

## 3. Integridad de Datos y Reglas de Negocio

### Lógica de Limpieza

**Pedidos (Orders)**
- **Deduplicación:** Lógica basada en `order_id` (enfoque de primer registro).
- **Validación de Restricciones:** Exclusión de cantidades negativas y precios unitarios nulos.
- **Normalización:** Formatos de fecha estándar ISO, descarte de fechas inválidas y normalización de nombres de canales a minúsculas.

**Clientes (Customers)**
- **Manejo de Nulos:** Los valores faltantes en `country` o `segment` se imputan como `'Unknown'`.
- **Casting de Tipos:** El campo `created_at` se convierte al tipo `DATE` para análisis temporal.

**Productos (Products)**
- **Mapeo Booleano:** El estado `active` se convierte a un formato de entero binario (`0`/`1`).

---

## 4. Modelo Analítico (Esquema en Estrella)

### Definición de Métricas

| Métrica | Fórmula |
|---------|---------|
| **Ingresos (Revenue)** | `quantity * unit_price` |
| **Utilidad Bruta (Gross Profit)** | `quantity * (unit_price - cost)` |
| **% de Margen** | `((unit_price - cost) / unit_price) * 100` |

---

## 5. Guía de Despliegue

### 5.1 Requisitos Previos

- Python 3.11+
- Instancia de PostgreSQL activa

### 5.2 Configuración del Entorno
```bash
# Instalar dependencias (desde la raíz del repo)
pip install -r app/requirements.txt

# Inicialización de la base de datos (PostgreSQL)
# CREATE DATABASE test;
# CREATE USER dev WITH PASSWORD 'test';
```

### 5.3 Pipeline de Ejecución

**Paso 1 — Ejecutar ETL:** Procesa archivos CSV y puebla PostgreSQL.
```bash
python etl/load_data.py
```

**Paso 2 — Verificar KPIs:** Ejecuta scripts analíticos para validar la consistencia de los datos.
```bash
psql -h localhost -U dev -d test -f sql/kpis.sql
```

Nota: los archivos `sql/01_staging.sql` y `sql/02_consumption.sql` se incluyen como referencia del modelo y transformaciones. El script `etl/load_data.py` ya crea y carga staging/consumo de forma automática.

**Paso 3 — Lanzar la interfaz web:**
```bash
cd app
python app.py
```

Acceda a la aplicación en [http://127.0.0.1:5000](http://127.0.0.1:5000).

---

## 6. Business Intelligence (Power BI)

La capa de reporte se conecta directamente a la vista de PostgreSQL `v_orders_full`.

### Medidas DAX Principales
```dax
Total Sales   = SUM(v_orders_full[revenue])
Average Ticket = DIVIDE([Total Sales], DISTINCTCOUNT(v_orders_full[order_id]))
Margin %      = DIVIDE(SUM(v_orders_full[gross_profit]), [Total Sales])
```

### Evidencia Visual

> En un entorno de producción real se incluirían capturas de pantalla de alta resolución de las siguientes secciones:

- **Dashboard Ejecutivo:** Resumen de ingresos, márgenes y tendencias de pedidos.
- **Análisis de Mercado:** Distribución de ventas por Canal y Categoría.
- **Insights de Clientes:** Top 10 de generadores de ingresos y rendimiento de productos.

---

## 7. Aplicación Web (Capa Transaccional)

Desarrollada con **Python Flask**, la aplicación sirve como puerta de entrada para el registro de pedidos en tiempo real.

**Stack Tecnológico:** Python · Flask · Jinja2 · PostgreSQL (`psycopg2`)

**Lógica de Validación:**
- Cumplimiento de campos obligatorios.
- Restricciones numéricas positivas para cantidad y precio.
- Validación estricta de Enums para canales de venta (`ecommerce`, `retail`, `wholesale`, `export`).
- Integridad relacional mantenida mediante restricciones de unicidad en `order_id`.

---

## 8. Estrategia de Actualización de Datos

Para actualizar el sistema con nuevos datos:

1. Sobrescriba los archivos origen en el directorio `/data`.
2. Vuelva a ejecutar el script ETL:
```bash
   python etl/load_data.py
```
3. Active la acción de **Actualizar (Refresh)** en el informe de Power BI Desktop.

> El proceso ETL es **idempotente**: realiza una operación de `TRUNCATE/LOAD` en las tablas de staging y consumo para asegurar la consistencia de los datos sin duplicidad.