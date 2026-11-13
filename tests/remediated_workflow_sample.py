def calculate_tax(amount: float, rate: float) -> float:
    if rate <= 0:
        return 0.0
    return round(amount * rate, 2)
