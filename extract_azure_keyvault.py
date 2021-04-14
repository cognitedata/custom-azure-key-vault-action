import argparse
import os
import shlex
from pathlib import Path
from typing import Dict

from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient


def init_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch", type=str, default="test", help="The current branch")
    parser.add_argument("--root", type=str, help="parameters directory")
    return parser


def _load_config_file(root: str, branch: str, environ: dict):
    with open(f"{root}/{branch}.cfg", "r") as fp:
        for line in fp:
            line = line.strip()
            if not len(line) or line[0] == "#":
                continue

            name, value = line.split("=", 2)
            environ[name] = value


def _load_azure_env(environ: dict):
    assert "AZURE_TENANT_ID" in environ and "AZURE_CLIENT_ID" in environ, (
        "The configuration files have to contain "
        "the AZURE_TENANT_ID and AZURE_CLIENT_ID"
    )
    assert (
        "AZURE_CLIENT_SECRET" in os.environ
    ), "AZURE_CLIENT_SECRET have to be set as an environmental variable"

    print(environ["AZURE_TENANT_ID"])
    print(environ["AZURE_CLIENT_ID"])
    print(os.environ["AZURE_CLIENT_SECRET"])

    credential = ClientSecretCredential(
        tenant_id=environ["AZURE_TENANT_ID"],
        client_id=environ["AZURE_CLIENT_ID"],
        client_secret=os.environ["AZURE_CLIENT_SECRET"],
    )
    keyVaultName = environ["AZURE_VAULT_NAME"]
    KVUri = f"https://{keyVaultName}.vault.azure.net"
    print(f"Extracting secrets from {KVUri}")
    client = SecretClient(vault_url=KVUri, credential=credential)
    secrets_to_mask = []
    for secret in client.list_properties_of_secrets():
        name = secret.name
        value = client.get_secret(name)
        name = name.replace("-", "_")
        environ[name] = shlex.quote(value.value)
        secrets_to_mask.append(environ[name])
    return list(set(secrets_to_mask))


if __name__ == "__main__":
    parser = init_parser()
    p = parser.parse_args()
    vars: Dict[str, str] = {}
    _load_config_file(p.root, p.branch, vars)
    # _test_env()
    secrets_to_mask = _load_azure_env(vars)
    masked = set()
    export = "set" if "nt" in os.name else "export"

    print(f'write to {os.environ["GITHUB_ENV"]}')
    with open(os.environ["GITHUB_ENV"], "a+") as fp:
        for key in vars:
            if vars[key] in secrets_to_mask:
                print(f"::add-mask::{vars[key]}")
            fp.write(f"{key}={vars[key]}\n")
            print(f"Key {key} Length of secret: {len(vars[key])}")

