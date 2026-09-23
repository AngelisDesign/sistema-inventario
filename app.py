from flask import Flask, render_template
from db import query

app = Flask(__name__)


@app.route("/")
def dashboard():
    return render_template("index.html")


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


if __name__ == "__main__":
    app.run(debug=True)