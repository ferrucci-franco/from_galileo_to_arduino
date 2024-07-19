# -*- coding: utf-8 -*-
"""
Created on Thu Jul 11 08:01:57 2024

@author: Franco FERRUCCI
"""

#%% Imports
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import scipy.fftpack
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.io as pio
pio.renderers.default = 'browser'

#%% Functions
def read_and_process_csv(filename):
    # Read the CSV file
    data = pd.read_csv(filename)
    
    # Ensure the CSV has the correct columns
    if 'Time' not in data.columns or 'Angle' not in data.columns:
        raise ValueError("CSV file must contain 'Time' and 'Angle' columns")
    
    time = data['Time'].values
    angle = data['Angle'].values
    
    # Find the first positive zero crossing
    zero_crossings = np.where(np.diff(np.sign(angle)) > 0)[0]
    
    if len(zero_crossings) == 0:
        raise ValueError("No positive zero crossing found in the data")
    
    first_zero_crossing = zero_crossings[0]
    
    # Strip data until the first positive zero crossing
    time = time[first_zero_crossing:] - time[first_zero_crossing]
    angle = angle[first_zero_crossing:]
    
    return time, angle

def sinusoidal_with_exponential_decay(t, A, omega, theta, phi, B):
    return A * np.exp(-theta * t) * np.sin(omega * t - phi) + B

def fit_data(time, angle):
    # Initial guess for the parameters
    A_guess = (np.max(angle) - np.min(angle)) / 2
    omega_guess = 2 * np.pi / 1  # Approximate frequency
    theta_guess = 0.05           # Small decay
    phi_guess = 0.0
    B_guess = 0.0

    initial_guess = [A_guess, omega_guess, theta_guess, phi_guess, B_guess]

    # Curve fitting
    popt, pcov = curve_fit(sinusoidal_with_exponential_decay, time, angle, p0=initial_guess)
    
    A, omega, theta, phi, B = popt
    
    return A, omega, theta, phi, B

def calculate_r_squared(angle, angle_fit):
    residuals = angle - angle_fit
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((angle - np.mean(angle))**2)
    r_squared = 1 - (ss_res / ss_tot)
    return r_squared

def compute_period_via_fft(time, angle):
    # Number of sample points
    N = len(time)
    
    # Increased number of sample points for higher resolution
    N_high_res = N * 20
    
    # Sample spacing
    T = time[1] - time[0]
    
    # Perform FFT with zero-padding
    yf = scipy.fftpack.fft(angle, N_high_res)
    xf = np.fft.fftfreq(N_high_res, T)
    
    # Only keep the positive frequencies
    xf = xf[:N_high_res//2]
    yf = 2.0/N * np.abs(yf[:N_high_res//2])
    
    # Identify the peak in the FFT amplitude spectrum
    idx_peak = np.argmax(yf)
    freq_peak = xf[idx_peak]
    
    # Compute the period
    period_fft = 1 / freq_peak
    
    return period_fft, xf, yf

def analyze_and_plot_csv(filename):
    time, angle = read_and_process_csv(filename)
    A, omega, theta, phi, B = fit_data(time, angle)
    period_fit = 2 * np.pi / omega
    freq_fit = 1/period_fit
    phi_deg = phi * 180/np.pi
    
    # Compute period via FFT
    period_fft, xf, yf = compute_period_via_fft(time, angle)
    freq_fft = 1/period_fft
    
    # Generate data points for the fitted curve
    t_fit = time
    angle_fit = sinusoidal_with_exponential_decay(t_fit, A, omega, theta, phi, B)
    
    # Calculate R^2
    r_squared = calculate_r_squared(angle, angle_fit)
    
    # Plotting with Plotly
    fig = make_subplots(rows=1, cols=2, subplot_titles=('<b>Time Domain</b>', '<b>Frequency Domain (FFT)</b>'))
    
    # Original data
    fig.add_trace(go.Scatter(x=time, y=angle, mode='lines+markers', name='Original Data'), row=1, col=1)
    
    # Fitted curve
    fig.add_trace(go.Scatter(x=t_fit, y=angle_fit, mode='lines', name='Fitted Curve'), row=1, col=1)
    
    # FFT
    fig.add_trace(go.Scatter(x=xf, y=yf, mode='lines', name='FFT'), row=1, col=2)
    
    # Constructing the title with fitting function and parameters
    title = f'<b>SINUSOIDAL WITH EXPONENTIAL DECAY FIT</b><br>'
    title += f'Function: A * exp(-theta * t) * sin(2π/T * t - phi) + B<br>'
    title += f'Parameters: Period={period_fit:.2f} s, Freq={freq_fit:.2f} Hz, A={A:.2f} °, theta={theta:.3f} s⁻¹, phi={phi_deg:.2f} °, B={B:.3f} °<br>'
    title += f'Goodness of fit R^2: {r_squared:.4f}'
    
    # Add layout information
    fig.update_layout(
        title=dict(
            text=title,
            x=0.5,
            y=0.95,
            xanchor='center',
            yanchor='top'
        ),
        margin=dict(t=140),  # Increase the top margin to provide space for the title
        legend=dict(
            x=1,
            y=1,
            traceorder='normal',
            yanchor='top',
            font=dict(
                family='sans-serif',
                size=12,
                color='black'
            ),
            bgcolor='LightSteelBlue',
            bordercolor='Black',
            borderwidth=0
        )
    )
    
    fig.update_xaxes(title_text='Time (sec)', row=1, col=1)
    fig.update_yaxes(title_text='Angle (°)', row=1, col=1)
    
    fig.update_xaxes(title_text='Frequency (Hz)',range=[0, 2.5], row=1, col=2)
    fig.update_yaxes(title_text='Amplitude', row=1, col=2)
    
    # Show the plot
    fig.show()
    
    print(f"Period from fit: {period_fit}")
    print(f"Period from FFT: {period_fft}")
    print(f"Freq. from fit: {freq_fit}")
    print(f"Freq. from FFT: {freq_fft}")
    print(f"A: {A}")
    print(f"Theta: {theta}")
    print(f"Phi: {phi}")
    print(f"B: {B}")
    
    return time, angle_fit


#%% Example usage
filename = r'./csv_data/galileo_2024-07-19_09-27-13.csv'
analyze_and_plot_csv(filename)
