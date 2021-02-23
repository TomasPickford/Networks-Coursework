# I developed this in Python 3.7.4 so please run using a similar version.

import sys
import socket
import select

MAX_USERS = 16 # maximum number of clients that can connect at once

NAME_HEADER_LEN = 2 # 2 digits are used to describe the length of the name
TEXT_HEADER_LEN = 5 # 5 digits describe the length of the text message

HELP_TEXT = """

HELP
To use a command, start your message with a slash (/).
To broadcast your message to everyone, do not use one.

Commands:
Send a message to a specific user:
/tell [username] [message]

Change your username:
/name [new username]

Get a list of online users:
/users

Display this help dialouge:
/help

"""

def log(text):
    print(text)
    with open("server.log", "a") as server_log:
        server_log.write(text+"\n")
    # the file is automatically closed
    return

def broadcast(text):
    log(text)
    text_buff_size = str(len(text)).zfill(TEXT_HEADER_LEN)
    encoded_msg = bytes(text_buff_size + text,'utf-8')
    for client_socket in users:
        client_socket.send(encoded_msg)
    return

def direct_msg(user, text):
    text_buff_size = str(len(text)).zfill(TEXT_HEADER_LEN)
    encoded_msg = bytes(text_buff_size + text,'utf-8')
    user.send(encoded_msg)
    return

def read_sockets():
    for read_socket in r:
        # a new connection will notify the server socket
        if read_socket == server_socket:
            new_socket, new_address = server_socket.accept()

            log((f"New connection from IP {new_address[0]} "
                f"and port {new_address[1]}."))
            direct_msg(new_socket, "Welcome to the server!")
            # the client sends its name immediately after connecting
            msg_type = new_socket.recv(1)
            # get the number of chars the new name takes up
            name_buff_size = int(new_socket.recv(NAME_HEADER_LEN))
            new_name = new_socket.recv(name_buff_size).decode('utf8')
            # check if another user already has the same name
            if new_name in users.values():
                direct_msg(new_socket, ("That name has already been "
                    "taken. Reconnect with a different name."))
                log((f"The connection from IP {new_address[0]} "
                    f"and port {new_address[1]} was rejected because the "
                    f"name {new_name} was already taken."))
                new_socket.close()
            else:
                # this socket will be passed into select.select() next time
                all_sockets.append(new_socket)
                # store the username, keyed by the socket
                users[new_socket] = new_name
                broadcast(f"{users[new_socket]} connected to the server")
        # handle messages from existing connections
        else:
            msg_type = read_socket.recv(1)
            # a message of length 0 is sent to close the connection
            if not msg_type:
                broadcast((f"{users[read_socket]} disconnected "
                    "from the server."))
                all_sockets.remove(read_socket)
                del users[read_socket]
                read_socket.close()
                continue
            msg_type = msg_type.decode('utf-8')
            # broadcast to all clients
            if msg_type == 'b':
                text_buff_size = \
                int(read_socket.recv(TEXT_HEADER_LEN).decode('utf-8'))
                new_text = read_socket.recv(text_buff_size).decode('utf-8')
                broadcast(f"{users[read_socket]}: {new_text}")
            # direct message a specific user
            elif msg_type == 'd':
                # get the number of chars the recipient name takes up
                name_buff_size = int(read_socket.recv(NAME_HEADER_LEN))
                # get the number of chars the message takes up
                text_buff_size = \
                int(read_socket.recv(TEXT_HEADER_LEN).decode('utf-8'))
                # read the socket for the name and then message
                recipient_name = \
                read_socket.recv(name_buff_size).decode('utf8')
                new_text = read_socket.recv(text_buff_size).decode('utf-8')
                # if a user tries to direct message themselves
                if users[read_socket] == recipient_name:
                    direct_msg(read_socket, ("You cannot send a private "
                        "message to yourself."))
                    log((f"{users[read_socket]} tried to direct message "
                        "themselves."))
                    continue
                if recipient_name in users.values():
                    # reverse-search the dictionary for the key from the value
                    for potential_socket in users:
                        if users[potential_socket] == recipient_name:
                            recipient_socket = potential_socket
                            break
                    out_text = (f"{users[read_socket]} > "
                    f"{recipient_name}: {new_text}")
                    # send the message to the recipient
                    direct_msg(recipient_socket, out_text)
                    # send the message to the sender
                    direct_msg(read_socket, out_text)
                    # log the message
                    log(out_text)
                else:
                    direct_msg(read_socket, (f"There is no user with the "
                        f"name {recipient_name}"))
                    log((f"{users[read_socket]} tried to direct message "
                        f"{recipient_name} but that user is not online."))
            # change their username
            elif msg_type == "n":
                # get the number of chars the new name takes up
                name_buff_size = int(read_socket.recv(NAME_HEADER_LEN))
                new_name = read_socket.recv(name_buff_size).decode('utf8')
                # check if another user already has the same name
                if new_name in users.values():
                    direct_msg(read_socket, ("That name has already been "
                        "taken."))
                    log((f"{users[read_socket]} tried to change their name "
                        f"to {new_name} but it was already taken."))
                else:
                    broadcast((f"{users[read_socket]} renamed "
                        f"themselves to {new_name}"))
                    # update the stored name
                    users[read_socket] = new_name
            # user list
            elif msg_type == 'u':
                users_str = ""
                for username in users.values():
                    users_str += username + "\n"
                direct_msg(read_socket, f"Connected Users:\n{users_str}")
                log(f"{users[read_socket]} used the list users command.")
            # help
            elif msg_type == 'h':
                direct_msg(read_socket, HELP_TEXT)
                log(f"{users[read_socket]} used the help command.")
            # no more possibilties unless the client code is modified
            else:
                log(("Error: an incoming message did not conform "
                "to the protocol."))

log("The server is being started.")

# get the port from the execution command
num_args = len(sys.argv) - 1
# if there is more than one argument, stop
if num_args != 1 and num_args != 0:
    error_msg = f"Error: {num_args} arguments provided instead of 1."
    log(error_msg)
    log("The server has stopped running.")
    sys.exit()
if num_args == 0:
    # default port if one isn't specified
    port = 4615
else:
    port = sys.argv[1]

ip = socket.gethostname()

# create TCP socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# allow the socket to reuse the address
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

try:
    port = int(port)
    server_socket.bind((ip, port))
    log(f"The server is running on IP {ip} and port {port}.")
except Exception as error:
    error_msg = f"Error binding socket: {error}"
    log(error_msg)
    log("The server has stopped running.")
    sys.exit()

# listen for incoming connections
server_socket.listen(MAX_USERS)

# a list of all sockets, that will be appended to with client sockets
all_sockets = [server_socket]
# a dictionary for storing usernames, keyed by their socket
users = {}

while True:
    try:
        r,w,e = select.select(all_sockets,[],all_sockets)
        # read the sockets that have received a message
        read_sockets()
        # remove the sockets that have encountered an error
        for error_socket in e:
            all_sockets.remove(error_socket)
            error_username = ""
            try:
                # the socket might not yet have a username set
                error_username = f"{users[error_socket]} "
                del users[error_socket]
            finally:
                error_socket.close()
                log((f"A socket {error_socket}has enountered "
                    "an error and has been closed."))
    # in case of a crash at any point (that isn't caught by an embedded
    # try clause), close remaining connections and log it
    except Exception as error:
        log(f"An unexpected error occured: {error}")
        for remaining_socket in all_sockets:
            remaining_socket.close()
        log("The server has stopped running.")
        sys.exit()
