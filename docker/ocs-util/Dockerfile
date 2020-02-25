FROM ocs:latest

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

USER ocs:ocs

WORKDIR /home/ocs/.jupyter
ENV JUPYTER_CONFIG_DIR /home/ocs/.jupyter
COPY jupyter_config.py /home/ocs/.jupyter

ENTRYPOINT ["jupyter", "notebook"]
CMD ["/home/ocs"]
