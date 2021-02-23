# I developed this with Python 3.7.4 so please run using a similar version.

import sys
import time
import socket
import errno
import tkinter as tk
from tkinter import scrolledtext

WIN_WIDTH = 64
WIN_HEIGHT = 24
UPDATE_FREQ = 200 # interval between attempts to receive messages in ms
ERROR_DISPLAY_TIME = 5 # time in s before window closes after error

MIN_NAME_LEN = 3 # least characters allowed in a username
MAX_NAME_LEN = 16 # most characters allowed in a username
MAX_TEXT_LEN = 90000 # most characters allowed in a text message

NAME_HEADER_LEN = 2 # 2 digits are used to describe the length of a name
TEXT_HEADER_LEN = 5 # 5 digits describe the length of a text message

def display_err(text):
    print(text)
    display_msg(text)
    window.update_idletasks()
    window.update()
    time.sleep(ERROR_DISPLAY_TIME)
    sys.exit()

# outputs the message the bottom of the scrolled text widget
def display_msg(text):
    text_area.configure(state ='normal')
    text_area.insert(tk.END, "\n" + text)
    text_area.configure(state ='disabled')
    text_area.see(tk.END)

# used for initial naming from the command line, as well as renaming
def validate_name(new_name):
    if (len(new_name) <= MAX_NAME_LEN
        and len(new_name) >= MIN_NAME_LEN
        and ' ' not in new_name):
        return True
    else:
        return False

def read_input(event=None):
    text = entry_field.get()
    entry_field.delete(0, tk.END)
    if len(text) == 0:
        # ignore empty input
        return
    # if it is a command
    if text[0] == '/':
        if text[1:6] == 'tell ':
            # two args: user, message
            username_end = 6
            for character in text[6:]:
                if character == ' ':
                    break
                username_end += 1
            if username_end < len(text):
                # then a delimiting space was found
                username = text[6:username_end]
                msg = text[username_end+1:]
                name_buff_size = str(len(username)).zfill(NAME_HEADER_LEN)
                text_buff_size = str(len(msg)).zfill(TEXT_HEADER_LEN)
                client_socket.send(bytes('d' + name_buff_size +
                text_buff_size + username + msg,'utf-8'))
            else:
                display_msg("Too few arguments were provided.")
        elif text[1:6] == 'name ':
            # one arg: new nickname
            new_name = text[6:]
            #check the name is valid
            if validate_name(new_name) == True:
                name_buff_size = str(len(new_name)).zfill(NAME_HEADER_LEN)
                client_socket.send(bytes('n' + name_buff_size +
                new_name,'utf-8'))
            else:
                display_msg(("Invalid name. Names must be between "
                    "3 and 16 characters long and contain no spaces."))
        elif text == '/users':
            # no args
            client_socket.send(bytes('u','utf-8'))
        elif text == '/help':
            # no args
            client_socket.send(bytes('h','utf-8'))
        else:
            display_msg(("Unrecognised command. See /help for  a list "
            "of valid commands."))
    # if it is a regular message
    else:
        if len(text) <= MAX_TEXT_LEN:
            text_buff_size = str(len(text)).zfill(TEXT_HEADER_LEN)
            client_socket.send(bytes('b' + text_buff_size + text,'utf-8'))
        else:
            display_msg((f"Your message was too long to send. The limit is "
                "{MAX_TEXT_LEN} characters"))

def recv_msg():
    try:
        # keep receiving messages until there are no more
        while True:
            text_buff_size = client_socket.recv(TEXT_HEADER_LEN)
            # a message of length 0 is sent to close the connection
            if not text_buff_size:
                display_err("The server has closed the connection.")
            text_buff_size = int(text_buff_size.decode('utf-8'))
            text = client_socket.recv(text_buff_size).decode('utf-8')
            display_msg(text)
    # the except clauses below are closely adapted from code on this website:
    # pythonprogramming.net/client-chatroom-sockets-tutorial-python-3/
    except IOError as error:
        # check if it's an error we can't handle
        if error.errno != errno.EAGAIN and error.errno != errno.EWOULDBLOCK:
            display_err(f'Error reading incoming message: {error}')
        # otherwise, the error just means that there was nothing more to read
    except Exception as error:
        # if it's not the error we are expecting, fail
        display_err(f'Error reading incoming message: {error}')

    # set this function to run again after an interval
    window.after(UPDATE_FREQ, recv_msg)
    return

# initialise the GUI

window = tk.Tk()
window.title("Chat Client")

text_area = scrolledtext.ScrolledText(width = WIN_WIDTH, height = WIN_HEIGHT)
text_area.insert(tk.END, 
"""
Welcome to the chat client!

Type /help for a list of commands
""")
# the text area should not be editable by a user
text_area.configure(state ='disabled')

# there are two ways to send a message: button and return key
entry_field = tk.Entry()
entry_field.bind("<Return>", read_input)
send_button = tk.Button(text="Enter", command=read_input)

text_area.pack()
entry_field.pack()
send_button.pack()

#tk.update_idletasks()
window.update_idletasks()
window.update()
# the GUI is now initialised

# get the username, hostname and port from the execution command
num_args = len(sys.argv) - 1
# if there are not 0 or 3 arguments, stop
if num_args != 3 and num_args != 0:
    print(f"Error: {num_args} argument(s) provided instead of 3.")
    sys.exit()
# use default settings if none specified
if num_args == 0:
    # generate a number 4-digit username
    username = str(time.time_ns())[-6:-2]
    ip = socket.gethostname()
    port = 4615
else:
    # num_args must equal 3; all have been provided
    username = sys.argv[1]
    ip = sys.argv[2]
    port = sys.argv[3]
    try:
        port = int(port)
    except:
        display_err("Error: the specified port is not an integer.")
    
    if validate_name(username) == False:
        display_err(("Invalid name. Names must be between "
            "3 and 16 characters long and contain no spaces"))

# create TCP socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# connect to the server
print(f"Connecting to the server with IP {ip} and port {port}")
display_msg(f"Connecting to the server with IP {ip} and port {port}")
try:
    client_socket.connect((ip, port))
except Exception as error:
    display_err(f"Error connecting to the server: {error}")

# the socket should be non-blocking
client_socket.setblocking(False)

# the username is immediately needed for the new connection broadcast
name_buff_size = str(len(username)).zfill(NAME_HEADER_LEN)
client_socket.send(bytes('n' + name_buff_size + username,'utf-8'))

# recv_msg() runs initially and then window.mainloop() keeps calling it
window.after(0,recv_msg)
# window.mainloop() also calls read_input() when necessary
window.mainloop()