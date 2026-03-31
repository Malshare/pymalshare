#!/bin/bash
tor &
sleep 3
exec python3 -u url_task_handler.py
