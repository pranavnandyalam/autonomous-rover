import socket
import time

TCP_IP = "192.168.50.207" # Make sure this matches your ESP32's IP
TCP_PORT = 5005
TIMEOUT_S = 5

def wifi_setup():
    print(f"Connecting to ESP32 at {TCP_IP}:{TCP_PORT}")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(TIMEOUT_S)
    s.connect((TCP_IP, TCP_PORT))
    print("Connected to ESP32.")
    return s

def main():
    try:
        sock = wifi_setup()
        print("Testing communication...")
        
        # Send test data
        test_data = "2,5\n"
        print(f"Sending: {test_data}")
        sock.sendall(test_data.encode('utf-8'))
        
        # Receive response
        result = sock.recv(1024).decode().strip()
        print(f"Received result: {result}")
        
        sock.close()
        print("Test completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
