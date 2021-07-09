###############################################################################
#
# Setup enclave with supplied credentials
#
###############################################################################

FROM wh-imaging-cdp-docker-local.artifactory.swg-devops.com/ubi8/whpa-cdp-ubi8-base-hardening:8.4-20210701123440 as enclave

ARG USERNAME
ARG PASSWORD

COPY build/dist/*.whl /tmp/files
COPY project.yaml /tmp/files/project.yaml

RUN set -eu; \
    ${WHPA_CDP_REPO_BASE}/scripts/generate-repo-credentials.sh


###############################################################################
#
# CDP Service
#
###############################################################################

FROM wh-imaging-cdp-docker-local.artifactory.swg-devops.com/ubi8/whpa-cdp-ubi8-base-python-38x:3.8-20210707124233

ARG USERNAME
ARG PASSWORD

USER root

ENV PYWEBWRAPPER_PROJECT_ROOT '/opt/ibm/py-service-wrapper'
ENV PYWEBWRAPPER_PROJECT_FILE 'project.yaml'

RUN --mount=from=enclave,src=/tmp/files,dst=/tmp/files \
    set -eu; \
    export PATH="${PATH}:/tmp/files/repo/scripts" ;\
    export WHPA_CDP_REPO_BASE=/tmp/files/repo ;\
#
# Install py service wrapper and the project
#
    mkdir -v -p ${PYWEBWRAPPER_PROJECT_ROOT} ;\
    mkdir -v -p /etc/pip ;\
    cp -v ${WHPA_CDP_REPO_BASE}/gen/pip.conf /etc/pip/pip.conf ;\
    cp -v /tmp/files/${PYWEBWRAPPER_PROJECT_FILE} ${PYWEBWRAPPER_PROJECT_ROOT}/${PYWEBWRAPPER_PROJECT_FILE} ;\
    pip3 install py-web-wrapper==0.0.1; \
    pip3 install /tmp/files/*.whl; \
    rm -f /etc/pip/pip.conf ;\
#
# Validate image hardening using IBM CIS checks
#
    rm -rf /var/tmp/* ;\
    validate_hardening.sh /tmp/files/cis-hardening ;\
    rm -f /@System.solv

#
# Set default user
#
USER ${USER_UID}


CMD [ "python3", "-m", "webwrapper.server" ]