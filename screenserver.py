import socket
from PIL import ImageGrab, Image
import io

# Create a socket object
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Set the server address and port
server_address = ('', 12345)

def start_server():
    try:
        # Bind the socket to the server address
        server_socket.bind(server_address)

        # Listen for incoming connections
        server_socket.listen(1)
        print('Server is listening on', server_address)

        while True:
            try:
                # Accept a client connection
                print('Waiting for a client connection...')
                client_socket, client_address = server_socket.accept()
                print('Client connected:', client_address)

                def send_screen_image():
                    try:
                        # Capture the screen
                        screen_image = ImageGrab.grab()

                        # Reduce the image quality to 30
                        screen_image = screen_image.convert('RGB')
                        screen_image = screen_image.resize((screen_image.width // 2, screen_image.height // 2), Image.ANTIALIAS)

                        # Create an in-memory stream for image data
                        image_data = io.BytesIO()
                        screen_image.save(image_data, format='JPEG', quality=30)
                        image_data = image_data.getvalue()

                        # Send the size of the image first
                        size_bytes = len(image_data).to_bytes(8, byteorder='big')
                        client_socket.sendall(size_bytes)

                        # Send the image data in smaller chunks
                        chunk_size = 1024
                        remaining_bytes = len(image_data)
                        while remaining_bytes > 0:
                            send_size = min(chunk_size, remaining_bytes)
                            client_socket.sendall(image_data[:send_size])
                            image_data = image_data[send_size:]
                            remaining_bytes -= send_size

                    except (ConnectionResetError, ConnectionAbortedError, socket.error) as e:
                        print('Connection closed by client:', e)
                        start_server()

                    # Schedule the next screen image capture and sending
                    send_screen_image()

                # Start sending the screen images
                print('Sending screen images...')
                send_screen_image()

            except KeyboardInterrupt:
                print('Server interrupted.')
                break

            except socket.error as e:
                print('Socket error:', e)
                break

    finally:
        # Close the client socket
        client_socket.close()

        # Restart the server
        print('Restarting the server...')
        start_server()

# Start the server
start_server()
