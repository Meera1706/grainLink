from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import desc, and_, or_

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'your-secret-key-123'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Context processor to inject current datetime into all templates
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# Database Models
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    is_farmer = db.Column(db.Boolean, default=False)
    products = db.relationship('Product', backref='farmer_ref', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.String(50))
    farmer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    orders = db.relationship('Order', backref='product_ref', lazy=True)

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    vendor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    quantity = db.Column(db.Integer)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')
    product = db.relationship('Product', backref='order_products')
    vendor = db.relationship('User', backref='vendor_orders')

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Context processor for unread message count
@app.context_processor
def inject_messages_count():
    if current_user.is_authenticated:
        unread_count = Message.query.filter_by(
            recipient_id=current_user.id,
            is_read=False
        ).count()
        return {'unread_messages_count': unread_count}
    return {'unread_messages_count': 0}

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_pw = generate_password_hash(request.form['password'])
        new_user = User(
            name=request.form['name'],
            email=request.form['email'],
            password=hashed_pw,
            is_farmer=request.form.get('user_type') == 'farmer'
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid email or password', 'error')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_farmer:
        products = Product.query.filter_by(farmer_id=current_user.id).all()
        product_ids = [p.id for p in products]
        pending_orders_count = Order.query.filter(
            Order.product_id.in_(product_ids),
            Order.status == 'pending'
        ).count()
        return render_template('farmer_dashboard.html', 
                             products=products,
                             pending_orders_count=pending_orders_count)
    else:
        products = Product.query.all()
        return render_template('vendor_dashboard.html', products=products)

@app.route('/farmer_orders')
@login_required
def farmer_orders():
    if current_user.is_farmer:
        products = Product.query.filter_by(farmer_id=current_user.id).all()
        product_ids = [p.id for p in products]
        orders = Order.query.filter(Order.product_id.in_(product_ids))\
                           .order_by(desc(Order.order_date))\
                           .all()
        return render_template('farmer_orders.html', orders=orders)
    return redirect(url_for('dashboard'))

@app.route('/update_order/<int:order_id>/<status>')
@login_required
def update_order(order_id, status):
    if current_user.is_farmer:
        order = Order.query.get_or_404(order_id)
        if order.product.farmer_id == current_user.id:
            order.status = status
            db.session.commit()
            flash(f'Order status updated to {status}', 'success')
    return redirect(url_for('farmer_orders'))

# Messaging Routes
@app.route('/messages')
@login_required
def messages():
    # Get distinct conversations
    sent_conversations = db.session.query(
        Message.recipient_id
    ).filter_by(
        sender_id=current_user.id
    ).distinct()

    received_conversations = db.session.query(
        Message.sender_id
    ).filter_by(
        recipient_id=current_user.id
    ).distinct()

    # Combine and get unique user IDs
    user_ids = {id for (id,) in sent_conversations.union(received_conversations).all()}
    
    # Get last message and unread count for each conversation
    conversations = []
    for user_id in user_ids:
        other_user = User.query.get(user_id)
        last_message = Message.query.filter(
            or_(
                and_(Message.sender_id == current_user.id, Message.recipient_id == user_id),
                and_(Message.sender_id == user_id, Message.recipient_id == current_user.id)
            )
        ).order_by(Message.timestamp.desc()).first()

        unread_count = Message.query.filter_by(
            sender_id=user_id,
            recipient_id=current_user.id,
            is_read=False
        ).count()

        conversations.append({
            'user': other_user,
            'last_message': last_message,
            'unread_count': unread_count
        })

    # Sort conversations by most recent message
    conversations.sort(key=lambda x: x['last_message'].timestamp, reverse=True)

    return render_template('messages.html', conversations=conversations)

@app.route('/messages/<int:user_id>', methods=['GET', 'POST'])
@login_required
def conversation(user_id):
    other_user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        content = request.form.get('content')
        if content and content.strip():
            new_message = Message(
                sender_id=current_user.id,
                recipient_id=user_id,
                content=content.strip()
            )
            db.session.add(new_message)
            db.session.commit()
            flash('Message sent!', 'success')
            return redirect(url_for('conversation', user_id=user_id))
        else:
            flash('Message cannot be empty', 'error')
    
    # Mark received messages as read
    Message.query.filter_by(
        sender_id=user_id,
        recipient_id=current_user.id,
        is_read=False
    ).update({'is_read': True})
    db.session.commit()
    
    # Get all messages between current user and other user
    messages = Message.query.filter(
        or_(
            and_(Message.sender_id == current_user.id, Message.recipient_id == user_id),
            and_(Message.sender_id == user_id, Message.recipient_id == current_user.id)
        )
    ).order_by(Message.timestamp.asc()).all()
    
    return render_template('conversation.html', 
                         other_user=other_user, 
                         messages=messages)

@app.route('/find-user')
@login_required
def find_user():
    # Get all users except current user
    users = User.query.filter(User.id != current_user.id).all()
    return render_template('find_user.html', users=users)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if current_user.is_farmer:
        if request.method == 'POST':
            new_product = Product(
                name=request.form['name'],
                price=float(request.form['price']),
                quantity=request.form['quantity'],
                farmer_id=current_user.id
            )
            db.session.add(new_product)
            db.session.commit()
            flash('Product added successfully!', 'success')
            return redirect(url_for('dashboard'))
        return render_template('add_product.html')
    return redirect(url_for('dashboard'))

@app.route('/place_order/<int:product_id>', methods=['POST'])
@login_required
def place_order(product_id):
    if not current_user.is_farmer:
        try:
            quantity = int(request.form['quantity'])
            product = Product.query.get_or_404(product_id)
            
            new_order = Order(
                product_id=product.id,
                vendor_id=current_user.id,
                quantity=quantity
            )
            db.session.add(new_order)
            db.session.commit()
            
            flash(f'Order placed for {quantity} {product.name}!', 'success')
        except ValueError:
            flash('Invalid quantity', 'error')
    return redirect(url_for('dashboard'))

# Initialize database
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)