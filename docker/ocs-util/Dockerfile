FROM ocs:latest

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

COPY setup_sotodlib.sh /tmp/setup_sotodlib.sh
RUN sh /tmp/setup_sotodlib.sh

USER ocs:ocs

ENV JUPYTER_CONFIG_DIR /home/ocs/.jupyter
COPY --chown=ocs:ocs dot_jupyter /home/ocs/.jupyter

ENV JUPYTER_PORT 8880
EXPOSE 8880/tcp

ENTRYPOINT ["jupyter", "lab"]
CMD ["/data"]
