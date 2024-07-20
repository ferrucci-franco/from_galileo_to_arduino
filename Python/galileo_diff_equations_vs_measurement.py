# -*- coding: utf-8 -*-
"""
Created on Thu Jul 11 08:01:57 2024
@author: Franco FERRUCCI

This script simulates the motion of a pendulum using differential equations 
and compares the simulation results with experimental data from a CSV file. 
It solves the equations of motion for a "physical" pendulum with given 
friction, mass, moment of inertia and the length of the rod, and then plots
the simulated angular displacement against the angular displacement from 
the CSV file. 

The plot shows the simulation and measurement data, allowing for visual 
comparison of the theoretical model with real-world measurements.

"""

import pandas as pd
import numpy as np
from scipy.integrate import solve_ivp
import plotly.graph_objs as go
import plotly.io as pio

# Global variables:
truncate_csv_time = True
csv_filename = './csv_data/galileo_2024-07-19_15-25-54.csv'

# Constants
b = 0.00125         # Friction coefficient
M = 0.11544         # Mass
L = 0.687           # Length of the rod
d = L / 2           # Distance of the center of mass of the rod to the rod extreme
J = M * L**2 / 3    # Moment of inertia
g = 9.81            # Gravitational acceleration

# Natural frequency for small angles
omega_natural_small_angles = np.sqrt(3 * g / (2 * L))
T_natural_small_angles = 2 * np.pi / omega_natural_small_angles

# Initial conditions
theta_0 = np.deg2rad(-68.6)  # Initial angle in radians
omega_0 = 0.5  # Initial angular velocity

# Time span for simulation
t_span = (0, 60)  # 0 to 60 seconds
t_eval = np.linspace(t_span[0], t_span[1], 2000)  # Time points where the solution is evaluated

# Differential equations
def equations(t, y):
    theta, omega = y
    dtheta_dt = omega
    domega_dt = -(b * omega + M * g * d * np.sin(theta)) / J
    return [dtheta_dt, domega_dt]

# Solve the differential equations
sol = solve_ivp(equations, t_span, [theta_0, omega_0], t_eval=t_eval)

# Extract the results
t_sim = sol.t
theta_sim = np.rad2deg(sol.y[0])  # Convert the simulation results to degrees

# Read the CSV file
data = pd.read_csv(csv_filename)

# Extract time and angle from CSV
t_csv = data['Time'].values
theta_csv = data['Angle'].values  # Angle is already in degrees

# Truncate CSV data to match the simulation time span
if truncate_csv_time:
    mask = (t_csv >= t_span[0]) & (t_csv <= t_span[1])
    t_csv = t_csv[mask]
    theta_csv = theta_csv[mask]

# Plot the results using Plotly
fig = go.Figure()

# Add simulation result
fig.add_trace(go.Scatter(x=t_sim, y=theta_sim, mode='lines', name='Simulation',
                         line=dict(width=5)))  # Increase the width of the blue curve

# Add CSV data
fig.add_trace(go.Scatter(x=t_csv, y=theta_csv, mode='lines+markers', name='Measurement', marker=dict(size=5)))

title =  f'<b>FROM GALILEO GALILEI TO ARDUINO</b><br>'
title += f'<b>Pendulum Simulation vs CSV Data</b><br>'
title += f'File: '
title += '<i>' + str(csv_filename) + '</i>'

fig.update_layout(
    title=title,
    xaxis_title='Time (s)',
    yaxis_title='Theta (deg)',
    showlegend=True,
    template='plotly'
    # template='seaborn'
    # template='plotly_dark'
    # template='plotly_white'
)

# Render the plot
pio.renderers.default = 'browser'
fig.show()
