#!/bin/bash

cd Data/
rm dump1.json
rm dump2.json
touch dump1.json
touch dump2.json
cd ..
python3 api1.py &
python3 api2.py &
docker compose up