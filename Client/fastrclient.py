import socket as s
import select
import time
try:
    import msvcrt
except:
    pass    
try:
    import readline
except:
    pass

class Fastrclient(object):
    """ Creates a connection object and manages all communication
    with the server."""
    
    def __init__(self, clientsocket, addr):
        self.clientsock = clientsocket
        self.cl = [self.clientsock]
        self.addr = addr
        self.count = 0

        self.username = None
        self.name_accepted_by_server = None

        self.deregistered = False
 
        self.subscriptions = {}
    
    def _send(self,message):
        """A convenience function to reduce verbosity"""
        return self.clientsock.sendto(message,self.addr)
        

    def send_message(self,message):
        """Send a fastr message, server will send it to all people
        who are subscribed to you."""
        length = len(message)
        if len(message) > 140:
            print "Error, your message is %i/140 characters" % length
            return
        self._send("CSMSG%u\a%s\a%s" % 
                    (self.count,self.username,message.replace("\a"," ")) )

        self.count = (self.count + 1) % 99999999


    def register(self,username):
        """Register with the fastr server. """
        #reset bad username flag since this is a new username
        self.username = username
        self.name_accepted_by_server = None

        # check for username validity
        if username.isalnum() and len(username) <= 32:
            tempcount = 0
            while self.name_accepted_by_server is None and tempcount <= 100:
                self._send("CREGR%s" % username) # send message to server
                time.sleep(0.01)
                self.receive()
                tempcount += 1
            return self.name_accepted_by_server
        else:
            return False
                    
                    
    def finish_register(self,response): 
        messages = response.split('\a')
        if len(messages) == 2:
            self.name_accepted_by_server = False
            return False
        else:
            self.name_accepted_by_server = True
            return True      

    def slist(self):
        """Sends a message to list the registered users."""
        self._send("CLIST")

    def subscribe_to(self, subscribee):
        """Subscribes to another user so you can receive their messages"""
        self._send("CASUB%s" % subscribee)
        self.subscriptions[subscribee] = None


    def unsubscribe_from(self, unsubscribee):
        """Unsubscribes from another user previously subscribed to"""
        self._send("CDSUB%s" % unsubscribee)
        if unsubscribee in self.subscriptions:
            del self.subscriptions[unsubscribee]


    def deregister(self):
        """Begins deregistration on the server"""
        retries = 0
        while self.deregistered == False and retries <= 5:
            self._send("CDRGR")
            retries += 1
            time.sleep(0.1)
            self.receive()
        if retries >= 5:
            return False
        else:
            return True

        
    def new_message(self,message):
        """Process and print a new message, and check if a message was missed."""
        sp = message.split('\a')
        if len(sp) != 3:
            return

        #assign a few names for clarity
        sequence_no = int(sp[0])
        username = sp[1]
        message = sp[2]
        
        #print the message out
        print username,": ",message
        
        #check if a sequence number was skipped
        #ignore if this is the first message received from this user
        if (username in self.subscriptions) and \
           (self.subscriptions[username] is not None) and \
           ((self.subscriptions[username] + 1) != sequence_no):
            print "A message from",username,"was missed."
        
        #update the sequence number

        self.subscriptions[username] = sequence_no


    def end_deregister(self, message):
        """Completes deregistration on the server."""
        sp = message.split('\a')
        if len(sp) == 2:
            print "Error deregistering."
        self.deregistered = True
        return True
        
    def receive(self):
        """Parses incoming messages and runs the corresponding function"""
        try:
            readable,_,_ = select.select(self.cl,self.cl,self.cl,60)
        except:
            return
        if readable == []:
            return
        Message = self.clientsock.recv(1024)
        Type = Message[:5]
        Rest = Message[5:]
        if Type == "SLIST":
            self.slister(Rest)
        elif Type == "SREGR":
            self.finish_register(Rest)
        elif Type == "SSMSG":
            self.new_message(Rest)
        elif Type == "SDRGR":
            self.end_deregister(Rest)
        else:
            print "Error:",Rest
        return
    
    def slister(self,message):
        """Prints out the user list in a nice format"""
        if message == "":
            return
        Arr = message.split('\a')
        TimeString = time.ctime(int(Arr[1]))
        Username = Arr[0]
        print Username, "last activity at:", TimeString


#Below is the main body of the code
if __name__ == "__main__":
    #Banner
    print "\n","fastr version 1.3".center(80),"\n"

    #Getting IP and Port #
    IP = raw_input("IP address of the server (default 127.0.0.1):")
    Port = raw_input("Port of the server (default 4168):")

    #handle defaults
    if IP == "":
        IP = "127.0.0.1"
    if Port == "":
        Port = 4168

    #create sockets
    clientsocket = s.socket(s.AF_INET, s.SOCK_DGRAM)
    clientsocket.setblocking(0)
    cl = [clientsocket]
    
    client = Fastrclient(clientsocket,(IP,Port)) #create the client

    #Try to register
    uname = raw_input("Desired username: ")
    while client.register(uname) == False:
        print "Username invalid or already in use"
        uname = raw_input("Desired username: ")

    print 'Username registered. Type "help" for help'
    
    while True:
        if msvcrt.kbhit() != 0: #check if user is trying to type something
            Inn = raw_input("")
            command,_,rest = Inn.partition(' ')
            if command == "send":
                client.send_message(rest)
            elif command == "list":
                client.slist()
            elif command == "exit":
                if client.deregister() == False:
                    print "Could not deregister on server."
                break
            elif command == "subto":
                client.subscribe_to(rest)
            elif command == "desubfrom":
                client.unsubscribe_from(rest)
            elif command == "help":
                print "Commands: send, list, exit, subto ,desubfrom"
            elif command == "debug":
                input("Debug input: ")
            else:
                print "Unrecognized command."
        else:
            client.receive()
        
        
