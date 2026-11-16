# Disposable negative qualification fixture only. No deployment use.
FROM python:3.12-slim-trixie@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b AS python
FROM quay.io/coreos/etcd:v3.5.21@sha256:a3ccd299377af4b9968d8cbaaf9722fe354297f11908f74a846075e1e5f4ee89 AS etcd
FROM postgres:16.16@sha256:dd2bf3ce2dc83a81674cf7f217fcfd8a5009a4b325dda5b843bfee82a06cff6f
COPY --from=python /usr/local /usr/local
COPY --from=etcd /usr/local/bin/etcd /usr/local/bin/etcd
COPY --from=etcd /usr/local/bin/etcdctl /usr/local/bin/etcdctl
COPY inputs /inputs
COPY requirements.txt build-requirements.txt /inputs/
RUN python -m pip install --no-index --find-links=/inputs --require-hashes -r /inputs/build-requirements.txt \
 && python -m pip install --no-index --find-links=/inputs --require-hashes --no-build-isolation -r /inputs/requirements.txt \
 && python -m pip check \
 && rm -rf /inputs /root/.cache
ENTRYPOINT []
CMD ["sleep", "infinity"]
