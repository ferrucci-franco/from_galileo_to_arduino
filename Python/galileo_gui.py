# -*- coding: utf-8 -*-
"""
Created on Thu Jul 11 08:01:57 2024

@author: Franco FERRUCCI
"""
#%% Version
__version__ = '1.1.0'

#%% Imports
import sys
import re
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QComboBox, QCheckBox, QLabel, QRadioButton, QButtonGroup, QGroupBox
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
import pyqtgraph as pg
import serial
import serial.tools.list_ports
import datetime
from scipy.io import savemat

#%%
# Global flag to reset the time axis when "Clear plot" button is pressed
# (variable shared between SerialReader and MainWindow classes):
this_is_the_first_read = True

#%% Serial port thread class
class SerialReader(QThread):
    data_received = pyqtSignal(float, float)  # Signal to send time and angle data

    def __init__(self, port='COM9', baudrate=115200, show_raw_data_checkbox=None, parent=None):
        super().__init__(parent)
        self.port = port
        self.baudrate = baudrate
        self.show_raw_data_checkbox = show_raw_data_checkbox
        self.running = True
        self.previous_time = -1
        self.startup_time = 0
        self.pattern = re.compile(r"Time:\s(\d+)\sms,\sAngle:\s([-\d.]+)")

    def run(self):
        global this_is_the_first_read

        try:
            self.serial_port = serial.serial_for_url(self.port, self.baudrate, timeout=1, do_not_open=True)

            # Disable DTR and RTS to prevent the Arduino from resetting:
            self.serial_port.dtr = False
            self.serial_port.rts = False
            
            # Open port:
            self.serial_port.open()
            
            # Flush the serial port buffer
            self.serial_port.flushInput()
            
            # Print port status:
            print(f"Opened serial port {self.port} at {self.baudrate} baud.")
            
        except serial.SerialException as e:
            print(f"Error opening serial port: {e}")
            self.serial_port = None
            return

        while self.running:
            if self.serial_port and self.serial_port.in_waiting > 0:
                try:
                    line = self.serial_port.readline().decode('utf-8').strip()
                except UnicodeDecodeError:
                    continue  # Skip this line if there's a decode error
                match = self.pattern.match(line)
                if match:
                    if this_is_the_first_read:                       
                        self.startup_time = int(match.group(1))
                        this_is_the_first_read = False
                        time_ms = 0
                    else:
                        time_ms = int(match.group(1)) - self.startup_time

                    if time_ms == self.previous_time:
                        continue # Skip line if it already parsed (not sure if it necessary)
                    
                    angle = float(match.group(2))
                    self.previous_time = time_ms
                    time_s = time_ms / 1000.0
                    self.data_received.emit(time_s, angle)
                    
                    if self.show_raw_data_checkbox.isChecked():
                        print(f"Parsed data: Time: {time_s}s, Angle: {angle}°")

        if self.serial_port:
            self.serial_port.close()
            print("Closed serial port.")

    def stop(self):
        self.running = False
        self.wait()

