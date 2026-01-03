ENV_FILE=config.env
  #-f index_deployment.yaml --env-file $ENV_FILE \

docker compose \
  -f base.yaml --env-file $ENV_FILE \
  -f storage.yaml --env-file $ENV_FILE \
  -f metrik.yaml --env-file $ENV_FILE \
  -f vllm.yaml --env-file $ENV_FILE \
  -f ai.yaml --env-file $ENV_FILE \
  -f ai_db.yaml --env-file $ENV_FILE \
  -f prefect_instance.yaml --env-file $ENV_FILE \
  -f api.yaml --env-file $ENV_FILE \
  -f rag_ui.yaml --env-file $ENV_FILE \
  -f evaluation_instances.yaml --env-file $ENV_FILE \
  -f file_converter_instances.yaml --env-file $ENV_FILE \
  -f embedding_instances.yaml --env-file $ENV_FILE \
  -f rag_instances.yaml --env-file $ENV_FILE \
  -f rag_default_instances.yaml --env-file $ENV_FILE \
  up -d

