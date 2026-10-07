#!/bin/bash
# Ping the keepalive endpoint every 5 minutes to prevent cold starts
while true; do
    curl -s -o /dev/null https://revenueforge-api.onrender.com/keepalive
    sleep 300
done
