from app import app, db, Product, InventoryOperation, OperationLine, Location
from datetime import datetime, timedelta

with app.app_context():
    # 1. Inject Products for the "Low Stock Alerts" Box
    # Added cost_price and sale_price to populate the financial dashboard
    p1 = Product(name="Copper Wire", sku="SKU-014", category_id=1, unit_of_measure="kg", cost_price=8.50, sale_price=12.00)
    p2 = Product(name="Safety Gloves", sku="SKU-031", category_id=1, unit_of_measure="pairs", cost_price=2.00, sale_price=4.50)
    p3 = Product(name="PVC Pipe 2in", sku="SKU-022", category_id=1, unit_of_measure="m", cost_price=1.20, sale_price=3.00)
    db.session.add_all([p1, p2, p3])
    db.session.flush()

    # 2. Inject a "Pending" Receipt (Waiting for arrival)
    pending_rec = InventoryOperation(document_type='Receipt', status='Waiting', source_location_id=2, dest_location_id=3, created_by=1)
    db.session.add(pending_rec)
    db.session.flush()
    db.session.add(OperationLine(operation_id=pending_rec.id, product_id=p1.id, quantity=150))

    # 3. Inject an "Overdue" Delivery (Failed to ship 2 days ago)
    overdue_del = InventoryOperation(document_type='Delivery', status='Overdue', source_location_id=3, dest_location_id=4, created_by=1)
    db.session.add(overdue_del)
    db.session.flush()
    db.session.add(OperationLine(operation_id=overdue_del.id, product_id=p2.id, quantity=25))

    # Backdate the overdue delivery
    overdue_del.created_at = datetime.utcnow() - timedelta(days=2)

    # 4. Save everything to the database
    db.session.commit()
    print("Hackathon Pitch Data Injected Successfully!")
