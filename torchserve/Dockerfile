# syntax = docker/dockerfile:1.2

FROM continuumio/miniconda3:24.1.2-0

# install os dependencies
RUN mkdir -p /usr/share/man/man1
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
    ca-certificates \
    curl \
    vim \
    sudo \
    default-jre \
    git \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN conda install python=3.8.13 -y

# Evita timeout durante il download di torch: 20 min
ENV PIP_DEFAULT_TIMEOUT=1200

# install python dependencies
# torch 1.13 + cu117: wheel precompilato mmcv-full (evita build da sorgente, v. https://github.com/open-mmlab/mmcv/issues/2637)
# Su Mac ARM buildare con: docker build --platform linux/amd64 ... così pip trova il wheel manylinux x86_64
RUN pip install --default-timeout=1200 torch==1.13.0 torchvision==0.14.0 --extra-index-url https://download.pytorch.org/whl/cu117
RUN pip install --default-timeout=1200 --only-binary mmcv-full mmcv-full==1.7.0 -f https://download.openmmlab.com/mmcv/dist/cu117/torch1.13.0/index.html
RUN pip install mmdet==2.27.0
RUN pip install torchserve

# bugfix for xtcocoapi, an mmpose dependency
RUN git clone https://github.com/jin-s13/xtcocoapi.git
WORKDIR xtcocoapi
RUN pip install -r requirements.txt
RUN python setup.py install
WORKDIR /
RUN pip install mmpose==0.29.0
RUN pip install numpy==1.24.4  # solve numpy version compatibility

# prep torchserve
RUN mkdir -p /home/torchserve/model-store
RUN wget https://github.com/facebookresearch/AnimatedDrawings/releases/download/v0.0.1/drawn_humanoid_detector.mar -P /home/torchserve/model-store/
RUN wget https://github.com/facebookresearch/AnimatedDrawings/releases/download/v0.0.1/drawn_humanoid_pose_estimator.mar -P /home/torchserve/model-store/
COPY config.properties /home/torchserve/config.properties

# starting command
CMD /opt/conda/bin/torchserve --start --disable-token-auth --ts-config /home/torchserve/config.properties && sleep infinity
