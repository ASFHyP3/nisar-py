FROM mambaorg/micromamba:latest

WORKDIR /home/mambauser

COPY --chown=$MAMBA_USER:$MAMBA_USER . /nisar-py/

RUN micromamba install -y -n base -f /nisar-py/environment.yml && \
    micromamba install -y -n base git && \
    micromamba clean --all --yes

ARG MAMBA_DOCKERFILE_ACTIVATE=1
RUN python -m pip install -e /nisar-py/

ENTRYPOINT ["/usr/local/bin/_entrypoint.sh", "python", "-m", "nisar_py.harmony_service"]
