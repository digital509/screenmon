import socket
import pygame
from pygame.locals import *
import struct
import threading
import io
import sys
import os

# Create a socket object
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Set the server address and port
server_address = (sys.argv[1], 12345)

# Connect to the server
client_socket.connect(server_address)
print('Connected to', server_address)

# Pygame initialization
pygame.init()
window_size = (960, 540)  # Window size for display
sent_img_size = (1920, 1080)
screen = pygame.display.set_mode(window_size)
clock = pygame.time.Clock()

# Flag to indicate if the client is actively receiving images
receiving_images = True

# Create a lock to synchronize access to the image data
data_lock = threading.Lock()

# Variables to store the current image, zoom level, and position
current_image = None
current_zoom = -0.5  # Default zoom level (-50%)
current_position = [0 - (sent_img_size[0] / 2), 0 - (sent_img_size[1] / 2)]
is_dragging = False
prev_mouse_pos = None

# Create the "screens" subfolder if it doesn't exist
if not os.path.exists("screens"):
    os.makedirs("screens")


def receive_image():
    global current_image

    try:
        # Receive the size of the image
        size_bytes = client_socket.recv(8)
        image_size = struct.unpack('!Q', size_bytes)[0]

        # Create a buffer to hold the received image data
        image_data = b''

        # Receive the image data in chunks
        while len(image_data) < image_size:
            remaining_bytes = image_size - len(image_data)
            chunk = client_socket.recv(1024 if remaining_bytes > 1024 else remaining_bytes)
            if not chunk:
                break
            image_data += chunk

        # Check if the complete image was received
        if len(image_data) == image_size:
            print('Received image:', len(image_data), 'bytes')

            # Create an in-memory stream to read the image data
            img_stream = io.BytesIO(image_data)

            # Load the image using Pygame
            img = pygame.image.load(img_stream)

            # Acquire the lock to update the current image
            with data_lock:
                current_image = img

                # Save the image
                save_image(img, 'screens')

    except (ConnectionResetError, ConnectionAbortedError, socket.error) as e:
        print('Connection error:', e)
        # Set the receiving flag to False on connection error to stop the image receiving loop
        global receiving_images
        receiving_images = False

    # Continue receiving images if the receiving flag is True
    if receiving_images:
        receive_image()


def save_image(image, folder):
    # Create the "screens" subfolder if it doesn't exist
    if not os.path.exists(folder):
        os.makedirs(folder)

    # Generate a unique filename for the image
    filename = f'{folder}/image_{pygame.time.get_ticks()}.png'

    # Save the image
    pygame.image.save(image, filename)


def update_canvas_with_image(image):
    # Scale the image based on the current zoom level
    size_x = int(sent_img_size[0] * abs(current_zoom))
    size_y = int(sent_img_size[1] * abs(current_zoom))
    scaled_image = pygame.transform.scale(image, (size_x, size_y))

    # Calculate the new position based on the current zoom level
    pos_x = int(window_size[0] // 2 - current_position[0] * current_zoom)
    pos_y = int(window_size[1] // 2 - current_position[1] * current_zoom)

    # Clear the screen
    screen.fill((0, 0, 0))

    # Update the screen with the scaled and positioned image
    screen.blit(scaled_image, (pos_x, pos_y))

    # Update the display
    pygame.display.flip()


def display_images():
    global is_dragging  # Declare is_dragging as a global variable

    while True:
        # Clear the screen
        screen.fill((0, 0, 0))

        # Acquire the lock to access the current image
        with data_lock:
            if current_image is not None:
                # Update the canvas with the current image
                update_canvas_with_image(current_image)

        # Limit the frame rate
        clock.tick(60)

        # Check for events
        for event in pygame.event.get():
            if event.type == QUIT:
                return
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    # Start dragging if left mouse button is pressed
                    is_dragging = True
                    prev_mouse_pos = event.pos
            elif event.type == MOUSEBUTTONUP:
                if event.button == 1:
                    # Stop dragging if left mouse button is released
                    is_dragging = False
            elif event.type == MOUSEMOTION:
                if is_dragging:
                    # Calculate the dragging distance
                    dx = event.pos[0] - prev_mouse_pos[0]
                    dy = event.pos[1] - prev_mouse_pos[1]

                    # Update the current position based on the dragging distance
                    current_position[0] += dx / current_zoom
                    current_position[1] += dy / current_zoom

                    # Update the previous mouse position
                    prev_mouse_pos = event.pos
            elif event.type == MOUSEWHEEL:
                # Check if the mouse wheel is scrolled up or down
                if event.y > 0:
                    # Scroll up (zoom in)
                    current_zoom += 0.1
                else:
                    # Scroll down (zoom out)
                    current_zoom -= 0.1


# Start the image receiving thread
receive_thread = threading.Thread(target=receive_image)
receive_thread.start()

# Start the image display
display_images()

# Wait for the receiving thread to finish
receive_thread.join()

# Close the socket
client_socket.close()
