import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

df = pd.read_csv("Laser.csv")
x = df["x_mm"]
P = df["P_mW"]
dP = np.gradient(P, x)  

plt.figure()
plt.plot(x, P)
plt.xlabel("Position (mm)")
plt.ylabel("Power (mW)")
plt.title("Laser Characterisation")
plt.grid()
plt.show()