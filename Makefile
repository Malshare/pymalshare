IMAGEID = $(shell eval docker images -aq malshare_pymalshare )
LOCAL_PKG_DIR := $(shell eval pwd)

build:
	docker build -t malshare_pymalshare -f docker/Dockerfile.upload_handler .
test:
	docker run --rm  malshare_pymalshare

build-generate-daily:
	docker build -t malshare-generate-daily -f docker/Docker.generate_daily .
run-generate-daily:
	docker run --rm --env-file .env -e OUTPUT_DIR='/daily' malshare-generate-daily

buildtest:
	docker build -t malshare_pymalshare -f docker/Dockerfile.upload_handler .
	docker run  --rm  malshare_pymalshare 

run:
	docker build -t malshare_pymalshare -f docker/Dockerfile.upload_handler .
	docker run  -d malshare_pymalshare 
