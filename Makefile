IMAGEID = $(shell eval docker images -aq malshare_pymalshare )
LOCAL_PKG_DIR := $(shell eval pwd)


build:
	docker build -t malshare_pymalshare -f docker/Dockerfile.upload_handler .
test:
	docker run --rm  malshare_pymalshare

buildtest:
	docker build -t malshare_pymalshare -f docker/Dockerfile.upload_handler .
	docker run  --rm  malshare_pymalshare 

run:
	docker build -t malshare_pymalshare -f docker/Dockerfile.upload_handler .
	docker run  -d malshare_pymalshare 



