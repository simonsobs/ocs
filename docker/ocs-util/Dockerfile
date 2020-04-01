FROM ocs:latest

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

USER ocs:ocs

ENV JUPYTER_CONFIG_DIR /home/ocs/.jupyter
COPY --chown=ocs:ocs dot_jupyter /home/ocs/.jupyter

ENTRYPOINT ["jupyter", "notebook"]
CMD ["/data"]
