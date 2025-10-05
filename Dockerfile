FROM python:3.11
ENV APPDIR=/home/app/webapp
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PGSERVICEFILE=$APPDIR/.pg_service.conf
ENV PGPASSFILE=$APPDIR/.pgpass
RUN mkdir -p $APPDIR
RUN mkdir -p $APPDIR/db
RUN mkdir -p $APPDIR/logs
# Regular production users
RUN groupadd -g 7887 app
RUN useradd -m -u 7887 -g app app
WORKDIR $APPDIR
COPY smb_to_kodi/ $APPDIR
RUN python -c 'import uuid; print(uuid.uuid4())' | base64 > $APPDIR/secret.key
COPY requirements.txt /tmp/requirements.txt
COPY docker_entrypoint.sh /docker_entrypoint.sh
COPY .pgpass_prod $APPDIR/.pgpass
COPY .pg_service_prod.conf $APPDIR/.pg_service.conf

RUN pip install --upgrade pip
RUN pip install -r /tmp/requirements.txt
RUN chmod +x /docker_entrypoint.sh
RUN chown -R app:app $APPDIR
RUN chmod 400 $APPDIR/.pg*
VOLUME $APPDIR/db
VOLUME $APPDIR/logs
EXPOSE 8001
USER app
CMD /docker_entrypoint.sh
