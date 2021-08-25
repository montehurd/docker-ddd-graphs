# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.9.5-slim-buster

EXPOSE 5000

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE 1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED 1



# app.py and `ddd` use these
ENV CONDUIT_TOKEN "api-pkzahk74gg7tpnltwmhhok5xwt4i"
ENV CONDUIT_URL "http://docker-phabricator-wmf_phabricator_1:80/api/"
# ENV CONDUIT_TOKEN ""
# ENV CONDUIT_URL "https://phabricator.wikimedia.org/api/"



# Install pip requirements
ADD requirements.txt .
RUN python -m pip install -r requirements.txt

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y git && \
    apt-get install -y curl

WORKDIR /app

# Switching to a non-root user, please refer to https://aka.ms/vscode-docker-python-user-rights
# RUN useradd appuser && chown -R appuser /app
# USER appuser

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["gunicorn", "--reload", "--bind", "0.0.0.0:5000", "app:app"]
