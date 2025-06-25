#!/bin/bash

# Script to renew SSL certificates
# This should be run via cron job for automatic renewal

echo "### Renewing SSL certificates ..."

docker-compose run --rm --entrypoint "\
  certbot renew --webroot -w /var/www/certbot \
    --quiet" certbot

echo "### Reloading nginx ..."
docker-compose exec nginx nginx -s reload

echo "### SSL renewal completed" 