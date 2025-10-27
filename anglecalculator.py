import math
l1 = 2
l2 = 3

class FK():
    def __init__(self,l1,l2):
        self.l1 = l1
        self.l2 = l2
        self.r1 = 0
        self.r2 = 0
        
    def forward(self, d1, d2): #d and r are angle in degrees and radians
        self.r1 = self.convert(d1)
        self.r2 = self.convert(d2)
        x = self.l1 * math.cos(self.r1) + self.l2 * math.cos(self.r1 + self.r2)
        y = self.l1 * math.sin(self.r1) + self.l2 * math.sin(self.r1 + self.r2)
        return (x,y)
    
    
    def convert(self, angle):
        return angle*math.pi / 180
    