#%% GUI class
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("From Galileo Galilei to Arduino")  # Set the window title

        self.data = {
            "Time": [],
            "Angle": []
        }
        self.running = True

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        self.plot_widget = pg.PlotWidget()
        self.layout.addWidget(self.plot_widget)

        self.combobox = QComboBox()
        self.combobox.addItems(self.get_serial_ports())
        
        self.refresh_button = QPushButton("Refresh Ports")
        self.refresh_button.clicked.connect(self.refresh_ports)
        
        self.connect_button = QPushButton("Connect and Run")
        self.connect_button.setCheckable(True)  # Make the button checkable
        self.connect_button.clicked.connect(self.connect_and_run)
        
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.disconnect)
        self.disconnect_button.setEnabled(False)  # Disable the button initially

        self.show_raw_data_checkbox = QCheckBox("Show received raw data in the console")
        
        self.h_layout = QHBoxLayout()
        self.h_layout.addWidget(self.refresh_button)  # Add the refresh button to the layout
        self.h_layout.addWidget(self.combobox)
        self.h_layout.addWidget(self.connect_button)
        self.h_layout.addWidget(self.disconnect_button)
        self.h_layout.addWidget(self.show_raw_data_checkbox)
        self.layout.addLayout(self.h_layout)  # Add the horizontal layout to the main vertical layout

        # Create a new horizontal layout for the first row of buttons
        self.first_row_layout = QHBoxLayout()
        
        # Add the Clear Plot button
        self.reset_button = QPushButton("Clear plot")
        self.reset_button.clicked.connect(self.reset_time)
        self.first_row_layout.addWidget(self.reset_button)
        
        # Add the Auto Scale XY button
        self.auto_scale_button = QPushButton("Auto Scale XY")
        self.auto_scale_button.clicked.connect(self.auto_scale_xy)
        self.first_row_layout.addWidget(self.auto_scale_button)

        # Add the Stop and Quit button to the right of Auto Scale XY button
        self.stop_button = QPushButton("Stop and Quit")
        self.stop_button.clicked.connect(self.stop_and_quit)
        self.first_row_layout.addWidget(self.stop_button)

        # Add the first row layout to the main layout
        self.layout.addLayout(self.first_row_layout)

        # Create a QGroupBox to enclose the third row
        self.third_row_groupbox = QGroupBox("Output Settings")
        self.third_row_layout = QHBoxLayout(self.third_row_groupbox)
        
        # Add the Save Data button
        self.save_data_button = QPushButton("Save current view to disk")
        self.save_data_button.clicked.connect(self.save_data)
        self.third_row_layout.addWidget(self.save_data_button)

        # Add the Output format label
        self.output_format_label = QLabel("Output file(s) format:")
        self.third_row_layout.addWidget(self.output_format_label)

        # Add radio buttons for file export options
        self.export_option_group = QButtonGroup()
        self.csv_only_radio = QRadioButton("CSV only")
        self.csv_and_mat_radio = QRadioButton("CSV and Matlab MAT file")
        self.export_option_group.addButton(self.csv_only_radio, 1)
        self.export_option_group.addButton(self.csv_and_mat_radio, 2)
        self.csv_only_radio.setChecked(True)  # Default to 'CSV only'

        # Add the radio buttons to the layout
        self.third_row_layout.addWidget(self.csv_only_radio)
        self.third_row_layout.addWidget(self.csv_and_mat_radio)

        # Add the third row groupbox to the main layout
        self.layout.addWidget(self.third_row_groupbox)

        self.plot_item = self.plot_widget.getPlotItem()
        self.configure_plot_item()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(50)

        self.serial_reader = None

        # Add the label at the bottom
        self.footer_label = QLabel()
        self.footer_label.setText(
            f'Created by Franco FERRUCCI | Version {__version__} | <a href="https://github.com/ferrucci-franco/from_galileo_to_arduino">https://github.com/ferrucci-franco/from_galileo_to_arduino</a>')
        self.footer_label.setOpenExternalLinks(True)
        self.layout.addWidget(self.footer_label)


    def get_serial_ports(self):
        ports = serial.tools.list_ports.comports()
        return [f"{port.device} ({port.description[:15]}...)" if len(port.description) > 15 else f"{port.device} ({port.description})" for port in ports]


    def refresh_ports(self):
        self.combobox.clear()
        self.combobox.addItems(self.get_serial_ports())

    def connect_and_run(self):
        self.reset_time()  # Clear the plot
        self.auto_scale_xy()  # Reset plot scale
        selected_port = self.combobox.currentText().split()[0]  # Extract the port number
        show_raw_data_checkbox = self.show_raw_data_checkbox
        self.serial_reader = SerialReader(port=selected_port, show_raw_data_checkbox=show_raw_data_checkbox)
        self.serial_reader.data_received.connect(self.add_data_point)
        self.serial_reader.start()
        
        # Disable the buttons only if the connection is successful
        QTimer.singleShot(1000, self.check_connection_status)

    def check_connection_status(self):
        if self.serial_reader and self.serial_reader.serial_port and self.serial_reader.serial_port.is_open:
            self.connect_button.setChecked(True)  # Keep the button pressed
            self.connect_button.setEnabled(False)  # Disable the button
            self.disconnect_button.setEnabled(True)  # Enable the "Disconnect" button
        else:
            self.connect_button.setChecked(False)  # Unpress the button
            self.connect_button.setEnabled(True)  # Enable the button

    def disconnect(self):
        if self.serial_reader is not None:
            self.serial_reader.stop()
            self.serial_reader = None
            print("Disconnected from the serial port.")
        self.connect_button.setChecked(False)  # Unpress the button
        self.connect_button.setEnabled(True)  # Enable the button
        self.disconnect_button.setEnabled(False)  # Disable the "Disconnect" button

    def configure_plot_item(self):
        self.plot_widget.setBackground('w')
        self.plot_item.setTitle("From Galileo Galilei to Arduino", color='black')
        self.plot_item.setLabel('left', 'Angle (°)', color='black')
        self.plot_item.setLabel('bottom', 'Time (seconds)', color='black')
        self.plot_item.showGrid(x=True, y=True, alpha=0.5)

    def add_data_point(self, time_s, angle):
        self.data["Time"].append(time_s)
        self.data["Angle"].append(angle)

    def update_plot(self):
        if not self.running:
            return

        self.plot_item.clear()
        pen = pg.mkPen(color=(255, 0, 0), width=2)
        self.plot_item.plot(self.data["Time"], self.data["Angle"], pen=pen)

    def reset_time(self):
        global this_is_the_first_read
        
        self.data = {
            "Time": [],
            "Angle": []
        }
        self.plot_item.clear()
        this_is_the_first_read = True

    def auto_scale_xy(self):
        self.plot_item.enableAutoRange()

    def stop_and_quit(self):
        self.running = False
        if self.serial_reader is not None:
            self.serial_reader.stop()

        # self.save_data()  # Save data
        self.close()  # Close the application

    def save_data(self):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if not os.path.exists('./csv_data'):
            os.makedirs('./csv_data')
        
        csv_filename = f"./csv_data/galileo_{timestamp}.csv"
        with open(csv_filename, 'w') as file:
            file.write("Time,Angle\n")
            for time, angle in zip(self.data["Time"], self.data["Angle"]):
                file.write(f"{time},{angle}\n")
        print(f"Data saved to {csv_filename}")

        if self.export_option_group.checkedId() == 2:  # 'CSV and MAT file' is selected
            mat_filename = csv_filename.rsplit('.', 1)[0] + '.mat'
            savemat(mat_filename, {'data': {'Time': self.data["Time"], 'Angle': self.data["Angle"]}})
            print(f"Data saved to MAT file at {mat_filename}")

    def closeEvent(self, event):
        # Override close event to call stop_and_quit when window is closed
        self.stop_and_quit()
        event.accept()

#%% Run the app
if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = MainWindow()
    window.setGeometry(100, 100, 800, 600)
    window.show()
    window.raise_()             # Bring the window to the foreground
    window.activateWindow()     # Activate the window
    sys.exit(app.exec_())
