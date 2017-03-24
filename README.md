# docker

* cuda:8.0-cudnn5-devel
  * cuda-base
    * cudo-python
      * cuda-tensorflow
        * cuda-caffe
          * cuda-theano
            * cuda-keras  
              * cuda-torch
                * cuda-utils
                  * cuda-jupyter
                    * cuda-sshd
                      * cuda-gym
                      * chickbot
                      * cuda-betago


* cuda:8.0-cudnn5-devel
  * cuda-base
    * cuda-neon

* cuda:8.0-cudnn5-devel-ubuntu16.04
  * cuda-base3
      * cuda-python3
        * cuda-jupyter3
          * cuda-sshd3


* cuda:8.0-cudnn5-devel-ubuntu16.04
  * paintchainer
  * pix2pix


* java:8
  * syntaxnet
    * displacy

* ubuntu:14.04
  * flask
    * webapp
  * gnugo
  * pyspider


* docker-compose.yml
  * wordpress
    * wp_solarcity
    * wp_deeplearn
  * wp_solarsuna
  * mariadb
    * db_solarcity
    * db_deeplearn
    * db_solarsuna


# Build
<code>
sudo nvidia-docker build -t sibuzu/cuda-base3 -f Dockerfile.cuda-base3 .
sudo nvidia-docker build -t sibuzu/cuda-python3 -f Dockerfile.cuda-python3 .
sudo nvidia-docker build -t sibuzu/cuda-jupyter3 -f Dockerfile.cuda-jupyter3 .
sudo nvidia-docker build -t sibuzu/cuda-sshd3 -f Dockerfile.cuda-sshd3 .
</code>

# RUN
<code>
sudo nvidia-docker run -p 3888:8888 -p 3222:22 -v /dvol:/dvol --name sshd3 -d sibuzu/cuda-sshd3
</code>

