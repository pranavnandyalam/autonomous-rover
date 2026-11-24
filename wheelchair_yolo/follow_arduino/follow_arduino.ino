int topspeed = 255;

#define FORWARD 'w'
#define LEFT 'a'
#define RIGHT 'd'
#define BACK 's'
#define STOP 'x'

#define WATCHDOG_MS 500
#define RAMP_STEP 10
#define RAMP_MS 10

unsigned long last_command_ms = 0;
unsigned long last_ramp_ms = 0;
char current_direction = STOP;
int target_left = 0;
int target_right = 0;
int current_left = 0;
int current_right = 0;

void Set_Speed(int Left, int Right)
{
  if (((int)Left)>topspeed) {Left = topspeed;}
  if (((int)Right)>topspeed) {Right = topspeed;}

  analogWrite(5,Left);
  analogWrite(6,Right);
}

void forward() {
  digitalWrite(7, HIGH);
  digitalWrite(8, LOW);
  digitalWrite(9, LOW);
  digitalWrite(11, HIGH);
}

void back() {
  digitalWrite(7, LOW);
  digitalWrite(8, HIGH);
  digitalWrite(9, HIGH);
  digitalWrite(11, LOW);
}

void stopcar() {
  target_left = 0;
  target_right = 0;
  current_left = 0;
  current_right = 0;
  analogWrite (5, 0);
  analogWrite (6, 0);
}

void setup() {
  pinMode (5, OUTPUT);
  pinMode (7, OUTPUT);
  pinMode (8, OUTPUT);

  pinMode (6, OUTPUT);
  pinMode (9, OUTPUT);
  pinMode (11, OUTPUT);

  Serial.begin(115200);

  stopcar();
}

void process_direction(char direction) {
  if (direction == BACK) {
    back();
  }
  else {
    forward();
  }
}

void apply_command(char direction, int left, int right) {
  char motor_direction = (direction == BACK) ? BACK : FORWARD;
  if (motor_direction != current_direction) {
    stopcar();
    process_direction(motor_direction);
    current_direction = motor_direction;
  }
  target_left = constrain(left, 0, topspeed);
  target_right = constrain(right, 0, topspeed);
}

int ramp(int current, int target) {
  if (target <= current) {
    return target;
  }
  return min(target, current + RAMP_STEP);
}

void loop() {
  while (Serial.available()) {
    String pid_command = Serial.readStringUntil('\n');
    pid_command.trim();

    if (pid_command == "STOP") {
      stopcar();
      last_command_ms = millis();
      continue;
    }

    int firstCommaIndex = pid_command.indexOf(',');
    int secondCommaIndex = pid_command.indexOf(',', firstCommaIndex + 1);

    if (firstCommaIndex > 0 && secondCommaIndex > firstCommaIndex) {
      int leftSpeed = pid_command.substring(0, firstCommaIndex).toInt();
      int rightSpeed = pid_command.substring(firstCommaIndex + 1, secondCommaIndex).toInt();
      char direction = pid_command.substring(secondCommaIndex + 1)[0];

      apply_command(direction, leftSpeed, rightSpeed);
      last_command_ms = millis();
    }
  }

  if (millis() - last_command_ms > WATCHDOG_MS) {
    stopcar();
  }

  if (millis() - last_ramp_ms >= RAMP_MS) {
    last_ramp_ms = millis();
    current_left = ramp(current_left, target_left);
    current_right = ramp(current_right, target_right);
    Set_Speed(current_left, current_right);
  }
}
