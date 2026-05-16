# Phase 3 Plan

Phase 3 will add an Arduino-based field sensor node that can collect simple
ground readings at a high-confidence zone and sync them back to the dashboard.

## Goal

Upgrade a zone from:

```text
satellite-predicted
```

to:

```text
ground-confirmed
```

when field readings are collected.

## Planned Hardware

```text
Arduino Uno
HMC5883L or compatible magnetometer
Neo-6M GPS module
soil resistivity probes
USB cable
breadboard and jumper wires
portable power source
```

## Planned Data Flow

```text
Arduino sensors
   -> serial output over USB
   -> Python serial listener
   -> SQLite sensor_readings table
   -> Flask dashboard badge/status update
```

## Planned Sensor Readings

```text
latitude
longitude
magnetic field strength
soil resistivity estimate
timestamp
```

## Important Demo Framing

The Arduino node will not prove mineral presence. It provides preliminary field
evidence that can support or challenge the satellite prediction.

Correct explanation:

```text
The model prioritizes zones for field investigation.
The sensor node records basic ground observations at a selected zone.
The dashboard marks that zone as ground-confirmed when readings are available.
```
