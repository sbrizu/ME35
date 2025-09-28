import machine, neopixel
np = neopixel.NeoPixel(machine.Pin(15), 2)
np[0] = (255, 0, 0)
np[1] = (0, 128, 0)
np.write()

