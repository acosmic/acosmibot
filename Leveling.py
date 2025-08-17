import math
from decimal import Decimal


class Leveling:
    def __init__(self):
        self.base_exp = 125

    def calc_level(self, exp):
        # Convert Decimal to float if needed
        if isinstance(exp, Decimal):
            exp = float(exp)

        level = math.floor((exp / self.base_exp) ** 0.5)
        return level

    def calc_exp_required(self, level):
        # Ensure level is also a float/int for consistency
        if isinstance(level, Decimal):
            level = float(level)

        exp_required_for_next_level = ((level) ** 2) * self.base_exp
        return exp_required_for_next_level