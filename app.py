from flask import Flask, render_template, request, redirect, url_for, flash
from db import query, transaction

app = Flask(__name__)
app.secret_key = "cambia-esto-en-produccion"


@app.route("/")
def dashboard():
    # Métricas generales
    total_productos = query("""
        SELECT COUNT(*) AS total
        FROM products
        WHERE active = 1
    """)[0]["total"]

    stock_bajo = query("""
        SELECT COUNT(*) AS total
        FROM products
        WHERE active = 1
          AND stock > 0
          AND stock <= stock_min
    """)[0]["total"]

    sin_stock = query("""
        SELECT COUNT(*) AS total
        FROM products
        WHERE active = 1
          AND stock = 0
    """)[0]["total"]

    movimientos_hoy = query("""
        SELECT COUNT(*) AS total
        FROM inventory_movements
        WHERE DATE(created_at) = CURDATE()
    """)[0]["total"]

    valor_inventario = query("""
        SELECT COALESCE(SUM(stock * price), 0) AS total
        FROM products
        WHERE active = 1
    """)[0]["total"]

    # Últimos 5 movimientos
    ultimos_movimientos = query("""
        SELECT m.id, m.type, m.quantity, m.stock_after,
               m.created_at, m.user_name,
               p.sku, p.name AS product_name
        FROM inventory_movements m
        JOIN products p ON p.id = m.product_id
        ORDER BY m.created_at DESC
        LIMIT 5
    """)

    # Productos que requieren atención (stock bajo o sin stock)
    alertas = query("""
        SELECT p.id, p.sku, p.name, p.stock, p.stock_min
        FROM products p
        WHERE p.active = 1
          AND p.stock <= p.stock_min
        ORDER BY p.stock ASC
        LIMIT 10
    """)

    return render_template("index.html",
                           total_productos=total_productos,
                           stock_bajo=stock_bajo,
                           sin_stock=sin_stock,
                           movimientos_hoy=movimientos_hoy,
                           valor_inventario=valor_inventario,
                           ultimos_movimientos=ultimos_movimientos,
                           alertas=alertas)


@app.route("/productos")
def productos():
    productos = query("""
        SELECT p.id, p.sku, p.name, c.name AS category,
               p.stock, p.stock_min, p.price
        FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        WHERE p.active = 1
        ORDER BY p.name
    """)
    return render_template("productos.html", productos=productos)


@app.route("/movimientos")
def movimientos():
    movimientos = query("""
        SELECT m.id, m.type, m.quantity, m.stock_before, m.stock_after,
               m.note, m.user_name, m.created_at,
               p.sku, p.name AS product_name
        FROM inventory_movements m
        JOIN products p ON p.id = m.product_id
        ORDER BY m.created_at DESC
        LIMIT 50
    """)
    productos = query("""
        SELECT id, sku, name
        FROM products
        WHERE active = 1
        ORDER BY name
    """)
    return render_template("movimientos.html",
                           movimientos=movimientos,
                           productos=productos)


@app.route("/movimientos/registrar", methods=["POST"])
def registrar_movimiento():
    product_id = request.form.get("product_id", type=int)
    tipo = request.form.get("tipo")
    cantidad = request.form.get("cantidad", type=int)
    nota = (request.form.get("nota") or "").strip() or None

    # Validaciones básicas
    if not product_id or tipo not in ("in", "out", "adjust") or not cantidad or cantidad <= 0:
        flash("Datos inválidos. Revisa el formulario.", "danger")
        return redirect(url_for("movimientos"))

    try:
        with transaction() as cursor:
            # 1. Bloquea la fila del producto para evitar condiciones de carrera
            cursor.execute(
                "SELECT stock FROM products WHERE id = %s FOR UPDATE",
                (product_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError("Producto no encontrado.")

            stock_antes = row["stock"]

            # 2. Calcula el nuevo stock según el tipo
            if tipo == "in":
                stock_despues = stock_antes + cantidad
            elif tipo == "out":
                stock_despues = stock_antes - cantidad
            else:  # adjust
                stock_despues = stock_antes - cantidad

            if stock_despues < 0:
                raise ValueError(
                    f"Stock insuficiente. Disponible: {stock_antes}, solicitado: {cantidad}."
                )

            # 3. Inserta el movimiento
            cursor.execute("""
                INSERT INTO inventory_movements
                  (product_id, type, quantity, stock_before, stock_after, note, user_name)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (product_id, tipo, cantidad, stock_antes, stock_despues, nota, "admin"))

            # 4. Actualiza el stock del producto
            cursor.execute(
                "UPDATE products SET stock = %s WHERE id = %s",
                (stock_despues, product_id)
            )

        flash("Movimiento registrado correctamente.", "success")

    except ValueError as e:
        flash(str(e), "warning")
    except Exception as e:
        flash(f"Error al registrar el movimiento: {e}", "danger")

    return redirect(url_for("movimientos"))


if __name__ == "__main__":
    app.run(debug=True)