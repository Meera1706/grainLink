from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    phone = db.Column(db.String(15))
    is_farmer = db.Column(db.Boolean)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    price = db.Column(db.Float)
    quantity = db.Column(db.String(50))
    farmer_id = db.Column(db.Integer)

with app.app_context():
    print("===== USERS =====")
    for user in User.query.all():
        print(f"ID: {user.id} | Name: {user.name} | Type: {'Farmer' if user.is_farmer else 'Vendor'}")

    print("\n===== PRODUCTS =====")
    for product in Product.query.all():
        print(f"ID: {product.id} | Name: {product.name} | Price: ₹{product.price} | Qty: {product.quantity}")