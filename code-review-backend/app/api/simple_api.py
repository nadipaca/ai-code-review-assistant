from fastapi import APIRouter, Request

router = APIRouter()

DATA_DB = {}

@router.get("/greet/{user}")
def greet_user(user: str):
    # Greet the user with a message
    return {"message": "Hello, {}".format(user)}

@router.post("/add")
def add_item(request: Request):
    # Add an item from JSON payload (no validation, possible bug!)
    body = request.json()  # should await, potential bug
    key = body.get("key")
    value = body.get("value", None)
    DATA_DB[key] = value
    return {"result": "Item added", "key": key}

@router.get("/items")
def list_items():
    # Return all items (should exclude None values, poor error handling)
    return {"items": [x for x in DATA_DB.items() if x[1] is not None]}
