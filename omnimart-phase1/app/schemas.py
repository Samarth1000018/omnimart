from pydantic import BaseModel, Field

class SessionCreate(BaseModel): source: str = Field(default="web", max_length=24)
class CartAdd(BaseModel): product_id: str; quantity: int = Field(default=1, ge=1, le=50); source: str = "manual"
class PaymentRequest(BaseModel): payment_method: str; simulate_success: bool = True
class EventCreate(BaseModel): event_type: str; payload: dict = Field(default_factory=dict)
class CartRemove(BaseModel): quantity: int | None = Field(default=None, ge=1, le=50)
