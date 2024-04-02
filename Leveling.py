import math

class Leveling:
    def __init__(self):
        self.base_exp = 25

    def calc_level(self, exp):
        level = math.floor((exp / self.base_exp) ** 0.5)
        return level
   
    def calc_exp_required(self, level):
        exp_required_for_next_level = ((level) ** 2) * self.base_exp
        return exp_required_for_next_level

