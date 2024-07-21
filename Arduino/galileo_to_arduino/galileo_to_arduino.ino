/*
  From Galileo Galilei to Arduino.
  https://github.com/ferrucci-franco/from_galileo_to_arduino
  Author: Franco FERRUCCI
  
  Encoder Position and Angle Measurement

  This program measures the position and angle of a rotary encoder and displays the angle on a MAX7219 7-segment display. 
  It also provides options for serial communication and debugging using an LED.

  Libraries Used:
  - TimerOne: For setting up and handling Timer1 interrupt service routine.
  - digitalWriteFast: For faster reading and writing of digital pins.
  - max7219: For controlling the MAX7219 display.

  Debug Levels (_LOG_LEVEL_):
  0: No debug.
  1: Send raw 'encoderPosition' via serial port.
  2: Toggle a debug pin when timer enters ISR.

  Definitions:
  - BAUD_RATE: Serial communication baud rate.
  - TIMER1_MICROSECONDS: Timer1 interval in microseconds.
  - MAX7219 display control pins and brightness settings.

  Encoder Setup:
  - Pins for encoder channels A and B, and a button for resetting the encoder position.
  - Encoder constants for counts per revolution (CPR) and angle calculation.

  Timer Setup:
  - Timer1 for periodic interrupts to handle data sending and angle calculations.

  Functions:
  - setup(): Initializes serial communication, pin modes, interrupts, Timer1, and the MAX7219 display.
  - loop(): Main loop to check button state and send data to the serial port and display.
  - updateEncoder(): Interrupt service routine to update encoder position based on pin changes.
  - sendData(): Timer1 interrupt service routine to increment time counter, calculate angle, and set flag for data transmission.
  - displayAngle(float angle): Converts the angle to a string and displays it on the MAX7219.

  Usage:
  - Connect the encoder to the specified pins and initialize the system by uploading the code.
  - The angle will be displayed on the MAX7219 display, and data can be sent to the serial port based on the debug level.
*/

#include <TimerOne.h>           // Timer1 library (interrupt service routine).
#include <digitalWriteFast.h>   // Library that reads and write pins faster.
#include <max7219.h>            // Library to control MAX7219 display.

#define _LOG_LEVEL_ 0 // 0: No debug.
                      // 1: Send raw 'encoderPosition' via serial port.
                      // 2: Toggle debug pin 1 when timer enter ISR.

// Serial transmission baud rate:
#define BAUD_RATE (115200)

// Timer 1 defines:
#define TIMER1_MICROSECONDS (20000)
#define TIMER1_MILLISECONDS (TIMER1_MICROSECONDS/1000)

// MAX7219 display defines:
#define LEFT  0
#define RIGHT 1
#define MAX7219_NUMBER_OF_DECIMALS 0

// MAX7219 library, redefine REG_INTENSITY. Note: 0x01 = low intensity, 0x0A = high intensity:
#ifdef REG_INTENSITY
#undef REG_INTENSITY
#define REG_INTENSITY     0x08                       
#endif

// MAX7219 library, redefine MAX_CLK pin (in case we want to change pin number):
#ifdef MAX_CLK
#undef MAX_CLK
#define MAX_CLK 10                       
#endif

// MAX7219 library, redefine MAX_CS pin (in case we want to change pin number):
#ifdef MAX_CS
#undef MAX_CS
#define MAX_CS 11                       
#endif

// MAX7219 library, redefine MAX_DIN pin (in case we want to change pin number):
#ifdef MAX_DIN
#undef MAX_DIN
#define MAX_DIN 12                       
#endif

// Define the pins for the encoder and the button:
const int encoderPinA = 2; // Interrupt pin 0
const int encoderPinB = 3; // Interrupt pin 1
const int buttonPin = 4;   // Button pin
const int encoderPinA_out = 5; // pin to duplicate 'encoderPinA' input 
const int encoderPinB_out = 6; // pin to duplicate 'encoderPinB' input

// Encoder variables:
volatile long encoderPosition = 0;
volatile double angle = 0;
volatile bool lastA = LOW;
volatile bool lastB = LOW;
volatile bool there_is_something_to_send = LOW;

