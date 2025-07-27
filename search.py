from app import app, db, Product

def search_products():
    search_term = input("Enter product name to search: ").strip().lower()
    
    with app.app_context():
        results = Product.query.filter(Product.name.ilike(f"%{search_term}%")).all()
        
        if not results:
            print("No products found!")
        else:
            print("\n===== SEARCH RESULTS =====")
            for product in results:
                print(f"• {product.name} (₹{product.price}) - Qty: {product.quantity}")

if __name__ == "__main__":
    search_products()