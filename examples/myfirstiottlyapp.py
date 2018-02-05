import os, time

# import iottly_sdk
from iottly_sdk import iottly

# define the callback to receive notification
# on the iottly agent status:
#   started
#   stopping
#   stopped
def on_agent_status_changed(status):
    print('on_agent_status_changed: {}'.format(status))

# define the callback to receive notification
# on the iottly agent mqtt connection status:
#   connected
#   disconnected
def on_connection_status_changed(status):
    print('on_connection_status_changed: {}'.format(status))

# create an instance of IottlySDK with:
#   a name to identify your application (will appear in the dashboard logs)
#   the optional size of messages to be retained if agent is closed (defaults to 1500)
#   the previously defined callbacks (optional) to receive agent status notifications
iottlysdk = iottly.IottlySDK(
    name  = 'myfirstiottlyapp',
    max_buffered_msgs = 100,
    on_agent_status_changed = on_agent_status_changed,
    on_connection_status_changed = on_connection_status_changed)

# define one callback for each of the incoming commands that you want to subscribe
# commands are defined in the iottly dashboard / management commands panel
def on_echo_received(cmdpars):
    print('on_echo_received: {}'.format(cmdpars))

def on_examplecommand_received(cmdpars):
    print('on_examplecommand_received: {}'.format(cmdpars))

# subscribe commands of interest with the callbacks
iottlysdk.subscribe(cmd_type='echo', callback=on_echo_received)
iottlysdk.subscribe(cmd_type='examplecommand', callback=on_examplecommand_received)

# start the sdk loops (this will start 4 threads)
iottlysdk.start()

# here follows the main blocking loop of your application
while True:
    try:
        s = input('\n^C to exit, "m" to send 1 message, "l" to send 20 messages:\n')
        if s == 'm':
            t = dict(temperature=22)
            iottlysdk.send(msg=t)
        if s == 'l':
            for t in range(10,30):
                t = dict(temperature=t)
                iottlysdk.send(msg=t)
                time.sleep(1)

    except KeyboardInterrupt:
        break
