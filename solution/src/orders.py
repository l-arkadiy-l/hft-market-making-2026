"""
Наши лимитные ордера. Execution policy в engine.py.
"""
from itertools import count

_id_counter = count(1)


class Order:
    def __init__(self, id: int, side: str, price: int, size: float,
                 placed_ts_us: int, filled_size: float = 0.0):
        self.id = id
        self.side = side
        self.price = price
        self.size = size
        self.placed_ts_us = placed_ts_us
        self.filled_size = filled_size

    def remaining(self) -> float:
        return self.size - self.filled_size

    def is_active(self) -> bool:
        return self.remaining() > 1e-9

    def __repr__(self):
        return (f"Order(id={self.id}, side={self.side}, price={self.price}, "
                f"size={self.size}, filled={self.filled_size})")


class OrderManager:
    def __init__(self):
        self.active: dict[int, Order] = {}
        self.history: list[Order] = []

    def place(self, side: str, price: int, size: float, ts_us: int) -> Order:
        order = Order(
            id=next(_id_counter),
            side=side,
            price=price,
            size=size,
            placed_ts_us=ts_us,
        )
        self.active[order.id] = order
        self.history.append(order)
        return order

    def cancel(self, order_id: int) -> None:
        self.active.pop(order_id, None)

    def cancel_all(self) -> None:
        self.active.clear()

    def cancel_side(self, side: str) -> None:
        ids = [oid for oid, o in self.active.items() if o.side == side]
        for oid in ids:
            self.active.pop(oid)
