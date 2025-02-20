from app.services import db

class Product(db.Model):
    __tablename__ = 'product'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)

    # Fixed: Remove `backref` here and explicitly define the relationship
    events = db.relationship('Event', back_populates='product', lazy=True)

    def __repr__(self):
        return f"<Product {self.id} - {self.name}>"

    def to_dict(self):
        return {"id": self.id, "name": self.name}
    
    @staticmethod
    def create_product(data):
        product = Product(**data)
        db.session.add(product)
        db.session.commit()
        return product
    
    @staticmethod
    def update_product(product_id, data):
        product = db.session.get(Product, product_id)
        if not product:
            raise ValueError("Product not found")
        for key, value in data.items():
            setattr(product, key, value)
        db.session.commit()
        return product
    
    @staticmethod
    def delete_product(product_id):
        product = db.session.get(Product, product_id)
        if not product:
            raise ValueError("Product not found")
        db.session.delete(product)
        db.session.commit()
        return True
