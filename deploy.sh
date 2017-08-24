#! /bin/bash

# check environment variables are set
: ${USERNAME:?"Environment variable needs setting"}
: ${EMAIL:?"Environment variable needs setting"}
: ${FULLNAME:?"Environment variable needs setting"}
: ${CHART_ENV_CONFIG_DIR:?"Environment variable needs setting"}
: ${PLATFORM_ENV:?"Environment variable needs setting"}
: ${HELM:?"Environment variable needs setting"}

set -e -x

$HELM upgrade init-user-${USERNAME} charts/init-user \
    -f ${CHART_ENV_CONFIG_DIR}/${PLATFORM_ENV}/init-user.yml \
    --set Username="$USERNAME" \
    --set Email="$EMAIL" \
    --set Fullname="$FULLNAME" \
    --install --wait

$HELM upgrade config-user-${USERNAME} charts/config-user \
    --namespace user-${USERNAME} \
    --set Username="$USERNAME" \
    --install --wait

$HELM upgrade ${USERNAME}-rstudio mojanalytics/rstudio \
    -f ${CHART_ENV_CONFIG_DIR}/${PLATFORM_ENV}/rstudio.yml \
    --set Username=${USERNAME} \
    --namespace user-${USERNAME} \
    --install
