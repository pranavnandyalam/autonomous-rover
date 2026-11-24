int topspeed = 255;

// Manual input definitions
#define FORWARD 'w'
#define LEFT 'a'
#define BACK 's'
#define RIGHT 'd'
#define STOP 'x'

void Set_Speed(unsigned char Left, unsigned char Right)
{
  // Ensure speeds don't exceed topspeed
  if (Left > topspeed) { Left = topspeed; }
  if (Right > topspeed) { Right = topspeed; }
  
  analogWrite(5, Left);    // Send a speed value (Left = 0-255) to Pin #5 for setting the rotation speed of the two left-side wheels.
  analogWrite(6, Right);   // Send a speed value (Right = 0-255) to Pin #6 for setting the rotation speed of the two right-side wheels.
}

void forward() {
  // Go forward
  digitalWrite(7, HIGH);       // Set Pin #7 to HIGH and set Pin #8 to LOW, making two left-side wheels rotate forward.
  digitalWrite(8, LOW);
  digitalWrite(9, LOW);        // Set Pin #11 to HIGH and set Pin #9 to LOW, making two right-side wheels rotate forward.
  digitalWrite(11, HIGH);
}

void back() {
   // Go backward
  digitalWrite(7, LOW);        // Set Pin #7 to LOW and set Pin #8 to HIGH, making two left-side wheels rotate backward.
  digitalWrite(8, HIGH);
  digitalWrite(9, HIGH);       // Set Pin #11 to LOW and set Pin #9 to HIGH, making two right-side wheels rotate backward.
  digitalWrite(11, LOW);
}

void left() {
  // Turn left
  digitalWrite(7, LOW);        // Set Pin #7 to LOW and set Pin #8 to HIGH, making two left-side wheels rotate backward.
  digitalWrite(8, HIGH);
  digitalWrite(9, LOW);        // Set Pin #11 to HIGH and set Pin #9 to LOW, making two right-side wheels rotate forward.
  digitalWrite(11, HIGH);
}

void right() {
  // Turn right
  digitalWrite(7, HIGH);       // Set Pin #7 to HIGH and set Pin #8 to LOW, making two left-side wheels rotate forward.
  digitalWrite(8, LOW);
  digitalWrite(9, HIGH);       // Set Pin #11 to LOW and set Pin #9 to HIGH, making two right-side wheels rotate backward.
  digitalWrite(11, LOW);
}

void stopcar() {
 // Stop
  analogWrite(5, 0);          // Set the rotation speed of left-side wheels to "0".
  analogWrite(6, 0);          // Set the rotation speed of right-side wheels to "0".
}

void setup() {
  // Put your setup code here, to run once:
  pinMode(5, OUTPUT);     // Pins #5, 7, 8 are used for controlling the two left-side wheels.
  pinMode(7, OUTPUT);
  pinMode(8, OUTPUT);

  pinMode(6, OUTPUT);    // Pins #6, 9, 11 are used for controlling the two right-side wheels
  pinMode(9, OUTPUT);
  pinMode(11, OUTPUT);

  Serial.begin(115200);
}

void process_input(char input) {
  Serial.println(input);
  switch(input) {
    case 'w':
      forward();
      Set_Speed(150, 150);
      break;

    case 'a':
      left();
      Set_Speed(150, 150);
      break;

    case 's':
      back();
      Set_Speed(150, 150);
      break;

    case 'd':
      right();
      Set_Speed(150, 150);
      break;

    case 'x':
      stopcar();
      break;
      
    default:
      // Handle invalid input
      Serial.println("Invalid command");
      break;
  }
}

void loop() {
  // Put your main code here, to run repeatedly:
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    Serial.println(command);
    if (command.length() > 0) {
      char cmd_char = command[10]; // Grab the first character, e.g. "w" in "w\n".
      Serial.println(cmd_char);
      // Process input, set motion according to WASD/X
      process_input(cmd_char);
    }
  }
}
