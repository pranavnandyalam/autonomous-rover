// Part B: The goal of this code is to receive 2 numbers wirelessly, sum the result, and send the result back to the user's laptop via Wi-Fi.
#include <WiFi.h>

#define port 5005

const char *ssid_STA = "ENGR100-400"; //Enter the router name
const char *password_STA = "notapwd777"; //Enter the router password

IPAddress local_IP(192,168,50, 207);//Set the IP address of ESP32 itself
IPAddress gateway(192,168,50,1);   //Set the gateway of ESP32 itself
IPAddress subnet(255,255,255,0);  //Set the subnet mask for ESP32 itself

WiFiServer server(port);
WiFiClient client;

// Defines: WASD manual commanding
#define FORWARD 'w'
#define LEFT 'a'
#define BACK 's'
#define RIGHT 'd'
#define STOP 'x'

void WiFiSetup() {
  WiFi.disconnect();
  WiFi.mode(WIFI_STA);

  // Set static IP, gateway, and subnet BEFORE WiFi.begin()
  if (!WiFi.config(local_IP, gateway, subnet)) {
    Serial.println("STA Failed to configure");
  }

  WiFi.begin(ssid_STA, password_STA);

  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected.");
  Serial.print("ESP32 IP address: ");
  Serial.println(WiFi.localIP());

  server.begin(port);
  WiFi.setAutoReconnect(true);
}

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  WiFiSetup();  // Enable WiFi using functions defined above
}


void loop() {
  // put your main code here, to run repeatedly:
  char direction = 'x'; // Start in "stop" mode.
  WiFiClient client = server.available();            // listen for incoming clients
  if (client) {                                     // if you get a client,
    while (client.connected()) {                    // Loop while the client is connected
      if (client.available() > 0) {                 // Check if the ESP32 is receiving data from the laptop  
        String data = client.readStringUntil('\n'); // If the ESP32 has data to read, grab it and print it over Serial to the Arduino Nano
        if (data.length() > 0) {
          Serial.println("Received: " + data);
          
          // Parse the numbers from the received data
          int commaIndex = data.indexOf(',');
          if (commaIndex != -1) {
            String num1_str = data.substring(0, commaIndex);
            String num2_str = data.substring(commaIndex + 1);
            
            // Convert strings to integers
            int num1 = num1_str.toInt();
            int num2 = num2_str.toInt();
            
            // Calculate sum
            int sum = num1 + num2;
            
            // Send result back to client
            client.println(sum);
            Serial.println("Sent result: " + String(sum));
          }
        }
      }
    }
    client.stop();                                  // stop the client connecting.
  }
}
