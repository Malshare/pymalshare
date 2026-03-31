#!/bin/bash
# Limit Tor bandwidth to avoid saturating the server's link
echo "BandwidthRate 1 MB" >> /etc/tor/torrc
echo "BandwidthBurst 2 MB" >> /etc/tor/torrc

tor &
sleep 5
exec python3 -u url_task_handler.py
