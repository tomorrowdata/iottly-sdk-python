from iottly_sdk import iottly
import logging


def on_agent_status_changed(status):
    logging.info('on_agent_status_changed: {}'.format(status))

def on_connection_status_changed(status):
    logging.info('on_connection_status_changed: {}'.format(status))

iottlysdk = iottly.IottlySDK(
    name  = 'myfirstiottlyapp',
    socket_path='/var/run/iottly.com-agent/sdk/iottly_sdk_socket',
    max_buffered_msgs = 100,
    on_agent_status_changed = on_agent_status_changed,
    on_connection_status_changed = on_connection_status_changed)

iottlysdk.start()

while True:
    s = input('q to exit: ')
    if s == 'q':
        break

iottlysdk.stop()
