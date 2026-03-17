# Instrucciones para crear el BI en Power BI

Este documento explica, paso a paso, como crear el archivo `RoseAmor_Dashboard.pbix` usando los datos ya preparados en PostgreSQL.

## 1. Antes de abrir Power BI

1. Verifica que PostgreSQL este encendido.
2. Verifica credenciales:
   - Host: `localhost`
   - Puerto: `5432`
   - Base de datos: `test`
   - Usuario: `dev`
   - Contrasena: `test`
3. Ejecuta el ETL para asegurar datos actualizados:

```bash
python etl/load_data.py
```

## 2. Conectar Power BI a PostgreSQL

1. Abre Power BI Desktop.
2. Clic en `Obtener datos`.
3. Busca y selecciona `PostgreSQL database`.
4. Configura:
   - `Server`: `localhost:5432`
   - `Database`: `test`
5. Modo recomendado: `Import`.
6. Ingresa usuario y contrasena (`dev` / `test`).
7. En `Navigator`, selecciona:
   - `public.v_orders_full` (recomendado para ir rapido)
8. Clic en `Load`.

## 3. Crear medidas DAX

En la tabla `v_orders_full`, crea estas medidas:

```DAX
Total Sales = SUM(v_orders_full[revenue])

Total Margin = SUM(v_orders_full[gross_profit])

Order Count = DISTINCTCOUNT(v_orders_full[order_id])

Average Ticket = DIVIDE([Total Sales], [Order Count], 0)

Margin % = DIVIDE([Total Margin], [Total Sales], 0)
```

## 4. Armar visuales obligatorios

Crea los siguientes visuales:

1. Tarjeta: `Total Sales`
2. Tarjeta: `Total Margin`
3. Tarjeta: `Order Count`
4. Tarjeta: `Average Ticket`
5. Grafico de linea: `Sales by month`
   - Eje: `year_month`
   - Valor: `[Total Sales]`
6. Grafico de columnas: `Sales by channel`
   - Eje: `channel`
   - Valor: `[Total Sales]`
7. Grafico de barras: `Margin by category`
   - Eje: `category`
   - Valor: `[Total Margin]` o `[Margin %]`
8. Grafico de barras: `Top 10 customers by revenue`
   - Eje: `customer_name`
   - Valor: `[Total Sales]`
   - Filtro Top N = 10
9. Grafico de barras: `Top 10 products sold`
   - Eje: `sku`
   - Valor: `SUM(quantity)` o `[Total Sales]`
   - Filtro Top N = 10

## 5. Agregar filtros (slicers)

Agrega estos slicers en la pagina:

1. `order_date` (tipo Between)
2. `channel`
3. `category`
4. `country`

## 6. Formato recomendado para entrega

1. Titulo: `RoseAmor Sales Dashboard`.
2. Muestra moneda en ventas y margen.
3. Muestra `Margin %` en porcentaje con 2 decimales.
4. Ordena `year_month` ascendente.

## 7. Validacion rapida

Compara las tarjetas con estos valores de control (base actual):

- `Total Sales`: `1,545,647.75`
- `Total Margin`: `1,055,508.34`
- `Order Count`: `1476`
- `Average Ticket`: `1047.19`

Si coinciden, la conexion y medidas estan bien.

## 8. Guardar y entregar

1. Guarda en la raiz del repo como:

`RoseAmor_Dashboard.pbix`

2. Verifica que el archivo quede junto a `README.md` e `instrucciones.md`.
3. Haz commit/push del `.pbix`.

## 9. (Opcional) Publicar en Power BI Service

1. Clic en `Publish`.
2. Copia el link del reporte.
3. Agrega el link al README si te lo piden.
