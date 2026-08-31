from fastapi import FastAPI, HTTPException, Query
from demo_api_clean.models import Product, ProductCategory


app = FastAPI(
    title="Clean Product API",
    version="1.0.0",
)


products_db: list[Product] = [
    Product(
        id=1001,
        name="Reference Product",
        sku="ABC-1001",
        category="electronics",
        active=True,
        price=100.0,
        quantity=10,
        warehouse_priority=1,
        tags=["reference"],
        feature_codes=["F1", "F2"],
        supported_regions=["EU"],
        manufacturer={
            "name": "Reference Manufacturer",
            "country": "Bulgaria",
        },
        serial_code="REFERENCE",
        primary_code="PRIMARY",
        secondary_code="SECONDARY",
    ),
    Product(
        id=1002,
        name="Sample Book",
        sku="BOK-1002",
        category="books",
        active=True,
        price=25.0,
        quantity=5,
        warehouse_priority=2,
        tags=["book"],
        feature_codes=["B1", "B2"],
        supported_regions=["EU", "US"],
        manufacturer={
            "name": "Sample Publisher",
            "country": "United Kingdom",
        },
        serial_code="SAMPLE",
        primary_code="BOOKONE",
        secondary_code="BOOKTWO",
    ),
]


@app.get("/products")
def get_products() -> list[Product]:
    return products_db


@app.get("/products/search")
def search_products(
    min_quantity: int = Query(..., ge=0),
    category: ProductCategory = Query(...),
) -> list[Product]:
    return [
        product
        for product in products_db
        if product.quantity >= min_quantity
        and product.category == category
    ]


@app.get("/products/{product_id}")
def get_product(product_id: int) -> Product:
    for product in products_db:
        if product.id == product_id:
            return product

    raise HTTPException(
        status_code=404,
        detail="Product not found",
    )


@app.post("/products")
def create_product(product: Product) -> Product:
    for index, existing_product in enumerate(products_db):
        if existing_product.id == product.id:
            products_db[index] = product
            return product

    products_db.append(product)
    return product


@app.put("/products/{product_id}")
def update_product(
    product_id: int,
    updated_product: Product,
) -> Product:
    if updated_product.id != product_id:
        raise HTTPException(
            status_code=422,
            detail="Body id must match path id",
        )

    for index, product in enumerate(products_db):
        if product.id == product_id:
            products_db[index] = updated_product
            return updated_product

    raise HTTPException(
        status_code=404,
        detail="Product not found",
    )


@app.delete("/products/{product_id}")
def delete_product(product_id: int) -> dict:
    for index, product in enumerate(products_db):
        if product.id == product_id:
            del products_db[index]

            return {
                "message": "Product deleted",
                "id": product_id,
            }

    raise HTTPException(
        status_code=404,
        detail="Product not found",
    )