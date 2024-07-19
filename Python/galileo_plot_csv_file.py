# -*- coding: utf-8 -*-
"""
Created on Thu Jul 11 08:01:57 2024

@author: Franco FERRUCCI
"""

#%% Imports
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

# Set default renderer to browser
pio.renderers.default = 'browser'

#%% Function
def read_and_plot_csv(filename):
    # Read the CSV file
    data = pd.read_csv(filename)
    
    # Ensure the CSV has the correct columns
    if 'Time' not in data.columns or 'Angle' not in data.columns:
        raise ValueError("CSV file must contain 'Time' and 'Angle' columns")
    
    time = data['Time']
    angle = data['Angle']
    
    # Create the plot
    fig = go.Figure()
    
    # Add the data trace
    fig.add_trace(go.Scatter(x=time, y=angle, mode='lines+markers', name='Angle'))
    
    title =  f'<b>FROM GALILEO GALILEI TO ARDUINO</b><br>'
    title += f'<b><i>ANGLE vs TIME</i></b><br>'
    title += f'File: '
    title += '<i>' + str(filename) + '</i>'
    
    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title='Time (sec)',
        yaxis_title='Angle (°)',
        template='seaborn'
        # template='plotly_dark'
        # template='plotly_white'
    )
    
    # Show the plot
    fig.show()

#%% Example usage
filename = r'./csv_data/galileo_2024-07-19_09-27-13.csv'
read_and_plot_csv(filename)
