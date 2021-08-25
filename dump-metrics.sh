#!/bin/bash

# PHID-PROJ-ap4p45xtz2tkbmobjpso is from my local dockerized phabricator's Test-Project
# python3 /usr/local/lib/python3.9/site-packages/ddd/boardmetrics.py --project PHID-PROJ-ap4p45xtz2tkbmobjpso --db /app/metrics.db --cache-columns --dump=json > /app/metrics.json

# PHID-PROJ-4623b3ohfuknkil7xf5n is from phabricator.wikimedia.org's QTE-TestingOverview
# python3 /usr/local/lib/python3.9/site-packages/ddd/boardmetrics.py --project PHID-PROJ-4623b3ohfuknkil7xf5n --db /app/metrics.db --cache-columns --dump=json > /app/metrics.json