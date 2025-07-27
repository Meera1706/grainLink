import csv
from app import app, db, User, Product

def export_to_csv():
    with app.app_context():
        # Export Users
        with open('users.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Name", "Phone", "User Type"])
            for user in User.query.all():
                writer.writerow([user.id, user.name, user.phone, "Farmer" if user.is_farmer else "Vendor"])

        # Export Products
        with open('products.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Name", "Price", "Quantity", "Farmer ID"])
            for product in Product.query.all():
                writer.writerow([product.id, product.name, product.price, product.quantity, product.farmer_id])

        print("Exported: users.csv and products.csv")

if __name__ == "__main__":
    export_to_csv()