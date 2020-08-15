# InfoCom-experiment
the source code for the experiment

# Branches
There are two branches experiment 1 and experiment 2.

# How to start ?
Here are the command lines we use in Linux system (Ubuntu 20). Copy and paste these lines you can conduct the experiment within 20 minutes.
You need to install docker first.

git clone https://github.com/ksl20200108/8.3.git

cd 8.3

docker build -t net_check:1.0 .

docker pull hyperledger/fabric-couchdb

git checkout 4.5

docker-compose -f 1.yaml up -d

(wait for 5 seconds)

docker-compose -f 2.yaml up -d

docker-compose -f 3.yaml up -d

(wait for 16 minutes)……

vi data12.txt (you can visit through data12 to data21) to find complete results.

(copy all the results, open a word to copy them)

