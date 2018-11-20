FROM ubuntu:xenial

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    libudunits2-dev

WORKDIR /src/
COPY requirements.txt /src/
RUN pip3 install numpy
RUN pip3 install -r requirements.txt

COPY . .
    
RUN pip3 install .

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

#RUN rm -rf /src

ENTRYPOINT [ "frost" ]
