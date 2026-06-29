import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm

df = pd.read_csv("LaserIntensityThreshold.csv")
I = df["I_mA"]
P = df["P_uW"]
threshold_1 = 110
threshold_2 = 138
h = I < threshold_1
v = I >= threshold_2

# Fit linear regression for region 1 (below threshold_1)
X1 = sm.add_constant(I[h])
model1 = sm.OLS(P[h], X1).fit()
m1, b1 = model1.params[1], model1.params[0]

# Fit linear regression for region 2 (above threshold_2)
X2 = sm.add_constant(I[v])
model2 = sm.OLS(P[v], X2).fit()
m2, b2 = model2.params[1], model2.params[0]

print("\nSlopes: x1 = ", m1, ", x2 = ", m2)
print("Lasing Threshold", -b2/m2)

plt.figure()
plt.plot(I, P, '.', label='Data')
plt.xlabel("Intensity (mA)")
plt.ylabel("Power (uW)")
plt.title("Laser Intensity Threshold")
plt.grid()
plt.show()