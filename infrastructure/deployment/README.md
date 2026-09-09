# Deployment

This directory contains deployment-related configuration for the
Customer Data Platform.

## Application components

The integrated application consists of:

- React frontend
- Django REST API
- PostgreSQL database
- Redis
- Celery worker

## Development

The application can be run locally without Docker.

Required services:

- PostgreSQL
- Redis when background processing is enabled

## Production

Production deployment must:

- use environment variables for secrets
- disable Django DEBUG mode
- restrict ALLOWED_HOSTS
- restrict CORS origins
- use HTTPS
- use secure cookies
- keep database credentials outside source control
- run background processing through Celery