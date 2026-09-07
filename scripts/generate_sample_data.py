import csv
import random
from datetime import datetime, timedelta

random.seed(42)

first_names = ["James","Mary","John","Patricia","Robert","Jennifer","Michael","Linda","William","Elizabeth",
               "David","Barbara","Richard","Susan","Joseph","Jessica","Thomas","Sarah","Charles","Karen",
               "Daniel","Nancy","Matthew","Lisa","Anthony","Betty","Mark","Margaret","Paul","Sandra"]
last_names = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez","Martinez",
              "Hernandez","Lopez","Gonzalez","Wilson","Anderson","Thomas","Taylor","Moore","Jackson","Martin",
              "Lee","Perez","Thompson","White","Harris","Sanchez","Clark","Ramirez","Lewis","Robinson"]
cities = [("New York","NY"),("Los Angeles","CA"),("Chicago","IL"),("Houston","TX"),("Phoenix","AZ"),
          ("Philadelphia","PA"),("San Antonio","TX"),("San Diego","CA"),("Dallas","TX"),("Austin","TX")]

N_CUSTOMERS = 50
N_ORDERS = 200

customers = []
base_date = datetime(2024, 1, 1)

for i in range(1, N_CUSTOMERS + 1):
    fn = random.choice(first_names)
    ln = random.choice(last_names)
    city, state = random.choice(cities)
    created = base_date + timedelta(days=random.randint(0, 500))
    row = {
        "customer_id": f"CUST{i:04d}",
        "first_name": fn,
        "last_name": ln,
        "email": f"{fn.lower()}.{ln.lower()}{i}@example.com",
        "phone": f"555-{random.randint(100,999)}-{random.randint(1000,9999)}",
        "address_line1": f"{random.randint(100,9999)} {random.choice(['Main St','Oak Ave','Maple Dr','Elm St','Pine Rd'])}",
        "city": city,
        "state": state,
        "postal_code": f"{random.randint(10000,99999)}",
        "country": "USA",
        "created_at": created.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": created.strftime("%Y-%m-%d %H:%M:%S"),
    }
    customers.append(row)

# Intentional data-quality issues for the pipeline to catch/demonstrate:
customers[4] = {**customers[4], "email": ""}                     # missing email
customers[9] = {**customers[9], "email": customers[3]["email"]}   # duplicate email across customers
dup_row = dict(customers[15])                                     # exact duplicate customer_id row
customers.append(dup_row)

with open("data/sample/customers.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(customers[0].keys()))
    writer.writeheader()
    writer.writerows(customers)

statuses = ["completed","completed","completed","pending","shipped","cancelled"]
orders = []
valid_customer_ids = [c["customer_id"] for c in customers[:N_CUSTOMERS]]

for i in range(1, N_ORDERS + 1):
    cust_id = random.choice(valid_customer_ids)
    order_date = base_date + timedelta(days=random.randint(0, 600))
    subtotal = round(random.uniform(10, 500), 2)
    tax = round(subtotal * 0.07, 2)
    row = {
        "order_id": f"ORD{i:05d}",
        "customer_id": cust_id,
        "order_date": order_date.strftime("%Y-%m-%d"),
        "status": random.choice(statuses),
        "subtotal": subtotal,
        "tax": tax,
        "total_amount": round(subtotal + tax, 2),
        "currency": "USD",
        "created_at": order_date.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": order_date.strftime("%Y-%m-%d %H:%M:%S"),
    }
    orders.append(row)

# Intentional data-quality issues:
orders[50] = {**orders[50], "customer_id": "CUST9999"}   # orphan order, no matching customer
orders[100] = {**orders[100], "total_amount": ""}         # missing total_amount

with open("data/sample/orders.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(orders[0].keys()))
    writer.writeheader()
    writer.writerows(orders)

print(f"Wrote {len(customers)} customers and {len(orders)} orders to data/sample/")
