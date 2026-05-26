#!/bin/bash

h2 init
sleep 0.2
genomixd &
sleep 0.5

# qualisys-pocolibs -f -i mocap &
optitrack-pocolibs -f -i mocap &
pom-pocolibs -f -i pom_mocap &
pom-pocolibs -f -i pom_lidar &
uavatt-pocolibs -f &
uavpos-pocolibs -f &
rotorcraft-pocolibs -f &
maneuver-pocolibs -f &
nhfc-pocolibs -f &
