# Galaxy

This directory contains Terraform config files that work in tandem with [Galaxy](https://github.com/duolingo/infra-terraform-galaxy) to deploy the necessary infrastructure to AWS for the service. Checkout the Galaxy documentation for more information on how this works.

# Maintenance

## Updating Zendesk Password

To update the KMS secret payload for the Zendesk password, generate a new ciphertext using the following commands:

```bash
$ echo -n '<Zendesk password>' > plaintext-password
$ aws kms encrypt --key-id <Jeeves KMS key ID> --plaintext fileb://plaintext-password --encryption-context product=duolingo,service=jeeves,subservice=s3-worker,environment=<prod|dev> --output text --query CiphertextBlob
```
