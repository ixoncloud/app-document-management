# Document Management App Cloud Function

Cloud Function which authorizes Object Storage operations for the Document Management app.

## Requirements

- Python 3.10 or higher (Functions are run in production with Python 3.10).
- [zip](https://infozip.sourceforge.net/Zip.html) for building a bundle.
- [curl](https://curl.se/) for deploying to IXON Cloud.
- [Docker](https://www.docker.com/) for setting up a DocumentDB for development

## Getting started

To get started, download this project as a ZIP, and extract it to your desired location.

To run the project, no additional commands are required, as this is automatically sets up your virtual environment and installs dependencies.

```sh
HTTP_SERVER_BIND="0.0.0.0" make run
```

## Deployment to IXON Cloud

The deployment of the Document Management App is handled mostly via Gitlab CI. After tagging a release,
run the manual `deploy` job. This job requires the `IXON_API_ACCESS_TOKEN_FILE` to be set to contain
an IXON API access token secret which can upload the cloud function to the IXON Sector 
Component Owner company (`4094-4607-2800-7692-6007`). Make sure to make this a `File` type environment variable,
since this is a secret.

## Other commands

Some other commands that may come in handy.

This commands sets up your virtual python environment without starting the ixoncdkingress.

```sh
make py-venv-dev
```

This commands cleans up your virtual python environment setup for this project.

```sh
make py-distclean
```
