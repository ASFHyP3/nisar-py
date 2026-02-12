# TODO: confirm Dockerfile is correct for this project

FROM condaforge/mambaforge:latest

# For opencontainers label definitions, see:
#    https://github.com/opencontainers/image-spec/blob/master/annotations.md
# TODO: confirm:
LABEL org.opencontainers.image.title="nisar-py"
LABEL org.opencontainers.image.description="NISAR data transformations."
LABEL org.opencontainers.image.vendor="Alaska Satellite Facility"
LABEL org.opencontainers.image.authors="ASF Tools Team <UAF-asf-apd@alaska.edu>"
LABEL org.opencontainers.image.licenses="BSD-3-Clause"
LABEL org.opencontainers.image.url="https://github.com/ASFHyP3/nisar-py"
LABEL org.opencontainers.image.source="https://github.com/ASFHyP3/nisar-py"
# TODO: confirm:
LABEL org.opencontainers.image.documentation="https://nisar-docs.asf.alaska.edu"

# TODO: what are these for?
# Dynamic lables to define at build time via `docker build --label`
# LABEL org.opencontainers.image.created=""
# LABEL org.opencontainers.image.version=""
# LABEL org.opencontainers.image.revision=""

ARG DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=true

RUN apt-get update && apt-get install -y --no-install-recommends unzip vim && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ARG CONDA_UID=1000
ARG CONDA_GID=1000

RUN groupadd -g "${CONDA_GID}" --system conda && \
    useradd -l -u "${CONDA_UID}" -g "${CONDA_GID}" --system -d /home/conda -m  -s /bin/bash conda && \
    chown -R conda:conda /opt && \
    echo ". /opt/conda/etc/profile.d/conda.sh" >> /home/conda/.profile && \
    echo "conda activate base" >> /home/conda/.profile

USER ${CONDA_UID}
SHELL ["/bin/bash", "-l", "-c"]
WORKDIR /home/conda/

COPY --chown=${CONDA_UID}:${CONDA_GID} . /nisar-py/

RUN mamba env create -f /nisar-py/environment.yml && \
    conda clean -afy && \
    conda activate nisar-py && \
    sed -i 's/conda activate base/conda activate nisar-py/g' /home/conda/.profile && \
    python -m pip install --no-cache-dir /nisar-py

ENTRYPOINT ["/nisar-py/src/nisar_py/etc/entrypoint.sh"]
CMD ["-h"]
