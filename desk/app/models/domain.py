from typing import Literal

STATUSES = ["submitted", "in_progress", "delivered", "accepted", "rejected"]
Status = Literal["submitted", "in_progress", "delivered", "accepted", "rejected"]
Role = Literal["client", "operator", "admin"]
Quality = Literal["good", "usable", "bad"]
STAFF = ("operator", "admin")
# (from, to) -> who owns the step
TRANSITIONS = {
    ("submitted", "in_progress"): "staff",
    ("in_progress", "delivered"): "staff",
    ("delivered", "accepted"): "client",
    ("delivered", "rejected"): "client",
    ("rejected", "in_progress"): "staff",
}
