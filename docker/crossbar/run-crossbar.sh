#!/bin/bash

CONFIG_DIR=/ocs/.crossbar
OCS_ADDRESS_ROOT=${OCS_ADDRESS_ROOT:-observatory}
OCS_CROSSBAR_REALM=${OCS_REALM:-test_realm}
OCS_CROSSBAR_PORT=${OCS_PORT:-8001}

# Did user mount in a config.json?
if [ -e $CONFIG_DIR/config.json ]; then
    echo Launching user-provided config.json
    CONFIG_FILE=$CONFIG_DIR/config.json
else
    pattern="
        s/{address_root}/${OCS_ADDRESS_ROOT}/g
        s/{realm}/${OCS_CROSSBAR_REALM}/g
        s/{port}/${OCS_CROSSBAR_PORT}/g
        "
    echo "Processing template with replacements:"
    echo "$pattern"
    echo

    CONFIG_FILE=$CONFIG_DIR/config-with-address.json
    sed "$pattern" \
        $CONFIG_DIR/config-with-address.json.template \
        > $CONFIG_FILE
fi

crossbar start --cbdir $CONFIG_DIR --config $CONFIG_FILE
