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
    return render_template("movimientos.html")


if __name__ == "__main__":
    app.run(debug=True)