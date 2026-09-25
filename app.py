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

@app.route("/productos/nuevo", methods=["GET"])
def producto_nuevo():
    categorias = query("SELECT id, name FROM categories ORDER BY name")
    return render_template("producto_form.html",
                           producto=None,
                           categorias=categorias)


@app.route("/productos/nuevo", methods=["POST"])
def producto_crear():
    sku = (request.form.get("sku") or "").strip().upper()
    name = (request.form.get("name") or "").strip()
    category_id = request.form.get("category_id", type=int)
    stock = request.form.get("stock", type=int) or 0
    stock_min = request.form.get("stock_min", type=int) or 0
    price = request.form.get("price", type=float) or 0.0

    # Validaciones
    errores = []
    if not sku:
        errores.append("El SKU es obligatorio.")
    if not name:
        errores.append("El nombre es obligatorio.")
    if stock < 0:
        errores.append("El stock no puede ser negativo.")
    if stock_min < 0:
        errores.append("El stock mínimo no puede ser negativo.")
    if price < 0:
        errores.append("El precio no puede ser negativo.")

    # SKU duplicado
    existente = query("SELECT id FROM products WHERE sku = %s", (sku,))
    if existente:
        errores.append(f"Ya existe un producto con el SKU {sku}.")

    if errores:
        for e in errores:
            flash(e, "danger")
        categorias = query("SELECT id, name FROM categories ORDER BY name")
        return render_template("producto_form.html",
                               producto=request.form,
                               categorias=categorias)

    # Insertar
    try:
        with transaction() as cursor:
            cursor.execute("""
                INSERT INTO products (sku, name, category_id, stock, stock_min, price, active)
                VALUES (%s, %s, %s, %s, %s, %s, 1)
            """, (sku, name, category_id, stock, stock_min, price))
        flash(f"Producto '{name}' creado correctamente.", "success")
        return redirect(url_for("productos"))
    except Exception as e:
        flash(f"Error al crear el producto: {e}", "danger")
        categorias = query("SELECT id, name FROM categories ORDER BY name")
        return render_template("producto_form.html",
                               producto=request.form,
                               categorias=categorias)

@app.route("/productos/<int:id>/editar", methods=["GET"])
def producto_editar(id):
    producto = query("SELECT * FROM products WHERE id = %s", (id,))
    if not producto:
        flash("Producto no encontrado.", "danger")
        return redirect(url_for("productos"))

    categorias = query("SELECT id, name FROM categories ORDER BY name")
    return render_template("producto_form.html",
                           producto=producto[0],
                           categorias=categorias)


@app.route("/productos/<int:id>/editar", methods=["POST"])
def producto_actualizar(id):
    # Verificar que exista
    existente = query("SELECT id FROM products WHERE id = %s", (id,))
    if not existente:
        flash("Producto no encontrado.", "danger")
        return redirect(url_for("productos"))

    sku = (request.form.get("sku") or "").strip().upper()
    name = (request.form.get("name") or "").strip()
    category_id = request.form.get("category_id", type=int)
    stock = request.form.get("stock", type=int) or 0
    stock_min = request.form.get("stock_min", type=int) or 0
    price = request.form.get("price", type=float) or 0.0

    errores = []
    if not sku:
        errores.append("El SKU es obligatorio.")
    if not name:
        errores.append("El nombre es obligatorio.")
    if stock < 0:
        errores.append("El stock no puede ser negativo.")
    if stock_min < 0:
        errores.append("El stock mínimo no puede ser negativo.")
    if price < 0:
        errores.append("El precio no puede ser negativo.")

    # SKU duplicado — excluye el propio producto
    duplicado = query(
        "SELECT id FROM products WHERE sku = %s AND id <> %s",
        (sku, id)
    )
    if duplicado:
        errores.append(f"Ya existe otro producto con el SKU {sku}.")

    if errores:
        for e in errores:
            flash(e, "danger")
        # Recargar el producto actual con los datos del form para no perder cambios
        producto_actual = query("SELECT * FROM products WHERE id = %s", (id,))[0]
        # Sobrescribe con lo que el usuario escribió
        producto_actual.update({
            "sku": sku, "name": name, "category_id": category_id,
            "stock": stock, "stock_min": stock_min, "price": price,
        })
        categorias = query("SELECT id, name FROM categories ORDER BY name")
        return render_template("producto_form.html",
                               producto=producto_actual,
                               categorias=categorias)

    try:
        with transaction() as cursor:
            cursor.execute("""
                UPDATE products
                SET sku = %s, name = %s, category_id = %s,
                    stock = %s, stock_min = %s, price = %s
                WHERE id = %s
            """, (sku, name, category_id, stock, stock_min, price, id))
        flash(f"Producto '{name}' actualizado correctamente.", "success")
        return redirect(url_for("productos"))
    except Exception as e:
        flash(f"Error al actualizar el producto: {e}", "danger")
        return redirect(url_for("producto_editar", id=id))

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