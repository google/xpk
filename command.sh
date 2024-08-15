export PROJECT=tpu-prod-env-multipod #<your_project_id>
export ZONE=us-central2-b #<zone>
gcloud config set project $PROJECT
gcloud config set compute/zone $ZONE

export CLUSTER_NAME=v4_demo #<your_cluster_name>
export NETWORK_NAME=${CLUSTER_NAME}-only-mtu9k
export NETWORK_FW_NAME=${NETWORK_NAME}-only-fw
export CLUSTER_ARGUMENTS="--network=${NETWORK_NAME} --subnetwork=${NETWORK_NAME}"
export TPU_TYPE=v4-128 #<your TPU Type>
export NUM_SLIECES=1 #<number of TPU node-pools you want to create>

python3 xpk.py workload list --cluster $CLUSTER_NAME --project $PROJECT --zone $ZONE

python3 xpk.py cluster create \
--default-pool-cpu-machine-type=n1-standard-32 \
--cluster ${CLUSTER_NAME} \
--tpu-type=${TPU_TYPE} \
--num-slices=${NUM_SLIECES} \
--custom-cluster-arguments="${CLUSTER_ARGUMENTS}" \
--on-demand

python3 xpk.py workload create \
--cluster ${CLUSTER_NAME} \
--workload hello-world-test \
--tpu-type=${TPU_TYPE} \
--num-slices=${NUM_SLIECES} \
--command "echo Hello World"


bash docker_build_dependency_image.sh MODE=stable DEVICE=tpu

bash docker_upload_runner.sh CLOUD_IMAGE_NAME=${USER}_runner

cd ../

export CLUSTER_NAME=v4-demo #<your_cluster_name>
export WORKLOAD_NAME=llam2-7b-tes8 #<your_workload_name>
export TPU_TYPE=v4-128 #<your TPU Type>
export NUM_SLIECES=1 #<number of TPU node-pools you want to use>
export LOCAL_IMAGE_NAME=gcr.io/tpu-prod-env-multipod/${USER}_runner
export OUTPUT_PATH=gs://v4-demo/


python3 xpk.py workload create \
--cluster ${CLUSTER_NAME} \
--workload ${WORKLOAD_NAME} \
--tpu-type=${TPU_TYPE} \
--num-slices=${NUM_SLIECES} \
--docker-image=${LOCAL_IMAGE_NAME} \
--command "\
   python MaxText/train.py MaxText/configs/base.yml\
   model_name=llama2-7b\
   base_output_directory=$OUTPUT_PATH\
   dataset_type=synthetic\
   tokenizer_path=assets/tokenizer.llama2\
   per_device_batch_size=16\
   enable_checkpointing=false\
   gcs_metrics=true\
   profiler=xplane\
   skip_first_n_steps_for_profiler=5\
   steps=10"


export WORKLOAD_NAME_TO_DELETE=llam2-7b-test

python3 xpk.py workload delete \
--workload ${WORKLOAD_NAME_TO_DELETE} \
--cluster ${CLUSTER_NAME}

python3 xpk.py workload list \
--cluster ${CLUSTER_NAME}
