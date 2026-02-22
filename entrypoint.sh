#!/bin/sh

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the provided command
echo "Starting application..."
exec "$@"
