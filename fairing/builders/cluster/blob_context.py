import os
import uuid

from fairing import utils
from fairing.builders.cluster.context_source import ContextSourceInterface
from fairing.cloud import azure
from fairing.constants import constants
from fairing.kubernetes.manager import KubeManager, client


class BlobContextSource(ContextSourceInterface):
    def __init__(self, region=None, storage_account_name=None, group_name=None, container_name=None, namespace='default'):
        self.region = region or "east-us"
        # TODO ME note that the generated name is not necessarily unique due to truncation...
        self.storage_account_name = storage_account_name or f"{uuid.uuid4().hex[:24]}"
        self.container_name = container_name or "fairing-demo"

        self.manager = KubeManager()
        self.namespace = namespace
        self.group_name = group_name

    def prepare(self, context_filename):
        if self.group_name is None:
            self.group_name = azure.get_resource_group_name()
        self.uploaded_context_url = self.upload_context(context_filename)

    def upload_context(self, context_filename):
        azure_uploader = azure.AzureUploader()
        context_hash = utils.crc(context_filename)
        # TODO ME find out what's happening with the return value
        return azure_uploader.upload_to_container(
                    self.region,
                    self.storage_account_name,
                    self.container_name,
                    self.group_name,
                    blob_name='fairing_builds/' + context_hash,
                    file_to_upload=context_filename)

    def cleanup(self):
        pass

    def generate_pod_spec(self, image_name, push):
        args = ["--dockerfile=Dockerfile",
                          "--destination=" + image_name,
                          "--context=" + self.uploaded_context_url]
        if not push:
            args.append("--no-push")
        return client.V1PodSpec(
                containers=[client.V1Container(
                    name='kaniko',
                    image='gcr.io/kaniko-project/executor:v0.7.0',
                    args=["--dockerfile=Dockerfile",
                          "--destination=" + image_name,
                          "--context=" + self.uploaded_context_url],
                )],
                restart_policy='Never'
            )
