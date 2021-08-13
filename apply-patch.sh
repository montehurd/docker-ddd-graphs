#!/bin/bash

cd /usr/local/lib/python3.9/site-packages

curl -w "\n" -L https://phab.wmfusercontent.org/file/data/kk5xox74563cckhmxd5y/PHID-FILE-qgpafso6bubvf7zcwl4h/phab_url | git apply
