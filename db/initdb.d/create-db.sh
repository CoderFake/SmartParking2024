#!/bin/bash

set -e

psql -v ON_ERROR_STOP=1 --username postgres <<-EOSQL
	CREATE DATABASE ${DB_NAME} ENCODING = 'UTF-8';
EOSQL