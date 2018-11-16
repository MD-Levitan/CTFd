#!/bin/sh
sudo apt-get update
sudo apt-get install build-essential python-dev python-pip libffi-dev -y
pip3 install -r requirements.txt
