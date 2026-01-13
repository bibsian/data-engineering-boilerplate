#!/bin/bash

createdb -U postgres earthquakes_dev &&
psql -U postgres -d earthquakes_prod -f /opt/program/tables.sql &&
    psql -U postgres -d earthquakes_dev -f /opt/program/tables.sql
    
