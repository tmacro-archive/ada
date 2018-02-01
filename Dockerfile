FROM tmacro/python:3

ENV MODE dev
ADD requirements.txt /tmp/requirements.txt
# RUN apk_add uwsgi nginx build-base libffi libffi-dev linux-headers python3-dev ca-certificates && pip install -v -r /tmp/requirements.txt
RUN apk_add uwsgi nginx ca-certificates zeromq py3-numpy \
			build-base \
			linux-headers \
			python3-dev \
			openssl-dev \
			file \
			uwsgi-python3 \
	&& pip install -v -r /tmp/requirements.txt

RUN mkdir /run/nginx
ADD ./s6 /etc
COPY ./nginx.conf /etc/nginx/conf.d/default.conf
ADD . /app