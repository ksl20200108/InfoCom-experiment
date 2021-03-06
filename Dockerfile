FROM daocloud.io/library/python:3.6.3-stretch

# ADD . /run/
WORKDIR /run    # change the work directory to "run", if there is no such directory the docker will create one
# VOLUME /run

RUN pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple couchdb \
    && pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple ecdsa==0.13 \
    && pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple kademlia



CMD ["python3", "cli.py", "start"]
