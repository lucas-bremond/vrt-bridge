# MIT License

ARG PYTHON_BASE_VERSION="3.11"
ARG PIP_VERSION="24.0"

ARG MAINTAINER="lucas.bremond@gmail.com"

# Build environment

FROM python:${PYTHON_BASE_VERSION}-slim as build-env

## Configure working directory

WORKDIR /workspace

## Install utilities

RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

## Update pip

ARG PIP_VERSION
RUN pip install --upgrade pip~=${PIP_VERSION}

## Install dependencies

COPY ./app/requirements.txt /workspace/app/requirements.txt
RUN pip install -r app/requirements.txt

## Install app

COPY . .

RUN cd app && \
    pip install .

# Production image

FROM python:${PYTHON_BASE_VERSION}-slim as prod

ARG MAINTAINER
LABEL maintainer=${MAINTAINER}

## Install libraries

COPY --from=build-env /usr/local/bin /usr/local/bin

ARG PYTHON_BASE_VERSION
COPY --from=build-env /usr/local/lib/python${PYTHON_BASE_VERSION}/site-packages /usr/local/lib/python${PYTHON_BASE_VERSION}/site-packages

## Add license

COPY LICENSE .

## Configure entrypoint

ENTRYPOINT [ "vrt-bridge" ]
CMD [ "--help" ]

# Development image for CI/CD

FROM prod as dev-ci

WORKDIR /workspace

## Install utilities

RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

## Install dependencies

COPY ./app/requirements-dev.txt /workspace/app/requirements-dev.txt
RUN pip install -r app/requirements-dev.txt

# Development image for humans

FROM mcr.microsoft.com/vscode/devcontainers/python:${PYTHON_BASE_VERSION} as dev

## Install utilities

RUN apt-get update && \
    apt-get install -y cmake && \
    rm -rf /var/lib/apt/lists/*

## Deal with filesystem ownership

ARG USERNAME="vscode"
ARG USER_UID="1000"
ARG USER_GID=${USER_UID}
RUN getent group ${USER_GID} || groupmod --gid ${USER_GID} ${USERNAME} && \
    usermod --uid ${USER_UID} --gid ${USER_GID} ${USERNAME}

USER ${USERNAME}

## Install static dependencies

ARG PIP_VERSION
RUN git clone https://github.com/bhilburn/powerlevel9k.git /home/${USERNAME}/.oh-my-zsh/custom/themes/powerlevel9k && \
    git clone https://github.com/zsh-users/zsh-autosuggestions /home/${USERNAME}/.oh-my-zsh/custom/plugins/zsh-autosuggestions && \
    git clone https://github.com/zsh-users/zsh-syntax-highlighting.git /home/${USERNAME}/.oh-my-zsh/custom/plugins/zsh-syntax-highlighting && \
    mkdir -p /home/${USERNAME}/.vscode-server/extensions /home/${USERNAME}/.vscode-server-insiders/extensions && \
    pipx uninstall-all && \
    pip install --upgrade pip~=${PIP_VERSION} && \
    pip install --user ipython

## Configure environment

COPY --chown=${USER_UID}:${USER_GID} ./docker/.zshrc /home/${USERNAME}/.zshrc

ENV PATH="/home/${USERNAME}/.local/bin:${PATH}"

## Install dependencies

COPY --chown=${USER_UID}:${USER_GID} app/requirements.txt app/requirements-dev.txt /home/${USERNAME}/tmp/

RUN pip --disable-pip-version-check --no-cache-dir install --user \
    -r /home/${USERNAME}/tmp/requirements-dev.txt \
    -r /home/${USERNAME}/tmp/requirements.txt && \
    rm -rf /home/${USERNAME}/tmp/