// Encoder constants:
const double encoder_CPR = 1000.0; // CPR: counts per revolution
const double encoder_divisor = encoder_CPR * 4.0 / 360.0; // 4 pulses per count, as in any incremental encoder

// Timer counter:
volatile unsigned long timeCounter = 0;

// Debug pin:
#if (_LOG_LEVEL_ == 2)
const int debugPin1 = 7;
#endif

// Declares display struct:
MAX7219 max7219;

void setup() {
  Serial.begin(BAUD_RATE);

  // Set the encoder pins as inputs
  pinModeFast(encoderPinA, INPUT);
  pinModeFast(encoderPinB, INPUT);

  // Set encoder output pins (equal to input pins)
  pinModeFast(encoderPinA_out, OUTPUT);
  pinModeFast(encoderPinB_out, OUTPUT);

  // Enable pull-up resistors for encoder
  digitalWriteFast(encoderPinA, HIGH);
  digitalWriteFast(encoderPinB, HIGH);

  // Set the button pin as input with pull-up resistor
  pinModeFast(buttonPin, INPUT_PULLUP);

  // Debug pin
  #if (_LOG_LEVEL_ == 2)
  pinModeFast(debugPin1, OUTPUT);
  digitalWriteFast(debugPin1, LOW);
  #endif

  // Attach interrupts to the encoder pins
  attachInterrupt(digitalPinToInterrupt(encoderPinA), updateEncoder, CHANGE);
  attachInterrupt(digitalPinToInterrupt(encoderPinB), updateEncoder, CHANGE);

  // Initialize Timer1 for periodic interrupt
  Timer1.initialize(TIMER1_MICROSECONDS);   // Set timer to TIMER1_MICROSECONDS micro-seconds
  Timer1.attachInterrupt(sendData);         // Attach the function to the timer interrupt

  // Initialize display
  max7219.Begin();
  max7219.MAX7219_SetBrightness(REG_INTENSITY);

}

void loop() {
  // Read the button state
  bool buttonState = digitalReadFast(buttonPin);

  if (buttonState == LOW) {
    encoderPosition = 0;
  }

  if (there_is_something_to_send == HIGH) {
    // Print the time mark and angle to the serial port:
    Serial.print("Time: ");
    Serial.print(timeCounter * TIMER1_MILLISECONDS); // Time in milliseconds
    Serial.print(" ms, Angle: ");
    Serial.println(angle, 1); // Angle with one decimal point

    // Display the angle on the MAX7219:
    displayAngle(angle);

    // Turn off flag:
    there_is_something_to_send = LOW;
  }
}

void updateEncoder() {
  // Read the encoder pins:
  bool newA = digitalReadFast(encoderPinA);
  bool newB = digitalReadFast(encoderPinB);

  // Compute encoder direction and add or substract accondingly:
  if (newA != lastA || newB != lastB) {
    if (newA == lastB) {
      encoderPosition++;
    } else if (newB == lastA) {
      encoderPosition--;
    }
  }
  // Store these values for next time:
  lastA = newA;
  lastB = newB;

  // Replicate pins to output:
  digitalWriteFast(encoderPinA_out, newA);
  digitalWriteFast(encoderPinB_out, newB);
}

void sendData() {
  // Increment the time counter:
  timeCounter++;

  // Calculate the angle:
  angle = encoderPosition / encoder_divisor;

  // Update flag to transmit data over serial port:
  there_is_something_to_send = HIGH;

  // Send raw encoder position:
  #if (_LOG_LEVEL_ == 1)
  Serial.println(encoderPosition >> 2);
  #endif

  // Toggle debug pin:
  #if (_LOG_LEVEL_ == 2)
  digitalToggleFast(debugPin1);
  #endif
}

void displayAngle(float angle) {
  // Convert float to string with 'MAX7219_NUMBER_OF_DECIMALS' decimal places:
  char buffer[9];
  dtostrf(angle, 8, MAX7219_NUMBER_OF_DECIMALS, buffer);

  // Write on display:
  max7219.DisplayText(buffer, RIGHT);
}
